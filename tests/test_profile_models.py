from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("build_profiles_under_test", ROOT / "scripts" / "build_profiles.py")
assert SPEC and SPEC.loader
BUILD_PROFILES = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILD_PROFILES)


def test_deepseek_model_configuration_is_accepted():
    assert BUILD_PROFILES.validate_model("DeepSeek", "deepseek-v4-pro") == (
        "deepseek",
        "deepseek-v4-pro",
    )


def test_unknown_model_provider_fails_closed():
    with pytest.raises(ValueError, match="unsupported model provider"):
        BUILD_PROFILES.validate_model("unreviewed-provider", "some-model")
