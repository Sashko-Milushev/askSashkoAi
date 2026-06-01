import datetime
from sqlalchemy import Boolean, Column, Date, DateTime, Float, Integer, String, Text
from core.database import Base


def _now() -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC)


class UnansweredQuestion(Base):
    __tablename__ = "unanswered_questions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    question = Column(Text, nullable=False)
    email = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)
    resolved = Column(Boolean, default=False, nullable=False)


class ContactSubmission(Base):
    __tablename__ = "contact_submissions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)


class DailyUsage(Base):
    __tablename__ = "daily_usage"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, unique=True, nullable=False)
    total_tokens = Column(Integer, default=0, nullable=False)
    estimated_cost_usd = Column(Float, default=0.0, nullable=False)
    cap_alert_sent = Column(Boolean, default=False, nullable=False)


class SessionUsage(Base):
    __tablename__ = "session_usage"

    session_id = Column(String(64), primary_key=True)
    message_count = Column(Integer, default=0, nullable=False)
    ip_address = Column(String(64), nullable=True)
    date = Column(Date, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)

