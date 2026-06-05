import datetime
import json
from typing import Any

from openai import OpenAI, APIError, APITimeoutError, RateLimitError
from sqlalchemy.orm import Session

from core.config import settings
from core.logging_config import get_logger
from models.schemas import ChatResponse, ResponseType
from models.db_models import DailyUsage, UnansweredQuestion
from services import rag_service

logger = get_logger(__name__)
client = OpenAI(api_key=settings.openai_api_key)

# ── System prompt ──────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are Sashko Milushev — a Python developer specializing in backend and AI solutions.
You are speaking directly to a visitor of your portfolio website.
Rules:
- Always refer to yourself as "I" (first person). You ARE Sashko.
- Be professional but approachable and human — not robotic. 
- Never talk as an assistant - keep the conversation as a software developer and a male in his 30s.
- Detect the language the user writes in and reply in that exact language.
- Only answer questions about the approved topics below.
- Use the provided context from my knowledge base to answer. The context is extracted from my CV and personal documents.

Approved topics:
- Professional background, skills, work experience, popular technologies, python, backend, ai, machine learning, developer, portfolio
- Projects and work history
- Future positions and availability to work
- Education
- Hobbies and personal life
- Technology opinions
- How to get in touch / contact

Response format — you MUST always return valid JSON with exactly these two fields:
{
  "type": "answer" | "off_topic" | "no_info",
  "message": "<your reply here>"
}

Type rules:
- "answer"    → topic is approved AND context contains relevant information → give a real answer
- "no_info"   → topic is approved BUT context doesn't have enough info to answer properly
- "off_topic" → topic is NOT in the approved list

For "no_info", the message must acknowledge the question warmly and say it's been noted.
For "off_topic", the message must politely redirect to the contact form. But this should not be felt like end or conversation. Suggest to move forward with a similar topic.
Never break out of JSON. Never add fields outside the JSON structure.
"""


# ── Cost tracking ──────────────────────────────────────────────────────────────

def _estimate_cost(input_tokens: int, output_tokens: int) -> float:
    input_cost = (input_tokens / 1_000_000) * settings.openai_input_cost_per_1m
    output_cost = (output_tokens / 1_000_000) * settings.openai_output_cost_per_1m
    return round(input_cost + output_cost, 6)


def _record_usage(db: Session, input_tokens: int, output_tokens: int) -> bool:
    """
    Add token usage to today's DailyUsage record.
    Returns True if the daily cost cap was just hit (alert not yet sent).
    """
    today = datetime.date.today()
    cost = _estimate_cost(input_tokens, output_tokens)
    total_tokens = input_tokens + output_tokens

    row = db.query(DailyUsage).filter(DailyUsage.date == today).first()
    if row is None:
        row = DailyUsage(
            date=today,
            total_tokens=total_tokens,
            estimated_cost_usd=cost,
            cap_alert_sent=False,
        )
        db.add(row)
    else:
        row.total_tokens += total_tokens
        row.estimated_cost_usd = round(row.estimated_cost_usd + cost, 6)

    db.commit()
    db.refresh(row)

    cap_hit = (
        row.estimated_cost_usd >= settings.daily_cost_cap_usd
        and not row.cap_alert_sent
    )
    if cap_hit:
        row.cap_alert_sent = True
        db.commit()

    logger.info(
        "Token usage recorded | input=%d output=%d cost=$%.4f | daily_total=$%.4f",
        input_tokens,
        output_tokens,
        cost,
        row.estimated_cost_usd,
    )
    return cap_hit


def get_daily_cost(db: Session) -> float:
    """Return today's accumulated OpenAI cost in USD."""
    today = datetime.date.today()
    row = db.query(DailyUsage).filter(DailyUsage.date == today).first()
    return float(row.estimated_cost_usd) if row else 0.0


# ── No-info handler ────────────────────────────────────────────────────────────

def save_unanswered_question(db: Session, question: str, email: str | None = None) -> None:
    row = UnansweredQuestion(question=question, email=email)
    db.add(row)
    db.commit()
    logger.info("Unanswered question saved: %.60s...", question)


# ── Core chat logic ────────────────────────────────────────────────────────────

def _build_user_message(question: str, context_chunks: list[dict]) -> str:
    if context_chunks:
        context_text = "\n\n---\n\n".join(
            f"[Source: {c['source']}, page {c['page']}]\n{c['text']}"
            for c in context_chunks
        )
    else:
        context_text = "No relevant context found."

    return f"""Context from my knowledge base:
{context_text}

Visitor's question:
{question}"""


def process_message(
    question: str,
    db: Session,
) -> ChatResponse:
    """
    Core pipeline:
    1. Check daily cost cap
    2. Query RAG for relevant context
    3. Call GPT-4o with system prompt + context
    4. Parse structured JSON response
    5. Record token usage
    6. Return ChatResponse
    """
    # 1. Daily cost cap check
    if get_daily_cost(db) >= settings.daily_cost_cap_usd:
        logger.warning("Daily cost cap reached — blocking request")
        return ChatResponse(
            reply=(
                "My AI self is taking a short break for today — too many great conversations! "
                "Try again tomorrow."
            ),
            action=ResponseType.limit_reached,
        )

    # 2. RAG retrieval
    context_chunks = rag_service.query(question)
    logger.info("RAG returned %d chunks for question: %.60s...", len(context_chunks), question)

    # 3. Build messages
    user_message = _build_user_message(question, context_chunks)
    messages: list[Any] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]

    # 4. Call OpenAI
    try:
        response = client.chat.completions.create(
            model=settings.openai_model,
            messages=messages,
            response_format={"type": "json_object"},  # type: ignore[arg-type]
            temperature=0.7,
            max_tokens=800,
        )
    except APITimeoutError:
        logger.error("OpenAI request timed out")
        return ChatResponse(
            reply="I'm having a bit of a brain freeze right now — please try again in a moment.",
            action=ResponseType.answer,
        )
    except RateLimitError:
        logger.error("OpenAI rate limit hit")
        return ChatResponse(
            reply="I'm a bit overwhelmed right now — give me a second and try again.",
            action=ResponseType.answer,
        )
    except APIError as exc:
        logger.error("OpenAI API error: %s", exc)
        return ChatResponse(
            reply="Something went wrong on my end — please try again shortly.",
            action=ResponseType.answer,
        )

    # 5. Parse response
    raw_content = response.choices[0].message.content or "{}"
    input_tokens = response.usage.prompt_tokens if response.usage else 0
    output_tokens = response.usage.completion_tokens if response.usage else 0

    try:
        parsed = json.loads(raw_content)
        response_type = parsed.get("type", "answer")
        message = parsed.get("message", "")
    except json.JSONDecodeError:
        logger.warning("GPT returned non-JSON: %s", raw_content[:200])
        response_type = "answer"
        message = raw_content

    # 6. Record usage + check cap alert
    cap_just_hit = _record_usage(db, input_tokens, output_tokens)
    if cap_just_hit:
        try:
            import asyncio
            from services.email_service import send_cap_alert as _send_cap_alert
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(_send_cap_alert(get_daily_cost(db)))
            else:
                loop.run_until_complete(_send_cap_alert(get_daily_cost(db)))
        except Exception as exc:
            logger.warning("Cap alert email failed to schedule: %s", exc)

    # 7. Map type → save unanswered if needed
    action_map = {
        "answer": ResponseType.answer,
        "no_info": ResponseType.no_info,
        "off_topic": ResponseType.off_topic,
    }
    action = action_map.get(response_type, ResponseType.answer)

    if action == ResponseType.no_info:
        save_unanswered_question(db, question)

    logger.info(
        "Chat response | type=%s | tokens in=%d out=%d",
        action.value,
        input_tokens,
        output_tokens,
    )
    return ChatResponse(reply=message, action=action)

