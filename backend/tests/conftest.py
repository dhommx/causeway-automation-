"""Tests use their own database (automation_portal_test) and storage folder, never the dev ones."""

import os
import tempfile

import psycopg
import pytest

BASE = os.environ.get(
    "AP_TEST_ADMIN_URL", "postgresql://automation:automation@localhost:5450/postgres"
)
TEST_DB = "automation_portal_test"

os.environ["AP_DATABASE_URL"] = (
    BASE.replace("postgresql://", "postgresql+psycopg://").rsplit("/", 1)[0] + f"/{TEST_DB}"
)
os.environ["AP_STORAGE_ROOT"] = tempfile.mkdtemp(prefix="ap-test-storage-")
os.environ["AP_RUN_INLINE"] = "true"


@pytest.fixture(scope="session")
def database():
    with psycopg.connect(BASE, autocommit=True) as conn:
        conn.execute(f"DROP DATABASE IF EXISTS {TEST_DB} WITH (FORCE)")
        conn.execute(f"CREATE DATABASE {TEST_DB}")
    from alembic.config import Config

    from alembic import command

    command.upgrade(Config(os.path.join(os.path.dirname(__file__), "..", "alembic.ini")), "head")
    yield


@pytest.fixture
def client(database):
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        yield c
