from fastapi import APIRouter, BackgroundTasks, Request

from core.dependencies import DbSession
from core.limiter import limiter
from core.logging_config import get_logger
from core.config import settings
from models.db_models import ContactSubmission, UnansweredQuestion
from models.schemas import (
    AskMeRequest, AskMeResponse,
    ContactRequest, ContactResponse,
)
from services.email_service import send_contact_notification

logger = get_logger(__name__)
router = APIRouter()


@router.post("/", response_model=ContactResponse)
@limiter.limit(settings.contact_burst_limit)
async def submit_contact(
    request: Request,
    payload: ContactRequest,
    background_tasks: BackgroundTasks,
    db: DbSession,
) -> ContactResponse:
    """Save contact form submission to DB and notify owner by email."""
    row = ContactSubmission(
        name=payload.name,
        email=str(payload.email),
        message=payload.message,
    )
    db.add(row)
    db.commit()
    logger.info("Contact submission saved | from=%s <%s>", payload.name, payload.email)

    background_tasks.add_task(
        send_contact_notification,
        payload.name,
        str(payload.email),
        payload.message,
    )
    return ContactResponse()


@router.post("/ask-me", response_model=AskMeResponse)
@limiter.limit(settings.contact_burst_limit)
async def ask_me(request: Request, payload: AskMeRequest, db: DbSession) -> AskMeResponse:
    """Save a question directly from the user (unanswered/to-do list)."""
    row = UnansweredQuestion(
        question=payload.question,
        email=payload.email,
    )
    db.add(row)
    db.commit()
    logger.info("Ask-me question saved | email=%s | q=%.60s...", payload.email, payload.question)
    return AskMeResponse()
