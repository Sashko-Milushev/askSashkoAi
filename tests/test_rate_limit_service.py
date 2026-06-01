from unittest.mock import patch


from services.rate_limit_service import (
    check_session_limit,
    check_ip_limit,
    increment_session_count,
    get_or_create_session,
)
from models.db_models import SessionUsage


SESSION_ID = "test-session-001"
IP = "1.2.3.4"


def test_new_session_is_within_limit(db_session):
    assert check_session_limit(db_session, SESSION_ID, IP) is True


def test_session_at_limit_is_blocked(db_session):
    with patch("services.rate_limit_service.settings") as mock_settings:
        mock_settings.session_message_limit = 3
        mock_settings.ip_daily_message_limit = 100
        for _ in range(3):
            increment_session_count(db_session, SESSION_ID, IP)
        assert check_session_limit(db_session, SESSION_ID, IP) is False


def test_increment_increases_count(db_session):
    increment_session_count(db_session, SESSION_ID, IP)
    increment_session_count(db_session, SESSION_ID, IP)
    row = db_session.query(SessionUsage).filter_by(session_id=SESSION_ID).first()
    assert row.message_count == 2


def test_ip_within_daily_limit(db_session):
    assert check_ip_limit(db_session, IP) is True


def test_ip_over_daily_limit_blocked(db_session):
    with patch("services.rate_limit_service.settings") as mock_settings:
        mock_settings.ip_daily_message_limit = 2
        mock_settings.session_message_limit = 100
        # Two different sessions from same IP
        increment_session_count(db_session, "sess-a", IP)
        increment_session_count(db_session, "sess-b", IP)
        assert check_ip_limit(db_session, IP) is False


def test_different_ips_are_independent(db_session):
    with patch("services.rate_limit_service.settings") as mock_settings:
        mock_settings.ip_daily_message_limit = 1
        mock_settings.session_message_limit = 100
        increment_session_count(db_session, SESSION_ID, "1.1.1.1")
        # Different IP should still pass
        assert check_ip_limit(db_session, "2.2.2.2") is True


def test_get_or_create_creates_once(db_session):
    row1 = get_or_create_session(db_session, SESSION_ID, IP)
    row2 = get_or_create_session(db_session, SESSION_ID, IP)
    assert row1.session_id == row2.session_id
    count = db_session.query(SessionUsage).filter_by(session_id=SESSION_ID).count()
    assert count == 1

