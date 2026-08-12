from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
from datetime import datetime, timezone

import httpx
from sqlalchemy import select

from app.db import SessionLocal
from app.models import AgentRun, Commitment, Outbox

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
log = logging.getLogger("1cat.worker")

HERMES_ENABLED = os.getenv("HERMES_EXECUTION_ENABLED", "false").lower() == "true"
PROFILE = {
    "pma": (os.getenv("HERMES_PMA_URL", "http://hermes-pma:8080"), os.getenv("HERMES_API_KEY_PMA", "")),
    "bga": (os.getenv("HERMES_BGA_URL", "http://hermes-bga:8080"), os.getenv("HERMES_API_KEY_BGA", "")),
    "mo": (os.getenv("HERMES_MO_URL", "http://hermes-mo:8080"), os.getenv("HERMES_API_KEY_MO", "")),
}
PROFILE_ROOT = os.getenv("PROFILE_ROOT", "/profiles")
ROLE = {"pma": "DROLE-01", "bga": "DROLE-02", "mo": "DROLE-03"}


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


def claim_run() -> str | None:
    with SessionLocal.begin() as db:
        stmt = select(AgentRun).where(AgentRun.status == "queued").order_by(AgentRun.created_at).limit(1)
        if db.bind.dialect.name == "postgresql":
            stmt = stmt.with_for_update(skip_locked=True)
        run = db.scalar(stmt)
        if not run:
            return None
        run.status = "accepted"
        run.version += 1
        return run.id


def finish_simulated(run_id: str) -> None:
    with SessionLocal.begin() as db:
        run = db.get(AgentRun, run_id)
        if not run:
            return
        run.status = "evidence_accepted"
        run.output = {
            "mode": "bounded-simulation",
            "candidate_status": "submitted",
            "message": "Hermes执行未启用；已完成Runtime协调、边界和输出合同验证。",
            "profile_id": run.profile_id,
            "input_digest": canonical_hash(run.input_text),
        }
        commitment = db.get(Commitment, run.commitment_id)
        if commitment and commitment.status in {"accepted", "active"}:
            commitment.status = "submitted"
            commitment.version += 1
            commitment.content_hash = canonical_hash({"run_id": run.id, "status": "submitted"})


async def execute_hermes(run_id: str) -> None:
    with SessionLocal.begin() as db:
        run = db.get(AgentRun, run_id)
        if not run:
            return
        run.status = "running"
        profile_id, input_text = run.profile_id, run.input_text
        commitment_id = run.commitment_id
    url, key = PROFILE[profile_id]
    headers = {"Authorization": f"Bearer {key}"}
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(f"{url}/v1/runs", headers=headers, json={
                "input": input_text,
                "instructions": profile_instructions(profile_id, commitment_id, run_id),
                "session_id": run_id,
            })
            response.raise_for_status()
            hermes_run_id = response.json()["run_id"]
            with SessionLocal.begin() as db:
                run = db.get(AgentRun, run_id)
                run.hermes_run_id = hermes_run_id
            for _ in range(360):
                await asyncio.sleep(2)
                status = (await client.get(f"{url}/v1/runs/{hermes_run_id}", headers=headers)).json()
                if status.get("status") in {"completed", "failed", "cancelled"}:
                    with SessionLocal.begin() as db:
                        run = db.get(AgentRun, run_id)
                        if status["status"] == "completed":
                            run.status = "evidence_accepted"
                            run.output = {"candidate_status": "submitted", "hermes": status}
                            commitment = db.get(Commitment, run.commitment_id)
                            if commitment and commitment.status in {"accepted", "active"}:
                                commitment.status = "submitted"
                        else:
                            run.status = status["status"]
                            run.failure = {"retryability": "unsafe", "hermes": status}
                    return
            raise TimeoutError("Hermes run timed out")
    except Exception as exc:
        log.exception("Hermes run failed: %s", run_id)
        with SessionLocal.begin() as db:
            run = db.get(AgentRun, run_id)
            if run:
                run.status = "unknown"
                run.failure = {"retryability": "unsafe", "message": str(exc)[:500]}
                db.add(Outbox(event_type="manual.reconciliation.required", aggregate_type="run", aggregate_id=run.id,
                              payload={"run_id": run.id, "reason": "unknown_result"}))


def process_outbox() -> None:
    with SessionLocal.begin() as db:
        stmt = select(Outbox).where(Outbox.status == "pending").order_by(Outbox.created_at).limit(20)
        if db.bind.dialect.name == "postgresql":
            stmt = stmt.with_for_update(skip_locked=True)
        for event in db.scalars(stmt).all():
            event.status = "delivered"
            event.attempt_count += 1


async def main() -> None:
    log.info("worker started hermes_enabled=%s", HERMES_ENABLED)
    while True:
        process_outbox()
        if run_id := claim_run():
            if HERMES_ENABLED:
                await execute_hermes(run_id)
            else:
                finish_simulated(run_id)
        else:
            await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
