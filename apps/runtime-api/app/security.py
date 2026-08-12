from dataclasses import dataclass

import jwt
from fastapi import Header, HTTPException, Request, status
from jwt import PyJWKClient

from .config import get_settings


@dataclass(frozen=True)
class Actor:
    id: str
    roles: frozenset[str]
    service: bool = False


def _roles(payload: dict) -> frozenset[str]:
    realm = payload.get("realm_access") or {}
    return frozenset(str(role) for role in realm.get("roles", []))


async def current_actor(
    request: Request,
    authorization: str | None = Header(default=None),
    x_actor_id: str | None = Header(default=None),
    x_actor_roles: str | None = Header(default=None),
) -> Actor:
    settings = get_settings()
    if settings.auth_mode == "development":
        if not x_actor_id:
            raise HTTPException(status_code=401, detail="development模式仍要求X-Actor-Id")
        return Actor(x_actor_id, frozenset(filter(None, (x_actor_roles or "operator").split(","))))
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="需要OIDC登录")
    token = authorization.removeprefix("Bearer ").strip()
    try:
        signing_key = PyJWKClient(settings.oidc_jwks_url).get_signing_key_from_jwt(token).key
        payload = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256"],
            issuer=settings.oidc_issuer,
            options={"verify_aud": False},
        )
    except Exception as exc:
        raise HTTPException(status_code=401, detail="OIDC令牌无效") from exc
    return Actor(str(payload.get("sub")), _roles(payload), payload.get("typ") == "Bearer" and "service" in _roles(payload))


def require_any(actor: Actor, *allowed: str) -> None:
    if not actor.roles.intersection(allowed):
        raise HTTPException(status_code=403, detail=f"权限不足，需要以下角色之一：{','.join(allowed)}")

