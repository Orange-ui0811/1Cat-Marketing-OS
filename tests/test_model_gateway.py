from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from fastapi import HTTPException


ROOT = Path(__file__).resolve().parents[1]


def load_gateway(monkeypatch, tmp_path: Path, *, key: str = "test-deepseek-secret"):
    secret = tmp_path / "model_api_key"
    secret.write_text(key, encoding="utf-8")
    monkeypatch.setenv("MODEL_API_KEY_FILE", str(secret))
    monkeypatch.setenv("MODEL_GATEWAY_CLIENT_TOKEN", "internal-test-token")
    monkeypatch.setenv("MODEL_UPSTREAM_BASE_URL", "https://api.deepseek.com/v1")
    monkeypatch.setenv("MODEL_UPSTREAM_MODEL_ID", "deepseek-v4-pro")
    spec = importlib.util.spec_from_file_location(
        f"model_gateway_{tmp_path.name}", ROOT / "apps" / "model-gateway" / "app.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, secret


def test_gateway_normalizes_upstream_and_locks_model(monkeypatch, tmp_path):
    gateway, _ = load_gateway(monkeypatch, tmp_path)
    assert gateway.upstream_url("chat/completions") == "https://api.deepseek.com/v1/chat/completions"
    gateway.validate_model("chat/completions", b'{"model":"deepseek-v4-pro"}')
    with pytest.raises(HTTPException) as error:
        gateway.validate_model("chat/completions", b'{"model":"another-model"}')
    assert error.value.status_code == 400


def test_gateway_keeps_provider_key_behind_internal_token(monkeypatch, tmp_path):
    gateway, _ = load_gateway(monkeypatch, tmp_path)
    assert gateway.api_key() == "test-deepseek-secret"
    gateway.require_internal_client("Bearer internal-test-token")
    with pytest.raises(HTTPException) as error:
        gateway.require_internal_client("Bearer wrong-token")
    assert error.value.status_code == 401


def test_gateway_fails_closed_when_secret_is_empty(monkeypatch, tmp_path):
    gateway, secret = load_gateway(monkeypatch, tmp_path)
    secret.write_text("", encoding="utf-8")
    with pytest.raises(HTTPException) as error:
        gateway.ready()
    assert error.value.status_code == 503
