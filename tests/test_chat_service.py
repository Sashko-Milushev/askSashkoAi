import json
from unittest.mock import patch, MagicMock


from services.chat_service import (
    process_message,
    _estimate_cost,
    _record_usage,
    get_daily_cost,
    save_unanswered_question,
)
from models.schemas import ResponseType
from models.db_models import DailyUsage, UnansweredQuestion
from tests.conftest import make_chat_response


# ── Cost helpers ───────────────────────────────────────────────────────────────

def test_estimate_cost_zero():
    assert _estimate_cost(0, 0) == 0.0


def test_estimate_cost_nonzero():
    cost = _estimate_cost(1_000_000, 0)
    assert cost > 0


# ── DB helpers ─────────────────────────────────────────────────────────────────

def test_record_usage_creates_row(db_session):
    _record_usage(db_session, 100, 50)
    row = db_session.query(DailyUsage).first()
    assert row is not None
    assert row.total_tokens == 150


def test_record_usage_accumulates(db_session):
    _record_usage(db_session, 100, 50)
    _record_usage(db_session, 200, 100)
    row = db_session.query(DailyUsage).first()
    assert row.total_tokens == 450


def test_record_usage_returns_cap_hit(db_session):
    with patch("services.chat_service.settings") as s:
        s.daily_cost_cap_usd = 0.000001
        s.openai_input_cost_per_1m = 2.5
        s.openai_output_cost_per_1m = 10.0
        cap_hit = _record_usage(db_session, 10_000, 0)
    assert cap_hit is True


def test_record_usage_no_duplicate_alert(db_session):
    with patch("services.chat_service.settings") as s:
        s.daily_cost_cap_usd = 0.000001
        s.openai_input_cost_per_1m = 2.5
        s.openai_output_cost_per_1m = 10.0
        _record_usage(db_session, 10_000, 0)  # first hit → True
        cap_hit2 = _record_usage(db_session, 10_000, 0)  # already alerted
    assert cap_hit2 is False


def test_get_daily_cost_zero_when_no_rows(db_session):
    assert get_daily_cost(db_session) == 0.0


def test_save_unanswered_question(db_session):
    save_unanswered_question(db_session, "What is your hobby?", "user@test.com")
    row = db_session.query(UnansweredQuestion).first()
    assert row.question == "What is your hobby?"
    assert row.email == "user@test.com"
    assert row.resolved is False


# ── process_message ────────────────────────────────────────────────────────────

def _mock_rag(monkeypatch):
    monkeypatch.setattr("services.chat_service.rag_service.query", lambda *a, **kw: [])


def test_process_message_answer(db_session, monkeypatch):
    _mock_rag(monkeypatch)
    gpt_resp = make_chat_response(json.dumps({"type": "answer", "message": "I work with Python."}))
    with patch("services.chat_service.client.chat.completions.create", return_value=gpt_resp):
        result = process_message("What do you do?", db_session)
    assert result.action == ResponseType.answer
    assert "Python" in result.reply


def test_process_message_off_topic(db_session, monkeypatch):
    _mock_rag(monkeypatch)
    gpt_resp = make_chat_response(json.dumps({"type": "off_topic", "message": "Please use the contact form."}))
    with patch("services.chat_service.client.chat.completions.create", return_value=gpt_resp):
        result = process_message("What is the weather today?", db_session)
    assert result.action == ResponseType.off_topic


def test_process_message_no_info_saves_question(db_session, monkeypatch):
    _mock_rag(monkeypatch)
    gpt_resp = make_chat_response(json.dumps({"type": "no_info", "message": "Noted, I'll look into it."}))
    with patch("services.chat_service.client.chat.completions.create", return_value=gpt_resp):
        result = process_message("What is your favourite food?", db_session)
    assert result.action == ResponseType.no_info
    saved = db_session.query(UnansweredQuestion).first()
    assert saved is not None


def test_process_message_blocks_when_cap_hit(db_session, monkeypatch):
    _mock_rag(monkeypatch)
    import datetime
    from models.db_models import DailyUsage
    row = DailyUsage(
        date=datetime.date.today(),
        total_tokens=999999,
        estimated_cost_usd=999.0,
        cap_alert_sent=True,
    )
    db_session.add(row)
    db_session.commit()

    with patch("services.chat_service.client.chat.completions.create") as mock_gpt:
        result = process_message("Tell me about yourself.", db_session)
        mock_gpt.assert_not_called()

    assert result.action == ResponseType.limit_reached


def test_process_message_handles_openai_timeout(db_session, monkeypatch):
    from openai import APITimeoutError
    _mock_rag(monkeypatch)
    with patch(
        "services.chat_service.client.chat.completions.create",
        side_effect=APITimeoutError(request=MagicMock()),
    ):
        result = process_message("Hello?", db_session)
    assert result.action == ResponseType.answer
    assert "brain freeze" in result.reply

