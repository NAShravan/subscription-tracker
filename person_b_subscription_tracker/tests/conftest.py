"""Shared pytest fixtures for Person B (throwaway SQLite via env)."""
import os
import tempfile

_TMP = tempfile.mkdtemp(prefix="csi3007_b_tests_")
# TEST_DATABASE_URL lets the same suite run against PostgreSQL (must be an empty DB).
os.environ["DATABASE_URL"] = os.getenv("TEST_DATABASE_URL") or f"sqlite:///{_TMP}/test_subscriptions.db"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as test_client:
        yield test_client
