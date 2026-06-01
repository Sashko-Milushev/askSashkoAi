"""
Shared pytest fixtures.
- Isolated in-memory SQLite DB per test
- FastAPI TestClient with overridden DB dependency
- Mocked OpenAI and RAG calls (never hit real API)
"""
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from core.database import Base, get_db

# ── Test DB — shared in-memory SQLite (StaticPool keeps a single connection) ──
TEST_DB_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,   # all operations share one connection → same in-memory DB
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(autouse=True)
def setup_test_db():
    """Create all tables before each test, drop after."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db_session(setup_test_db) -> Generator[Session, None, None]:
    """Yield a test DB session — tables guaranteed to exist (depends on setup_test_db)."""
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """FastAPI TestClient with DB dependency overridden to use test DB."""
    # Import here to avoid triggering lifespan (RAG build) during test collection
    from main import app

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with patch("services.rag_service.build_index"):   # skip RAG build on startup
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c

    app.dependency_overrides.clear()


# ── OpenAI mock helpers ────────────────────────────────────────────────────────

def make_chat_response(content: str, input_tokens: int = 50, output_tokens: int = 30):
    """Build a minimal fake OpenAI chat completion response."""
    choice = MagicMock()
    choice.message.content = content
    resp = MagicMock()
    resp.choices = [choice]
    resp.usage.prompt_tokens = input_tokens
    resp.usage.completion_tokens = output_tokens
    return resp


def make_embedding_response(dim: int = 8):
    """Build a minimal fake OpenAI embedding response."""
    item = MagicMock()
    item.embedding = [0.1] * dim
    resp = MagicMock()
    resp.data = [item]
    return resp

