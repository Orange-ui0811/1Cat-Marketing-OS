from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import random
import socket
import time
import uuid
from collections.abc import Callable
from typing import TypeVar

import httpx
from sqlalchemy import select
from sqlalchemy.exc import DisconnectionError, InterfaceError, OperationalError

from app.db import SessionLocal, engine
from app.models import AgentRun, AgentRunAttempt, Outbox
from app.marketing_case import prepare_synthetic_candidates
from app.observability import attempt_span, configure_observability, metrics
from app.run_state import (
    AttemptClaim,
    StaleLease,
    claim_next_run,
    finish_failure_or_requeue,
    finish_success,
    finish_terminal,
    heartbeat,
    mark_external_starting,
    mark_running,
    recover_expired,
    set_hermes_run,
)
from app.worker_resilience import database_retry_delay, lease_authority_expired

configure_observability(service_name="1cat-runtime-worker", engine=engine)
log = logging.getLogger("1cat.worker")

HERMES_ENABLED_DEFAULT = os.getenv("HERMES_EXECUTION_ENABLED", "false").lower() == "true"
HERMES_EXECUTION_STATE_FILE = os.getenv("HERMES_EXECUTION_STATE_FILE", "/runtime-control/model-runtime.json")
MODEL_PROVIDER = os.getenv("HERMES_MODEL_PROVIDER", "deepseek")
MODEL_ID = os.getenv("HERMES_MODEL_ID", "deepseek-v4-pro")
LEASE_SECONDS = int(os.getenv("RUN_LEASE_SECONDS", "30"))
HEARTBEAT_SECONDS = int(os.getenv("RUN_HEARTBEAT_SECONDS", "10"))
RECOVERY_SCAN_SECONDS = int(os.getenv("RUN_RECOVERY_SCAN_SECONDS", "5"))
MAX_ATTEMPTS = int(os.getenv("RUN_MAX_ATTEMPTS", "2"))
HERMES_POLL_SECONDS = max(0.1, float(os.getenv("HERMES_POLL_SECONDS", "2")))
HERMES_MAX_POLLS = max(1, int(os.getenv("HERMES_MAX_POLLS", "360")))
WORKER_ID = os.getenv("WORKER_ID") or f"{socket.gethostname()}-{uuid.uuid4().hex[:8]}"
CLAIM_RUN_ID = os.getenv("RUNTIME_CLAIM_RUN_ID") or None
CLAIM_INPUT_PREFIX = os.getenv("RUNTIME_CLAIM_INPUT_PREFIX") or None
DRILL_ENABLED = os.getenv("RUNTIME_DRILL_ENABLED", "false").lower() == "true"
DRILL_STAGE = os.getenv("RUNTIME_DRILL_STAGE", "none").lower()
DRILL_DELAY_SECONDS = max(1, int(os.getenv("RUNTIME_DRILL_DELAY_SECONDS", "60")))
DRILL_ATTEMPT_NO = max(1, int(os.getenv("RUNTIME_DRILL_ATTEMPT_NO", "1")))
SIMULATION_DELAY_SECONDS = max(0.0, float(os.getenv("RUNTIME_SIMULATION_DELAY_SECONDS", "0")))
DATABASE_RETRY_INITIAL_SECONDS = max(0.1, float(os.getenv("DATABASE_RETRY_INITIAL_SECONDS", "1")))
DATABASE_RETRY_MAX_SECONDS = max(
    DATABASE_RETRY_INITIAL_SECONDS,
    float(os.getenv("DATABASE_RETRY_MAX_SECONDS", "10")),
)
PROFILE = {
    "pma": (os.getenv("HERMES_PMA_URL", "http://hermes-pma:8080"), os.getenv("HERMES_API_KEY_PMA", "")),
    "bga": (os.getenv("HERMES_BGA_URL", "http://hermes-bga:8080"), os.getenv("HERMES_API_KEY_BGA", "")),
    "mo": (os.getenv("HERMES_MO_URL", "http://hermes-mo:8080"), os.getenv("HERMES_API_KEY_MO", "")),
}
PROFILE_ROOT = os.getenv("PROFILE_ROOT", "/profiles")
ROLE = {"pma": "DROLE-01", "bga": "DROLE-02", "mo": "DROLE-03"}
CANDIDATE_KINDS_BY_PROFILE = {
    "pma": "brief, evidence, fact, claim",
    "bga": "campaign, content, review",
    "mo": "review",
}

DATABASE_UNAVAILABLE_ERRORS = (OperationalError, InterfaceError, DisconnectionError)
T = TypeVar("T")


def run_log_fields(
    run: AgentRun | None = None,
    attempt: AgentRunAttempt | None = None,
    *,
    run_id: str | None = None,
    attempt_id: str | None = None,
    correlation_id: str | None = None,
    hermes_run_id: str | None = None,
) -> dict[str, str]:
    fields = {
        "run_id": run_id or (run.id if run else None),
        "attempt_id": attempt_id or (attempt.id if attempt else None),
        "correlation_id": correlation_id or (run.correlation_id if run else None),
        "hermes_run_id": hermes_run_id or (attempt.hermes_run_id if attempt else None),
        "worker_id": WORKER_ID,
        "case_id": run.case_id if run else None,
        "stage_key": run.stage_key if run else None,
    }
    return {key: value for key, value in fields.items() if value}


def retry_seconds(failure_count: int) -> float:
    return database_retry_delay(
        failure_count,
        initial_seconds=DATABASE_RETRY_INITIAL_SECONDS,
        maximum_seconds=DATABASE_RETRY_MAX_SECONDS,
        jitter_sample=random.random(),
    )


def dispose_database_connections() -> None:
    """Discard pooled connections after PostgreSQL has restarted."""
    engine.dispose()


def log_database_unavailable(
    operation: str,
    failure_count: int,
    delay: float,
    exc: BaseException,
    *,
    claim: AttemptClaim | None = None,
) -> None:
    metrics.add(metrics.database_unavailable, operation=operation)
    log.warning(
        "database unavailable operation=%s failure_count=%s retry_seconds=%.2f error=%s",
        operation,
        failure_count,
        delay,
        type(exc).__name__,
        extra={
            **run_log_fields(
                run_id=claim.run_id if claim else None,
                attempt_id=claim.attempt_id if claim else None,
            ),
            "operation": operation,
            "failure_count": failure_count,
            "retry_seconds": round(delay, 3),
            "outcome": "database_unavailable",
        },
    )


async def retry_database_operation(
    operation: Callable[[], T],
    *,
    name: str,
    claim: AttemptClaim,
    lease_lost: asyncio.Event,
) -> T:
    """Retry coordinator writes only while the current Attempt may still own its lease."""
    failures = 0
    while not lease_lost.is_set():
        try:
            result = operation()
            if failures:
                log.info(
                    "database connection recovered operation=%s failure_count=%s",
                    name,
                    failures,
                    extra={
                        **run_log_fields(run_id=claim.run_id, attempt_id=claim.attempt_id),
                        "operation": name,
                        "failure_count": failures,
                        "outcome": "database_recovered",
                    },
                )
            return result
        except DATABASE_UNAVAILABLE_ERRORS as exc:
            failures += 1
            delay = retry_seconds(failures)
            dispose_database_connections()
            log_database_unavailable(name, failures, delay, exc, claim=claim)
            try:
                await asyncio.wait_for(lease_lost.wait(), timeout=delay)
            except asyncio.TimeoutError:
                pass
    raise StaleLease("database authority could not be revalidated before lease expiry")


def hermes_enabled() -> bool:
    try:
        with open(HERMES_EXECUTION_STATE_FILE, encoding="utf-8") as state_file:
            value = json.load(state_file).get("execution_enabled")
        if isinstance(value, bool):
            return value
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        pass
    return HERMES_ENABLED_DEFAULT


def claim_uses_real_execution(claim: AttemptClaim) -> bool:
    with SessionLocal() as db:
        run = db.get(AgentRun, claim.run_id)
        return execution_mode_uses_real(run.execution_mode if run else None)


def execution_mode_uses_real(execution_mode: str | None) -> bool:
    """Explicit Case mode wins; null preserves the behavior of historical Runs."""
    if execution_mode is None:
        return hermes_enabled()
    return execution_mode == "real"


def tool_contract_instruction(profile_id: str) -> str:
    allowed = CANDIDATE_KINDS_BY_PROFILE[profile_id]
    return (
        f"object_create_candidate.kind只能逐字使用以下值之一：{allowed}。"
        "禁止使用ProductFactCandidate、ClaimCandidate等对象名代替kind。"
        "禁止调用tool_search或get_prompt寻找参数说明；需要时调用candidate_kinds_read。"
        "任一Tool因参数校验失败时，修正后最多重试一次；再次失败必须停止调用该Tool，"
        "在最终候选中说明未持久化及需人工处理，不得循环重试。"
        "当前Run启动前Commitment已经是accepted；标准执行中不要调用commitment_respond去activate或submit，"
        "Runtime Worker会在Hermes成功后原子推进到submitted。只有确认无法安全继续时，才可逐字使用"
        "request_takeover或pause请求人工介入，不能使用submitted、active等状态名代替action。"
    )


def profile_instructions(profile_id: str, commitment_id: str, attempt_id: str) -> str:
    """Build a stable, read-only prompt from the signed profile bundle.

    Hermes' mutable skill management tool is intentionally disabled. R0 skills
    are loaded by the trusted worker and supplied as immutable run instructions.
    """
    root = os.path.join(PROFILE_ROOT, profile_id)
    parts = [
        "1Cat Hermes OS R0受控岗位运行。只能调用organization-runtime MCP；禁止终端、文件、浏览器、任意HTTP、Cron、A2A和平台写入。",
        f"调用每个Tool时必须使用 role_id={ROLE[profile_id]}、profile_id={profile_id}、commitment_id={commitment_id}、attempt_id={attempt_id}。",
        "任何产出只能创建候选或送审；运行成功最多把Commitment推进到submitted，不能声称已发布、已履约或已完成业务验收。",
        tool_contract_instruction(profile_id),
    ]
    for name in ("SOUL.md", "ROLE_MANIFEST.md", "DAILY_OPERATION.md", "MEMORY_POLICY.md", "TOOL_ALLOWLIST.md"):
        path = os.path.join(root, name)
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as handle:
                parts.append(f"\n## {name}\n{handle.read()}")
    skills_root = os.path.join(root, "skills")
    if os.path.isdir(skills_root):
        for skill_name in sorted(os.listdir(skills_root)):
            path = os.path.join(skills_root, skill_name, "SKILL.md")
            if os.path.isfile(path):
                with open(path, encoding="utf-8") as handle:
                    parts.append(f"\n## Skill {skill_name}\n{handle.read()}")
    return "\n".join(parts)


def canonical_hash(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()


def claim_run() -> AttemptClaim | None:
    with SessionLocal.begin() as db:
        claim = claim_next_run(
            db,
            WORKER_ID,
            LEASE_SECONDS,
            run_id=CLAIM_RUN_ID,
            input_prefix=CLAIM_INPUT_PREFIX,
        )
        if claim:
            run = db.get(AgentRun, claim.run_id)
            attempt = db.get(AgentRunAttempt, claim.attempt_id)
            delay = max(0.0, (time.time() - run.created_at.timestamp()))
            metrics.record(metrics.claim_delay, delay, profile_id=run.profile_id)
            log.info("agent run claimed", extra=run_log_fields(run, attempt))
        return claim


async def finish_simulated(claim: AttemptClaim) -> None:
    started = time.monotonic()
    with SessionLocal.begin() as db:
        run = db.get(AgentRun, claim.run_id)
        attempt = db.get(AgentRunAttempt, claim.attempt_id)
        if not run or not attempt:
            return
        mark_running(db, claim)
        profile_id = run.profile_id
        input_text = run.input_text
        attempt_no = attempt.attempt_no

    if DRILL_ENABLED and DRILL_STAGE in {"before_external", "after_external"} and attempt_no == DRILL_ATTEMPT_NO:
        if DRILL_STAGE == "after_external":
            with SessionLocal.begin() as db:
                mark_external_starting(db, claim)
        log.warning(
            "runtime drill pause stage=%s seconds=%s run_id=%s attempt_id=%s worker_id=%s",
            DRILL_STAGE,
            DRILL_DELAY_SECONDS,
            claim.run_id,
            claim.attempt_id,
            WORKER_ID,
            extra=run_log_fields(run, attempt),
        )
        await asyncio.sleep(DRILL_DELAY_SECONDS)
        try:
            with SessionLocal.begin() as db:
                current = db.get(AgentRun, claim.run_id)
                output = {
                    "mode": "bounded-simulation-drill",
                    "candidate_status": "submitted",
                    "message": "故障停顿结束后尝试写回；只有仍持有有效租约时才会成功。",
                    "profile_id": current.profile_id,
                    "model_provider": MODEL_PROVIDER,
                    "model_id": MODEL_ID,
                    "input_digest": canonical_hash(current.input_text),
                }
                finish_success(db, claim, output)
            metrics.record(
                metrics.run_duration,
                time.monotonic() - started,
                profile_id=profile_id,
                status="evidence_accepted",
            )
            metrics.add(metrics.run_terminal, profile_id=profile_id, status="evidence_accepted")
        except StaleLease:
            log.warning(
                "runtime drill stale write blocked run_id=%s attempt_id=%s worker_id=%s",
                claim.run_id,
                claim.attempt_id,
                WORKER_ID,
                extra=run_log_fields(run, attempt),
            )
        return

    hold_seconds = DRILL_DELAY_SECONDS if DRILL_ENABLED and DRILL_STAGE == "database_outage" else SIMULATION_DELAY_SECONDS
    heartbeat_stop = asyncio.Event()
    lease_lost = asyncio.Event()
    heartbeat_task = None
    if hold_seconds > 0:
        heartbeat_task = asyncio.create_task(maintain_heartbeat(claim, heartbeat_stop, lease_lost))
        log.info(
            "simulated run holding for reliability drill",
            extra={
                **run_log_fields(run, attempt),
                "operation": DRILL_STAGE if DRILL_ENABLED else "simulation_delay",
            },
        )
    try:
        if hold_seconds > 0:
            try:
                await asyncio.wait_for(lease_lost.wait(), timeout=hold_seconds)
            except asyncio.TimeoutError:
                pass
        if lease_lost.is_set():
            raise StaleLease("simulation lease authority expired during hold")

        def persist_success() -> None:
            with SessionLocal.begin() as db:
                current_run = db.get(AgentRun, claim.run_id)
                current_attempt = db.get(AgentRunAttempt, claim.attempt_id)
                output = {
                    "mode": "bounded-simulation",
                    "candidate_status": "submitted",
                    "message": "Hermes执行未启用；已完成Runtime协调、边界和输出合同验证。",
                    "profile_id": profile_id,
                    "model_provider": MODEL_PROVIDER,
                    "model_id": MODEL_ID,
                    "input_digest": canonical_hash(input_text),
                }
                with attempt_span(current_run, current_attempt):
                    candidates = prepare_synthetic_candidates(db, current_run, current_attempt)
                    if candidates:
                        output["candidate_ids"] = [item.id for item in candidates]
                        output["candidate_kinds"] = sorted({item.kind for item in candidates})
                    finish_success(db, claim, output)
                    log.info("simulated agent run completed", extra=run_log_fields(current_run, current_attempt))

        if heartbeat_task:
            await retry_database_operation(
                persist_success,
                name="simulation_finish",
                claim=claim,
                lease_lost=lease_lost,
            )
        else:
            persist_success()
        metrics.record(
            metrics.run_duration,
            time.monotonic() - started,
            profile_id=profile_id,
            status="evidence_accepted",
        )
        metrics.add(metrics.run_terminal, profile_id=profile_id, status="evidence_accepted")
    except StaleLease:
        log.warning(
            "simulated result was not written because lease authority was lost",
            extra=run_log_fields(run, attempt),
        )
    finally:
        if heartbeat_task:
            heartbeat_stop.set()
            await heartbeat_task


async def maintain_heartbeat(claim: AttemptClaim, stop: asyncio.Event, lost: asyncio.Event) -> None:
    loop = asyncio.get_running_loop()
    last_confirmed_at = loop.time()
    failures = 0
    wait_seconds = float(HEARTBEAT_SECONDS)
    while not stop.is_set():
        try:
            await asyncio.wait_for(stop.wait(), timeout=wait_seconds)
            return
        except asyncio.TimeoutError:
            pass
        try:
            with SessionLocal.begin() as db:
                renewed = heartbeat(db, claim, LEASE_SECONDS)
        except DATABASE_UNAVAILABLE_ERRORS as exc:
            failures += 1
            now = loop.time()
            delay = retry_seconds(failures)
            dispose_database_connections()
            log_database_unavailable("heartbeat", failures, delay, exc, claim=claim)
            if lease_authority_expired(
                last_confirmed_at=last_confirmed_at,
                now=now,
                lease_seconds=LEASE_SECONDS,
            ):
                lost.set()
                log.warning(
                    "lease authority expired while database was unavailable",
                    extra={
                        **run_log_fields(run_id=claim.run_id, attempt_id=claim.attempt_id),
                        "operation": "heartbeat",
                        "failure_count": failures,
                        "outcome": "lease_authority_expired",
                    },
                )
                return
            remaining = max(0.1, LEASE_SECONDS - (now - last_confirmed_at))
            wait_seconds = min(delay, remaining)
            continue
        if not renewed:
            lost.set()
            log.warning(
                "attempt lease lost run_id=%s attempt_id=%s",
                claim.run_id,
                claim.attempt_id,
                extra=run_log_fields(run_id=claim.run_id, attempt_id=claim.attempt_id),
            )
            return
        if failures:
            log.info(
                "database connection recovered operation=heartbeat failure_count=%s",
                failures,
                extra={
                    **run_log_fields(run_id=claim.run_id, attempt_id=claim.attempt_id),
                    "operation": "heartbeat",
                    "failure_count": failures,
                    "outcome": "database_recovered",
                },
            )
        now = loop.time()
        metrics.record(metrics.heartbeat_lag, now - last_confirmed_at, worker_id=WORKER_ID)
        last_confirmed_at = now
        failures = 0
        wait_seconds = float(HEARTBEAT_SECONDS)


async def execute_hermes(claim: AttemptClaim) -> None:
    started = time.monotonic()
    with SessionLocal.begin() as db:
        run = db.get(AgentRun, claim.run_id)
        if not run:
            return
        mark_running(db, claim)
        attempt = db.get(AgentRunAttempt, claim.attempt_id)
        profile_id, input_text = run.profile_id, run.input_text
        profile_snapshot = dict(run.profile_snapshot or {})
        profile_version = run.profile_version
        commitment_id = run.commitment_id
    url, key = PROFILE[profile_id]
    headers = {"Authorization": f"Bearer {key}"}
    heartbeat_stop = asyncio.Event()
    lease_lost = asyncio.Event()
    heartbeat_task = asyncio.create_task(maintain_heartbeat(claim, heartbeat_stop, lease_lost))
    span_scope = attempt_span(run, attempt)
    span_scope.__enter__()
    terminal_status = "unknown"
    hermes_run_id = None
    try:
        configured_timeout = int(profile_snapshot.get("model", {}).get("timeout_seconds", 60) or 60)
        configured_timeout = max(10, min(configured_timeout, 600))
        profile_note = (
            f"\n本次Run绑定服务端Profile版本={profile_version or 'legacy'}；"
            f"配置超时={configured_timeout}秒。运行中配置变更不会覆盖本次快照。"
        )
        async with httpx.AsyncClient(timeout=configured_timeout) as client:
            def persist_external_starting() -> None:
                with SessionLocal.begin() as db:
                    mark_external_starting(db, claim)

            await retry_database_operation(
                persist_external_starting,
                name="mark_external_starting",
                claim=claim,
                lease_lost=lease_lost,
            )
            response = await client.post(f"{url}/v1/runs", headers=headers, json={
                "input": input_text,
                "instructions": profile_instructions(profile_id, commitment_id, claim.attempt_id) + profile_note,
                "session_id": claim.run_id,
            })
            response.raise_for_status()
            hermes_run_id = response.json()["run_id"]

            def persist_hermes_run() -> None:
                with SessionLocal.begin() as db:
                    set_hermes_run(db, claim, hermes_run_id)

            await retry_database_operation(
                persist_hermes_run,
                name="set_hermes_run",
                claim=claim,
                lease_lost=lease_lost,
            )
            log.info(
                "Hermes run dispatched",
                extra=run_log_fields(run, attempt, hermes_run_id=hermes_run_id),
            )
            stop_requested = False
            for _ in range(HERMES_MAX_POLLS):
                await asyncio.sleep(HERMES_POLL_SECONDS)
                if lease_lost.is_set():
                    raise StaleLease("heartbeat reported a stale lease")

                def read_cancellation() -> bool:
                    with SessionLocal() as db:
                        current_run = db.get(AgentRun, claim.run_id)
                        return bool(current_run and current_run.cancellation_requested_at)

                cancellation_requested = await retry_database_operation(
                    read_cancellation,
                    name="read_cancellation",
                    claim=claim,
                    lease_lost=lease_lost,
                )
                if cancellation_requested and not stop_requested:
                    stop_response = await client.post(f"{url}/v1/runs/{hermes_run_id}/stop", headers=headers)
                    stop_response.raise_for_status()
                    stop_requested = True
                status_response = await client.get(f"{url}/v1/runs/{hermes_run_id}", headers=headers)
                status_response.raise_for_status()
                status = status_response.json()
                if status.get("status") in {"completed", "failed", "cancelled"}:
                    def persist_terminal() -> str:
                        with SessionLocal.begin() as db:
                            if status["status"] == "completed":
                                finish_success(db, claim, {
                                    "candidate_status": "submitted",
                                    "model_provider": MODEL_PROVIDER,
                                    "model_id": MODEL_ID,
                                    "hermes": status,
                                })
                                return "evidence_accepted"
                            if status["status"] == "failed":
                                retryability = str(status.get("retryability", "unsafe"))
                                requeued = finish_failure_or_requeue(
                                    db,
                                    claim,
                                    failure={"retryability": retryability, "hermes": status},
                                    failure_class="hermes_failed",
                                    retryability=retryability,
                                    max_attempts=MAX_ATTEMPTS,
                                )
                                return "retry_scheduled" if requeued else "failed"
                            finish_terminal(
                                db,
                                claim,
                                "cancelled",
                                failure={"retryability": "unsafe", "hermes": status},
                                failure_class="hermes_cancelled",
                                retryability="unsafe",
                            )
                            return "cancelled"

                    terminal_status = await retry_database_operation(
                        persist_terminal,
                        name="persist_hermes_terminal",
                        claim=claim,
                        lease_lost=lease_lost,
                    )
                    return
            raise TimeoutError("Hermes run timed out")
    except StaleLease:
        terminal_status = "lease_lost"
        log.warning(
            "stale worker write blocked run_id=%s attempt_id=%s",
            claim.run_id,
            claim.attempt_id,
            extra=run_log_fields(run, attempt, hermes_run_id=hermes_run_id),
        )
    except Exception as exc:
        log.exception(
            "Hermes run failed: %s",
            claim.run_id,
            extra=run_log_fields(run, attempt, hermes_run_id=hermes_run_id),
        )
        try:
            def persist_unknown() -> None:
                with SessionLocal.begin() as db:
                    finish_terminal(
                        db,
                        claim,
                        "unknown",
                        failure={"retryability": "unsafe", "message": str(exc)[:500]},
                        failure_class="hermes_result_unknown",
                        retryability="unsafe",
                    )

            await retry_database_operation(
                persist_unknown,
                name="persist_unknown",
                claim=claim,
                lease_lost=lease_lost,
            )
            terminal_status = "unknown"
        except StaleLease:
            log.warning(
                "unknown result was not written because lease is stale run_id=%s",
                claim.run_id,
                extra=run_log_fields(run, attempt, hermes_run_id=hermes_run_id),
            )
    finally:
        heartbeat_stop.set()
        await heartbeat_task
        log.info(
            "agent run attempt finished",
            extra={
                **run_log_fields(run, attempt, hermes_run_id=hermes_run_id),
                "status": terminal_status,
            },
        )
        metrics.record(metrics.run_duration, time.monotonic() - started, profile_id=profile_id, status=terminal_status)
        if terminal_status in {"evidence_accepted", "failed", "cancelled", "unknown"}:
            metrics.add(metrics.run_terminal, profile_id=profile_id, status=terminal_status)
        span_scope.__exit__(None, None, None)


def process_outbox() -> None:
    with SessionLocal.begin() as db:
        stmt = select(Outbox).where(Outbox.status == "pending").order_by(Outbox.created_at).limit(20)
        if db.bind.dialect.name == "postgresql":
            stmt = stmt.with_for_update(skip_locked=True)
        for event in db.scalars(stmt).all():
            event.status = "delivered"
            event.attempt_count += 1


async def main() -> None:
    log.info(
        "worker started worker_id=%s hermes_enabled=%s lease_seconds=%s heartbeat_seconds=%s",
        WORKER_ID,
        hermes_enabled(),
        LEASE_SECONDS,
        HEARTBEAT_SECONDS,
        extra={"worker_id": WORKER_ID},
    )
    loop = asyncio.get_running_loop()
    next_recovery_scan = 0.0
    database_failures = 0
    while True:
        try:
            if loop.time() >= next_recovery_scan:
                with SessionLocal.begin() as db:
                    result = recover_expired(db, max_attempts=MAX_ATTEMPTS, run_id=CLAIM_RUN_ID)
                if any(result.values()):
                    log.warning("runtime recovery result=%s", result)
                    for outcome, count in result.items():
                        if count:
                            metrics.add(metrics.recovery, count, outcome=outcome)
                            metrics.add(metrics.lease_expired, count, outcome=outcome)
                next_recovery_scan = loop.time() + RECOVERY_SCAN_SECONDS
            process_outbox()
            if claim := claim_run():
                if claim_uses_real_execution(claim):
                    await execute_hermes(claim)
                else:
                    await finish_simulated(claim)
            else:
                await asyncio.sleep(1)
            if database_failures:
                log.info(
                    "database connection recovered operation=worker_loop failure_count=%s",
                    database_failures,
                    extra={
                        "worker_id": WORKER_ID,
                        "operation": "worker_loop",
                        "failure_count": database_failures,
                        "outcome": "database_recovered",
                    },
                )
                database_failures = 0
        except DATABASE_UNAVAILABLE_ERRORS as exc:
            database_failures += 1
            delay = retry_seconds(database_failures)
            dispose_database_connections()
            log_database_unavailable("worker_loop", database_failures, delay, exc)
            await asyncio.sleep(delay)


if __name__ == "__main__":
    asyncio.run(main())
