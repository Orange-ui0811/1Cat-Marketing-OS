#!/usr/bin/env python3
"""Container-level Runtime reliability acceptance using synthetic work only.

Scenarios:
- four Workers claim a private batch of Runs without duplicate effective execution;
- PostgreSQL is briefly stopped before claim and during heartbeat, then safely recovers;
- a running Run is cancelled only after a deterministic fake Hermes confirms cancellation.
"""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from collections import Counter
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE_URL = "http://127.0.0.1:8080"
WORKER_PREFIX = "1cat-runtime-reliability-worker-"
FAKE_HERMES_CONTAINER = "1cat-runtime-reliability-fake-hermes"
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


def container_running(name: str) -> bool:
    result = docker("inspect", "--format", "{{.State.Running}}", name, check=False)
    return result.returncode == 0 and result.stdout.strip().lower() == "true"


def container_logs(name: str) -> str:
    result = docker("logs", name, check=False)
    return (result.stdout or "") + (result.stderr or "")


def cleanup_containers(worker_count: int = 4) -> None:
    names = [f"{WORKER_PREFIX}{index}" for index in range(1, worker_count + 1)]
    names.extend([f"{WORKER_PREFIX}db-queued", f"{WORKER_PREFIX}db-heartbeat", f"{WORKER_PREFIX}cancel"])
    docker("rm", "-f", *names, FAKE_HERMES_CONTAINER, check=False)


def call(base_url: str, path: str, method: str = "GET", payload=None, token: str | None = None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if method != "GET":
        operation_id = f"runtime-reliability-{uuid.uuid4().hex}"
        headers.update({"X-Correlation-ID": operation_id, "Idempotency-Key": operation_id})
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(base_url + path, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {path}: HTTP {exc.code} {detail}") from exc


def wait_http(base_url: str, timeout_seconds: int = 90) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(base_url + "/health/ready", timeout=5) as response:
                if response.status == 200:
                    return
        except Exception as exc:  # readiness intentionally spans a real outage
            last_error = exc
        time.sleep(1)
    raise TimeoutError(f"Runtime API did not recover: {last_error}")


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


def create_run(base_url: str, token: str, label: str, input_text: str) -> dict:
    suffix = uuid.uuid4().hex[:8]
    commitment = call(base_url, "/v1/commitments", "POST", {
        "title": f"Runtime 可靠性验收 · {label} · {suffix}",
        "proposed_role": "DROLE-01",
        "objective": "使用合成任务验证并发、数据库恢复与取消安全边界。",
        "acceptance": {"runtime_reliability_drill": True, "human_confirmation_required": True},
        "dependencies": [],
        "context": {"source": "runtime-reliability-drill", "pii": False, "scenario": label},
    }, token)
    call(base_url, f"/v1/commitments/{commitment['id']}/transition", "POST", {
        "status": "accepted",
        "reason": "本机管理员批准无真实业务副作用的可靠性演练",
    }, token)
    run = call(base_url, "/v1/runs", "POST", {
        "commitment_id": commitment["id"],
        "role_id": "DROLE-01",
        "input": input_text,
        "context_version": 1,
    }, token)
    return {"commitment": commitment, "run": run}


def start_worker(name: str, worker_id: str, **environment: str) -> None:
    values = {
        "WORKER_ID": worker_id,
        "HERMES_EXECUTION_ENABLED": "false",
        "HERMES_EXECUTION_STATE_FILE": "/runtime-control/reliability-model-disabled.json",
        "RUN_LEASE_SECONDS": "20",
        "RUN_HEARTBEAT_SECONDS": "2",
        "RUN_RECOVERY_SCAN_SECONDS": "1",
        "RUN_MAX_ATTEMPTS": "2",
        "DATABASE_RETRY_INITIAL_SECONDS": "0.5",
        "DATABASE_RETRY_MAX_SECONDS": "2",
        **environment,
    }
    args = ["run", "--no-deps", "-d", "--name", name]
    for key, value in values.items():
        args.extend(["-e", f"{key}={value}"])
    args.append("runtime-worker")
    compose(*args)


def wait_run(base_url: str, token: str, run_id: str, predicate, timeout_seconds: int = 90) -> dict:
    deadline = time.monotonic() + timeout_seconds
    latest = None
    while time.monotonic() < deadline:
        latest = call(base_url, f"/v1/runs/{run_id}", token=token)
        if predicate(latest):
            return latest
        time.sleep(0.25)
    raise TimeoutError(f"Run {run_id} did not reach expected state; latest={latest}")


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def percentile(values: list[float], percentile_value: float) -> float:
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil(percentile_value * len(ordered)) - 1))
    return ordered[index]


def run_concurrency(base_url: str, token: str, run_count: int, worker_count: int) -> dict:
    batch = uuid.uuid4().hex
    input_prefix = f"RUNTIME RELIABILITY BATCH {batch}"
    created = [
        create_run(base_url, token, "multi-worker", f"{input_prefix} item={index}; synthetic only")
        for index in range(1, run_count + 1)
    ]
    if any(item["run"]["status"] != "queued" for item in created):
        raise AssertionError("private concurrency batch was not fully queued before Workers started")

    started = time.monotonic()
    for index in range(1, worker_count + 1):
        start_worker(
            f"{WORKER_PREFIX}{index}",
            f"reliability-concurrency-{index}",
            RUNTIME_CLAIM_INPUT_PREFIX=input_prefix,
            RUNTIME_SIMULATION_DELAY_SECONDS="0.5",
        )

    terminal_runs = [
        wait_run(base_url, token, item["run"]["id"], lambda run: run["status"] in TERMINAL)
        for item in created
    ]
    duration = time.monotonic() - started
    attempt_sets = [
        call(base_url, f"/v1/runs/{run['id']}/attempts", token=token)
        for run in terminal_runs
    ]
    if any(run["status"] != "evidence_accepted" for run in terminal_runs):
        raise AssertionError("one or more concurrency Runs did not succeed")
    if any(len(attempts) != 1 or attempts[0]["status"] != "succeeded" for attempts in attempt_sets):
        raise AssertionError("duplicate or non-successful effective Attempt detected")
    attempt_ids = [attempts[0]["id"] for attempts in attempt_sets]
    if len(attempt_ids) != len(set(attempt_ids)):
        raise AssertionError("an Attempt ID was reused across Runs")
    distribution = Counter(attempts[0]["worker_id"] for attempts in attempt_sets)
    if len(distribution) != worker_count:
        raise AssertionError(f"not all Workers claimed work: {dict(distribution)}")
    claim_delays = [
        max(0.0, (parse_time(attempts[0]["created_at"]) - parse_time(run["created_at"])).total_seconds())
        for run, attempts in zip(terminal_runs, attempt_sets, strict=True)
    ]
    return {
        "scenario": "four-worker-concurrency",
        "passed": True,
        "synthetic_only": True,
        "run_count": run_count,
        "worker_count": worker_count,
        "queue_peak": run_count,
        "total_duration_seconds": round(duration, 3),
        "p95_claim_delay_seconds": round(percentile(claim_delays, 0.95), 3),
        "duplicate_effective_execution_count": 0,
        "worker_distribution": dict(sorted(distribution.items())),
        "run_ids": [run["id"] for run in terminal_runs],
        "attempt_ids": attempt_ids,
    }


def stop_postgres() -> None:
    compose("stop", "-t", "1", "postgres")


def start_postgres(base_url: str) -> None:
    compose("start", "postgres")
    wait_http(base_url)


def run_database_outage_queued(base_url: str, token: str, outage_seconds: float) -> dict:
    created = create_run(
        base_url,
        token,
        "database-before-claim",
        f"RUNTIME DATABASE OUTAGE QUEUED {uuid.uuid4().hex}; synthetic only",
    )
    run_id = created["run"]["id"]
    name = f"{WORKER_PREFIX}db-queued"
    stop_postgres()
    try:
        start_worker(name, "reliability-db-queued", RUNTIME_CLAIM_RUN_ID=run_id)
        time.sleep(outage_seconds)
        if not container_running(name):
            raise AssertionError("Worker exited while PostgreSQL was unavailable before claim")
        unavailable_logged = "database unavailable" in container_logs(name)
        if not unavailable_logged:
            raise AssertionError("Worker did not emit database_unavailable evidence")
    finally:
        start_postgres(base_url)
    terminal = wait_run(base_url, token, run_id, lambda run: run["status"] in TERMINAL)
    attempts = call(base_url, f"/v1/runs/{run_id}/attempts", token=token)
    logs = container_logs(name)
    if terminal["status"] != "evidence_accepted" or len(attempts) != 1 or attempts[0]["status"] != "succeeded":
        raise AssertionError(f"queued outage did not recover safely: terminal={terminal} attempts={attempts}")
    if "database connection recovered" not in logs:
        raise AssertionError("Worker recovery log is missing after PostgreSQL restart")
    return {
        "scenario": "database-outage-before-claim",
        "passed": True,
        "runtime_run_id": run_id,
        "attempt_id": attempts[0]["id"],
        "worker_survived": True,
        "database_unavailable_logged": True,
        "database_recovered_logged": True,
        "terminal_status": terminal["status"],
        "attempt_count": len(attempts),
    }


def run_database_outage_heartbeat(base_url: str, token: str, outage_seconds: float) -> dict:
    created = create_run(
        base_url,
        token,
        "database-during-heartbeat",
        f"RUNTIME DATABASE OUTAGE HEARTBEAT {uuid.uuid4().hex}; synthetic only",
    )
    run_id = created["run"]["id"]
    name = f"{WORKER_PREFIX}db-heartbeat"
    start_worker(
        name,
        "reliability-db-heartbeat",
        RUNTIME_CLAIM_RUN_ID=run_id,
        RUNTIME_DRILL_ENABLED="true",
        RUNTIME_DRILL_STAGE="database_outage",
        RUNTIME_DRILL_DELAY_SECONDS="16",
    )
    running = wait_run(
        base_url,
        token,
        run_id,
        lambda run: run["status"] == "running" and bool(run.get("current_attempt")),
    )
    attempt_id = running["current_attempt"]["id"]
    stop_postgres()
    try:
        time.sleep(outage_seconds)
        if not container_running(name):
            raise AssertionError("Worker exited during PostgreSQL heartbeat outage")
        if "database unavailable" not in container_logs(name):
            raise AssertionError("heartbeat outage did not produce database_unavailable evidence")
    finally:
        start_postgres(base_url)
    terminal = wait_run(base_url, token, run_id, lambda run: run["status"] in TERMINAL)
    attempts = call(base_url, f"/v1/runs/{run_id}/attempts", token=token)
    logs = container_logs(name)
    if terminal["status"] != "evidence_accepted":
        raise AssertionError(f"heartbeat outage did not complete safely: {terminal}")
    if len(attempts) != 1 or attempts[0]["id"] != attempt_id or attempts[0]["status"] != "succeeded":
        raise AssertionError(f"heartbeat outage overwrote or duplicated Attempt history: {attempts}")
    if "database connection recovered operation=heartbeat" not in logs:
        raise AssertionError("heartbeat recovery log is missing")
    return {
        "scenario": "database-outage-during-heartbeat",
        "passed": True,
        "runtime_run_id": run_id,
        "attempt_id": attempt_id,
        "worker_survived": True,
        "lease_revalidated_after_reconnect": True,
        "duplicate_effective_execution_count": 0,
        "terminal_status": terminal["status"],
    }


FAKE_HERMES = r'''
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

state = {"stopped": False}

class Handler(BaseHTTPRequestHandler):
    def send_json(self, payload):
        body = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length:
            self.rfile.read(length)
        if self.path.endswith("/stop"):
            state["stopped"] = True
            print("fake Hermes stop confirmed", flush=True)
            self.send_json({"status": "cancelled"})
        else:
            self.send_json({"run_id": "fake-hermes-cancel-run"})

    def do_GET(self):
        status = "cancelled" if state["stopped"] else "running"
        self.send_json({"run_id": "fake-hermes-cancel-run", "status": status})

    def log_message(self, *_args):
        return

ThreadingHTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
'''.strip()


def start_fake_hermes() -> None:
    compose(
        "run", "--no-deps", "-d", "--name", FAKE_HERMES_CONTAINER,
        "runtime-worker", "python", "-u", "-c", FAKE_HERMES,
    )
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        if container_running(FAKE_HERMES_CONTAINER):
            time.sleep(0.5)
            return
        time.sleep(0.2)
    raise RuntimeError("fake Hermes container did not start")


def run_hermes_timeout(base_url: str, token: str) -> dict:
    created = create_run(
        base_url,
        token,
        "hermes-timeout",
        f"RUNTIME HERMES TIMEOUT {uuid.uuid4().hex}; deterministic fake Hermes only",
    )
    run_id = created["run"]["id"]
    start_fake_hermes()
    name = f"{WORKER_PREFIX}cancel"
    start_worker(
        name,
        "reliability-timeout",
        RUNTIME_CLAIM_RUN_ID=run_id,
        HERMES_EXECUTION_ENABLED="true",
        HERMES_EXECUTION_STATE_FILE="/runtime-control/reliability-force-hermes.json",
        HERMES_PMA_URL=f"http://{FAKE_HERMES_CONTAINER}:8080",
        HERMES_API_KEY_PMA="fake-local-only",
        HERMES_POLL_SECONDS="0.5",
        HERMES_MAX_POLLS="2",
    )
    terminal = wait_run(base_url, token, run_id, lambda run: run["status"] in TERMINAL)
    attempts = call(base_url, f"/v1/runs/{run_id}/attempts", token=token)
    if terminal["status"] != "unknown":
        raise AssertionError(f"timed-out Hermes result did not preserve unknown: {terminal}")
    if (
        len(attempts) != 1
        or attempts[0]["status"] != "unknown"
        or attempts[0].get("failure_class") != "hermes_result_unknown"
        or attempts[0].get("retryability") != "unsafe"
    ):
        raise AssertionError(f"timeout Attempt evidence is inconsistent: {attempts}")
    return {
        "scenario": "hermes-timeout-preserves-unknown",
        "passed": True,
        "runtime_run_id": run_id,
        "attempt_id": attempts[0]["id"],
        "terminal_status": terminal["status"],
        "failure_class": attempts[0]["failure_class"],
        "retryability": attempts[0]["retryability"],
        "automatic_retry_count": 0,
    }


def run_cancellation(base_url: str, token: str) -> dict:
    created = create_run(
        base_url,
        token,
        "running-cancellation",
        f"RUNTIME CANCELLATION {uuid.uuid4().hex}; deterministic fake Hermes only",
    )
    run_id = created["run"]["id"]
    start_fake_hermes()
    name = f"{WORKER_PREFIX}cancel"
    start_worker(
        name,
        "reliability-cancel",
        RUNTIME_CLAIM_RUN_ID=run_id,
        HERMES_EXECUTION_ENABLED="true",
        HERMES_EXECUTION_STATE_FILE="/runtime-control/reliability-force-hermes.json",
        HERMES_PMA_URL=f"http://{FAKE_HERMES_CONTAINER}:8080",
        HERMES_API_KEY_PMA="fake-local-only",
    )
    running = wait_run(
        base_url,
        token,
        run_id,
        lambda run: run["status"] == "running"
        and bool(run.get("current_attempt", {}).get("hermes_run_id")),
    )
    requested = call(base_url, f"/v1/runs/{run_id}/cancel", "POST", token=token)
    if requested["status"] != "running" or not requested.get("cancellation_requested_at"):
        raise AssertionError("running cancellation was applied before Hermes confirmation")
    terminal = wait_run(base_url, token, run_id, lambda run: run["status"] in TERMINAL)
    attempts = call(base_url, f"/v1/runs/{run_id}/attempts", token=token)
    if terminal["status"] != "cancelled":
        raise AssertionError(f"Hermes-confirmed cancellation did not become cancelled: {terminal}")
    if len(attempts) != 1 or attempts[0]["status"] != "cancelled":
        raise AssertionError(f"cancellation Attempt history is inconsistent: {attempts}")
    if "fake Hermes stop confirmed" not in container_logs(FAKE_HERMES_CONTAINER):
        raise AssertionError("fake Hermes did not record the stop confirmation")
    return {
        "scenario": "running-cancel-after-hermes-confirmation",
        "passed": True,
        "runtime_run_id": run_id,
        "attempt_id": running["current_attempt"]["id"],
        "status_immediately_after_request": requested["status"],
        "hermes_stop_confirmed": True,
        "terminal_status": terminal["status"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run synthetic container-level Runtime reliability acceptance.")
    parser.add_argument(
        "--scenario",
        choices=("concurrency", "database", "timeout", "cancellation", "all"),
        default="all",
    )
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--run-count", type=int, default=20)
    parser.add_argument("--worker-count", type=int, default=4)
    parser.add_argument("--database-outage-seconds", type=float, default=6)
    args = parser.parse_args(argv)
    if args.run_count < args.worker_count:
        raise ValueError("run-count must be at least worker-count")

    running_services = set(compose("ps", "--status", "running", "--services").stdout.splitlines())
    restore_regular_worker = "runtime-worker" in running_services
    report = {
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "synthetic_only": True,
        "scenarios": [],
    }
    postgres_stopped = False
    try:
        wait_http(args.base_url)
        token = login(args.base_url)
        if restore_regular_worker:
            compose("stop", "runtime-worker")
        cleanup_containers(args.worker_count)
        if args.scenario in {"concurrency", "all"}:
            report["scenarios"].append(run_concurrency(
                args.base_url, token, args.run_count, args.worker_count,
            ))
            cleanup_containers(args.worker_count)
        if args.scenario in {"database", "all"}:
            postgres_stopped = True
            report["scenarios"].append(run_database_outage_queued(
                args.base_url, token, args.database_outage_seconds,
            ))
            postgres_stopped = False
            cleanup_containers(args.worker_count)
            postgres_stopped = True
            report["scenarios"].append(run_database_outage_heartbeat(
                args.base_url, token, args.database_outage_seconds,
            ))
            postgres_stopped = False
            cleanup_containers(args.worker_count)
        if args.scenario in {"timeout", "all"}:
            report["scenarios"].append(run_hermes_timeout(args.base_url, token))
            cleanup_containers(args.worker_count)
        if args.scenario in {"cancellation", "all"}:
            report["scenarios"].append(run_cancellation(args.base_url, token))
    finally:
        if postgres_stopped:
            compose("start", "postgres", check=False)
            try:
                wait_http(args.base_url)
            except Exception:
                pass
        cleanup_containers(args.worker_count)
        if restore_regular_worker:
            compose("start", "runtime-worker", check=False)

    report["completed_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    report["passed"] = bool(report["scenarios"]) and all(item["passed"] for item in report["scenarios"])
    evidence_dir = ROOT / ".runtime" / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    output = evidence_dir / "runtime-reliability-drill-latest.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    for item in report["scenarios"]:
        print(json.dumps(item, ensure_ascii=False), flush=True)
    print(json.dumps({"event": "reliability-drill-complete", "passed": report["passed"], "evidence": str(output)}, ensure_ascii=False))
    return 0 if report["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
