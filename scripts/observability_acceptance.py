#!/usr/bin/env python3
"""Run or inspect one real Agent Run and verify its observability evidence."""

from __future__ import annotations

import argparse
import base64
import json
import subprocess
import time
import urllib.parse
import urllib.request

from real_agent_demo import ROOT, call, login, run_role


JAEGER = "http://127.0.0.1:16686"
PROMETHEUS = "http://127.0.0.1:9090"
GRAFANA = "http://127.0.0.1:3000"


def get_json(url: str, headers: dict[str, str] | None = None) -> dict:
    request = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def optional_env(name: str, default: str) -> str:
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith(name + "="):
            return line.split("=", 1)[1] or default
    return default


def prometheus_series(expression: str) -> int:
    encoded = urllib.parse.quote(expression, safe="")
    response = get_json(f"{PROMETHEUS}/api/v1/query?query={encoded}")
    return len(response.get("data", {}).get("result", []))


def structured_logs(since: str) -> list[dict]:
    process = subprocess.run(
        [
            "docker", "compose", "logs", "--since", since,
            "runtime-api", "runtime-worker", "organization-mcp",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    )
    records: list[dict] = []
    for line in process.stdout.splitlines():
        start = line.find("{")
        if start < 0:
            continue
        try:
            records.append(json.loads(line[start:]))
        except json.JSONDecodeError:
            continue
    return records


def inspect_run(run_id: str, export_wait_seconds: int, log_since: str) -> dict:
    token = login()
    run = call(f"/v1/runs/{run_id}", token=token, prefix="observability")
    attempts = call(f"/v1/runs/{run_id}/attempts", token=token, prefix="observability")
    timeline = call(f"/v1/runs/{run_id}/timeline", token=token, prefix="observability")
    attempt = run.get("current_attempt") or (attempts[-1] if attempts else {})
    trace_id = run.get("trace_id")
    if not trace_id:
        raise RuntimeError("Run has no persisted Trace ID; create a Run after observability is enabled")

    deadline = time.monotonic() + export_wait_seconds
    trace_response: dict = {}
    while time.monotonic() < deadline:
        trace_response = get_json(f"{JAEGER}/api/traces/{trace_id}")
        if trace_response.get("data"):
            break
        time.sleep(2)
    trace = (trace_response.get("data") or [{}])[0]
    processes = trace.get("processes", {})
    services = sorted({item.get("serviceName") for item in processes.values() if item.get("serviceName")})

    linked_mcp_spans: list[dict] = []
    mcp_response = get_json(f"{JAEGER}/api/traces?service=1cat-organization-mcp&lookback=1h&limit=100")
    for mcp_trace in mcp_response.get("data", []):
        for span in mcp_trace.get("spans", []):
            for reference in span.get("references", []):
                if reference.get("traceID") == trace_id:
                    linked_mcp_spans.append({
                        "trace_id": mcp_trace.get("traceID"),
                        "operation": span.get("operationName"),
                        "reference": reference.get("refType"),
                    })

    metric_names = (
        "onecat_run_created_total",
        "onecat_run_terminal_total",
        "onecat_run_duration_seconds_count",
        "onecat_run_queue_depth",
        "onecat_run_queue_age_seconds",
        "onecat_mcp_call_total",
    )
    metric_series = {name: prometheus_series(name) for name in metric_names}

    password = optional_env("GRAFANA_ADMIN_PASSWORD", "onecat-observe")
    credential = base64.b64encode(f"admin:{password}".encode()).decode()
    dashboard = get_json(
        f"{GRAFANA}/api/dashboards/uid/onecat-runtime-overview",
        {"Authorization": f"Basic {credential}"},
    ).get("dashboard", {})

    logs = structured_logs(log_since)
    correlation_id = run.get("correlation_id")
    attempt_id = attempt.get("id")
    linked_mcp_trace_ids = {item["trace_id"] for item in linked_mcp_spans}

    def has_log(logger: str, *, require_attempt: bool = False) -> bool:
        return any(
            item.get("logger") == logger
            and item.get("run_id") == run_id
            and item.get("correlation_id") == correlation_id
            and item.get("trace_id") == trace_id
            and (not require_attempt or item.get("attempt_id") == attempt_id)
            for item in logs
        )

    def has_linked_mcp_log() -> bool:
        return any(
            item.get("logger") == "1cat.organization-mcp"
            and item.get("run_id") == run_id
            and item.get("correlation_id") == correlation_id
            and item.get("attempt_id") == attempt_id
            and item.get("trace_id") in linked_mcp_trace_ids
            for item in logs
        )

    checks = {
        "runtime_terminal": run.get("status") == "evidence_accepted",
        "timeline_persisted": bool(timeline) and timeline[-1].get("to_status") == run.get("status"),
        "api_worker_trace": {"1cat-runtime-api", "1cat-runtime-worker"}.issubset(services),
        "mcp_span_link": bool(linked_mcp_spans),
        "prometheus_metrics": all(metric_series.values()),
        "grafana_dashboard": dashboard.get("uid") == "onecat-runtime-overview" and len(dashboard.get("panels", [])) >= 10,
        "api_structured_log": has_log("1cat.runtime.api"),
        "worker_structured_log": has_log("1cat.worker", require_attempt=True),
        "mcp_structured_log": has_linked_mcp_log(),
    }
    return {
        "passed": all(checks.values()),
        "run_id": run_id,
        "correlation_id": correlation_id,
        "trace_id": trace_id,
        "attempt_id": attempt_id,
        "hermes_run_id": attempt.get("hermes_run_id"),
        "runtime_status": run.get("status"),
        "services": services,
        "span_count": len(trace.get("spans", [])),
        "linked_mcp_spans": linked_mcp_spans,
        "metric_series": metric_series,
        "grafana": {
            "title": dashboard.get("title"),
            "version": dashboard.get("version"),
            "panels": len(dashboard.get("panels", [])),
        },
        "checks": checks,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify Trace, metrics, logs and timeline for one real Run.")
    parser.add_argument("--run-id", help="Inspect an existing Run instead of creating a new real Run")
    parser.add_argument("--role", choices=("pma", "bga", "mo"), default="pma")
    parser.add_argument("--timeout-seconds", type=int, default=900)
    parser.add_argument("--export-wait-seconds", type=int, default=30)
    parser.add_argument("--log-since", default="30m")
    args = parser.parse_args(argv)

    run_id = args.run_id
    if not run_id:
        real_result = run_role(args.role, args.timeout_seconds)
        run_id = real_result["runtime_run_id"]
    time.sleep(6)
    result = inspect_run(run_id, args.export_wait_seconds, args.log_since)
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
