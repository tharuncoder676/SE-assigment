"""Pytest fixtures.

Each test gets a throw-away file-backed SQLite database. A file (rather than
an in-memory) database is used deliberately: the concurrency test spawns real
threads, and every thread must be able to open its own connection to the same
database, exactly as it would against PostgreSQL in production.

Three things are redirected at that database:
  * the ``get_db`` request dependency,
  * ``database.session_scope`` used by the background event-bus workers,
  * the ``db_session`` fixture used for direct assertions.
"""
import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("PBKDF2_ITERATIONS", "1000")   # keep the suite fast
os.environ.setdefault("JWT_SECRET", "test-secret")

from app import database                       # noqa: E402
from app.database import Base, get_db          # noqa: E402
from app.main import app                        # noqa: E402
from app.ratelimit import limiter               # noqa: E402
from app.seed import seed_database              # noqa: E402


@pytest.fixture()
def engine(tmp_path):
    url = "sqlite:///%s" % (tmp_path / "test.db").as_posix()
    engine = create_engine(url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def SessionFactory(engine, monkeypatch):
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    # Background workers must land in the test database too.
    monkeypatch.setattr(database, "session_scope", lambda: factory())
    return factory


@pytest.fixture()
def db_session(SessionFactory):
    session = SessionFactory()
    seed_database(session, days=2)
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db_session, SessionFactory):
    """TestClient whose every request opens its own session, so concurrent
    requests behave as they do under uvicorn."""
    def override_get_db():
        session = SessionFactory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    limiter.reset()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def patient(client):
    """A registered patient plus an Authorization header for that patient."""
    response = client.post("/api/v1/auth/register", json={
        "full_name": "Priya Sharma",
        "email": "priya.patient@smartcare.local",
        "phone": "9876543210",
        "password": "Patient@12345",
    })
    assert response.status_code == 201, response.text
    token = response.json()["access_token"]
    return {"Authorization": "Bearer " + token}


@pytest.fixture()
def free_slot(client):
    doctor_id = client.get("/api/v1/doctors").json()[0]["id"]
    return client.get("/api/v1/doctors/%d/slots" % doctor_id).json()[0]
