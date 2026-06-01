from enum import Enum
from pydantic import BaseModel, EmailStr, field_validator
from core.sanitize import sanitize


# ── Chat ──────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    session_id: str
    message: str

    @field_validator("message")
    @classmethod
    def message_not_empty(cls, v: str) -> str:
        v = sanitize(v, max_length=2000)
        if not v:
            raise ValueError("message cannot be empty")
        return v


class ResponseType(str, Enum):
    answer = "answer"
    off_topic = "off_topic"
    no_info = "no_info"
    limit_reached = "limit_reached"


class ChatResponse(BaseModel):
    reply: str
    action: ResponseType


# ── Contact form ───────────────────────────────────────────────────────────────

class ContactRequest(BaseModel):
    name: str
    email: EmailStr
    message: str

    @field_validator("name", "message")
    @classmethod
    def not_empty(cls, v: str) -> str:
        v = sanitize(v, max_length=2000)
        if not v:
            raise ValueError("field cannot be empty")
        return v


class ContactResponse(BaseModel):
    status: str = "ok"


# ── Ask-me form ────────────────────────────────────────────────────────────────

class AskMeRequest(BaseModel):
    question: str
    email: str | None = None

    @field_validator("question")
    @classmethod
    def question_not_empty(cls, v: str) -> str:
        v = sanitize(v, max_length=2000)
        if not v:
            raise ValueError("question cannot be empty")
        return v


class AskMeResponse(BaseModel):
    status: str = "ok"

