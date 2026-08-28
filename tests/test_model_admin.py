from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app import model_admin


def settings(tmp_path):
    return SimpleNamespace(
        model_api_key_file=str(tmp_path / "secrets" / "model_api_key"),
        model_runtime_state_file=str(tmp_path / "control" / "model-runtime.json"),
        hermes_execution_enabled=False,
        hermes_model_provider="deepseek",
        hermes_model_id="deepseek-v4-pro",
        model_mode="deepseek-api-key",
        local_admin_token="local-test-token",
        model_gateway_client_token="gateway-test-token",
        model_gateway_url="http://model-gateway:8010",
    )


def test_local_model_configuration_is_persisted_and_dynamic(monkeypatch, tmp_path):
    configured = settings(tmp_path)
    monkeypatch.setattr(model_admin, "get_settings", lambda: configured)
    calls = []
    monkeypatch.setattr(model_admin, "_gateway_request", lambda path, **kwargs: calls.append(path) or {"data": []})

    result = model_admin.configure_model(model_admin.LocalModelConfigRequest(api_key="sk-test-deepseek-key-123456"))

    assert calls == ["models"]
    assert (tmp_path / "secrets" / "model_api_key").read_text(encoding="utf-8").strip() == "sk-test-deepseek-key-123456"
    assert model_admin.execution_enabled() is True
    assert result["credential_configured"] is True
    assert result["execution_enabled"] is True


def test_invalid_replacement_restores_previous_secret(monkeypatch, tmp_path):
    configured = settings(tmp_path)
    monkeypatch.setattr(model_admin, "get_settings", lambda: configured)
    secret = tmp_path / "secrets" / "model_api_key"
    secret.parent.mkdir(parents=True)
    secret.write_text("sk-previous-working-key\n", encoding="utf-8")

    def reject(*_args, **_kwargs):
        raise HTTPException(502, "DeepSeek 拒绝了当前凭据")

    monkeypatch.setattr(model_admin, "_gateway_request", reject)
    with pytest.raises(HTTPException):
        model_admin.configure_model(model_admin.LocalModelConfigRequest(api_key="sk-invalid-replacement-key"))

    assert secret.read_text(encoding="utf-8") == "sk-previous-working-key\n"


def test_local_admin_header_is_required(monkeypatch, tmp_path):
    configured = settings(tmp_path)
    monkeypatch.setattr(model_admin, "get_settings", lambda: configured)

    model_admin.require_local_admin("local-test-token")
    with pytest.raises(HTTPException) as error:
        model_admin.require_local_admin("wrong-token")
    assert error.value.status_code == 403
