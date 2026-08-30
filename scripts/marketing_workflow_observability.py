#!/usr/bin/env python3
"""Cross-locate one complete Marketing Case across every local observability surface."""

from __future__ import annotations

import argparse
import base64
import json
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from observability_acceptance import (
    GRAFANA,
    JAEGER,
    get_json,
    optional_env,
    prometheus_series,
    structured_logs,
)
from real_agent_demo import ROOT, call, login


EVIDENCE_DIR = ROOT / ".runtime" / "evidence"
LATEST_EVIDENCE = EVIDENCE_DIR / "marketing-workflow-observability-latest.json"
EXPECTED_STAGES = {"mo_plan", "pma", "bga", "mo_retrospective"}


def postgres_counts(case_id: str) -> dict[str, int]:
    if not re.fullmatch(r"case_[a-zA-Z0-9]+", case_id):
        raise ValueError("invalid Marketing Case ID")
    user = optional_env("POSTGRES_USER", "onecat")
    database = optional_env("POSTGRES_DB", "onecat")
    query = (
        "SELECT "
        f"(SELECT COUNT(*) FROM marketing_cases WHERE id='{case_id}'),"
        f"(SELECT COUNT(*) FROM marketing_case_steps WHERE case_id='{case_id}'),"
        f"(SELECT COUNT(*) FROM collaboration_agent_runs WHERE case_id='{case_id}'),"
        f"(SELECT COUNT(*) FROM marketing_case_resources WHERE case_id='{case_id}');"
    )
    process = subprocess.run(
        [
            "docker", "compose", "exec", "-T", "postgres", "psql",
            "-U", user, "-d", database, "-At", "-F", ",", "-c", query,
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    )
    values = [int(value) for value in process.stdout.strip().split(",")]
    return dict(zip(("cases", "steps", "runs", "resources"), values, strict=True))


def wait_for_trace(trace_id: str, timeout_seconds: int) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        response = get_json(f"{JAEGER}/api/traces/{trace_id}")
        if response.get("data"):
            return response["data"][0]
        time.sleep(2)
    return {}


def linked_mcp_index() -> dict[str, list[dict[str, str]]]:
    result: dict[str, list[dict[str, str]]] = {}
    response = get_json(f"{JAEGER}/api/traces?service=1cat-organization-mcp&lookback=1h&limit=300")
    for trace in response.get("data", []):
        for span in trace.get("spans", []):
            for reference in span.get("references", []):
                parent = reference.get("traceID")
                if parent:
                    result.setdefault(parent, []).append({
                        "trace_id": trace.get("traceID", ""),
                        "operation": span.get("operationName", ""),
                        "reference": reference.get("refType", ""),
                    })
    return result


def dashboard_snapshot() -> dict[str, Any]:
    password = optional_env("GRAFANA_ADMIN_PASSWORD", "onecat-observe")
    credential = base64.b64encode(f"admin:{password}".encode()).decode()
    dashboard = get_json(
        f"{GRAFANA}/api/dashboards/uid/onecat-runtime-overview",
        {"Authorization": f"Basic {credential}"},
    ).get("dashboard", {})
    panels = dashboard.get("panels", [])
    return {
        "uid": dashboard.get("uid"),
        "title": dashboard.get("title"),
        "version": dashboard.get("version"),
        "panel_count": len(panels),
        "marketing_panels": [panel.get("title") for panel in panels if (panel.get("id") or 0) >= 12],
        "tags": dashboard.get("tags", []),
    }


def inspect_case(case_id: str, *, trace_wait_seconds: int, log_since: str) -> dict[str, Any]:
    token = login()
    case = call(f"/v1/marketing-cases/{case_id}", token=token, prefix="workflow-observability")
    run_refs = [item for item in case.get("resources", []) if item.get("resource_type") == "run"]
    runs: list[dict[str, Any]] = []
    for ref in run_refs:
        run_id = ref["resource_id"]
        run = call(f"/v1/runs/{run_id}", token=token, prefix="workflow-observability")
        attempts = call(f"/v1/runs/{run_id}/attempts", token=token, prefix="workflow-observability")
        timeline = call(f"/v1/runs/{run_id}/timeline", token=token, prefix="workflow-observability")
        runs.append({"run": run, "attempts": attempts, "timeline": timeline})

    trace_payloads: dict[str, dict[str, Any]] = {}
    for item in runs:
        trace_id = item["run"].get("trace_id")
        if trace_id:
            trace_payloads[trace_id] = wait_for_trace(trace_id, trace_wait_seconds)
    mcp_links = linked_mcp_index()
    logs = structured_logs(log_since)
    db_counts = postgres_counts(case_id)
    dashboard = dashboard_snapshot()

    run_results: list[dict[str, Any]] = []
    for item in runs:
        run = item["run"]
        attempt = run.get("current_attempt") or (item["attempts"][-1] if item["attempts"] else {})
        trace_id = run.get("trace_id")
        trace = trace_payloads.get(trace_id, {})
        processes = trace.get("processes", {})
        services = sorted({value.get("serviceName") for value in processes.values() if value.get("serviceName")})
        matching_logs = [entry for entry in logs if entry.get("case_id") == case_id and entry.get("run_id") == run["id"]]
        run_results.append({
            "run_id": run["id"],
            "stage_key": run.get("stage_key"),
            "status": run.get("status"),
            "execution_mode": run.get("execution_mode"),
            "attempt_id": attempt.get("id"),
            "hermes_run_id": attempt.get("hermes_run_id"),
            "trace_id": trace_id,
            "trace_services": services,
            "span_count": len(trace.get("spans", [])),
            "mcp_span_links": mcp_links.get(trace_id, []),
            "structured_loggers": sorted({entry.get("logger") for entry in matching_logs if entry.get("logger")}),
            "timeline_terminal": bool(item["timeline"]) and item["timeline"][-1].get("to_status") == run.get("status"),
        })

    metric_names = (
        "onecat_marketing_case_created_total",
        "onecat_marketing_case_completed_total",
        "onecat_marketing_stage_duration_seconds_count",
        "onecat_marketing_case_active",
        "onecat_run_terminal_total",
        "onecat_mcp_call_total",
    )
    metric_series = {name: prometheus_series(name) for name in metric_names}
    case_logs = [entry for entry in logs if entry.get("case_id") == case_id]
    case_loggers = sorted({entry.get("logger") for entry in case_logs if entry.get("logger")})
    observed_stages = {item["stage_key"] for item in run_results}
    retry_count = max(0, len(run_results) - len(observed_stages))
    checks = {
        "frontend_api_case": case.get("id") == case_id and len(case.get("stages", [])) == 9,
        "case_completed": case.get("status") == "completed",
        "real_mode": case.get("execution_mode") == "real",
        "terminal_agent_runs": len(run_results) >= 4 and all(
            item["status"] == "evidence_accepted" for item in run_results
        ),
        "stage_coverage": observed_stages == EXPECTED_STAGES,
        "attempts_and_hermes": all(item["attempt_id"] and item["hermes_run_id"] for item in run_results),
        "trace_coverage": all(
            {"1cat-runtime-api", "1cat-runtime-worker"}.issubset(item["trace_services"])
            and item["span_count"] > 0
            for item in run_results
        ),
        "mcp_span_links": all(item["mcp_span_links"] for item in run_results),
        # Docker log retention is container-lifetime scoped.  A force-recreate
        # can remove older run logs while Jaeger/Postgres retain their evidence,
        # so require all three services at Case scope and one fully correlated
        # run instead of pretending old container logs are durable storage.
        "structured_logs": {"1cat.runtime.api", "1cat.worker", "1cat.organization-mcp"}.issubset(
            set(case_loggers)
        ) and any(
            {"1cat.worker", "1cat.organization-mcp"}.issubset(set(item["structured_loggers"]))
            for item in run_results
        ),
        "database_rows": db_counts["cases"] == 1 and db_counts["steps"] == 9
        and db_counts["runs"] == len(run_results) and db_counts["resources"] > 0,
        "prometheus_metrics": all(metric_series.values()),
        "grafana_marketing_workflow": dashboard["uid"] == "onecat-runtime-overview"
        and dashboard["version"] >= 4
        and dashboard["panel_count"] >= 20
        and "Marketing Workflow" in dashboard["marketing_panels"],
        "safe_publish_boundary": case.get("boundary") == {
            "publishing": "simulated", "external_effect": False, "pii": False, "business_outcome_claimed": False,
        },
    }


def write_evidence(result: dict[str, Any]) -> list[Path]:
    """Preserve mode-specific evidence and only advance canonical latest on a full pass."""
    mode = str(result.get("execution_mode") or "unknown")
    if mode not in {"synthetic", "real"}:
        mode = "unknown"
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    mode_path = EVIDENCE_DIR / f"marketing-workflow-observability-{mode}-latest.json"
    mode_path.write_text(payload, encoding="utf-8")
    paths = [mode_path]
    if result.get("passed") is True:
        LATEST_EVIDENCE.write_text(payload, encoding="utf-8")
        paths.append(LATEST_EVIDENCE)
    return paths
    return {
        "checked_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "passed": all(checks.values()),
        "case_id": case_id,
        "case_status": case.get("status"),
        "execution_mode": case.get("execution_mode"),
        "case_version": case.get("version"),
        "safe_retry_count": retry_count,
        "runs": run_results,
        "database": db_counts,
        "prometheus": metric_series,
        "grafana": dashboard,
        "case_log_count": len(case_logs),
        "case_loggers": case_loggers,
        "checks": checks,
        "boundary": case.get("boundary"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify one complete Marketing Case across API/DB/logs/Jaeger/Prometheus/Grafana.")
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--trace-wait-seconds", type=int, default=45)
    parser.add_argument("--log-since", default="30m")
    args = parser.parse_args(argv)
    result = inspect_case(args.case_id, trace_wait_seconds=args.trace_wait_seconds, log_since=args.log_since)
    evidence_paths = write_evidence(result)
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
    for path in evidence_paths:
        print(f"Evidence: {path}", flush=True)
    if result["passed"] is not True:
        print("Canonical latest evidence was not replaced because this acceptance did not fully pass.", flush=True)
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
