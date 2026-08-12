#!/usr/bin/env python3
from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

BASE = "http://localhost:8080"
ROOT = Path(__file__).resolve().parents[1]


def env_value(name: str) -> str:
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith(name + "="):
            return line.split("=", 1)[1]
    raise RuntimeError(f"missing {name} in .env")


def call(path: str, method: str = "GET", payload=None, token: str | None = None, extra_headers: dict | None = None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if method != "GET":
        correlation = f"smoke-{uuid.uuid4().hex}"
        headers.update({"X-Correlation-ID": correlation, "Idempotency-Key": correlation})
    headers.update(extra_headers or {})
    data = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(BASE + path, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"{method} {path}: {exc.code} {exc.read().decode()}") from exc


def expect_error(path: str, method: str, payload, token: str, status: int):
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    correlation = f"smoke-deny-{uuid.uuid4().hex}"
    headers.update({"X-Correlation-ID": correlation, "Idempotency-Key": correlation})
    request = urllib.request.Request(BASE + path, data=json.dumps(payload).encode(), method=method, headers=headers)
    try:
        urllib.request.urlopen(request, timeout=20)
    except urllib.error.HTTPError as exc:
        assert exc.code == status, (exc.code, exc.read().decode())
        return
    raise AssertionError(f"{method} {path} 应被拒绝")


def accept_and_run(token: str, role_id: str, title: str, objective: str, instruction: str):
    commitment = call("/v1/commitments", "POST", {
        "title": title, "proposed_role": role_id, "objective": objective,
        "acceptance": {"human": True, "synthetic": True}, "dependencies": [], "context": {"pii": False},
    }, token)
    call(f"/v1/commitments/{commitment['id']}/transition", "POST",
         {"status": "accepted", "reason": "合成Smoke路径的人工接受"}, token)
    run = call("/v1/runs", "POST", {
        "commitment_id": commitment["id"], "role_id": role_id,
        "input": instruction, "context_version": 1,
    }, token)
    for _ in range(30):
        time.sleep(1)
        run = call(f"/v1/runs/{run['id']}", token=token)
        if run["status"] not in {"queued", "accepted", "running"}:
            break
    assert run["status"] in {"evidence_accepted", "unknown"}, run
    latest = [x for x in call("/v1/commitments", token=token) if x["id"] == commitment["id"]][0]
    assert latest["status"] == "submitted"
    return commitment, run


def login() -> str:
    body = urllib.parse.urlencode({"grant_type": "password", "client_id": "1cat-workspace", "username": "admin", "password": env_value("INITIAL_ADMIN_PASSWORD")}).encode()
    request = urllib.request.Request(BASE + "/auth/realms/1cat/protocol/openid-connect/token", data=body,
                                     headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.load(response)["access_token"]


def main():
    print("[1/12] 检查服务健康与身份")
    assert call("/health/ready")["status"] == "ready"
    token = login()
    print("[2/12] 检查三个岗位和R0边界")
    assert len(call("/v1/roles", token=token)) == 3
    boundary = call("/v1/runtime-boundary", token=token)
    assert boundary["publishing"] == "manual" and boundary["pii"] == "disabled"
    print("[3/12] 创建合成Brief")
    brief = call("/v1/knowledge", "POST", {"kind":"brief","title":"R0合成产品Brief","body":"面向实验环境验证三岗位协作。","source_refs":["synthetic://smoke"],"metadata":{"synthetic":True}}, token)
    print("[4/12] 验证PMA候选链与submitted上限")
    pma_commitment, _ = accept_and_run(token, "DROLE-01", "验证PMA产品表达", "生成事实和Claim候选",
                                       "整理合成产品事实并输出候选，不得正式批准。")
    fact = call("/v1/knowledge", "POST", {"kind":"fact","title":"合成产品事实候选","body":"仅用于部署验收。","source_refs":[f"knowledge:{brief['id']}:v1"],"metadata":{"synthetic":True,"commitment_id":pma_commitment["id"]}}, token)
    claim = call("/v1/knowledge", "POST", {"kind":"claim","title":"合成Claim候选","body":"这不是正式批准的市场Claim。","source_refs":[f"knowledge:{fact['id']}:v1"],"metadata":{"synthetic":True,"commitment_id":pma_commitment["id"]}}, token)
    print("[5/12] 验证BGA Campaign、母稿与四平台人工任务")
    bga_commitment, _ = accept_and_run(token, "DROLE-02", "验证BGA内容链", "生成Campaign与平台候选",
                                       "基于合成Claim生成Campaign和内容候选，只准备人工任务。")
    campaign = call("/v1/knowledge", "POST", {"kind":"campaign","title":"合成Campaign候选","body":"不含预算操作和平台写入。","source_refs":[f"knowledge:{claim['id']}:v1"],"metadata":{"synthetic":True}}, token)
    content = call("/v1/knowledge", "POST", {"kind":"content","title":"合成内容母稿候选","body":"只用于人工发布任务验证。","source_refs":[f"knowledge:{campaign['id']}:v1"],"metadata":{"synthetic":True,"platforms":["douyin","xiaohongshu","bilibili","wechat_official"]}}, token)
    task = call("/v1/manual-tasks", "POST", {"task_type":"publish","platform":"douyin","object_ref":{"id":content["id"],"version":1},"instructions":"合成验收：不得实际登录或发布。","assigned_to":"admin"}, token)
    task = call(f"/v1/manual-tasks/{task['id']}/receipt", "POST", {"status":"unknown","receipt":{"synthetic":True,"published":False,"note":"未执行真实平台动作"}}, token, {"If-Match":"1"})
    assert task["status"] == "unknown"
    print("[6/12] 验证PII-free LeadStub")
    lead = call("/v1/leads", "POST", {"source_record_ref":"synthetic://touchpoint/001","touchpoint":"douyin-comment","campaign_ref":campaign["id"],"content_ref":content["id"]}, token)
    assert "inquiry_status" not in lead
    print("[7/12] 验证销售人类四状态反馈")
    feedback = call("/v1/sales-feedback", "POST", {"lead_stub_id":lead["id"],"lead_version":lead["version"],"inquiry_status":"needs_more_info","reason_code":"SYNTHETIC_MORE_INFO","registry_version":"r0-smoke"}, token)
    assert feedback["inquiry_status"] == "needs_more_info"
    print("[8/12] 验证MO复盘候选")
    mo_commitment, _ = accept_and_run(token, "DROLE-03", "验证MO复盘", "组织证据与人工待决项",
                                      "汇总合成闭环并生成复盘候选，不得作出G4业务决定。")
    review = call("/v1/knowledge", "POST", {"kind":"review","title":"合成增长复盘候选","body":"软件路径通过；真实Shadow、UAT和G4仍待人类执行。","source_refs":[f"sales-feedback:{feedback['id']}",f"commitment:{mo_commitment['id']}"],"metadata":{"synthetic":True,"gate_claim":False}}, token)
    assert review["status"] == "candidate"
    print("[9/12] 验证视频号范围拒绝")
    expect_error("/v1/manual-tasks", "POST", {"task_type":"publish","platform":"wechat_channels","object_ref":{"id":content["id"],"version":1},"instructions":"应被拒绝","assigned_to":"admin"}, token, 422)
    print("[10/12] 验证真实PII拒绝")
    expect_error("/v1/knowledge", "POST", {"kind":"brief","title":"越界输入","body":"联系13800138000","source_refs":[],"metadata":{}}, token, 422)
    print("[11/12] 验证没有业务完成自动认定")
    assert all(x["status"] != "fulfilled" for x in call("/v1/commitments", token=token) if x["id"] in {pma_commitment["id"], bga_commitment["id"], mo_commitment["id"]})
    print("[12/12] 验证审计链")
    assert len(call("/v1/audit", token=token)) >= 12
    print("Smoke Test通过：合成Brief→PMA→BGA→人工任务→LeadStub→销售反馈→MO复盘完整闭环可用；未执行真实发布或真实业务验收。")


if __name__ == "__main__":
    main()
