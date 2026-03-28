import asyncio
import logging
from datetime import date
from math import ceil

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.chat_message import ChatMessage
from app.models.user import User
from app.schemas.chat import ChatRequest
from app.services.ai.llm_service import generate_response
from app.services.ai.prompt_builder import build_messages
from app.services.finance_service import get_financial_profile
from app.services.fire.fire_planner import generate_fire_plan
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
GREETING_ONLY_MESSAGE = (
    "Hi. Ask a specific finance question so I can give a precise decision. "
    "For example: Should I repay debt first, increase SIP, or build emergency fund?"
)


def _is_greeting_or_smalltalk(query: str) -> bool:
    text = " ".join((query or "").strip().lower().split())
    if not text:
        return True

    exact_greetings = {
        "hi",
        "hello",
        "hey",
        "yo",
        "hola",
        "good morning",
        "good afternoon",
        "good evening",
        "how are you",
        "how r u",
        "sup",
        "whats up",
        "what's up",
    }
    if text in exact_greetings:
        return True

    finance_terms = {
        "loan",
        "emi",
        "debt",
        "savings",
        "invest",
        "sip",
        "mutual",
        "fund",
        "expense",
        "expenses",
        "income",
        "budget",
        "portfolio",
        "tax",
        "insurance",
        "repay",
        "credit",
        "goal",
    }
    tokens = set(text.split())
    short_greeting = len(tokens) <= 3 and bool(
        tokens.intersection({"hi", "hello", "hey", "yo", "sup", "morning", "evening"})
    )

    return short_greeting and not any(term in text for term in finance_terms)


def _is_fire_related_query(query: str) -> bool:
    text = (query or "").strip().lower()
    if not text:
        return False

    fire_terms = {
        "fire",
        "retire",
        "retirement",
        "financial independence",
        "goal",
        "house",
        "car",
        "travel",
        "sip",
    }
    return any(term in text for term in fire_terms)


def _is_sip_affordability_query(query: str) -> bool:
    text = (query or "").strip().lower()
    if not text:
        return False
    terms = {"sip", "invest", "investment", "afford", "feasible", "realistic", "goal"}
    return any(term in text for term in terms)


def _fallback_finance_response(query: str, financial_analysis: dict | None) -> str:
    if not financial_analysis:
        return FALLBACK_LLM_MESSAGE

    metrics = financial_analysis.get("metrics", {}) if isinstance(financial_analysis, dict) else {}
    flags = financial_analysis.get("flags", {}) if isinstance(financial_analysis, dict) else {}

    if _is_sip_affordability_query(query):
        investable_surplus = float(metrics.get("investable_surplus", 0.0))
        available_surplus = float(metrics.get("available_surplus", 0.0))
        safety_buffer_amount = float(metrics.get("safety_buffer_amount", 0.0))
        should_invest = bool(flags.get("should_invest"))

        if should_invest:
            return (
                "Based on your financial data, starting or increasing SIP is feasible now. "
                f"Your available surplus is about ₹{available_surplus:,.0f} per month, "
                f"with ₹{safety_buffer_amount:,.0f} reserved as safety buffer, leaving "
                f"₹{investable_surplus:,.0f} investable each month."
            )

        return (
            "Based on your financial data, this SIP is not feasible right now. "
            f"Your available surplus is about ₹{available_surplus:,.0f} per month, "
            f"and after a ₹{safety_buffer_amount:,.0f} safety buffer, investable surplus is ₹{investable_surplus:,.0f}. "
            "You should first improve monthly surplus or extend the goal timeline."
        )

    return FALLBACK_LLM_MESSAGE


def _years_from_target_date(target_date: date) -> int:
    days_remaining = (target_date - date.today()).days
    if days_remaining <= 0:
        return 0
    return max(ceil(days_remaining / 365), 1)


def _profile_for_fire(profile: object) -> dict[str, float | int | str]:
    return {
        "age": int(getattr(profile, "age", 0) or 0),
        "monthly_income": float(getattr(profile, "income", 0.0) or 0.0),
        "monthly_expenses": float(getattr(profile, "expenses", 0.0) or 0.0),
        "current_savings": float(getattr(profile, "savings", 0.0) or 0.0),
        "monthly_emi": float(getattr(profile, "emi", 0.0) or 0.0),
        "risk_profile": str(getattr(profile, "risk_profile", "moderate") or "moderate"),
    }


def _goals_for_fire(goals: list[object]) -> list[dict[str, float | int | str]]:
    mapped_goals: list[dict[str, float | int | str]] = []
    for goal in goals:
        target_date = getattr(goal, "target_date", None)
        years = _years_from_target_date(target_date) if isinstance(target_date, date) else 0
        mapped_goals.append(
            {
                "name": str(getattr(goal, "title", "Goal") or "Goal"),
                "amount": float(getattr(goal, "target_amount", 0.0) or 0.0),
                "years": years,
            }
        )
    return mapped_goals


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

    if _is_greeting_or_smalltalk(payload.query):
        assistant_response = GREETING_ONLY_MESSAGE
        _save_chat_turn(db, user, payload.query, assistant_response)
        return assistant_response

    goals = list_goals(db, user, status="active")
    history = _recent_chat_history(db, user, limit=5)

    financial_analysis = None
    try:
        financial_analysis = run_all_rules(profile)
    except Exception:
        logger.exception("Finance rules evaluation failed; continuing without system analysis")

    fire_plan = None
    if _is_fire_related_query(payload.query):
        try:
            fire_plan = generate_fire_plan(_profile_for_fire(profile), _goals_for_fire(goals))
        except Exception:
            logger.exception("FIRE plan generation failed; continuing without FIRE context")

    messages = build_messages(
        user_profile=profile,
        goals=goals,
        user_query=payload.query,
        chat_history=history,
        financial_analysis=financial_analysis,
        fire_plan=fire_plan,
    )

    try:
        assistant_response = _run_async_response(messages)
    except Exception:
        assistant_response = _fallback_finance_response(payload.query, financial_analysis)

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
