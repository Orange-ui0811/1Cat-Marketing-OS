import uuid

from app.db import SessionLocal
from app.marketing_case import prepare_synthetic_candidates
from app.models import AgentRun, AgentRunAttempt, KnowledgeItem
from app.run_state import claim_next_run, finish_success, finish_terminal, mark_running


def write_headers(auth_headers, prefix: str, version: int | None = None):
    operation = f"{prefix}-{uuid.uuid4().hex}"
    headers = {
        **auth_headers,
        "X-Correlation-ID": operation,
        "Idempotency-Key": operation,
    }
    if version is not None:
        headers["If-Match"] = str(version)
    return headers


def create_case(client, auth_headers, *, mode="synthetic", headers=None):
    request_headers = headers or write_headers(auth_headers, "case-create")
    return client.post("/v1/marketing-cases", headers=request_headers, json={
        "title": "合成新品单平台闭环",
        "objective": "验证三Agent媒体业务闭环和人工门禁",
        "brief_body": "合成设备在一次受控测试中连续运行8小时，不包含真实用户数据。",
        "source_refs": ["synthetic://demo/brief-001"],
        "target_platform": "bilibili",
        "execution_mode": mode,
    })


def command(client, auth_headers, case, action, payload=None):
    response = client.post(
        f"/v1/marketing-cases/{case['id']}/commands",
        headers=write_headers(auth_headers, f"case-{action}", case["version"]),
        json={"action": action, "payload": payload or {}},
    )
    assert response.status_code == 200, response.text
    return response.json()


def finish_current_synthetic_run(client, auth_headers, case):
    step = next(item for item in case["stages"] if item["step_key"] == case["current_stage"])
    run_id = step["active_run_id"]
    with SessionLocal.begin() as db:
        claim = claim_next_run(db, "workflow-test-worker", 30, run_id=run_id)
        assert claim is not None
        mark_running(db, claim)
        run = db.get(AgentRun, run_id)
        attempt = db.get(AgentRunAttempt, claim.attempt_id)
        candidates = prepare_synthetic_candidates(db, run, attempt)
        finish_success(db, claim, {
            "mode": "bounded-simulation",
            "candidate_ids": [item.id for item in candidates],
            "candidate_kinds": sorted({item.kind for item in candidates}),
        })
    response = client.get(f"/v1/marketing-cases/{case['id']}", headers=auth_headers)
    assert response.status_code == 200
    return response.json()


def finish_current_run_without_candidates(client, auth_headers, case):
    step = next(item for item in case["stages"] if item["step_key"] == case["current_stage"])
    run_id = step["active_run_id"]
    with SessionLocal.begin() as db:
        claim = claim_next_run(db, "workflow-empty-worker", 30, run_id=run_id)
        assert claim is not None
        mark_running(db, claim)
        finish_success(db, claim, {"mode": "test", "candidate_ids": []})
    return client.get(f"/v1/marketing-cases/{case['id']}", headers=auth_headers).json()


def finish_current_terminal(client, auth_headers, case, status, retryability):
    step = next(item for item in case["stages"] if item["step_key"] == case["current_stage"])
    run_id = step["active_run_id"]
    with SessionLocal.begin() as db:
        claim = claim_next_run(db, f"workflow-{status}-worker", 30, run_id=run_id)
        assert claim is not None
        mark_running(db, claim)
        finish_terminal(
            db,
            claim,
            status,
            failure={"reason": f"test {status}", "retryability": retryability},
            failure_class=f"test_{status}",
            retryability=retryability,
        )
    return client.get(f"/v1/marketing-cases/{case['id']}", headers=auth_headers).json()


def test_marketing_case_create_is_idempotent_and_real_mode_is_guarded(client, auth_headers):
    headers = write_headers(auth_headers, "same-case")
    first = create_case(client, auth_headers, headers=headers)
    second = create_case(client, auth_headers, headers=headers)
    assert first.status_code == second.status_code == 201
    assert first.json()["id"] == second.json()["id"]
    assert len(first.json()["stages"]) == 9
    assert first.json()["current_stage"] == "mo_plan"
    assert first.json()["next_actions"][0]["action"] == "start_mo_plan"

    real = create_case(client, auth_headers, mode="real")
    assert real.status_code == 409
    assert "DeepSeek" in real.text


def test_marketing_case_requires_if_match_and_rejects_illegal_action(client, auth_headers):
    case = create_case(client, auth_headers).json()
    missing = client.post(
        f"/v1/marketing-cases/{case['id']}/commands",
        headers=write_headers(auth_headers, "missing-version"),
        json={"action": "start_mo_plan", "payload": {}},
    )
    assert missing.status_code == 428
    stale = client.post(
        f"/v1/marketing-cases/{case['id']}/commands",
        headers=write_headers(auth_headers, "stale-version", 999),
        json={"action": "start_mo_plan", "payload": {}},
    )
    assert stale.status_code == 412
    illegal = client.post(
        f"/v1/marketing-cases/{case['id']}/commands",
        headers=write_headers(auth_headers, "illegal-stage", case["version"]),
        json={"action": "approve_product", "payload": {}},
    )
    assert illegal.status_code == 409


def test_case_command_is_idempotent_and_list_returns_current_server_fact(client, auth_headers):
    case = create_case(client, auth_headers).json()
    headers = write_headers(auth_headers, "repeat-start", case["version"])
    payload = {"action": "start_mo_plan", "payload": {}}
    first = client.post(f"/v1/marketing-cases/{case['id']}/commands", headers=headers, json=payload)
    second = client.post(f"/v1/marketing-cases/{case['id']}/commands", headers=headers, json=payload)
    assert first.status_code == second.status_code == 200
    assert first.json()["version"] == second.json()["version"]
    assert first.json()["stages"][1]["active_run_id"] == second.json()["stages"][1]["active_run_id"]
    assert len([item for item in second.json()["resources"] if item["resource_type"] == "run"]) == 1

    listed = client.get("/v1/marketing-cases?limit=20", headers=auth_headers)
    assert listed.status_code == 200
    found = next(item for item in listed.json() if item["id"] == case["id"])
    assert found["status"] == "running" and found["next_actions"] == []


def test_real_case_rechecks_execution_switch_when_starting_agent(client, auth_headers, monkeypatch):
    monkeypatch.setattr("app.main.execution_enabled", lambda: True)
    case = create_case(client, auth_headers, mode="real").json()
    monkeypatch.setattr("app.main.execution_enabled", lambda: False)
    denied = client.post(
        f"/v1/marketing-cases/{case['id']}/commands",
        headers=write_headers(auth_headers, "real-disabled-before-start", case["version"]),
        json={"action": "start_mo_plan", "payload": {}},
    )
    assert denied.status_code == 409
    assert "DeepSeek" in denied.text


def test_complete_synthetic_three_agent_marketing_case(client, auth_headers):
    case = create_case(client, auth_headers).json()

    case = command(client, auth_headers, case, "start_mo_plan")
    case = finish_current_synthetic_run(client, auth_headers, case)
    assert case["status"] == "awaiting_human"
    case = command(client, auth_headers, case, "approve_mo_plan")
    first_handoff = next(item["resource"] for item in case["resources"] if item["resource_type"] == "handoff")
    assert first_handoff["status"] == "pending" and first_handoff["recipient"] == "DROLE-01"

    case = command(client, auth_headers, case, "start_pma")
    first_handoff = next(item["resource"] for item in case["resources"] if item["resource_type"] == "handoff")
    assert first_handoff["status"] == "accepted"
    mo_review = next(
        item["resource"] for item in case["resources"]
        if item["resource_type"] == "knowledge" and item["resource"]["kind"] == "review"
    )
    pma_run = next(
        item["resource"] for item in case["resources"]
        if item["resource_type"] == "run" and item["resource"]["stage_key"] == "pma"
    )
    assert f"review:{mo_review['id']}@v{mo_review['version']}" in pma_run["input_text"]
    assert "至少一个fact和一个claim" in pma_run["input_text"]
    case = finish_current_synthetic_run(client, auth_headers, case)
    assert case["current_stage"] == "product_review"
    case = command(client, auth_headers, case, "approve_product")
    second_handoff = [item["resource"] for item in case["resources"] if item["resource_type"] == "handoff"][-1]
    assert second_handoff["status"] == "pending" and second_handoff["recipient"] == "DROLE-02"

    case = command(client, auth_headers, case, "start_bga")
    second_handoff = [item["resource"] for item in case["resources"] if item["resource_type"] == "handoff"][-1]
    assert second_handoff["status"] == "accepted"
    bga_run = next(
        item["resource"] for item in case["resources"]
        if item["resource_type"] == "run" and item["resource"]["stage_key"] == "bga"
    )
    pma_candidates = [
        item["resource"] for item in case["resources"]
        if item["resource_type"] == "knowledge" and item["resource"]["kind"] in {"fact", "claim"}
    ]
    assert all(f"{item['kind']}:{item['id']}@v{item['version']}" in bga_run["input_text"] for item in pma_candidates)
    assert "不得创建发布任务" in bga_run["input_text"]
    case = finish_current_synthetic_run(client, auth_headers, case)
    assert case["current_stage"] == "content_review"
    premature_publish = client.post(
        f"/v1/marketing-cases/{case['id']}/commands",
        headers=write_headers(auth_headers, "publish-before-approval", case["version"]),
        json={"action": "record_simulated_publish", "payload": {}},
    )
    assert premature_publish.status_code == 409
    assert not [item for item in case["resources"] if item["resource_type"] == "manual_task"]
    case = command(client, auth_headers, case, "approve_content")

    case = command(client, auth_headers, case, "record_simulated_publish")
    case = command(client, auth_headers, case, "record_synthetic_feedback")

    case = command(client, auth_headers, case, "start_mo_retrospective")
    retrospective_run = next(
        item["resource"] for item in case["resources"]
        if item["resource_type"] == "run" and item["resource"]["stage_key"] == "mo_retrospective"
    )
    assert "manual_task:" in retrospective_run["input_text"]
    assert "status=simulated,external_effect=False" in retrospective_run["input_text"]
    assert "lead:" in retrospective_run["input_text"] and "sales_feedback:" in retrospective_run["input_text"]
    case = finish_current_synthetic_run(client, auth_headers, case)
    assert case["status"] == "awaiting_human"
    draft = case["final_deliverable"]
    assert draft["status"] == "draft"
    assert len(draft["markdown"]) >= 2200
    assert {section["key"] for section in draft["document"]["sections"]} == {
        "executive_summary", "audience_and_problem", "verified_facts",
        "claims_and_boundaries", "campaign_strategy", "content_package",
        "publishing_and_feedback", "measurement_and_risk", "retrospective",
        "evidence_index",
    }
    case = command(client, auth_headers, case, "accept_retrospective")

    assert case["status"] == "completed"
    assert not case["next_actions"]
    assert all(item["status"] == "completed" for item in case["stages"])
    assert case["boundary"] == {
        "publishing": "simulated",
        "external_effect": False,
        "pii": False,
        "business_outcome_claimed": False,
    }

    resources = case["resources"]
    by_type = {}
    for item in resources:
        by_type.setdefault(item["resource_type"], []).append(item)
    assert len(by_type["run"]) == 4
    assert len(by_type["commitment"]) == 4
    assert len(by_type["handoff"]) == 2
    assert len(by_type["approval"]) == 7
    assert len(by_type["knowledge"]) == 7
    assert len(by_type["deliverable"]) == 1
    assert len(by_type["manual_task"]) == 1
    assert len(by_type["lead"]) == 1
    assert len(by_type["sales_feedback"]) == 1
    knowledge_versions = {
        item["resource_id"]: item["resource"]["version"] for item in by_type["knowledge"]
    }
    for approval_ref in by_type["approval"]:
        approval = approval_ref["resource"]
        if approval["subject_type"] == "knowledge":
            assert approval["subject_version"] == knowledge_versions[approval["subject_id"]]
        else:
            assert approval["subject_type"] == "marketing_deliverable"
            assert approval["action"] == "accept_final_deliverable"
    for knowledge_ref in by_type["knowledge"]:
        metadata = knowledge_ref["resource"]["metadata"]
        assert metadata["case_id"] == case["id"]
        assert metadata["execution_mode"] == "synthetic"
        assert metadata["stage_key"] in {
            "brief", "mo_plan", "pma", "bga", "mo_retrospective",
        }
        if metadata["stage_key"] != "brief":
            assert metadata["attempt_id"] and metadata["role_id"] and metadata["commitment_id"]
    task = by_type["manual_task"][0]["resource"]
    assert task["status"] == "simulated"
    assert task["receipt"]["external_effect"] is False
    assert task["receipt"]["case_id"] == case["id"]
    deliverable = case["final_deliverable"]
    assert deliverable["status"] == "accepted"
    assert deliverable["accepted_by"] == "test-operator"
    assert deliverable["document"]["boundary"] == case["boundary"]


def test_short_required_artifact_blocks_instead_of_pretending_completion(client, auth_headers):
    case = create_case(client, auth_headers).json()
    case = command(client, auth_headers, case, "start_mo_plan")
    step = next(item for item in case["stages"] if item["step_key"] == "mo_plan")
    with SessionLocal.begin() as db:
        claim = claim_next_run(db, "workflow-short-worker", 30, run_id=step["active_run_id"])
        assert claim is not None
        mark_running(db, claim)
        run = db.get(AgentRun, step["active_run_id"])
        candidate = KnowledgeItem(
            kind="review",
            title="占位计划",
            body="稍后补充。",
            source_refs=[f"synthetic://marketing-case/{case['id']}/short"],
            metadata_json={
                "candidate": True,
                "case_id": case["id"],
                "stage_key": "mo_plan",
                "role_id": run.role_id,
                "commitment_id": run.commitment_id,
                "attempt_id": claim.attempt_id,
                "execution_mode": "synthetic",
            },
            created_by="test-short-worker",
            content_hash="0" * 64,
        )
        db.add(candidate)
        db.flush()
        finish_success(db, claim, {"candidate_ids": [candidate.id], "candidate_kinds": ["review"]})
    case = client.get(f"/v1/marketing-cases/{case['id']}", headers=auth_headers).json()
    current = next(item for item in case["stages"] if item["step_key"] == "mo_plan")
    assert case["status"] == current["status"] == "blocked"
    assert current["failure"]["failure_class"] == "incomplete_required_artifacts"
    assert current["failure"]["quality_failures"]["review"] == {"minimum": 180, "actual": 5}
    assert [item["action"] for item in case["next_actions"]] == ["retry_safe_step", "cancel_case"]


def test_missing_required_artifacts_blocks_and_allows_human_safe_retry(client, auth_headers):
    case = create_case(client, auth_headers).json()
    case = command(client, auth_headers, case, "start_mo_plan")
    original_run = next(item for item in case["resources"] if item["resource_type"] == "run")["resource_id"]
    case = finish_current_run_without_candidates(client, auth_headers, case)

    current = next(item for item in case["stages"] if item["step_key"] == "mo_plan")
    assert case["status"] == current["status"] == "blocked"
    assert current["failure"] == {
        "failure_class": "missing_required_artifacts",
        "retryability": "safe",
        "missing_kinds": ["review"],
    }
    assert [item["action"] for item in case["next_actions"]] == ["retry_safe_step", "cancel_case"]

    case = command(client, auth_headers, case, "retry_safe_step")
    retry_run = next(item for item in case["stages"] if item["step_key"] == "mo_plan")["active_run_id"]
    assert case["status"] == "running" and retry_run != original_run
    assert len([item for item in case["resources"] if item["resource_type"] == "run"]) == 2


def test_failed_safe_run_can_retry_but_unknown_run_cannot(client, auth_headers):
    failed_case = create_case(client, auth_headers).json()
    failed_case = command(client, auth_headers, failed_case, "start_mo_plan")
    failed_case = finish_current_terminal(client, auth_headers, failed_case, "failed", "safe")
    assert [item["action"] for item in failed_case["next_actions"]] == ["retry_safe_step", "cancel_case"]
    failed_case = command(client, auth_headers, failed_case, "retry_safe_step")
    assert failed_case["status"] == "running"

    unknown_case = create_case(client, auth_headers).json()
    unknown_case = command(client, auth_headers, unknown_case, "start_mo_plan")
    unknown_case = finish_current_terminal(client, auth_headers, unknown_case, "unknown", "unsafe")
    assert [item["action"] for item in unknown_case["next_actions"]] == ["resolve_unknown", "cancel_case"]
    denied = client.post(
        f"/v1/marketing-cases/{unknown_case['id']}/commands",
        headers=write_headers(auth_headers, "unsafe-retry", unknown_case["version"]),
        json={"action": "retry_safe_step", "payload": {}},
    )
    assert denied.status_code == 409
    unknown_case = command(client, auth_headers, unknown_case, "resolve_unknown", {
        "resolution": "confirmed_failed",
        "note": "已核对外部执行记录，确认没有产生副作用。",
        "evidence": {"source": "test-run-log"},
    })
    assert unknown_case["reconciliations"][0]["resolution"] == "confirmed_failed"
    assert [item["action"] for item in unknown_case["next_actions"]] == ["retry_safe_step", "cancel_case"]


def test_eight_page_workspace_persists_messages_decisions_and_human_hold(client, auth_headers):
    case = create_case(client, auth_headers).json()
    message = client.post(
        f"/v1/marketing-cases/{case['id']}/messages",
        headers=write_headers(auth_headers, "case-message"),
        json={"channel": "MO", "body": "请在计划中明确人工门禁。", "intent": "change_request"},
    )
    assert message.status_code == 201, message.text
    case = message.json()
    assert case["messages"][-1]["intent"] == "change_request"

    case = command(client, auth_headers, case, "start_mo_plan")
    case = finish_current_synthetic_run(client, auth_headers, case)
    actions = [item["action"] for item in case["next_actions"]]
    assert "approve_mo_plan" in actions
    assert "return_mo_plan" in actions
    assert "hold_case" in actions

    case = command(client, auth_headers, case, "hold_case", {"reason": "等待产品负责人补充边界"})
    assert case["status"] == "blocked"
    assert case["decisions"][-1]["decision"] == "hold"
    assert [item["action"] for item in case["next_actions"]] == ["resume_case", "cancel_case"]

    case = command(client, auth_headers, case, "resume_case", {"reason": "证据已补齐，恢复审核"})
    assert case["status"] == "awaiting_human"
    case = command(client, auth_headers, case, "return_mo_plan", {"reason": "重新细化验收标准"})
    assert case["current_stage"] == "mo_plan"
    assert case["status"] == "active"
    assert case["decisions"][-1]["decision"] == "returned"
    assert case["next_actions"][0]["action"] == "start_mo_plan"


def test_agent_profile_config_is_server_versioned(client, auth_headers):
    profiles = client.get("/v1/agent-configs", headers=auth_headers)
    assert profiles.status_code == 200, profiles.text
    pma = next(item for item in profiles.json() if item["agent_key"] == "PMA")
    config = pma["config"]
    config["model"]["timeout_seconds"] = 120
    saved = client.put(
        "/v1/agent-configs/PMA",
        headers={**write_headers(auth_headers, "profile-update"), "If-Match": str(pma["version"])},
        json={"config": config, "summary": "将 PMA 超时调整为 120 秒"},
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["status"] == "draft"
    validated = client.post(
        "/v1/agent-configs/PMA/commands",
        headers={**write_headers(auth_headers, "profile-validate"), "If-Match": str(saved.json()["version"])},
        json={"action": "validate", "summary": "校验 PMA 配置"},
    )
    assert validated.status_code == 200, validated.text
    published = client.post(
        "/v1/agent-configs/PMA/commands",
        headers={**write_headers(auth_headers, "profile-publish"), "If-Match": str(validated.json()["version"])},
        json={"action": "publish", "summary": "发布 PMA 配置"},
    )
    assert published.status_code == 200, published.text
    assert published.json()["status"] == "published"
    assert published.json()["config"]["model"]["timeout_seconds"] == 120
    assert published.json()["published_config"]["model"]["timeout_seconds"] == 120
    assert len(published.json()["published_hash"]) == 64


def test_agent_profile_schema_rejects_incomplete_or_duplicated_runtime_config(client, auth_headers):
    profiles = client.get("/v1/agent-configs", headers=auth_headers).json()
    pma = next(item for item in profiles if item["agent_key"] == "PMA")
    invalid = pma["config"]
    invalid["prompt_templates"]["chat"]["body"] = "过短"
    invalid["skills"][1]["id"] = invalid["skills"][0]["id"]
    response = client.put(
        "/v1/agent-configs/PMA",
        headers={**write_headers(auth_headers, "profile-invalid"), "If-Match": str(pma["version"])},
        json={"config": invalid, "summary": "非法配置必须被拒绝"},
    )
    assert response.status_code == 422


def test_unpublished_profile_draft_never_changes_new_run_snapshot(client, auth_headers):
    profiles = client.get("/v1/agent-configs", headers=auth_headers).json()
    mo = next(item for item in profiles if item["agent_key"] == "MO")
    original_hash = mo["published_hash"]
    original_timeout = mo["published_config"]["model"]["timeout_seconds"]
    draft = mo["config"]
    draft["model"]["timeout_seconds"] = 222
    draft["prompt_templates"]["workflow"]["version"] = "v2-draft"
    saved = client.put(
        "/v1/agent-configs/MO",
        headers={**write_headers(auth_headers, "profile-draft-isolation"), "If-Match": str(mo["version"])},
        json={"config": draft, "summary": "尚未发布的MO配置"},
    )
    assert saved.status_code == 200
    assert saved.json()["status"] == "draft"
    assert saved.json()["published_hash"] == original_hash
    assert saved.json()["published_config"]["model"]["timeout_seconds"] == original_timeout

    case = create_case(client, auth_headers).json()
    case = command(client, auth_headers, case, "start_mo_plan")
    first_run = next(item["resource"] for item in case["resources"] if item["resource_type"] == "run")
    assert first_run["profile_hash"] == original_hash
    assert first_run["profile_snapshot"]["model"]["timeout_seconds"] == original_timeout
    assert first_run["profile_snapshot"]["prompt_templates"]["workflow"]["version"] == "v1.0"

    validated = client.post(
        "/v1/agent-configs/MO/commands",
        headers={**write_headers(auth_headers, "profile-draft-validate"), "If-Match": str(saved.json()["version"])},
        json={"action": "validate", "summary": "校验MO草稿"},
    )
    assert validated.status_code == 200
    published = client.post(
        "/v1/agent-configs/MO/commands",
        headers={**write_headers(auth_headers, "profile-draft-publish"), "If-Match": str(validated.json()["version"])},
        json={"action": "publish", "summary": "发布MO草稿"},
    )
    assert published.status_code == 200
    assert published.json()["published_hash"] != original_hash

    second_case = create_case(client, auth_headers).json()
    second_case = command(client, auth_headers, second_case, "start_mo_plan")
    second_run = next(item["resource"] for item in second_case["resources"] if item["resource_type"] == "run")
    assert second_run["profile_version"] == published.json()["published_version"]
    assert second_run["profile_hash"] == published.json()["published_hash"]
    assert second_run["profile_snapshot"]["model"]["timeout_seconds"] == 222
    assert first_run["profile_hash"] == original_hash


def test_running_case_cancel_waits_for_run_terminal_and_never_skips_stage(client, auth_headers):
    case = create_case(client, auth_headers).json()
    case = command(client, auth_headers, case, "start_mo_plan")
    step = next(item for item in case["stages"] if item["step_key"] == "mo_plan")
    with SessionLocal.begin() as db:
        claim = claim_next_run(db, "workflow-cancel-worker", 30, run_id=step["active_run_id"])
        assert claim is not None
        mark_running(db, claim)

    case = command(client, auth_headers, case, "cancel_case")
    step = next(item for item in case["stages"] if item["step_key"] == "mo_plan")
    run = next(item["resource"] for item in case["resources"] if item["resource_type"] == "run")
    assert case["status"] == step["status"] == "blocked"
    assert run["status"] == "running" and run["cancellation_requested_at"]
    assert all(item["status"] != "completed" for item in case["stages"] if item["step_key"] != "brief")

    with SessionLocal.begin() as db:
        finish_terminal(
            db,
            claim,
            "cancelled",
            failure={"reason": "Hermes confirmed stop", "retryability": "unsafe"},
            failure_class="hermes_cancelled",
            retryability="unsafe",
        )
    case = client.get(f"/v1/marketing-cases/{case['id']}", headers=auth_headers).json()
    assert case["status"] == "blocked"
    case = command(client, auth_headers, case, "cancel_case")
    assert case["status"] == "cancelled"
