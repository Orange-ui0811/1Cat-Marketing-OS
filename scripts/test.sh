#!/bin/sh
set -eu
PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$PROJECT_DIR"
mkdir -p .runtime
if [ ! -x .venv/bin/python ]; then
  UV_VENV_CLEAR=1 uv venv --python 3.12 .venv
fi
if ! .venv/bin/python -c 'import fastapi, httpx, jsonschema, pytest, sqlalchemy' >/dev/null 2>&1; then
  uv pip install --python .venv/bin/python -r apps/runtime-api/requirements.txt pytest==8.4.1 pytest-cov==6.2.1 httpx==0.28.1
fi
PYTHONPYCACHEPREFIX="$PROJECT_DIR/.runtime/pycache" \
  AUTH_MODE=development DATABASE_URL=sqlite:///./.runtime/test.db .venv/bin/pytest
cd apps/workspace
npm ci
npm run build
