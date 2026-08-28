import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator


def test_health_and_roles(client, auth_headers):
    assert client.get("/health/ready").json()["pii_enabled"] is False
    roles = client.get("/v1/roles", headers=auth_headers).json()
    assert {role["profile_id"] for role in roles} == {"pma", "bga", "mo"}
    model = client.get("/v1/runtime-model", headers=auth_headers).json()
    assert model["provider"] == "deepseek"
    assert model["model"] == "deepseek-v4-pro"
    assert model["execution_enabled"] is False


def test_write_headers_required(client, auth_headers):
    response = client.post("/v1/events", headers=auth_headers, json={"event_type": "test", "payload": {}})
    assert response.status_code == 400
    assert "X-Correlation-ID" in response.json()["detail"]


def test_commitment_state_and_run_boundary(client, write_headers, auth_headers):
    commitment = client.post("/v1/commitments", headers=write_headers, json={
        "title": "测试协作承诺", "proposed_role": "DROLE-01", "objective": "只生成候选表达",
        "acceptance": {"human": True}, "dependencies": [], "context": {"pii": False},
    }).json()
    bad = dict(write_headers); bad["Idempotency-Key"] = "bad-transition"; bad["X-Correlation-ID"] = "bad-transition"
    assert client.post(f"/v1/commitments/{commitment['id']}/transition", headers=bad,
                       json={"status": "fulfilled", "reason": "不得跳过"}).status_code == 409
    good = dict(write_headers); good["Idempotency-Key"] = "accept-transition"; good["X-Correlation-ID"] = "accept-transition"
    assert client.post(f"/v1/commitments/{commitment['id']}/transition", headers=good,
                       json={"status": "accepted", "reason": "测试接受"}).status_code == 200
    run_headers = dict(write_headers); run_headers["Idempotency-Key"] = "run-once"; run_headers["X-Correlation-ID"] = "run-once"
    run_headers["traceparent"] = "00-0123456789abcdef0123456789abcdef-0123456789abcdef-01"
    run = client.post("/v1/runs", headers=run_headers, json={
        "commitment_id": commitment["id"], "role_id": "DROLE-01", "input": "生成候选", "context_version": 1,
    })
    assert run.status_code == 202 and run.json()["status"] == "queued"
    assert run.json()["trace_id"] == "0123456789abcdef0123456789abcdef"


def test_idempotency_conflict(client, write_headers):
    payload = {"event_type": "one", "payload": {}}
    first = client.post("/v1/events", headers=write_headers, json=payload)
    second = client.post("/v1/events", headers=write_headers, json=payload)
    assert first.status_code == second.status_code == 201
    conflict = client.post("/v1/events", headers=write_headers, json={"event_type": "two", "payload": {}})
    assert conflict.status_code == 409


def test_knowledge_serializes_metadata_without_cycle(client, write_headers):
    response = client.post("/v1/knowledge", headers=write_headers, json={
        "kind": "brief", "title": "合成Brief", "body": "只用于测试",
        "source_refs": ["synthetic://test"], "metadata": {"synthetic": True},
    })
    assert response.status_code == 201
    assert response.json()["metadata"] == {"synthetic": True}


def test_run_role_must_match_commitment(client, write_headers):
    commitment = client.post("/v1/commitments", headers=write_headers, json={
        "title": "岗位边界", "proposed_role": "DROLE-01", "objective": "验证岗位绑定",
        "acceptance": {}, "dependencies": [], "context": {},
    }).json()
    transition_headers = dict(write_headers, **{"Idempotency-Key": "role-accept", "X-Correlation-ID": "role-accept"})
    client.post(f"/v1/commitments/{commitment['id']}/transition", headers=transition_headers,
                json={"status": "accepted", "reason": "测试"})
    run_headers = dict(write_headers, **{"Idempotency-Key": "role-run", "X-Correlation-ID": "role-run"})
    response = client.post("/v1/runs", headers=run_headers, json={
        "commitment_id": commitment["id"], "role_id": "DROLE-02", "input": "越界运行", "context_version": 1,
    })
    assert response.status_code == 409


def test_lead_stub_and_sales_feedback_are_pii_free_and_role_bound(client, write_headers):
    lead = client.post("/v1/leads", headers=write_headers, json={
        "source_record_ref": "synthetic://touch/001", "touchpoint": "douyin-comment",
        "campaign_ref": "campaign:synthetic", "content_ref": "content:synthetic",
    })
    assert lead.status_code == 201 and "inquiry_status" not in lead.json()
    non_sales = dict(write_headers, **{"Idempotency-Key": "feedback-deny", "X-Correlation-ID": "feedback-deny"})
    denied = client.post("/v1/sales-feedback", headers=non_sales, json={
        "lead_stub_id": lead.json()["id"], "lead_version": 1, "inquiry_status": "needs_more_info",
        "reason_code": "SYNTHETIC_MORE_INFO", "registry_version": "r0-test",
    })
    assert denied.status_code == 403
    sales = dict(write_headers, **{
        "X-Actor-Id": "test-sales", "X-Actor-Roles": "sales_owner",
        "Idempotency-Key": "feedback-allow", "X-Correlation-ID": "feedback-allow",
    })
    allowed = client.post("/v1/sales-feedback", headers=sales, json={
        "lead_stub_id": lead.json()["id"], "lead_version": 1, "inquiry_status": "needs_more_info",
        "reason_code": "SYNTHETIC_MORE_INFO", "registry_version": "r0-test",
    })
    assert allowed.status_code == 201 and allowed.json()["sales_actor_id"] == "test-sales"


def test_manual_receipt_requires_version(client, write_headers):
    task = client.post("/v1/manual-tasks", headers=write_headers, json={
        "task_type": "publish", "platform": "douyin", "object_ref": {"id": "synthetic", "version": 1},
        "instructions": "仅验证人工任务，不执行发布", "assigned_to": "test-admin",
    }).json()
    receipt_headers = dict(write_headers, **{"Idempotency-Key": "receipt", "X-Correlation-ID": "receipt"})
    missing = client.post(f"/v1/manual-tasks/{task['id']}/receipt", headers=receipt_headers,
                          json={"status": "unknown", "receipt": {"synthetic": True}})
    assert missing.status_code == 412
    receipt_headers["If-Match"] = "1"
    recorded = client.post(f"/v1/manual-tasks/{task['id']}/receipt", headers=receipt_headers,
                           json={"status": "unknown", "receipt": {"synthetic": True, "published": False}})
    assert recorded.status_code == 200 and recorded.json()["version"] == 2


def test_all_business_writes_reject_obvious_pii(client, write_headers):
    response = client.post("/v1/knowledge", headers=write_headers, json={
        "kind": "brief", "title": "含敏感信息", "body": "联系13800138000",
        "source_refs": [], "metadata": {},
    })
    assert response.status_code == 422


def test_opaque_attempt_id_is_not_misclassified_as_phone(client, write_headers):
    headers = dict(write_headers, **{
        "Idempotency-Key": "opaque-attempt-id",
        "X-Correlation-ID": "opaque-attempt-id",
    })
    response = client.post("/v1/knowledge", headers=headers, json={
        "kind": "review",
        "title": "合法复盘候选",
        "body": "仅验证随机运行标识不会被误判为手机号。",
        "source_refs": ["synthetic://case/case_26571297a8f9438e891d18fe77771f86"],
        "metadata": {"attempt_id": "attempt_16099574444cb0b3f317739a5c693e"},
    })
    assert response.status_code == 201, response.text


@pytest.mark.parametrize("fact", ["联系我13800138000", "邮件test@example.com"])
def test_memory_rejects_pii(client, write_headers, fact):
    response = client.post("/v1/memory", headers=write_headers, json={
        "profile_id": "pma", "category": "stable_preference", "fact": fact, "source_ref": "synthetic://test",
    })
    assert response.status_code == 422


def test_contracts_are_draft_2020_12():
    schemas = list(Path("packages/contracts").glob("*.schema.json"))
    assert len(schemas) == 10
    for path in schemas:
        schema = json.loads(path.read_text())
        Draft202012Validator.check_schema(schema)


def test_video_channel_is_dormant():
    assert not Path("profiles/bga/skills/SKL-BG-11").exists()
    assert Path("profiles/dormant/SKL-BG-11/ACTIVATION_BLOCKED").exists()
    active_unique = set()
    for profile in ("pma", "bga", "mo"):
        active_unique.update(path.parent.name for path in Path("profiles", profile, "skills").glob("*/SKILL.md"))
    assert len(active_unique) == 27
