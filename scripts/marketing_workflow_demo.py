#!/usr/bin/env python3
"""Run the bounded, human-gated three-Agent marketing workflow through HTTP."""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
TERMINAL_CASE = {"completed", "cancelled"}
AGENT_START_ACTIONS = {
    "start_mo_plan",
    "start_pma",
    "start_bga",
    "start_mo_retrospective",
    "retry_safe_step",
}
FLOW = (
    "start_mo_plan",
    "approve_mo_plan",
    "start_pma",
    "approve_product",
    "start_bga",
    "approve_content",
    "record_simulated_publish",
    "record_synthetic_feedback",
    "start_mo_retrospective",
    "accept_retrospective",
)


def env_value(name: str, default: str | None = None) -> str:
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.startswith(name + "="):
                return line.split("=", 1)[1]
    if default is not None:
        return default
    raise RuntimeError(f"missing {name} in {env_file}")


class Client:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.token: str | None = None

    def login(self) -> None:
        body = urllib.parse.urlencode({
            "grant_type": "password",
            "client_id": "1cat-workspace",
            "username": "admin",
            "password": env_value("INITIAL_ADMIN_PASSWORD", "123456"),
        }).encode()
        request = urllib.request.Request(
            self.base_url + "/auth/realms/1cat/protocol/openid-connect/token",
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            self.token = json.load(response)["access_token"]

    def call(
        self,
        path: str,
        method: str = "GET",
        payload: dict[str, Any] | None = None,
        *,
        if_match: int | None = None,
        operation: str = "workflow",
    ) -> Any:
        request_id = f"{operation}-{uuid.uuid4().hex}" if method != "GET" else None
        base_headers = {"Content-Type": "application/json"}
        if method != "GET":
            base_headers["X-Correlation-ID"] = request_id or ""
            base_headers["Idempotency-Key"] = request_id or ""
        if if_match is not None:
            base_headers["If-Match"] = str(if_match)
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
        for auth_attempt in range(2):
            headers = dict(base_headers)
            if self.token:
                headers["Authorization"] = f"Bearer {self.token}"
            request = urllib.request.Request(self.base_url + path, data=data, method=method, headers=headers)
            try:
                with urllib.request.urlopen(request, timeout=30) as response:
                    return json.load(response)
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")
                if exc.code == 401 and auth_attempt == 0:
                    self.login()
                    continue
                raise RuntimeError(f"{method} {path}: HTTP {exc.code} {detail}") from exc
        raise RuntimeError(f"{method} {path}: authentication retry exhausted")


def next_action(case: dict[str, Any]) -> str | None:
    actions = case.get("next_actions") or []
    return actions[0].get("action") if actions else None


def wait_for_gate(
    client: Client,
    case_id: str,
    timeout_seconds: int,
    *,
    allow_safe_retry: bool = False,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    last_marker = None
    while time.monotonic() < deadline:
        case = client.call(f"/v1/marketing-cases/{case_id}")
        marker = (case["current_stage"], case["status"], next_action(case))
        if marker != last_marker:
            print(json.dumps({
                "event": "case_status",
                "case_id": case_id,
                "stage": marker[0],
                "status": marker[1],
                "next_action": marker[2],
                "version": case["version"],
            }, ensure_ascii=False), flush=True)
            last_marker = marker
        if case["status"] == "blocked":
            if allow_safe_retry and marker[2] == "retry_safe_step":
                return case
            current = next(step for step in case["stages"] if step["step_key"] == case["current_stage"])
            raise RuntimeError(f"case blocked at {case['current_stage']}: {current.get('failure')}")
        if marker[2] or case["status"] in TERMINAL_CASE:
            return case
        time.sleep(2)
    raise TimeoutError(f"case {case_id} did not reach its next human gate in {timeout_seconds}s")


def command(client: Client, case: dict[str, Any], action: str) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if action == "record_simulated_publish":
        payload = {"note": "演示流程，未登录或写入真实平台"}
    elif action == "record_synthetic_feedback":
        payload = {
            "touchpoint": case["target_platform"],
            "inquiry_status": "valid",
            "reason_code": "synthetic_demo_signal",
        }
    result = client.call(
        f"/v1/marketing-cases/{case['id']}/commands",
        "POST",
        {"action": action, "payload": payload},
        if_match=case["version"],
        operation=f"workflow-{action}",
    )
    print(json.dumps({
        "event": "command",
        "case_id": case["id"],
        "action": action,
        "stage": result["current_stage"],
        "status": result["status"],
        "version": result["version"],
    }, ensure_ascii=False), flush=True)
    return result


def collect_evidence(client: Client, case: dict[str, Any], elapsed: float) -> dict[str, Any]:
    resources = case.get("resources") or []
    grouped: dict[str, list[dict[str, Any]]] = {}
    for ref in resources:
        grouped.setdefault(ref["resource_type"], []).append(ref["resource"])

    run_evidence = []
    for run in grouped.get("run", []):
        current = client.call(f"/v1/runs/{run['id']}")
        attempts = client.call(f"/v1/runs/{run['id']}/attempts")
        timeline = client.call(f"/v1/runs/{run['id']}/timeline")
        run_evidence.append({"run": current, "attempts": attempts, "timeline": timeline})

    knowledge_kinds: dict[str, int] = {}
    for item in grouped.get("knowledge", []):
        knowledge_kinds[item["kind"]] = knowledge_kinds.get(item["kind"], 0) + 1
    manual_tasks = grouped.get("manual_task", [])
    commitments = grouped.get("commitment", [])
    evidence = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": round(elapsed, 1),
        "case": case,
        "runs": run_evidence,
        "summary": {
            "case_id": case["id"],
            "execution_mode": case["execution_mode"],
            "status": case["status"],
            "stage_count": len(case.get("stages") or []),
            "run_count": len(run_evidence),
            "run_statuses": [item["run"]["status"] for item in run_evidence],
            "run_stages": [item["run"].get("stage_key") for item in run_evidence],
            "trace_ids": [item["run"].get("trace_id") for item in run_evidence],
            "knowledge_kinds": knowledge_kinds,
            "commitment_statuses": [item["status"] for item in commitments],
            "handoff_count": len(grouped.get("handoff", [])),
            "approval_count": len(grouped.get("approval", [])),
            "manual_receipts": [item.get("receipt") for item in manual_tasks],
            "lead_count": len(grouped.get("lead", [])),
            "sales_feedback_count": len(grouped.get("sales_feedback", [])),
            "boundary": case.get("boundary"),
        },
    }
    return evidence


def assert_evidence(evidence: dict[str, Any], *, allow_safe_retry: bool = False) -> None:
    summary = evidence["summary"]
    assert summary["status"] == "completed", summary
    assert summary["stage_count"] == 9, summary
    if allow_safe_retry:
        assert summary["run_count"] >= 4, summary
    else:
        assert summary["run_count"] == 4, summary
    assert {"mo_plan", "pma", "bga", "mo_retrospective"}.issubset(set(summary["run_stages"])), summary
    assert set(summary["run_statuses"]) == {"evidence_accepted"}, summary
    assert set(summary["commitment_statuses"]) == {"fulfilled"}, summary
    assert summary["handoff_count"] == 2, summary
    assert summary["approval_count"] >= 6, summary
    assert summary["lead_count"] == 1 and summary["sales_feedback_count"] == 1, summary
    assert summary["knowledge_kinds"].get("review", 0) >= 2, summary
    assert summary["knowledge_kinds"].get("fact", 0) >= 1, summary
    assert summary["knowledge_kinds"].get("claim", 0) >= 1, summary
    assert summary["knowledge_kinds"].get("campaign", 0) >= 1, summary
    assert summary["knowledge_kinds"].get("content", 0) >= 1, summary
    assert all(receipt.get("external_effect") is False for receipt in summary["manual_receipts"]), summary
    assert summary["boundary"] == {
        "publishing": "simulated",
        "external_effect": False,
        "pii": False,
        "business_outcome_claimed": False,
    }, summary


def run_workflow(
    base_url: str,
    mode: str,
    timeout_seconds: int,
    case_id: str | None = None,
    *,
    allow_safe_retry: bool = False,
) -> dict[str, Any]:
    client = Client(base_url)
    client.login()
    if mode == "real":
        model = client.call("/v1/runtime-model")
        if not model.get("execution_enabled") or model.get("provider") != "deepseek":
            raise RuntimeError(f"real DeepSeek execution is not enabled: {model}")
    started = time.monotonic()
    if case_id:
        case = client.call(f"/v1/marketing-cases/{case_id}")
        if case["execution_mode"] != mode:
            raise RuntimeError(
                f"case {case_id} execution_mode is {case['execution_mode']}, not requested {mode}"
            )
        event = "resumed"
    else:
        case = client.call("/v1/marketing-cases", "POST", {
            "title": f"三Agent完整Demo · {mode}",
            "objective": "通过MO、PMA与BGA的人工门禁协作形成可追踪的单平台营销候选闭环。",
            "brief_body": "面向开发者验证Agent Runtime：只使用合成业务事实，不含PII，不访问真实内容平台。",
            "source_refs": [f"synthetic://marketing-workflow-demo/{uuid.uuid4().hex}"],
            "target_platform": "bilibili",
            "execution_mode": mode,
        }, operation=f"workflow-create-{mode}")
        event = "created"
    print(json.dumps({
        "event": event,
        "case_id": case["id"],
        "execution_mode": mode,
        "stage": case["current_stage"],
        "version": case["version"],
    }, ensure_ascii=False), flush=True)

    previous_index = -1
    while case["status"] != "completed":
        if not next_action(case):
            case = wait_for_gate(
                client,
                case["id"],
                timeout_seconds,
                allow_safe_retry=allow_safe_retry,
            )
        actual_action = next_action(case)
        if actual_action == "retry_safe_step":
            if not allow_safe_retry:
                raise RuntimeError("workflow reached a safe retry gate; rerun with --allow-safe-retry")
            case = command(client, case, actual_action)
            case = wait_for_gate(
                client,
                case["id"],
                timeout_seconds,
                allow_safe_retry=allow_safe_retry,
            )
            continue
        if actual_action not in FLOW:
            raise RuntimeError(f"workflow cannot auto-accept action {actual_action}: {case['status']}")
        action_index = FLOW.index(actual_action)
        if action_index < previous_index:
            raise RuntimeError(f"workflow action order regressed from {FLOW[previous_index]} to {actual_action}")
        previous_index = action_index
        case = command(client, case, actual_action)
        if actual_action in AGENT_START_ACTIONS:
            case = wait_for_gate(
                client,
                case["id"],
                timeout_seconds,
                allow_safe_retry=allow_safe_retry,
            )

    case = client.call(f"/v1/marketing-cases/{case['id']}")
    evidence = collect_evidence(client, case, time.monotonic() - started)
    assert_evidence(evidence, allow_safe_retry=allow_safe_retry)
    target = ROOT / ".runtime" / "evidence" / "marketing-workflow-demo-latest.json"
    mode_target = ROOT / ".runtime" / "evidence" / f"marketing-workflow-demo-{mode}-latest.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(evidence, ensure_ascii=False, indent=2, default=str)
    target.write_text(serialized, encoding="utf-8")
    mode_target.write_text(serialized, encoding="utf-8")
    print(json.dumps({
        "event": "accepted",
        **evidence["summary"],
        "evidence_files": [str(target), str(mode_target)],
    }, ensure_ascii=False), flush=True)
    return evidence


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the complete three-Agent marketing workflow demo.")
    parser.add_argument("--mode", choices=("synthetic", "real"), default="synthetic")
    parser.add_argument("--base-url", default="http://localhost:8080")
    parser.add_argument("--timeout-seconds", type=int, default=900)
    parser.add_argument("--case-id", help="Resume one existing Case without repeating completed Agent Runs.")
    parser.add_argument(
        "--allow-safe-retry",
        action="store_true",
        help="At a human safe-retry gate, create one replacement Run and preserve the failed history.",
    )
    args = parser.parse_args(argv)
    try:
        run_workflow(
            args.base_url,
            args.mode,
            args.timeout_seconds,
            args.case_id,
            allow_safe_retry=args.allow_safe_retry,
        )
    except (AssertionError, RuntimeError, TimeoutError, urllib.error.URLError) as exc:
        print(json.dumps({"event": "failed", "error": str(exc)}, ensure_ascii=False), flush=True)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
