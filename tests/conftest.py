import pytest
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from api.main import app
from api.database import init_db, create_user
from api.auth import create_token


@pytest.fixture(scope="session", autouse=True)
def setup_db():
    os.environ.setdefault("LEXAVO_JWT_SECRET", "test-secret-key")
    os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
    init_db()
    yield


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers():
    email = f"test_{os.urandom(4).hex()}@lexavo.be"
    user = create_user(
        email=email,
        password_hash="fakehash",
        name="Test User",
        language="fr",
    )
    token = create_token(user["id"], email)
    return {"Authorization": f"Bearer {token}"}
