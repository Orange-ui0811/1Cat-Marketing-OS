#!/usr/bin/env python3
"""Validate the Week 8 portfolio package without exposing secrets or mutating runtime data."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_DIR = PROJECT_ROOT / ".runtime" / "evidence"


@dataclass
class Check:
    name: str
    passed: bool
    detail: str


def require_tokens(path: Path, tokens: tuple[str, ...]) -> Check:
    relative = path.relative_to(PROJECT_ROOT).as_posix()
    if not path.is_file():
        return Check(f"artifact:{relative}", False, "file missing")
    content = path.read_text(encoding="utf-8")
    missing = [token for token in tokens if token not in content]
    if missing:
        return Check(f"artifact:{relative}", False, f"missing markers: {', '.join(missing)}")
    return Check(f"artifact:{relative}", True, f"{len(content)} UTF-8 characters")


def validate_drill_evidence(filename: str, expected_scenarios: int) -> Check:
    path = EVIDENCE_DIR / filename
    if not path.is_file():
        return Check(f"evidence:{filename}", False, "run the corresponding drill first")
    try:
        payload: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return Check(f"evidence:{filename}", False, f"invalid JSON: {exc}")
    scenarios = payload.get("scenarios", [])
    passed = payload.get("passed") is True and len(scenarios) == expected_scenarios
    passed = passed and all(item.get("passed") is True for item in scenarios)
    detail = f"{sum(item.get('passed') is True for item in scenarios)}/{expected_scenarios} scenarios passed"
    return Check(f"evidence:{filename}", passed, detail)


def validate_workflow_evidence(filename: str, *, observability: bool = False) -> Check:
    path = EVIDENCE_DIR / filename
    if not path.is_file():
        return Check(f"evidence:{filename}", False, "run the complete Marketing Workflow acceptance first")
    try:
        payload: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return Check(f"evidence:{filename}", False, f"invalid JSON: {exc}")
    if observability:
        checks = payload.get("checks") or {}
        passed = payload.get("passed") is True and bool(checks) and all(checks.values())
        return Check(
            f"evidence:{filename}",
            passed,
            f"{sum(value is True for value in checks.values())}/{len(checks)} observability checks passed",
        )
    summary = payload.get("summary") or {}
    kinds = summary.get("knowledge_kinds") or {}
    boundary = summary.get("boundary") or {}
    passed = (
        summary.get("status") == "completed"
        and summary.get("stage_count") == 9
        and summary.get("run_count", 0) >= 4
        and set(summary.get("run_statuses") or []) == {"evidence_accepted"}
        and all(kinds.get(kind, 0) >= count for kind, count in {
            "review": 2, "fact": 1, "claim": 1, "campaign": 1, "content": 1,
        }.items())
        and boundary == {
            "publishing": "simulated", "external_effect": False,
            "pii": False, "business_outcome_claimed": False,
        }
    )
    return Check(
        f"evidence:{filename}",
        passed,
        f"case={summary.get('case_id')}, stages={summary.get('stage_count')}, runs={summary.get('run_count')}",
    )


def http_check(name: str, url: str, timeout: float, json_key: tuple[str, str] | None = None) -> Check:
    request = urllib.request.Request(url, headers={"User-Agent": "1cat-week8-readiness/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read(256_000)
            status = response.status
    except (OSError, urllib.error.URLError) as exc:
        return Check(f"online:{name}", False, str(exc))
    if status != 200:
        return Check(f"online:{name}", False, f"HTTP {status}")
    if json_key:
        try:
            payload = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            return Check(f"online:{name}", False, f"invalid JSON: {exc}")
        key, expected = json_key
        if str(payload.get(key)) != expected:
            return Check(f"online:{name}", False, f"{key}={payload.get(key)!r}, expected {expected!r}")
    return Check(f"online:{name}", True, f"HTTP {status}")


def artifact_checks() -> list[Check]:
    portfolio = PROJECT_ROOT / "docs" / "portfolio"
    return [
        require_tokens(portfolio / "README.md", ("portfolio-check", "独立新环境复现")),
        require_tokens(
            portfolio / "Agent_Runtime_架构一页图.md",
            ("flowchart TB", "stateDiagram-v2", "unknown/unsafe", "明确边界"),
        ),
        require_tokens(
            portfolio / "5到8分钟演示脚本.md",
            ("三 Agent 完整业务闭环", "Worker 崩溃恢复", "`unknown` 安全边界", "全链路可观测性"),
        ),
        require_tokens(
            portfolio / "简历项目描述与岗位映射.md",
            ("4 Worker × 20 Run", "与 AI Agent 系统平台实习岗位的对应关系", "不要写进简历"),
        ),
        require_tokens(
            portfolio / "面试讲解稿.md",
            ("90 秒项目介绍", "Lease、Heartbeat、Fencing", "为什么需要 `unknown`", "下一步怎么演进"),
        ),
        require_tokens(
            portfolio / "独立环境复现清单.md",
            ("无模型基线", "可靠性与观测", "可选真实 DeepSeek 验收", "最终签字"),
        ),
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Week 8 portfolio readiness")
    parser.add_argument("--online", action="store_true", help="also check the running local stack")
    parser.add_argument("--write-evidence", action="store_true", help="write a machine-readable result")
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    parser.add_argument("--timeout", type=float, default=5.0)
    args = parser.parse_args()

    checks = artifact_checks()
    checks.extend(
        [
            validate_drill_evidence("runtime-failure-drill-latest.json", 2),
            validate_drill_evidence("runtime-reliability-drill-latest.json", 5),
            validate_workflow_evidence("marketing-workflow-demo-synthetic-latest.json"),
            validate_workflow_evidence("marketing-workflow-demo-real-latest.json"),
            validate_workflow_evidence("marketing-workflow-observability-latest.json", observability=True),
        ]
    )
    if args.online:
        checks.extend(
            [
                http_check("workspace", args.base_url, args.timeout),
                http_check("runtime-ready", f"{args.base_url}/health/ready", args.timeout, ("status", "ready")),
                http_check("jaeger", "http://127.0.0.1:16686/", args.timeout),
                http_check("prometheus", "http://127.0.0.1:9090/-/ready", args.timeout),
                http_check("grafana", "http://127.0.0.1:3000/api/health", args.timeout, ("database", "ok")),
            ]
        )

    passed = all(check.passed for check in checks)
    for check in checks:
        mark = "PASS" if check.passed else "FAIL"
        print(f"[{mark}] {check.name}: {check.detail}")
    print(f"Week 8 readiness: {'PASS' if passed else 'FAIL'} ({sum(c.passed for c in checks)}/{len(checks)})")

    if args.write_evidence:
        EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
        output = EVIDENCE_DIR / "week8-readiness-latest.json"
        payload = {
            "checked_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "online_checks_enabled": args.online,
            "secret_material_read": False,
            "runtime_data_mutated": False,
            "checks": [asdict(check) for check in checks],
            "passed": passed,
        }
        output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Evidence: {output}")

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
