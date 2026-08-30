from app.db import SessionLocal
import app.main as runtime_main
from app.marketing_case import sync_case_after_run_terminal
from app.models import AgentRun, KnowledgeItem, MarketingChatTurn
from app.policy import canonical_hash


def write_headers(auth_headers, key, version=None):
    result = {
        **auth_headers,
        "X-Correlation-ID": f"corr-{key}",
        "Idempotency-Key": key,
    }
    if version is not None:
        result["If-Match"] = str(version)
    return result


def create_case(client, auth_headers):
    response = client.post(
        "/v1/marketing-cases",
        headers=write_headers(auth_headers, "unified-case-create"),
        json={
            "title": "统一工作台安全整合",
            "objective": "验证活动、变更请求和对象版本谱系",
            "brief_body": "所有正式操作写入服务端，不允许前端假回复。",
            "source_refs": ["synthetic://tests/unified-workspace"],
            "target_platform": "bilibili",
            "execution_mode": "synthetic",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_case_activity_and_message_change_request_are_persisted(client, auth_headers):
    case = create_case(client, auth_headers)
    assert case["change_requests"] == []
    assert case["chat_turns"] == []

    activity = client.get(f"/v1/marketing-cases/{case['id']}/activity", headers=auth_headers)
    assert activity.status_code == 200
    assert [item["event_type"] for item in activity.json()] == ["case.created"]

    message = client.post(
        f"/v1/marketing-cases/{case['id']}/messages",
        headers=write_headers(auth_headers, "unified-normal-message"),
        json={"channel": "MO", "body": "补充目标受众背景", "intent": "message"},
    )
    assert message.status_code == 201, message.text

    change_message = client.post(
        f"/v1/marketing-cases/{case['id']}/messages",
        headers=write_headers(auth_headers, "unified-change-message"),
        json={"channel": "PMA", "body": "请把验收标准改为必须提供证据版本。", "intent": "change_request"},
    )
    assert change_message.status_code == 201, change_message.text
    snapshot = change_message.json()
    assert len(snapshot["change_requests"]) == 1
    assert snapshot["change_requests"][0]["status"] == "proposed"
    assert snapshot["change_requests"][0]["channel"] == "PMA"

    activity = client.get(f"/v1/marketing-cases/{case['id']}/activity", headers=auth_headers).json()
    assert {item["event_type"] for item in activity} == {
        "case.created", "message.created", "change_request.proposed",
    }


def test_structured_change_request_requires_current_case_version_and_is_idempotent(client, auth_headers):
    case = create_case(client, auth_headers)
    payload = {
        "channel": "MO",
        "stage_key": "mo_plan",
        "summary": "收紧计划验收标准",
        "detail": "MO Plan 必须明确 Fact、Claim 和人工门禁的验收条件。",
        "target_refs": [{"type": "stage", "id": "mo_plan", "version": 1}],
        "proposed_change": {"acceptance": ["对象版本可追溯"]},
    }
    headers = write_headers(auth_headers, "unified-structured-change", case["version"])
    created = client.post(
        f"/v1/marketing-cases/{case['id']}/change-requests",
        headers=headers,
        json=payload,
    )
    assert created.status_code == 201, created.text
    snapshot = created.json()
    assert snapshot["version"] == case["version"] + 1
    assert snapshot["change_requests"][0]["proposed_change"]["acceptance"] == ["对象版本可追溯"]

    repeated = client.post(
        f"/v1/marketing-cases/{case['id']}/change-requests",
        headers=headers,
        json=payload,
    )
    assert repeated.status_code == 201
    assert len(repeated.json()["change_requests"]) == 1

    stale = client.post(
        f"/v1/marketing-cases/{case['id']}/change-requests",
        headers=write_headers(auth_headers, "unified-stale-change", case["version"]),
        json={**payload, "summary": "过期修改"},
    )
    assert stale.status_code == 412


def test_knowledge_lineage_returns_immutable_revisions_and_diff(client, auth_headers):
    with SessionLocal.begin() as db:
        first_body = "第一版事实：仅证明技术链路完成。"
        first = KnowledgeItem(
            kind="fact",
            title="技术链路事实",
            body=first_body,
            status="candidate",
            source_refs=["synthetic://tests/fact-v1"],
            metadata_json={"stage_key": "pma"},
            created_by="test-worker",
            content_hash=canonical_hash({"body": first_body}),
        )
        db.add(first)
        db.flush()
        lineage_id = first.lineage_id
        first_id = first.id
        second_body = "第二版事实：技术链路完成，但不代表真实营销效果。"
        second = KnowledgeItem(
            lineage_id=lineage_id,
            revision_no=2,
            version=2,
            supersedes_id=first_id,
            kind="fact",
            title="技术链路事实",
            body=second_body,
            status="candidate",
            source_refs=["synthetic://tests/fact-v2"],
            metadata_json={"stage_key": "pma"},
            created_by="test-worker",
            content_hash=canonical_hash({"body": second_body}),
        )
        db.add(second)

    revisions = client.get(f"/v1/object-lineages/{lineage_id}/revisions", headers=auth_headers)
    assert revisions.status_code == 200
    assert [item["revision_no"] for item in revisions.json()] == [2, 1]
    assert revisions.json()[0]["supersedes_id"] == first_id

    diff = client.get(
        f"/v1/object-lineages/{lineage_id}/diff?from=1&to=2",
        headers=auth_headers,
    )
    assert diff.status_code == 200
    assert any("不代表真实营销效果" in line for line in diff.json()["diff"])


def test_agent_chat_fails_closed_when_real_execution_is_disabled(client, auth_headers):
    case = create_case(client, auth_headers)
    response = client.post(
        f"/v1/marketing-cases/{case['id']}/chat-turns",
        headers=write_headers(auth_headers, "unified-chat-disabled", case["version"]),
        json={"channel": "MO", "mode": "consultation", "body": "请说明当前案例的风险。"},
    )

    assert response.status_code == 409
    assert "不会降级为前端模拟回复" in response.json()["detail"]


def test_real_agent_chat_creates_a_read_only_run_and_persists_reply(
    client, auth_headers, monkeypatch,
):
    case = create_case(client, auth_headers)
    monkeypatch.setattr(runtime_main, "execution_enabled", lambda: True)
    created = client.post(
        f"/v1/marketing-cases/{case['id']}/chat-turns",
        headers=write_headers(auth_headers, "unified-real-chat", case["version"]),
        json={"channel": "PMA", "mode": "consultation", "body": "当前Claim最需要补什么证据？"},
    )
    assert created.status_code == 202, created.text
    result = created.json()
    assert result["turn"]["status"] == "queued"
    assert result["turn"]["execution_mode"] == "real"
    assert result["run"]["purpose"] == "chat"
    assert result["run"]["execution_mode"] == "real"
    assert result["run"]["profile_snapshot"]["agent"] == "PMA"

    run_id = result["run"]["id"]
    with SessionLocal.begin() as db:
        run = db.get(AgentRun, run_id)
        run.status = "evidence_accepted"
        run.output = {"hermes": {"output": "建议先补充可复现测试条件、样本范围和来源版本。"}}
        sync_case_after_run_terminal(db, run)

    turns = client.get(
        f"/v1/marketing-cases/{case['id']}/chat-turns?channel=PMA",
        headers=auth_headers,
    )
    assert turns.status_code == 200
    assert turns.json()[0]["status"] == "completed"
    assert turns.json()[0]["agent_message_id"]

    snapshot = client.get(f"/v1/marketing-cases/{case['id']}", headers=auth_headers).json()
    chat_messages = [message for message in snapshot["messages"] if message["channel"] == "PMA"]
    assert [message["sender_type"] for message in chat_messages] == ["human", "agent"]
    assert "可复现测试条件" in chat_messages[-1]["body"]
    assert chat_messages[-1]["attachments"][0]["run_id"] == run_id
    assert any(item["event_type"] == "chat.completed" for item in client.get(
        f"/v1/marketing-cases/{case['id']}/activity", headers=auth_headers,
    ).json())

    with SessionLocal() as db:
        turn = db.get(MarketingChatTurn, result["turn"]["id"])
        assert turn.profile_version == result["run"]["profile_version"]


def test_message_attachments_persist_metadata_and_reject_embedded_content(client, auth_headers):
    case = create_case(client, auth_headers)
    metadata = {
        "id": "attachment-brief-v1",
        "name": "brief.md",
        "type": "text/markdown",
        "size": 128,
        "last_modified": 1_788_000_000_000,
    }
    created = client.post(
        f"/v1/marketing-cases/{case['id']}/messages",
        headers=write_headers(auth_headers, "unified-attachment-metadata"),
        json={"channel": "MO", "body": "补充 Brief 文件元数据。", "attachments": [metadata]},
    )
    assert created.status_code == 201, created.text
    message = created.json()["messages"][-1]
    assert message["attachments"] == [metadata]

    rejected = client.post(
        f"/v1/marketing-cases/{case['id']}/messages",
        headers=write_headers(auth_headers, "unified-attachment-content-rejected"),
        json={
            "channel": "MO",
            "body": "不得嵌入文件正文。",
            "attachments": [{**metadata, "content_base64": "c2Vuc2l0aXZl"}],
        },
    )
    assert rejected.status_code == 422
