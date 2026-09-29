from __future__ import annotations

import sys
import tempfile
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.database.connection as db_conn
from app.database.connection import Base
from main import app

# Isolated SQLite test database
test_db_path = Path(tempfile.gettempdir()) / "sentinel_isolated_test.db"
TEST_DATABASE_URL = f"sqlite:///{test_db_path}"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)


@event.listens_for(test_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):  # type: ignore[no-untyped-def]
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


@pytest.fixture(autouse=True, scope="session")
def setup_test_db():
    if test_db_path.exists():
        try:
            test_db_path.unlink()
        except Exception:
            pass

    # Rebind SessionLocal and engine to test_engine
    original_engine = db_conn.engine
    db_conn.engine = test_engine
    db_conn.SessionLocal.configure(bind=test_engine)

    Base.metadata.create_all(bind=test_engine)

    yield

    # Teardown
    db_conn.engine = original_engine
    db_conn.SessionLocal.configure(bind=original_engine)
    if test_db_path.exists():
        try:
            test_db_path.unlink()
        except Exception:
            pass


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client
