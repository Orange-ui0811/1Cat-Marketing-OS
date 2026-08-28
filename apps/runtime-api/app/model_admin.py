from __future__ import annotations

import hmac
import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import httpx
from fastapi import Header, HTTPException
from pydantic import BaseModel, Field

from .config import get_settings


_operation_lock = threading.Lock()


class LocalModelConfigRequest(BaseModel):
    api_key: str | None = Field(default=None, max_length=512)
    action: Literal["configure", "test"] | None = None


def _secret_path() -> Path:
    return Path(get_settings().model_api_key_file)


def _state_path() -> Path:
    return Path(get_settings().model_runtime_state_file)


def execution_enabled() -> bool:
    try:
        payload = json.loads(_state_path().read_text(encoding="utf-8"))
        value = payload.get("execution_enabled")
        if isinstance(value, bool):
            return value
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        pass
    return get_settings().hermes_execution_enabled


def require_local_admin(x_local_admin_token: str | None = Header(default=None)) -> None:
    expected = get_settings().local_admin_token
    if not expected or not x_local_admin_token or not hmac.compare_digest(expected, x_local_admin_token):
        raise HTTPException(403, "本机模型配置通道不可用")


def status_payload(*, operation_in_progress: bool | None = None) -> dict:
    settings = get_settings()
    secret = _secret_path()
    try:
        credential_configured = secret.is_file() and secret.stat().st_size > 0
    except OSError:
        credential_configured = False
    return {
        "available": True,
        "provider": settings.hermes_model_provider,
        "model": settings.hermes_model_id,
        "mode": settings.model_mode,
        "credential_configured": credential_configured,
        "execution_enabled": execution_enabled(),
        "operation_in_progress": _operation_lock.locked() if operation_in_progress is None else operation_in_progress,
    }


def _atomic_write(path: Path, content: bytes, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_bytes(content)
    try:
        temporary.chmod(mode)
    except OSError:
        pass
    os.replace(temporary, path)


def _validate_key(value: str) -> str:
    normalized = value.strip()
    if len(normalized) < 16 or len(normalized) > 512 or any(character.isspace() for character in normalized):
        raise HTTPException(422, "API Key 格式无效")
    return normalized


def _write_execution_state(enabled: bool) -> None:
    settings = get_settings()
    payload = {
        "execution_enabled": enabled,
        "provider": settings.hermes_model_provider,
        "model": settings.hermes_model_id,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "updated_by": "local-admin",
    }
    _atomic_write(_state_path(), (json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8"))


def _gateway_request(path: str, *, payload: dict | None = None, timeout: float = 120.0) -> dict:
    settings = get_settings()
    if not settings.model_gateway_client_token:
        raise HTTPException(503, "Model Gateway 内部凭据尚未初始化")
    headers = {"Authorization": f"Bearer {settings.model_gateway_client_token}"}
    url = f"{settings.model_gateway_url.rstrip('/')}/v1/{path}"
    try:
        with httpx.Client(timeout=timeout) as client:
            if payload is None:
                response = client.get(url, headers=headers)
            else:
                response = client.post(url, headers=headers, json=payload)
    except httpx.HTTPError as exc:
        raise HTTPException(502, "Model Gateway 尚未就绪，请确认本机服务已经启动") from exc
    if response.status_code in {401, 403}:
        raise HTTPException(502, "DeepSeek 拒绝了当前凭据")
    if response.status_code == 404:
        raise HTTPException(502, "DeepSeek 未找到当前模型或接口")
    if response.status_code >= 400:
        raise HTTPException(502, f"模型验证失败（上游状态 {response.status_code}）")
    try:
        return response.json()
    except ValueError as exc:
        raise HTTPException(502, "模型服务返回了无法识别的响应") from exc


def configure_model(payload: LocalModelConfigRequest) -> dict:
    if not _operation_lock.acquire(blocking=False):
        raise HTTPException(409, "模型配置正在进行，请稍候")
    secret = _secret_path()
    previous = secret.read_bytes() if secret.exists() else None
    key_replaced = payload.api_key is not None
    try:
        if payload.api_key is not None:
            _atomic_write(secret, (_validate_key(payload.api_key) + "\n").encode("utf-8"))
        if not secret.exists() or secret.stat().st_size == 0:
            raise HTTPException(422, "请先输入 DeepSeek API Key")

        if payload.action == "test":
            if not execution_enabled():
                raise HTTPException(409, "请先验证 Key 并启用真实执行")
            settings = get_settings()
            result = _gateway_request("chat/completions", payload={
                "model": settings.hermes_model_id,
                "messages": [{"role": "user", "content": "Reply with exactly OK."}],
                "stream": False,
                "max_tokens": 32,
            })
            if not result.get("choices"):
                raise HTTPException(502, "模型响应缺少 choices")
            return {
                **status_payload(operation_in_progress=False),
                "message": "DeepSeek Chat Completion 测试通过，模型可以正常调用。",
                "model_test_passed": True,
            }

        _gateway_request("models", timeout=60.0)
        _write_execution_state(True)
        return {
            **status_payload(operation_in_progress=False),
            "message": "DeepSeek 已验证，三个 Agent 已切换到真实执行。",
        }
    except Exception:
        if key_replaced:
            if previous is None:
                try:
                    secret.unlink(missing_ok=True)
                except OSError:
                    pass
            else:
                _atomic_write(secret, previous)
        raise
    finally:
        _operation_lock.release()
