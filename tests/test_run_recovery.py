from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor

import pytest

from app.db import SessionLocal, engine
from app.models import AgentRun, AgentRunAttempt
from app.run_state import (
    InvalidRunTransition,
    append_transition,
    claim_next_run,
    finish_failure_or_requeue,
    finish_success,
    heartbeat,
    mark_external_starting,
    mark_running,
    recover_expired,
    request_cancellation,
    set_hermes_run,
    utcnow,
)


def unique_headers(auth_headers, value):
    return {
        **auth_headers,
        "X-Correlation-ID": value,
        "Idempotency-Key": value,
    }


def create_accepted_run(client, auth_headers, suffix="runtime"):
    commitment = client.post(
        "/v1/commitments",
        headers=unique_headers(auth_headers, f"{suffix}-commitment"),
        json={
            "title": "PMA Runtime恢复测试",
            "proposed_role": "DROLE-01",
            "objective": "只生成候选产出",
            "acceptance": {"human": True},
            "dependencies": [],
            "context": {"synthetic": True},
        },
    ).json()
    accepted = client.post(
        f"/v1/commitments/{commitment['id']}/transition",
        headers=unique_headers(auth_headers, f"{suffix}-accept"),
        json={"status": "accepted", "reason": "test"},
    )
    assert accepted.status_code == 200
    run = client.post(
        "/v1/runs",
        headers=unique_headers(auth_headers, f"{suffix}-run"),
        json={
            "commitment_id": commitment["id"],
            "role_id": "DROLE-01",
            "input": "生成候选表达",
            "context_version": 1,
        },
    )
    assert run.status_code == 202
    return run.json()


def test_attempt_history_timeline_and_stale_fencing(client, auth_headers):
    run = create_accepted_run(client, auth_headers, "attempt")
    with SessionLocal.begin() as db:
        claim = claim_next_run(db, "worker-a", lease_seconds=30)
        assert claim and claim.run_id == run["id"]
        assert heartbeat(db, claim, lease_seconds=30)
        mark_running(db, claim)
    details = client.get(f"/v1/runs/{run['id']}", headers=auth_headers).json()
    assert details["status"] == "running"
    assert details["current_attempt"]["worker_id"] == "worker-a"
    with SessionLocal.begin() as db:
        attempt = db.get(AgentRunAttempt, claim.attempt_id)
        attempt.lease_until = utcnow() - timedelta(seconds=1)
    with SessionLocal.begin() as db:
        assert heartbeat(db, claim, lease_seconds=30) is False
    with SessionLocal.begin() as db:
        result = recover_expired(db, max_attempts=2)
    assert result == {"requeued": 1, "unknown": 0, "failed": 0}
    with SessionLocal.begin() as db:
        second = claim_next_run(db, "worker-b", lease_seconds=30)
        assert second and second.attempt_id != claim.attempt_id
        mark_running(db, second)
        finish_success(db, second, {"candidate_status": "submitted"})
    attempts = client.get(f"/v1/runs/{run['id']}/attempts", headers=auth_headers).json()
    timeline = client.get(f"/v1/runs/{run['id']}/timeline", headers=auth_headers).json()
    assert all("lease_token" not in item for item in attempts)
    assert "lease_token" not in client.get(f"/v1/runs/{run['id']}", headers=auth_headers).json()["current_attempt"]
    assert [item["status"] for item in attempts] == ["lost", "succeeded"]
    assert [item["to_status"] for item in timeline] == [
        "queued", "accepted", "running", "queued", "accepted", "running", "evidence_accepted",
    ]


def test_targeted_worker_claims_only_the_selected_run(client, auth_headers):
    first = create_accepted_run(client, auth_headers, "target-first")
    selected = create_accepted_run(client, auth_headers, "target-selected")
    with SessionLocal.begin() as db:
        claim = claim_next_run(db, "drill-victim", lease_seconds=30, run_id=selected["id"])
        assert claim and claim.run_id == selected["id"]
        untouched = db.get(AgentRun, first["id"])
        assert untouched.status == "queued"


def test_private_batch_worker_claims_only_matching_input_prefix(client, auth_headers):
    selected = create_accepted_run(client, auth_headers, "private-batch-selected")
    other = create_accepted_run(client, auth_headers, "private-batch-other")
    with SessionLocal.begin() as db:
        db.get(AgentRun, selected["id"]).input_text = "RELIABILITY-BATCH-123 item=1"
        db.get(AgentRun, other["id"]).input_text = "UNRELATED item=1"
    with SessionLocal.begin() as db:
        claim = claim_next_run(
            db,
            "batch-worker",
            lease_seconds=30,
            input_prefix="RELIABILITY-BATCH-123",
        )
        assert claim and claim.run_id == selected["id"]
        assert db.get(AgentRun, other["id"]).status == "queued"


def test_targeted_recovery_does_not_touch_other_expired_runs(client, auth_headers):
    selected = create_accepted_run(client, auth_headers, "recover-selected")
    other = create_accepted_run(client, auth_headers, "recover-other")
    with SessionLocal.begin() as db:
        selected_claim = claim_next_run(db, "worker-a", lease_seconds=30, run_id=selected["id"])
        other_claim = claim_next_run(db, "worker-b", lease_seconds=30, run_id=other["id"])
        mark_running(db, selected_claim)
        mark_running(db, other_claim)
        db.get(AgentRunAttempt, selected_claim.attempt_id).lease_until = utcnow() - timedelta(seconds=1)
        db.get(AgentRunAttempt, other_claim.attempt_id).lease_until = utcnow() - timedelta(seconds=1)
    with SessionLocal.begin() as db:
        result = recover_expired(db, max_attempts=2, run_id=selected["id"])
        assert result == {"requeued": 1, "unknown": 0, "failed": 0}
        assert db.get(AgentRun, selected["id"]).status == "queued"
        assert db.get(AgentRun, other["id"]).status == "running"


def test_expired_external_attempt_becomes_unknown_without_retry(client, auth_headers):
    run = create_accepted_run(client, auth_headers, "unknown")
    with SessionLocal.begin() as db:
        claim = claim_next_run(db, "worker-a", lease_seconds=30)
        mark_running(db, claim)
        set_hermes_run(db, claim, "hermes-external-001")
        db.get(AgentRunAttempt, claim.attempt_id).lease_until = utcnow() - timedelta(seconds=1)
    with SessionLocal.begin() as db:
        result = recover_expired(db, max_attempts=2)
    assert result == {"requeued": 0, "unknown": 1, "failed": 0}
    details = client.get(f"/v1/runs/{run['id']}", headers=auth_headers).json()
    assert details["status"] == "unknown"
    assert details["current_attempt"]["retryability"] == "unsafe"


def test_expired_external_dispatch_without_run_id_is_unknown(client, auth_headers):
    run = create_accepted_run(client, auth_headers, "dispatch-unknown")
    with SessionLocal.begin() as db:
        claim = claim_next_run(db, "worker-a", lease_seconds=30)
        mark_running(db, claim)
        mark_external_starting(db, claim)
        attempt = db.get(AgentRunAttempt, claim.attempt_id)
        assert attempt.hermes_run_id is None
        attempt.lease_until = utcnow() - timedelta(seconds=1)
    with SessionLocal.begin() as db:
        result = recover_expired(db, max_attempts=2)
    assert result == {"requeued": 0, "unknown": 1, "failed": 0}
    details = client.get(f"/v1/runs/{run['id']}", headers=auth_headers).json()
    assert details["status"] == "unknown"
    assert details["current_attempt"]["failure_class"] == "lease_expired_after_external_dispatch"


def test_queued_cancel_is_terminal_and_idempotent(client, auth_headers):
    run = create_accepted_run(client, auth_headers, "cancel")
    headers = unique_headers(auth_headers, "cancel-request")
    first = client.post(f"/v1/runs/{run['id']}/cancel", headers=headers)
    second = client.post(f"/v1/runs/{run['id']}/cancel", headers=headers)
    assert first.status_code == second.status_code == 200
    assert first.json()["status"] == second.json()["status"] == "cancelled"
    with SessionLocal.begin() as db:
        assert claim_next_run(db, "worker-a", lease_seconds=30) is None


def test_illegal_run_transition_is_rejected(client, auth_headers):
    run = create_accepted_run(client, auth_headers, "illegal")
    with SessionLocal.begin() as db:
        item = db.get(AgentRun, run["id"])
        with pytest.raises(InvalidRunTransition):
            append_transition(db, item, "evidence_accepted", reason="skip worker", actor="test")


def test_running_cancel_waits_for_external_confirmation(client, auth_headers):
    run = create_accepted_run(client, auth_headers, "running-cancel")
    with SessionLocal.begin() as db:
        claim = claim_next_run(db, "worker-a", lease_seconds=30)
        mark_running(db, claim)
    response = client.post(
        f"/v1/runs/{run['id']}/cancel",
        headers=unique_headers(auth_headers, "running-cancel-request"),
    )
    assert response.status_code == 200
    assert response.json()["status"] == "running"
    assert response.json()["cancellation_requested_at"] is not None


def test_explicit_safe_failure_retries_once_then_stops(client, auth_headers):
    run = create_accepted_run(client, auth_headers, "retry")
    with SessionLocal.begin() as db:
        first = claim_next_run(db, "worker-a", lease_seconds=30)
        mark_running(db, first)
        assert finish_failure_or_requeue(
            db,
            first,
            failure={"retryability": "safe"},
            failure_class="hermes_capacity",
            retryability="safe",
            max_attempts=2,
        ) is True
    with SessionLocal.begin() as db:
        second = claim_next_run(db, "worker-b", lease_seconds=30)
        mark_running(db, second)
        assert finish_failure_or_requeue(
            db,
            second,
            failure={"retryability": "safe"},
            failure_class="hermes_capacity",
            retryability="safe",
            max_attempts=2,
        ) is False
    details = client.get(f"/v1/runs/{run['id']}", headers=auth_headers).json()
    assert details["status"] == "failed"
    attempts = client.get(f"/v1/runs/{run['id']}/attempts", headers=auth_headers).json()
    assert [attempt["attempt_no"] for attempt in attempts] == [1, 2]


@pytest.mark.skipif(engine.dialect.name != "postgresql", reason="SKIP LOCKED requires PostgreSQL")
def test_two_postgres_workers_claim_only_once(client, auth_headers):
    run = create_accepted_run(client, auth_headers, "postgres-claim")

    def claim(worker_id):
        with SessionLocal.begin() as db:
            result = claim_next_run(db, worker_id, lease_seconds=30)
            return result.run_id if result else None

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(claim, ("worker-a", "worker-b")))
    assert results.count(run["id"]) == 1


@pytest.mark.skipif(engine.dialect.name != "postgresql", reason="row-lock race requires PostgreSQL")
def test_cancellation_and_known_completion_race_keeps_one_terminal_result(client, auth_headers):
    run = create_accepted_run(client, auth_headers, "cancel-complete-race")
    with SessionLocal.begin() as db:
        claim = claim_next_run(db, "race-worker", lease_seconds=30)
        mark_running(db, claim)

    def complete():
        with SessionLocal.begin() as db:
            finish_success(db, claim, {"result": "Hermes completed"})

    def cancel():
        with SessionLocal.begin() as db:
            item = db.get(AgentRun, run["id"], with_for_update=True)
            request_cancellation(db, item, "race-operator")

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(complete), pool.submit(cancel)]
        for future in futures:
            future.result()

    details = client.get(f"/v1/runs/{run['id']}", headers=auth_headers).json()
    attempts = client.get(f"/v1/runs/{run['id']}/attempts", headers=auth_headers).json()
    assert details["status"] == "evidence_accepted"
    assert len(attempts) == 1 and attempts[0]["status"] == "succeeded"
