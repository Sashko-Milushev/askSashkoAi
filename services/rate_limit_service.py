import datetime

from sqlalchemy.orm import Session

from core.config import settings
from core.logging_config import get_logger
from models.db_models import SessionUsage

logger = get_logger(__name__)


def get_or_create_session(db: Session, session_id: str, ip: str) -> SessionUsage:
    today = datetime.date.today()
    row = db.query(SessionUsage).filter(SessionUsage.session_id == session_id).first()
    if row is None:
        row = SessionUsage(
            session_id=session_id,
            message_count=0,
            ip_address=ip,
            date=today,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def check_session_limit(db: Session, session_id: str, ip: str) -> bool:
    """Returns True if the session is within the allowed message limit."""
    row = get_or_create_session(db, session_id, ip)
    return int(row.message_count) < settings.session_message_limit


def check_ip_limit(db: Session, ip: str) -> bool:
    """Returns True if the IP is within the allowed daily message limit."""
    today = datetime.date.today()
    total = (
        db.query(SessionUsage)
        .filter(SessionUsage.ip_address == ip, SessionUsage.date == today)
        .with_entities(SessionUsage.message_count)
        .all()
    )
    ip_total = sum(int(row.message_count) for row in total)
    return ip_total < settings.ip_daily_message_limit


def increment_session_count(db: Session, session_id: str, ip: str) -> None:
    row = get_or_create_session(db, session_id, ip)
    row.message_count = int(row.message_count) + 1
    db.commit()
    logger.info(
        "Session count | session=%s ip=%s count=%d",
        session_id[:8],
        ip,
        row.message_count,
    )

