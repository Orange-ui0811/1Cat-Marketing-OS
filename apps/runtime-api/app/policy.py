import json
import re
from dataclasses import dataclass

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import AuditLog, IdempotencyRecord
from .hashing import canonical_hash
from .security import Actor


@dataclass
class WriteContext:
    actor: Actor
    correlation_id: str
    idempotency_key: str
    request_hash: str


PII_PATTERNS = (
    # Do not treat a numeric run inside an opaque ASCII identifier (for example
    # ``attempt_16099574444abc``) as a phone number.  Chinese prose immediately
    # adjacent to a real phone number is still rejected.
    re.compile(r"(?<![A-Za-z0-9_])1[3-9]\d{9}(?![A-Za-z0-9_])"),
    re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}"),
)


def reject_obvious_pii(payload: object) -> None:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    if any(pattern.search(raw) for pattern in PII_PATTERNS):
        raise HTTPException(status_code=422, detail="R0真实PII关闭：请求包含疑似手机号或邮箱")


def prepare_write(actor: Actor, correlation_id: str | None, idempotency_key: str | None, payload: object) -> WriteContext:
    if not correlation_id:
        raise HTTPException(status_code=400, detail="缺少X-Correlation-ID")
    if not idempotency_key:
        raise HTTPException(status_code=400, detail="缺少Idempotency-Key")
    reject_obvious_pii(payload)
    return WriteContext(actor, correlation_id, idempotency_key, canonical_hash(payload))


def find_idempotent(db: Session, ctx: WriteContext) -> IdempotencyRecord | None:
    record = db.scalar(
        select(IdempotencyRecord).where(
            IdempotencyRecord.actor_id == ctx.actor.id,
            IdempotencyRecord.idempotency_key == ctx.idempotency_key,
        )
    )
    if record and record.request_hash != ctx.request_hash:
        raise HTTPException(status_code=409, detail="同一幂等键对应不同请求")
    return record


def record_write(db: Session, ctx: WriteContext, resource_type: str, resource_id: str, action: str) -> None:
    db.add(IdempotencyRecord(
        actor_id=ctx.actor.id,
        idempotency_key=ctx.idempotency_key,
        request_hash=ctx.request_hash,
        resource_type=resource_type,
        resource_id=resource_id,
    ))
    db.add(AuditLog(
        actor_id=ctx.actor.id,
        actor_roles=sorted(ctx.actor.roles),
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        correlation_id=ctx.correlation_id,
        decision="allow",
        detail={"idempotency_key": ctx.idempotency_key},
    ))


def audit_deny(db: Session, actor: Actor, correlation_id: str, action: str, resource_type: str, reason: str) -> None:
    db.add(AuditLog(
        actor_id=actor.id,
        actor_roles=sorted(actor.roles),
        action=action,
        resource_type=resource_type,
        resource_id="unknown",
        correlation_id=correlation_id,
        decision="deny",
        detail={"reason": reason},
    ))
    db.commit()
