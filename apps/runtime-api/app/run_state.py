"""Transactional Agent Runtime state transitions shared by API and Worker."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import AgentRun, AgentRunAttempt, AgentRunTransition, Commitment, Outbox


TERMINAL_RUN_STATUSES = {"evidence_accepted", "failed", "cancelled", "unknown"}
RUN_TRANSITIONS = {
    "queued": {"accepted", "cancelled"},
    "accepted": {"queued", "running", "cancelled", "failed", "unknown"},
    "running": {"queued", "evidence_accepted", "failed", "cancelled", "unknown"},
}


class InvalidRunTransition(ValueError):
    pass


class StaleLease(RuntimeError):
    pass


@dataclass(frozen=True)
class AttemptClaim:
    run_id: str
    attempt_id: str
    lease_token: str


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _hash(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()


def _sync_marketing_case(db: Session, run: AgentRun) -> None:
    # Local import keeps the generic runtime state machine independent from the bounded demo module.
    from .marketing_case import sync_case_after_run_terminal

    sync_case_after_run_terminal(db, run)


def append_transition(
    db: Session,
    run: AgentRun,
    to_status: str,
    *,
    reason: str,
    actor: str,
    attempt_id: str | None = None,
    allow_same: bool = False,
) -> AgentRunTransition:
    from_status = run.status
    if from_status != to_status:
        if to_status not in RUN_TRANSITIONS.get(from_status, set()):
            raise InvalidRunTransition(f"非法Run状态迁移：{from_status} -> {to_status}")
        run.status = to_status
        run.version += 1
        if to_status == "running" and run.started_at is None:
            run.started_at = utcnow()
        if to_status in TERMINAL_RUN_STATUSES:
            run.completed_at = utcnow()
    elif not allow_same:
        raise InvalidRunTransition(f"Run已经处于{to_status}")
    run.transition_seq += 1
    event = AgentRunTransition(
        run_id=run.id,
        attempt_id=attempt_id,
        from_status=from_status,
        to_status=to_status,
        reason=reason[:240],
        actor=actor[:160],
        correlation_id=run.correlation_id,
        sequence_no=run.transition_seq,
        created_at=utcnow(),
    )
    db.add(event)
    # 时间线是审计证据；禁用autoflush时也要固化调用顺序，避免同事务事件被UUID二次排序。
    db.flush()
    return event


def claim_next_run(
    db: Session,
    worker_id: str,
    lease_seconds: int,
    *,
    run_id: str | None = None,
    input_prefix: str | None = None,
) -> AttemptClaim | None:
    stmt = select(AgentRun).where(AgentRun.status == "queued")
    if run_id:
        stmt = stmt.where(AgentRun.id == run_id)
    if input_prefix:
        stmt = stmt.where(AgentRun.input_text.startswith(input_prefix))
    stmt = stmt.order_by(AgentRun.created_at).limit(1)
    if db.bind and db.bind.dialect.name == "postgresql":
        stmt = stmt.with_for_update(skip_locked=True)
    run = db.scalar(stmt)
    if not run:
        return None
    attempt_no = int(db.scalar(select(func.count()).select_from(AgentRunAttempt).where(AgentRunAttempt.run_id == run.id)) or 0) + 1
    now = utcnow()
    token = uuid.uuid4().hex
    attempt = AgentRunAttempt(
        run_id=run.id,
        attempt_no=attempt_no,
        status="claimed",
        worker_id=worker_id,
        lease_token=token,
        lease_until=now + timedelta(seconds=lease_seconds),
        heartbeat_at=now,
        retryability="conditional",
    )
    db.add(attempt)
    db.flush()
    run.current_attempt_id = attempt.id
    append_transition(db, run, "accepted", reason="worker claimed queued run", actor=worker_id, attempt_id=attempt.id)
    # SessionLocal关闭了autoflush；同一事务中的heartbeat/mark_running必须立即看到fencing字段。
    db.flush()
    return AttemptClaim(run.id, attempt.id, token)


def _locked_attempt(db: Session, claim: AttemptClaim) -> tuple[AgentRun, AgentRunAttempt]:
    run_stmt = select(AgentRun).where(
        AgentRun.id == claim.run_id,
        AgentRun.current_attempt_id == claim.attempt_id,
    )
    attempt_stmt = select(AgentRunAttempt).where(
        AgentRunAttempt.id == claim.attempt_id,
        AgentRunAttempt.run_id == claim.run_id,
        AgentRunAttempt.lease_token == claim.lease_token,
        AgentRunAttempt.lease_until >= utcnow(),
    )
    if db.bind and db.bind.dialect.name == "postgresql":
        run_stmt = run_stmt.with_for_update()
        attempt_stmt = attempt_stmt.with_for_update()
    run = db.scalar(run_stmt)
    attempt = db.scalar(attempt_stmt)
    if not run or not attempt:
        raise StaleLease("Attempt lease已经失效")
    return run, attempt


def heartbeat(db: Session, claim: AttemptClaim, lease_seconds: int) -> bool:
    try:
        run, attempt = _locked_attempt(db, claim)
    except StaleLease:
        return False
    if run.status not in {"accepted", "running"} or attempt.status not in {"claimed", "running", "external_starting"}:
        return False
    now = utcnow()
    attempt.heartbeat_at = now
    attempt.lease_until = now + timedelta(seconds=lease_seconds)
    return True


def mark_running(db: Session, claim: AttemptClaim) -> None:
    run, attempt = _locked_attempt(db, claim)
    attempt.status = "running"
    attempt.started_at = attempt.started_at or utcnow()
    append_transition(db, run, "running", reason="worker started attempt", actor=attempt.worker_id, attempt_id=attempt.id)


def mark_external_starting(db: Session, claim: AttemptClaim) -> None:
    """Persist the point after which a missing Hermes ID is no longer safe to retry."""
    _, attempt = _locked_attempt(db, claim)
    attempt.status = "external_starting"


def set_hermes_run(db: Session, claim: AttemptClaim, hermes_run_id: str) -> None:
    run, attempt = _locked_attempt(db, claim)
    attempt.status = "running"
    attempt.hermes_run_id = hermes_run_id
    run.hermes_run_id = hermes_run_id


def finish_success(db: Session, claim: AttemptClaim, output: dict) -> None:
    run, attempt = _locked_attempt(db, claim)
    attempt.status = "succeeded"
    attempt.output = output
    attempt.retryability = "safe"
    attempt.completed_at = utcnow()
    run.output = output
    run.failure = {}
    append_transition(db, run, "evidence_accepted", reason="attempt completed with accepted evidence", actor=attempt.worker_id, attempt_id=attempt.id)
    commitment = db.get(Commitment, run.commitment_id)
    if commitment and commitment.status in {"accepted", "active"}:
        commitment.status = "submitted"
        commitment.version += 1
        commitment.content_hash = _hash({"run_id": run.id, "status": "submitted"})
    _sync_marketing_case(db, run)


def finish_terminal(
    db: Session,
    claim: AttemptClaim,
    status: str,
    *,
    failure: dict,
    failure_class: str,
    retryability: str,
) -> None:
    if status not in {"failed", "cancelled", "unknown"}:
        raise ValueError(f"不支持的终态：{status}")
    run, attempt = _locked_attempt(db, claim)
    attempt.status = status
    attempt.failure = failure
    attempt.failure_class = failure_class
    attempt.retryability = retryability
    attempt.completed_at = utcnow()
    run.failure = failure
    append_transition(db, run, status, reason=failure_class, actor=attempt.worker_id, attempt_id=attempt.id)
    if status == "unknown":
        db.add(Outbox(
            event_type="manual.reconciliation.required",
            aggregate_type="run",
            aggregate_id=run.id,
            payload={"run_id": run.id, "attempt_id": attempt.id, "reason": failure_class},
        ))
    _sync_marketing_case(db, run)


def finish_failure_or_requeue(
    db: Session,
    claim: AttemptClaim,
    *,
    failure: dict,
    failure_class: str,
    retryability: str,
    max_attempts: int,
) -> bool:
    """Persist an explicit Hermes failure and requeue only when it is declared safe."""
    run, attempt = _locked_attempt(db, claim)
    attempt.status = "failed"
    attempt.failure = failure
    attempt.failure_class = failure_class
    attempt.retryability = retryability
    attempt.completed_at = utcnow()
    run.failure = failure
    if retryability == "safe" and attempt.attempt_no < max_attempts:
        append_transition(
            db,
            run,
            "queued",
            reason=f"safe retry after {failure_class}",
            actor=attempt.worker_id,
            attempt_id=attempt.id,
        )
        run.current_attempt_id = None
        return True
    append_transition(db, run, "failed", reason=failure_class, actor=attempt.worker_id, attempt_id=attempt.id)
    _sync_marketing_case(db, run)
    return False


def request_cancellation(db: Session, run: AgentRun, actor: str) -> None:
    if run.status in TERMINAL_RUN_STATUSES:
        return
    run.cancellation_requested_at = run.cancellation_requested_at or utcnow()
    if run.status == "queued":
        append_transition(db, run, "cancelled", reason="cancelled before claim", actor=actor)
        _sync_marketing_case(db, run)
    else:
        append_transition(
            db,
            run,
            run.status,
            reason="cancellation requested",
            actor=actor,
            attempt_id=run.current_attempt_id,
            allow_same=True,
        )


def recover_expired(
    db: Session,
    *,
    max_attempts: int,
    actor: str = "runtime-recovery",
    run_id: str | None = None,
) -> dict[str, int]:
    now = utcnow()
    stmt = select(AgentRunAttempt).where(
        AgentRunAttempt.status.in_({"claimed", "running", "external_starting"}),
        AgentRunAttempt.lease_until < now,
    )
    if run_id:
        stmt = stmt.where(AgentRunAttempt.run_id == run_id)
    expired = list(db.scalars(stmt.order_by(AgentRunAttempt.lease_until)).all())
    result = {"requeued": 0, "unknown": 0, "failed": 0}
    for attempt in expired:
        run_stmt = select(AgentRun).where(AgentRun.id == attempt.run_id)
        if db.bind and db.bind.dialect.name == "postgresql":
            run_stmt = run_stmt.with_for_update()
        run = db.scalar(run_stmt)
        if not run or run.current_attempt_id != attempt.id or run.status not in {"accepted", "running"}:
            continue
        attempt.completed_at = now
        if attempt.hermes_run_id or attempt.status == "external_starting":
            attempt.status = "unknown"
            attempt.failure_class = "lease_expired_after_external_dispatch"
            attempt.retryability = "unsafe"
            attempt.failure = {
                "reason": "worker lease expired after Hermes dispatch began",
                "retryability": "unsafe",
                "hermes_run_id": attempt.hermes_run_id,
            }
            run.failure = attempt.failure
            append_transition(db, run, "unknown", reason=attempt.failure_class, actor=actor, attempt_id=attempt.id)
            db.add(Outbox(
                event_type="manual.reconciliation.required",
                aggregate_type="run",
                aggregate_id=run.id,
                payload={"run_id": run.id, "attempt_id": attempt.id, "reason": attempt.failure_class},
            ))
            _sync_marketing_case(db, run)
            result["unknown"] += 1
        elif attempt.attempt_no < max_attempts:
            attempt.status = "lost"
            attempt.failure_class = "lease_expired_before_external_start"
            attempt.retryability = "safe"
            attempt.failure = {"reason": "worker lease expired before Hermes start", "retryability": "safe"}
            append_transition(db, run, "queued", reason="safe recovery requeued run", actor=actor, attempt_id=attempt.id)
            run.current_attempt_id = None
            result["requeued"] += 1
        else:
            attempt.status = "failed"
            attempt.failure_class = "attempt_limit_exhausted"
            attempt.retryability = "unsafe"
            attempt.failure = {"reason": "safe recovery attempt limit exhausted", "retryability": "unsafe"}
            run.failure = attempt.failure
            append_transition(db, run, "failed", reason=attempt.failure_class, actor=actor, attempt_id=attempt.id)
            _sync_marketing_case(db, run)
            result["failed"] += 1
    return result
