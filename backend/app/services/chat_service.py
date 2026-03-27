import asyncio
import logging

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.chat_message import ChatMessage
from app.models.user import User
from app.schemas.chat import ChatRequest
from app.services.ai.llm_service import generate_response
from app.services.ai.prompt_builder import build_messages
from app.services.finance_service import get_financial_profile
from app.services.finance_rules.engine import run_all_rules
from app.services.goal_service import list_goals


logger = logging.getLogger(__name__)


ONBOARDING_REQUIRED_MESSAGE = (
    "I need your financial profile before I can give personalized advice. "
    "Please complete onboarding first."
)
FALLBACK_LLM_MESSAGE = (
    "I could not generate a full analysis right now. "
    "Please try again in a moment."
)


def _recent_chat_history(db: Session, user: User, limit: int = 5) -> list[ChatMessage]:
    return (
        db.query(ChatMessage)
        .filter(ChatMessage.user_id == user.id)
        .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
        .limit(limit)
        .all()
    )


def _save_chat_turn(db: Session, user: User, user_query: str, assistant_response: str) -> None:
    db.add(ChatMessage(user_id=user.id, role="user", content=user_query))
    db.add(ChatMessage(user_id=user.id, role="assistant", content=assistant_response))
    db.commit()


def _run_async_response(messages: list[dict[str, str]]) -> str:
    try:
        return asyncio.run(generate_response(messages))
    except RuntimeError as exc:
        if "asyncio.run() cannot be called from a running event loop" not in str(exc):
            raise
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(generate_response(messages))
        finally:
            loop.close()


def chat_with_mentor(db: Session, user: User, payload: ChatRequest) -> str:
    try:
        profile = get_financial_profile(db, user)
    except HTTPException as exc:
        if exc.status_code != 404:
            raise
        assistant_response = ONBOARDING_REQUIRED_MESSAGE
        _save_chat_turn(db, user, payload.query, assistant_response)
        return assistant_response

    goals = list_goals(db, user)
    history = _recent_chat_history(db, user, limit=5)

    financial_analysis = None
    try:
        financial_analysis = run_all_rules(profile)
    except Exception:
        logger.exception("Finance rules evaluation failed; continuing without system analysis")

    messages = build_messages(
        user_profile=profile,
        goals=goals,
        user_query=payload.query,
        chat_history=history,
        financial_analysis=financial_analysis,
    )

    try:
        assistant_response = _run_async_response(messages)
    except Exception:
        assistant_response = FALLBACK_LLM_MESSAGE

    _save_chat_turn(db, user, payload.query, assistant_response)
    return assistant_response


def get_chat_history(db: Session, user: User, limit: int = 50) -> list[ChatMessage]:
    return (
        db.query(ChatMessage)
        .filter(ChatMessage.user_id == user.id)
        .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
        .limit(limit)
        .all()
    )
