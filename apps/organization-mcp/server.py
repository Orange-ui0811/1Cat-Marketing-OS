import os
import logging
import time
import uuid
from contextvars import ContextVar
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP
from candidate_contract import (
    CandidateKind,
    allowed_candidate_kinds,
    candidate_metadata,
    validate_candidate_kind,
    validate_manual_publish_context,
)
from commitment_contract import CommitmentAction, target_commitment_status
from observability import configure_observability, metrics

RUNTIME = os.getenv("RUNTIME_API_URL", "http://runtime-api:8000")
KEYCLOAK = os.getenv("KEYCLOAK_TOKEN_URL", "http://keycloak:8080/auth/realms/1cat/protocol/openid-connect/token")
CLIENT_ID = os.getenv("OIDC_CLIENT_ID", "organization-mcp")
CLIENT_SECRET = os.getenv("OIDC_CLIENT_SECRET", "")
DEV = os.getenv("AUTH_MODE", "oidc") == "development"

configure_observability(service_name="1cat-organization-mcp")
log = logging.getLogger("1cat.organization-mcp")
_attempt_link: ContextVar[object | None] = ContextVar("attempt_link", default=None)
_runtime_context: ContextVar[dict[str, str]] = ContextVar("runtime_context", default={})

mcp = FastMCP("1Cat Organization Runtime", host="0.0.0.0", port=8001)
_token = {"value": "", "expires": 0.0}


def token() -> str:
    if DEV:
        return ""
    if _token["value"] and _token["expires"] > time.time() + 30:
        return _token["value"]
    if not CLIENT_SECRET:
        raise RuntimeError("organization-mcp client secret is not configured")
    response = httpx.post(KEYCLOAK, data={"grant_type": "client_credentials", "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET}, timeout=10)
    response.raise_for_status()
    data = response.json()
    _token.update(value=data["access_token"], expires=time.time() + int(data.get("expires_in", 60)))
    return _token["value"]


def request(method: str, path: str, *, payload: dict | None = None, correlation_id: str | None = None,
            if_match: int | None = None) -> Any:
    correlation_id = correlation_id or f"mcp-{uuid.uuid4().hex}"
    headers = {"X-Correlation-ID": correlation_id, "Idempotency-Key": f"{correlation_id}-{path}"}
    if DEV:
        headers.update({"X-Actor-Id": "organization-mcp", "X-Actor-Roles": "service,operator"})
    else:
        headers["Authorization"] = f"Bearer {token()}"
    if if_match is not None:
        headers["If-Match"] = str(if_match)
    runtime_context = _runtime_context.get()
    span_attributes = {
        "http.request.method": method,
        "url.path": path,
        "onecat.correlation_id": correlation_id,
    }
    for field, attribute in (
        ("run_id", "onecat.run.id"),
        ("attempt_id", "onecat.attempt.id"),
        ("hermes_run_id", "onecat.hermes_run.id"),
        ("case_id", "onecat.case.id"),
        ("stage_key", "onecat.stage.key"),
    ):
        if value := runtime_context.get(field):
            span_attributes[attribute] = value
    if run_correlation_id := runtime_context.get("correlation_id"):
        span_attributes["onecat.run.correlation_id"] = run_correlation_id

    def record_call(response: httpx.Response) -> None:
        result = "accepted" if response.is_success else "rejected"
        metrics.add(metrics.mcp_calls, tool_path=path, result=result)
        log.info("MCP runtime call", extra={
            "correlation_id": correlation_id,
            "tool_call_id": path,
            "status": result,
            **runtime_context,
        })

    try:
        from opentelemetry import trace

        link = _attempt_link.get()
        links = [link] if link is not None else None
        tracer = trace.get_tracer("onecat.organization-mcp")
        with tracer.start_as_current_span(
            "organization-mcp.runtime-call", links=links,
            attributes=span_attributes,
        ):
            response = httpx.request(method, f"{RUNTIME}{path}", json=payload, headers=headers, timeout=20)
            record_call(response)
    except ImportError:
        response = httpx.request(method, f"{RUNTIME}{path}", json=payload, headers=headers, timeout=20)
        record_call(response)
    if not response.is_success:
        try:
            detail = response.json().get("detail", response.text)
        except (ValueError, AttributeError):
            detail = response.text
        safe_detail = str(detail).replace("\r", " ").replace("\n", " ")[:500]
        raise ValueError(f"Runtime API {response.status_code}: {safe_detail}")
    return response.json()


def assert_context(role_id: str, profile_id: str, commitment_id: str, attempt_id: str) -> dict:
    _attempt_link.set(None)
    _runtime_context.set({})
    expected = {"DROLE-01": "pma", "DROLE-02": "bga", "DROLE-03": "mo"}
    if expected.get(role_id) != profile_id:
        raise ValueError("role/profile mismatch")
    if not commitment_id or not attempt_id:
        raise ValueError("commitment_id and attempt_id are required")
    commitment = next((item for item in request("GET", "/v1/commitments")
                       if item.get("id") == commitment_id), None)
    if not commitment:
        raise ValueError("commitment not found")
    if commitment.get("proposed_role") != role_id and commitment.get("committed_role") != role_id:
        raise ValueError("commitment role mismatch")
    attempt = request("GET", f"/v1/attempts/{attempt_id}")
    run = attempt.get("run") or {}
    if (run.get("commitment_id") != commitment_id or run.get("role_id") != role_id
            or run.get("profile_id") != profile_id):
        raise ValueError("attempt context mismatch")
    if run.get("current_attempt_id") != attempt_id or attempt.get("status") not in {"claimed", "running"}:
        raise ValueError("attempt is not the active runtime lease")
    _runtime_context.set({
        "run_id": run["id"],
        "attempt_id": attempt_id,
        "correlation_id": run.get("correlation_id") or "",
        "hermes_run_id": attempt.get("hermes_run_id") or "",
        "case_id": run.get("case_id") or "",
        "stage_key": run.get("stage_key") or "",
    })
    traceparent = run.get("traceparent")
    if traceparent:
        try:
            from opentelemetry import trace
            from opentelemetry.propagate import extract

            span_context = trace.get_current_span(extract({"traceparent": traceparent})).get_span_context()
            if span_context.is_valid:
                _attempt_link.set(trace.Link(span_context, {"onecat.attempt.id": attempt_id}))
        except ImportError:
            pass
    return run


@mcp.tool()
def organization_roles(role_id: str, profile_id: str, commitment_id: str, attempt_id: str) -> list[dict]:
    """读取稳定组织目录；必须提供当前岗位、Profile、Commitment与Attempt上下文。"""
    assert_context(role_id, profile_id, commitment_id, attempt_id)
    return request("GET", "/v1/roles")


@mcp.tool()
def knowledge_search_scoped(role_id: str, profile_id: str, commitment_id: str, attempt_id: str, query: str) -> list[dict]:
    """在授权知识范围内检索候选和正式对象，不返回PII。"""
    assert_context(role_id, profile_id, commitment_id, attempt_id)
    items = request("GET", "/v1/knowledge")
    needle = query.casefold()
    return [item for item in items if needle in (item.get("title", "") + " " + item.get("body", "")).casefold()][:20]


@mcp.tool()
def knowledge_source_read(role_id: str, profile_id: str, commitment_id: str, attempt_id: str,
                          object_id: str) -> dict:
    """按权威对象ID读取正文、版本、内容hash与SourceRef；不存在时失败关闭。"""
    assert_context(role_id, profile_id, commitment_id, attempt_id)
    for item in request("GET", "/v1/knowledge"):
        if item.get("id") == object_id:
            return item
    raise ValueError("knowledge object not found")


@mcp.tool()
def commitment_read(role_id: str, profile_id: str, commitment_id: str, attempt_id: str) -> dict:
    """读取当前Commitment权威状态；Hermes Session、Memory或Kanban不能覆盖该状态。"""
    assert_context(role_id, profile_id, commitment_id, attempt_id)
    for item in request("GET", "/v1/commitments"):
        if item.get("id") == commitment_id:
            return item
    raise ValueError("commitment not found")


@mcp.tool()
def commitment_respond(role_id: str, profile_id: str, commitment_id: str, attempt_id: str,
                       action: CommitmentAction, reason: str) -> dict:
    """单步响应Commitment。action仅可为accept/activate/wait/submit/request_takeover/pause；不能自行fulfilled。"""
    assert_context(role_id, profile_id, commitment_id, attempt_id)
    target = target_commitment_status(action)
    current = commitment_read(role_id, profile_id, commitment_id, attempt_id)
    if current.get("proposed_role") != role_id and current.get("committed_role") != role_id:
        raise ValueError("commitment owner mismatch")
    if current.get("status") == target:
        return current
    return request("POST", f"/v1/commitments/{commitment_id}/transition",
                   correlation_id=f"{attempt_id}-{uuid.uuid4().hex}",
                   if_match=int(current["version"]), payload={"status": target, "reason": reason})


@mcp.tool()
def candidate_kinds_read(role_id: str, profile_id: str, commitment_id: str, attempt_id: str) -> dict:
    """返回当前岗位可用于object_create_candidate的精确kind枚举；不要猜测或改写这些值。"""
    assert_context(role_id, profile_id, commitment_id, attempt_id)
    return {"role_id": role_id, "allowed_kinds": list(allowed_candidate_kinds(role_id))}


@mcp.tool()
def object_create_candidate(role_id: str, profile_id: str, commitment_id: str, attempt_id: str,
                            kind: CandidateKind, title: str, body: str, source_refs: list[str]) -> dict:
    """创建候选对象。PMA仅brief/evidence/fact/claim；BGA仅campaign/content/review；MO仅review。"""
    run = assert_context(role_id, profile_id, commitment_id, attempt_id)
    validate_candidate_kind(role_id, kind)
    metadata = candidate_metadata(role_id, commitment_id, attempt_id, run)
    return request("POST", "/v1/knowledge", correlation_id=f"{attempt_id}-{uuid.uuid4().hex}", payload={
        "kind": kind, "title": title, "body": body, "source_refs": source_refs,
        "metadata": metadata,
    })


@mcp.tool()
def handoff_create(role_id: str, profile_id: str, commitment_id: str, attempt_id: str,
                   recipient: str, purpose: str, payload: dict) -> dict:
    """创建岗位交接；发送成功不代表接收者接受。"""
    assert_context(role_id, profile_id, commitment_id, attempt_id)
    return request("POST", "/v1/handoffs", correlation_id=f"{attempt_id}-{uuid.uuid4().hex}", payload={
        "commitment_id": commitment_id, "sender_role": role_id, "recipient": recipient,
        "purpose": purpose, "payload": payload,
    })


@mcp.tool()
def approval_status_verify(role_id: str, profile_id: str, commitment_id: str, attempt_id: str,
                           approval_id: str) -> dict:
    """只读核验ApprovalGrant状态、范围与有效期；不能创建或批准授权。"""
    assert_context(role_id, profile_id, commitment_id, attempt_id)
    for item in request("GET", "/v1/approvals"):
        if item.get("id") == approval_id:
            return item
    raise ValueError("approval not found")


@mcp.tool()
def manual_publish_task_create(role_id: str, profile_id: str, commitment_id: str, attempt_id: str,
                               platform: str, object_ref: dict, instructions: str) -> dict:
    """创建不可变人工发布任务。该Tool不会登录或写入任何内容平台。"""
    run = assert_context(role_id, profile_id, commitment_id, attempt_id)
    validate_manual_publish_context(role_id, run)
    if platform == "wechat_channels":
        raise ValueError("SKL-BG-11/video channel is dormant in R0")
    if platform not in {"douyin", "xiaohongshu", "bilibili", "wechat_official"}:
        raise ValueError("platform outside R0")
    return request("POST", "/v1/manual-tasks", correlation_id=f"{attempt_id}-{uuid.uuid4().hex}", payload={
        "task_type": "publish", "platform": platform, "object_ref": object_ref,
        "instructions": instructions, "assigned_to": None,
    })


@mcp.tool()
def manual_publish_receipt_read(role_id: str, profile_id: str, commitment_id: str, attempt_id: str,
                                task_id: str) -> dict:
    """读取人工发布任务和人工回执；Agent不能填写或伪造回执。"""
    assert_context(role_id, profile_id, commitment_id, attempt_id)
    for item in request("GET", "/v1/manual-tasks"):
        if item.get("id") == task_id:
            return item
    raise ValueError("manual task not found")


@mcp.tool()
def lead_stub_create(role_id: str, profile_id: str, commitment_id: str, attempt_id: str,
                     source_record_ref: str, touchpoint: str, campaign_ref: str, content_ref: str) -> dict:
    """创建不含姓名、手机、邮箱或对话正文的LeadStub；不判断询盘有效性。"""
    assert_context(role_id, profile_id, commitment_id, attempt_id)
    if role_id != "DROLE-02":
        raise ValueError("only BGA may register a LeadStub")
    return request("POST", "/v1/leads", correlation_id=f"{attempt_id}-{uuid.uuid4().hex}", payload={
        "source_record_ref": source_record_ref, "touchpoint": touchpoint,
        "campaign_ref": campaign_ref or None, "content_ref": content_ref or None,
    })


@mcp.tool()
def sales_feedback_read(role_id: str, profile_id: str, commitment_id: str, attempt_id: str) -> list[dict]:
    """只读销售人类已写入的四状态反馈；Agent没有反馈写入能力。"""
    assert_context(role_id, profile_id, commitment_id, attempt_id)
    return request("GET", "/v1/sales-feedback")


@mcp.tool()
def memory_write_bounded(role_id: str, profile_id: str, commitment_id: str, attempt_id: str,
                         category: str, fact: str, source_ref: str) -> dict:
    """写入少量耐久Memory；API会拒绝明显手机号与邮箱。"""
    assert_context(role_id, profile_id, commitment_id, attempt_id)
    return request("POST", "/v1/memory", correlation_id=f"{attempt_id}-{uuid.uuid4().hex}", payload={
        "profile_id": profile_id, "category": category, "fact": fact, "source_ref": source_ref,
    })


@mcp.tool()
def risk_escalate(role_id: str, profile_id: str, commitment_id: str, attempt_id: str,
                  reason: str, evidence_refs: list[str]) -> dict:
    """创建人工接管事件；不自行作出业务批准。"""
    assert_context(role_id, profile_id, commitment_id, attempt_id)
    return request("POST", "/v1/events", correlation_id=f"{attempt_id}-{uuid.uuid4().hex}", payload={
        "event_type": "risk.manual_takeover.requested",
        "payload": {"role_id": role_id, "profile_id": profile_id, "commitment_id": commitment_id,
                    "attempt_id": attempt_id, "reason": reason, "evidence_refs": evidence_refs},
    })


@mcp.tool()
def audit_references_read(role_id: str, profile_id: str, commitment_id: str, attempt_id: str,
                          correlation_id: str) -> list[dict]:
    """读取与指定Correlation ID相关的审计引用，最多返回100项。"""
    assert_context(role_id, profile_id, commitment_id, attempt_id)
    return [item for item in request("GET", "/v1/audit?limit=100")
            if item.get("correlation_id") == correlation_id]


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
