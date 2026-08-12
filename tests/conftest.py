import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "runtime-api"))

from app.db import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture()
def client():
    Base.metadata.drop_all(bind=engine)
    with TestClient(app) as test_client:
        yield test_client
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def auth_headers():
    return {
        "X-Actor-Id": "test-operator",
        "X-Actor-Roles": "operator,company_admin",
    }


@pytest.fixture()
def write_headers(auth_headers):
    return {
        **auth_headers,
        "X-Correlation-ID": "test-correlation",
        "Idempotency-Key": "test-idempotency",
    }
