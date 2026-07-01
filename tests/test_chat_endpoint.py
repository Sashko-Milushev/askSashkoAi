import json
import datetime
from unittest.mock import patch


from models.db_models import ConversationMessage, ConversationSession, DailyUsage
from tests.conftest import make_chat_response

SESSION = "test-session-abc"


def _chat(client, message=None, session_id=SESSION):
    return client.post("/chat/", json={
        "session_id": session_id,
        "message": message or "Tell me about yourself.",
    })


def _mock_gpt(response_type: str, message: str):
    return make_chat_response(json.dumps({"type": response_type, "message": message}))


# ── Basic ──────────────────────────────────────────────────────────────────────

def test_chat_valid_message(client, monkeypatch):
    monkeypatch.setattr("services.chat_service.rag_service.query", lambda *a, **kw: [])
    gpt = _mock_gpt("answer", "I am Sashko.")
    with patch("services.chat_service.client.chat.completions.create", return_value=gpt):
        resp = _chat(client)
    assert resp.status_code == 200
    data = resp.json()
    assert data["action"] == "answer"
    assert data["reply"] == "I am Sashko."


def test_chat_saves_conversation_turn(client, monkeypatch, db_session):
    monkeypatch.setattr("services.chat_service.rag_service.query", lambda *a, **kw: [])
    gpt = _mock_gpt("answer", "I am Sashko.")
    with patch("services.chat_service.client.chat.completions.create", return_value=gpt):
        resp = _chat(client, message="Tell me about your backend work.")

    assert resp.status_code == 200

    conversation = db_session.query(ConversationSession).filter_by(session_id=SESSION).first()
    assert conversation is not None

    messages = (
        db_session.query(ConversationMessage)
        .filter_by(conversation_id=conversation.id)
        .order_by(ConversationMessage.id)
        .all()
    )
    assert len(messages) == 2
    assert messages[0].role == "user"
    assert messages[0].content == "Tell me about your backend work."
    assert messages[0].action is None
    assert messages[1].role == "assistant"
    assert messages[1].content == "I am Sashko."
    assert messages[1].action == "answer"


def test_chat_empty_message_rejected(client):
    resp = _chat(client, message="   ")
    assert resp.status_code == 422


def test_chat_off_topic_returns_off_topic(client, monkeypatch):
    monkeypatch.setattr("services.chat_service.rag_service.query", lambda *a, **kw: [])
    gpt = _mock_gpt("off_topic", "Please use the contact form.")
    with patch("services.chat_service.client.chat.completions.create", return_value=gpt):
        resp = _chat(client, message="What is 2+2?")
    assert resp.json()["action"] == "off_topic"


def test_chat_no_info_returns_no_info(client, monkeypatch, db_session):
    monkeypatch.setattr("services.chat_service.rag_service.query", lambda *a, **kw: [])
    gpt = _mock_gpt("no_info", "Noted, I'll find out.")
    with patch("services.chat_service.client.chat.completions.create", return_value=gpt):
        resp = _chat(client, message="What is your favourite colour?")
    assert resp.json()["action"] == "no_info"


# ── Rate limits ────────────────────────────────────────────────────────────────

def test_chat_session_limit_hit(client, db_session, monkeypatch):
    monkeypatch.setattr("services.chat_service.rag_service.query", lambda *a, **kw: [])
    gpt = _mock_gpt("answer", "Hello.")
    with patch("services.chat_service.client.chat.completions.create", return_value=gpt):
        with patch("services.rate_limit_service.settings") as mock_s:
            mock_s.session_message_limit = 2
            mock_s.ip_daily_message_limit = 1000
            _chat(client, session_id="cap-sess")
            _chat(client, session_id="cap-sess")
            resp = _chat(client, session_id="cap-sess")
    assert resp.json()["action"] == "limit_reached"


def test_chat_cost_cap_blocks_openai(client, db_session, monkeypatch):
    monkeypatch.setattr("services.chat_service.rag_service.query", lambda *a, **kw: [])
    row = DailyUsage(
        date=datetime.date.today(),
        total_tokens=999999,
        estimated_cost_usd=999.0,
        cap_alert_sent=True,
    )
    db_session.add(row)
    db_session.commit()

    with patch("services.chat_service.client.chat.completions.create") as mock_gpt:
        resp = _chat(client)
        mock_gpt.assert_not_called()

    assert resp.json()["action"] == "limit_reached"

