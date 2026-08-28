#!/usr/bin/env python3
"""Run real container-kill drills against the local recoverable Agent Runtime.

The drill never calls Hermes or an external model. It stops the regular worker,
creates a targeted synthetic Run, starts an isolated victim worker, kills that
container, and lets a second isolated worker prove the recovery decision.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE_URL = "http://127.0.0.1:8080"
VICTIM_CONTAINER = "1cat-runtime-drill-victim"
RECOVERY_CONTAINER = "1cat-runtime-drill-recovery"
TERMINAL = {"evidence_accepted", "failed", "cancelled", "unknown"}


def env_value(name: str) -> str:
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith(name + "="):
            return line.split("=", 1)[1]
    raise RuntimeError(f"missing {name} in .env")


def docker(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["docker", *args],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    if check and result.returncode:
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError(f"docker {' '.join(args)} failed: {detail}")
    return result


def compose(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return docker("compose", *args, check=check)


def remove_drill_containers() -> None:
    docker("rm", "-f", VICTIM_CONTAINER, RECOVERY_CONTAINER, check=False)


def call(base_url: str, path: str, method: str = "GET", payload=None, token: str | None = None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if method != "GET":
        operation_id = f"runtime-drill-{uuid.uuid4().hex}"
        headers.update({"X-Correlation-ID": operation_id, "Idempotency-Key": operation_id})
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(base_url + path, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {path}: HTTP {exc.code} {detail}") from exc


def login(base_url: str) -> str:
    body = urllib.parse.urlencode({
        "grant_type": "password",
        "client_id": "1cat-workspace",
        "username": "admin",
        "password": env_value("INITIAL_ADMIN_PASSWORD"),
    }).encode()
    request = urllib.request.Request(
        base_url + "/auth/realms/1cat/protocol/openid-connect/token",
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)["access_token"]


def create_run(base_url: str, token: str, scenario: str) -> dict:
    suffix = uuid.uuid4().hex[:8]
    commitment = call(base_url, "/v1/commitments", "POST", {
        "title": f"Runtime 故障演练 · {scenario} · {suffix}",
        "proposed_role": "DROLE-01",
        "objective": "使用无外部调用的合成任务验证 Lease、Attempt、恢复与 unknown 安全边界。",
        "acceptance": {"runtime_failure_drill": True, "human_confirmation_required": True},
        "dependencies": [],
        "context": {"source": "runtime-failure-drill", "pii": False, "scenario": scenario},
    }, token)
    call(base_url, f"/v1/commitments/{commitment['id']}/transition", "POST", {
        "status": "accepted",
        "reason": "本机管理员批准无模型、无外部副作用的恢复演练",
    }, token)
    run = call(base_url, "/v1/runs", "POST", {
        "commitment_id": commitment["id"],
        "role_id": "DROLE-01",
        "input": f"RUNTIME FAILURE DRILL {scenario}; synthetic only; no model or tool calls.",
        "context_version": 1,
    }, token)
    return {"commitment": commitment, "run": run}


def start_drill_worker(container: str, run_id: str, worker_id: str, *, stage: str = "none") -> None:
    environment = {
        "WORKER_ID": worker_id,
        "RUNTIME_CLAIM_RUN_ID": run_id,
        "HERMES_EXECUTION_ENABLED": "false",
        "HERMES_EXECUTION_STATE_FILE": "/runtime-control/runtime-drill-model-disabled.json",
        "RUN_LEASE_SECONDS": "8",
        "RUN_HEARTBEAT_SECONDS": "3",
        "RUN_RECOVERY_SCAN_SECONDS": "1",
        "RUN_MAX_ATTEMPTS": "2",
        "RUNTIME_DRILL_ENABLED": "true" if stage != "none" else "false",
        "RUNTIME_DRILL_STAGE": stage,
        "RUNTIME_DRILL_DELAY_SECONDS": "120",
        "RUNTIME_DRILL_ATTEMPT_NO": "1",
    }
    args = ["run", "--no-deps", "-d", "--name", container]
    for key, value in environment.items():
        args.extend(["-e", f"{key}={value}"])
    args.append("runtime-worker")
    compose(*args)


def wait_for(base_url: str, token: str, run_id: str, predicate, timeout_seconds: int) -> dict:
    deadline = time.monotonic() + timeout_seconds
    latest = None
    while time.monotonic() < deadline:
        latest = call(base_url, f"/v1/runs/{run_id}", token=token)
        if predicate(latest):
            return latest
        time.sleep(0.5)
    raise TimeoutError(f"Run {run_id} did not reach the expected state; latest={latest}")


def stale_lease_probe(run_id: str, attempt_id: str) -> bool:
    probe = """
import json, os
from app.db import SessionLocal
from app.models import AgentRunAttempt
from app.run_state import AttemptClaim, heartbeat
with SessionLocal.begin() as db:
    attempt = db.get(AgentRunAttempt, os.environ["DRILL_ATTEMPT_ID"])
    claim = AttemptClaim(os.environ["DRILL_RUN_ID"], attempt.id, attempt.lease_token)
    accepted = heartbeat(db, claim, lease_seconds=8)
print(json.dumps({"old_lease_write_accepted": accepted}))
""".strip()
    result = compose(
        "exec", "-T",
        "-e", f"DRILL_RUN_ID={run_id}",
        "-e", f"DRILL_ATTEMPT_ID={attempt_id}",
        "runtime-api", "python", "-c", probe,
    )
    return bool(json.loads(result.stdout.strip())["old_lease_write_accepted"])


def run_scenario(base_url: str, token: str, scenario: str, timeout_seconds: int) -> dict:
    stage = "before_external" if scenario == "safe-recovery" else "after_external"
    expected_attempt_status = "running" if scenario == "safe-recovery" else "external_starting"
    created = create_run(base_url, token, scenario)
    run_id = created["run"]["id"]
    victim_worker_id = f"drill-victim-{scenario}"
    recovery_worker_id = f"drill-recovery-{scenario}"

    remove_drill_containers()
    start_drill_worker(VICTIM_CONTAINER, run_id, victim_worker_id, stage=stage)
    claimed = wait_for(
        base_url,
        token,
        run_id,
        lambda item: bool(item.get("current_attempt"))
        and item["current_attempt"]["worker_id"] == victim_worker_id
        and item["current_attempt"]["status"] == expected_attempt_status,
        timeout_seconds,
    )
    first_attempt_id = claimed["current_attempt"]["id"]
    docker("kill", VICTIM_CONTAINER)

    start_drill_worker(RECOVERY_CONTAINER, run_id, recovery_worker_id)
    terminal = wait_for(base_url, token, run_id, lambda item: item["status"] in TERMINAL, timeout_seconds)
    attempts = call(base_url, f"/v1/runs/{run_id}/attempts", token=token)
    timeline = call(base_url, f"/v1/runs/{run_id}/timeline", token=token)
    old_write_accepted = stale_lease_probe(run_id, first_attempt_id)

    if any("lease_token" in attempt for attempt in attempts):
        raise AssertionError("Attempt API exposed a private lease_token")
    if old_write_accepted:
        raise AssertionError("expired victim lease unexpectedly accepted a heartbeat")
    if scenario == "safe-recovery":
        if terminal["status"] != "evidence_accepted" or [item["status"] for item in attempts] != ["lost", "succeeded"]:
            raise AssertionError(f"safe recovery evidence mismatch: status={terminal['status']} attempts={attempts}")
        if attempts[1]["worker_id"] != recovery_worker_id:
            raise AssertionError("the recovery Attempt was not executed by the recovery worker")
    else:
        if terminal["status"] != "unknown" or [item["status"] for item in attempts] != ["unknown"]:
            raise AssertionError(f"unknown boundary evidence mismatch: status={terminal['status']} attempts={attempts}")
        if attempts[0].get("failure_class") != "lease_expired_after_external_dispatch":
            raise AssertionError("unknown failure class did not preserve the external-dispatch boundary")

    return {
        "scenario": scenario,
        "passed": True,
        "runtime_run_id": run_id,
        "commitment_id": created["commitment"]["id"],
        "correlation_id": terminal["correlation_id"],
        "terminal_status": terminal["status"],
        "victim_container_killed": True,
        "old_lease_write_accepted": old_write_accepted,
        "attempts": [{
            "id": item["id"],
            "attempt_no": item["attempt_no"],
            "status": item["status"],
            "worker_id": item["worker_id"],
            "failure_class": item.get("failure_class"),
            "retryability": item["retryability"],
        } for item in attempts],
        "timeline": [{
            "from_status": item["from_status"],
            "to_status": item["to_status"],
            "reason": item["reason"],
            "actor": item["actor"],
        } for item in timeline],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run safe-recovery and unknown-boundary container kill drills.")
    parser.add_argument("--scenario", choices=("safe-recovery", "unknown-after-dispatch", "all"), default="all")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--timeout-seconds", type=int, default=45)
    args = parser.parse_args(argv)

    running_services = set(compose("ps", "--status", "running", "--services").stdout.splitlines())
    restore_regular_worker = "runtime-worker" in running_services
    scenarios = ["safe-recovery", "unknown-after-dispatch"] if args.scenario == "all" else [args.scenario]
    report = {"started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "synthetic_only": True, "scenarios": []}

    try:
        if restore_regular_worker:
            compose("stop", "runtime-worker")
        remove_drill_containers()
        token = login(args.base_url)
        for scenario in scenarios:
            result = run_scenario(args.base_url, token, scenario, args.timeout_seconds)
            report["scenarios"].append(result)
            print(json.dumps(result, ensure_ascii=False), flush=True)
            remove_drill_containers()
    finally:
        remove_drill_containers()
        if restore_regular_worker:
            compose("start", "runtime-worker", check=False)

    report["completed_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    report["passed"] = len(report["scenarios"]) == len(scenarios) and all(item["passed"] for item in report["scenarios"])
    evidence_dir = ROOT / ".runtime" / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    output = evidence_dir / "runtime-failure-drill-latest.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"event": "drill-complete", "passed": report["passed"], "evidence": str(output)}, ensure_ascii=False))
    return 0 if report["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
