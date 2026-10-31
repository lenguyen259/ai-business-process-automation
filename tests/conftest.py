import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Isolate test DB / audit log before app import side effects.
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["JWT_SECRET"] = "test-secret"
os.environ["LLM_PROVIDER"] = "mock"
os.environ["ENABLE_PII_REDACTION"] = "true"
os.environ["AUDIT_LOG_PATH"] = str(Path(__file__).parent / "_audit_test.jsonl")

from app.config import get_settings
from app.db import Base, get_db
from app.main import app
from app.security import DEMO_USERS


@pytest.fixture()
def client(tmp_path, monkeypatch):
    get_settings.cache_clear()
    audit_path = tmp_path / "audit.jsonl"
    monkeypatch.setenv("AUDIT_LOG_PATH", str(audit_path))
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    get_settings.cache_clear()

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    get_settings.cache_clear()


@pytest.fixture()
def auth_header(client: TestClient) -> dict[str, str]:
    # Ensure demo user exists (module import may hash lazily).
    assert "engineer@example.com" in DEMO_USERS
    response = client.post(
        "/auth/login",
        json={"email": "engineer@example.com", "password": "demo-pass-123"},
    )
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
