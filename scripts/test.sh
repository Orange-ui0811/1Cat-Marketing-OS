#!/bin/sh
set -eu
PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$PROJECT_DIR"
mkdir -p .runtime
if [ -x .venv/bin/python ]; then
  PYTHON=.venv/bin/python
elif [ -x .venv/Scripts/python.exe ]; then
  PYTHON=.venv/Scripts/python.exe
else
  if command -v uv >/dev/null 2>&1; then
    uv venv --python 3.12 .venv
  elif command -v python3 >/dev/null 2>&1; then
    python3 -m venv .venv
  else
    python -m venv .venv
  fi
  if [ -x .venv/bin/python ]; then PYTHON=.venv/bin/python; else PYTHON=.venv/Scripts/python.exe; fi
fi
if ! "$PYTHON" -c 'import fastapi, httpx, jsonschema, pytest, sqlalchemy' >/dev/null 2>&1; then
  if command -v uv >/dev/null 2>&1; then
    uv pip install --python "$PYTHON" -r apps/runtime-api/requirements.txt pytest==8.4.2 pytest-cov==6.2.1
  else
    "$PYTHON" -m pip install -r apps/runtime-api/requirements.txt pytest==8.4.2 pytest-cov==6.2.1
  fi
fi
PYTHONPYCACHEPREFIX="$PROJECT_DIR/.runtime/pycache" \
  AUTH_MODE=development DATABASE_URL=sqlite:///./.runtime/test.db "$PYTHON" -m pytest
cd apps/workspace
npm ci
npm run build
