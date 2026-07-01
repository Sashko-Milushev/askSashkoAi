import datetime

from sqlalchemy.orm import Session

from core.logging_config import get_logger
from models.db_models import ConversationMessage, ConversationSession
from models.schemas import ResponseType

logger = get_logger(__name__)


def get_or_create_conversation(
    db: Session,
    session_id: str,
    ip: str | None = None,
) -> ConversationSession:
    conversation = (
        db.query(ConversationSession)
        .filter(ConversationSession.session_id == session_id)
        .first()
    )
    if conversation is None:
        conversation = ConversationSession(session_id=session_id, ip_address=ip)
        db.add(conversation)
        db.flush()
    else:
        if ip and conversation.ip_address != ip:
            conversation.ip_address = ip
        conversation.updated_at = datetime.datetime.now(datetime.UTC)
    return conversation


def save_chat_turn(
    db: Session,
    session_id: str,
    ip: str | None,
    user_message: str,
    assistant_reply: str,
    action: ResponseType,
) -> None:
    conversation = get_or_create_conversation(db, session_id, ip)
    db.add_all(
        [
            ConversationMessage(
                conversation_id=conversation.id,
                role="user",
                content=user_message,
            ),
            ConversationMessage(
                conversation_id=conversation.id,
                role="assistant",
                content=assistant_reply,
                action=action.value,
            ),
        ]
    )
    db.commit()
    logger.info(
        "Conversation turn saved | session=%s action=%s",
        session_id[:8],
        action.value,
    )
