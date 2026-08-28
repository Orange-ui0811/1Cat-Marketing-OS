#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass
from pathlib import Path


BASE = "http://localhost:8080"
ROOT = Path(__file__).resolve().parents[1]
TERMINAL = {"evidence_accepted", "failed", "cancelled", "unknown"}


@dataclass(frozen=True)
class RoleSpec:
    role_id: str
    title: str
    objective: str
    instruction: str
    allowed_candidate_kinds: tuple[str, ...]


ROLE_SPECS = {
    "pma": RoleSpec(
        role_id="DROLE-01",
        title="DeepSeek PMA 真实调用验收",
        objective="基于给定合成事实生成可送交人工审阅的产品表达候选，不使用PII，不执行发布。",
        instruction=(
            "合成事实：设备在一次受控测试中连续运行8小时；没有长期、跨环境或竞品数据。"
            "请输出三条带证据边界的产品价值表达候选，并列出不能宣称的强结论。"
            "可按契约创建fact或claim候选；不得补充外部事实，不得执行发布。"
        ),
        allowed_candidate_kinds=("brief", "evidence", "fact", "claim"),
    ),
    "bga": RoleSpec(
        role_id="DROLE-02",
        title="DeepSeek BGA 真实调用验收",
        objective="基于合成Claim生成Campaign与内容候选，保持四平台MANUAL边界，不执行真实发布。",
        instruction=(
            "合成Claim：一次受控测试观察到设备连续运行8小时，仅可表述为单次条件下的观察结果。"
            "请形成一个B站Campaign候选和一份内容母稿候选，清楚标出证据边界与人工发布步骤。"
            "可创建campaign/content候选；不得登录平台、不得发布、不得处理PII。"
        ),
        allowed_candidate_kinds=("campaign", "content", "review"),
    ),
    "mo": RoleSpec(
        role_id="DROLE-03",
        title="DeepSeek MO 真实调用验收",
        objective="汇总合成PMA与BGA候选，形成协作复盘和人工待决项，不代替人类作出业务决定。",
        instruction=(
            "合成PMA结论：单次8小时观察可作为候选事实，长期稳定性Claim被阻断。"
            "合成BGA结论：B站Campaign和母稿仅为候选，发布保持MANUAL。"
            "请汇总岗位关系、风险、下一步与需要人类决定的事项；可创建review候选，"
            "不得批准Claim、不得声明发布或履约。"
        ),
        allowed_candidate_kinds=("review",),
    ),
}


def env_value(name: str) -> str:
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith(name + "="):
            return line.split("=", 1)[1]
    raise RuntimeError(f"missing {name} in .env")


def call(path: str, method: str = "GET", payload=None, token: str | None = None, *, prefix: str = "real-agent"):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if method != "GET":
        operation_id = f"{prefix}-{uuid.uuid4().hex}"
        headers.update({"X-Correlation-ID": operation_id, "Idempotency-Key": operation_id})
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(BASE + path, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {path}: HTTP {exc.code} {detail}") from exc


def login() -> str:
    body = urllib.parse.urlencode({
        "grant_type": "password",
        "client_id": "1cat-workspace",
        "username": "admin",
        "password": env_value("INITIAL_ADMIN_PASSWORD"),
    }).encode()
    request = urllib.request.Request(
        BASE + "/auth/realms/1cat/protocol/openid-connect/token",
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)["access_token"]


def run_role(profile_id: str, timeout_seconds: int) -> dict:
    spec = ROLE_SPECS[profile_id]
    prefix = f"real-{profile_id}"
    token = login()
    model = call("/v1/runtime-model", token=token, prefix=prefix)
    if not model.get("execution_enabled") or model.get("provider") != "deepseek":
        raise RuntimeError(f"real DeepSeek execution is not enabled: {model}")

    commitment = call("/v1/commitments", "POST", {
        "title": spec.title,
        "proposed_role": spec.role_id,
        "objective": spec.objective,
        "acceptance": {"human_confirmation_required": True, "real_model": True},
        "dependencies": [],
        "context": {"source": f"real-{profile_id}-demo", "pii": False, "synthetic_business_data": True},
    }, token, prefix=prefix)
    call(f"/v1/commitments/{commitment['id']}/transition", "POST", {
        "status": "accepted",
        "reason": "人工已确认真实模型验收边界；候选输出不等于业务履约",
    }, token, prefix=prefix)
    run = call("/v1/runs", "POST", {
        "commitment_id": commitment["id"],
        "role_id": spec.role_id,
        "input": spec.instruction,
        "context_version": 1,
    }, token, prefix=prefix)

    print(json.dumps({
        "event": "created",
        "profile_id": profile_id,
        "provider": model["provider"],
        "model": model["model"],
        "commitment_id": commitment["id"],
        "runtime_run_id": run["id"],
        "correlation_id": run["correlation_id"],
        "trace_id": run.get("trace_id"),
    }, ensure_ascii=False), flush=True)

    last_status = None
    started = time.monotonic()
    deadline = started + timeout_seconds
    while time.monotonic() < deadline:
        run = call(f"/v1/runs/{run['id']}", token=token, prefix=prefix)
        if run["status"] != last_status:
            attempt = run.get("current_attempt") or {}
            print(json.dumps({
                "event": "status",
                "profile_id": profile_id,
                "status": run["status"],
                "attempt_id": attempt.get("id"),
                "hermes_run_id": attempt.get("hermes_run_id"),
            }, ensure_ascii=False), flush=True)
            last_status = run["status"]
        if run["status"] in TERMINAL:
            break
        time.sleep(2)
    else:
        raise TimeoutError(f"{profile_id} Run did not reach a terminal state in {timeout_seconds} seconds")

    latest_commitment = next(
        item for item in call("/v1/commitments", token=token, prefix=prefix) if item["id"] == commitment["id"]
    )
    attempt = run.get("current_attempt") or {}
    hermes = (run.get("output") or {}).get("hermes") or (run.get("failure") or {}).get("hermes") or {}
    knowledge = call("/v1/knowledge", token=token, prefix=prefix)
    candidates = [
        item for item in knowledge
        if (item.get("metadata") or {}).get("attempt_id") == attempt.get("id")
    ]
    candidate_kinds = sorted({item.get("kind") for item in candidates})
    result = {
        "event": "terminal",
        "profile_id": profile_id,
        "runtime_run_id": run["id"],
        "correlation_id": run["correlation_id"],
        "trace_id": run.get("trace_id"),
        "runtime_status": run["status"],
        "commitment_status": latest_commitment["status"],
        "attempt_id": attempt.get("id"),
        "hermes_run_id": attempt.get("hermes_run_id"),
        "hermes_status": hermes.get("status"),
        "model_provider": (run.get("output") or {}).get("model_provider"),
        "model_id": (run.get("output") or {}).get("model_id"),
        "duration_seconds": round(time.monotonic() - started, 1),
        "human_confirmation_required": latest_commitment["status"] != "fulfilled",
        "candidate_count": len(candidates),
        "candidate_kinds": candidate_kinds,
        "candidate_kinds_authorized": bool(candidates) and set(candidate_kinds).issubset(spec.allowed_candidate_kinds),
    }
    print(json.dumps(result, ensure_ascii=False), flush=True)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run one bounded real DeepSeek Agent acceptance scenario.")
    parser.add_argument("--role", choices=tuple(ROLE_SPECS), required=True)
    parser.add_argument("--timeout-seconds", type=int, default=900)
    args = parser.parse_args(argv)
    result = run_role(args.role, args.timeout_seconds)
    passed = (
        result["runtime_status"] == "evidence_accepted"
        and result["hermes_status"] == "completed"
        and result["commitment_status"] == "submitted"
        and result["human_confirmation_required"]
        and result["candidate_kinds_authorized"]
    )
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
