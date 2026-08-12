#!/usr/bin/env python3
"""Create a project-owned Codex OAuth singleton in the shared Hermes root."""
from types import SimpleNamespace

from hermes_cli.auth import PROVIDER_REGISTRY, _login_openai_codex

args = SimpleNamespace(no_browser=True, timeout=30.0, insecure=False, ca_bundle=None)
_login_openai_codex(args, PROVIDER_REGISTRY["openai-codex"], force_new_login=True)

