from fastapi import APIRouter, Request

from core.dependencies import DbSession
from core.limiter import limiter
from core.logging_config import get_logger
from core.config import settings
from models.schemas import ChatRequest, ChatResponse, ResponseType
from services import chat_service, rate_limit_service

logger = get_logger(__name__)
router = APIRouter()

_LIMIT_REPLY = (
    "I've really enjoyed our chat, but I've hit my message limit for this session. "
    "Come back tomorrow and we can continue!"
)


def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.post("/", response_model=ChatResponse)
@limiter.limit(settings.chat_burst_limit)
async def chat(request: Request, payload: ChatRequest, db: DbSession) -> ChatResponse:
    """Main chat endpoint — processes a user message and returns Sashko's AI reply."""
    ip = _get_client_ip(request)

    # Session limit check
    if not rate_limit_service.check_session_limit(db, payload.session_id, ip):
        logger.info("Session limit hit | session=%s", payload.session_id[:8])
        return ChatResponse(reply=_LIMIT_REPLY, action=ResponseType.limit_reached)

    # IP daily limit check
    if not rate_limit_service.check_ip_limit(db, ip):
        logger.info("IP daily limit hit | ip=%s", ip)
        return ChatResponse(reply=_LIMIT_REPLY, action=ResponseType.limit_reached)

    # Process through AI pipeline
    response = chat_service.process_message(question=payload.message, db=db)

    # Only increment counter on real AI calls (not limit_reached from cost cap)
    if response.action != ResponseType.limit_reached:
        rate_limit_service.increment_session_count(db, payload.session_id, ip)

    return response
