import asyncio
import json
import logging
from datetime import date
from math import ceil
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.chat_message import ChatMessage
from app.models.user import User
from app.models.user_investment import UserInvestment
from app.models.fire_plan import FirePlan
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


def _build_user_context(
    db: Session,
    user: User,
    profile: Any,
    goals: list[Any],
    fire_plan: dict[str, Any] | None,
) -> dict[str, Any]:
    """
    Build comprehensive user context from database for AI prompt injection.
    
    Fetches:
    - User profile (income, expenses, EMI, insurance, loans, risk profile)
    - Latest investment allocation (equity, debt, gold breakdown)
    - FIRE plan (target, SIP, timeline, remaining surplus)
    - All goals (target, SIP, status, timeline)
    
    Returns structured context hashmap for use in AI prompt.
    """
    # Fetch latest investment record
    latest_investment = (
        db.query(UserInvestment)
        .filter(UserInvestment.user_id == user.id)
        .order_by(UserInvestment.created_at.desc())
        .first()
    )

    investment_context = {
        "total_amount": float(latest_investment.total_amount) if latest_investment else 0.0,
        "equity_amount": float(latest_investment.equity_amount) if latest_investment else 0.0,
        "debt_amount": float(latest_investment.debt_amount) if latest_investment else 0.0,
        "gold_amount": float(latest_investment.gold_amount) if latest_investment else 0.0,
        "equity_percent": (
            round((latest_investment.equity_amount / latest_investment.total_amount * 100), 1)
            if latest_investment and latest_investment.total_amount > 0
            else 0.0
        ),
        "debt_percent": (
            round((latest_investment.debt_amount / latest_investment.total_amount * 100), 1)
            if latest_investment and latest_investment.total_amount > 0
            else 0.0
        ),
        "gold_percent": (
            round((latest_investment.gold_amount / latest_investment.total_amount * 100), 1)
            if latest_investment and latest_investment.total_amount > 0
            else 0.0
        ),
    }

    # Build goals context
    goals_context = []
    for goal in goals:
        goals_context.append(
            {
                "title": str(getattr(goal, "title", "Goal")),
                "category": str(getattr(goal, "category", "Other")),
                "target_amount": float(getattr(goal, "target_amount", 0.0)),
                "current_amount": float(getattr(goal, "current_amount", 0.0)),
                "monthly_sip": float(getattr(goal, "monthly_sip_required", 0.0)),
                "target_date": str(getattr(goal, "target_date", "")),
                "status": str(getattr(goal, "status", "active")),
            }
        )

    # Build FIRE plan context
    fire_context = {}
    if fire_plan:
        fire_context = {
            "fire_target": float(fire_plan.get("fire_target", 0.0)),
            "monthly_sip_fire": float(fire_plan.get("monthly_sip_fire", 0.0)),
            "years_to_retire": int(fire_plan.get("years_to_retire", 0)),
            "retirement_age": int(fire_plan.get("retirement_age", 0)),
            "available_surplus": float(fire_plan.get("available_surplus", 0.0)),
            "remaining_surplus": float(fire_plan.get("remaining_surplus", 0.0)),
            "investable_surplus": float(fire_plan.get("investable_surplus", 0.0)),
            "goals_feasible": bool(fire_plan.get("goals_feasible", False)),
            "status": str(fire_plan.get("status", "Not planned")),
        }

    # Build comprehensive user context
    user_context = {
        "profile": {
            "age": int(getattr(profile, "age", 0)),
            "monthly_income": float(getattr(profile, "income", 0.0)),
            "monthly_expenses": float(getattr(profile, "expenses", 0.0)),
            "monthly_emi": float(getattr(profile, "emi", 0.0)),
            "current_savings": float(getattr(profile, "savings", 0.0)),
            "insurance_coverage": float(getattr(profile, "insurance_coverage", 0.0)),
            "outstanding_loans": float(getattr(profile, "loans", 0.0)),
            "risk_profile": str(getattr(profile, "risk_profile", "moderate")),
            "has_investments": bool(getattr(profile, "has_investments", False)),
        },
        "investments": investment_context,
        "goals": goals_context,
        "fire_plan": fire_context,
    }

    return user_context


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

    # CONTEXT INJECTION: Build full user context for AI prompt
    user_context = _build_user_context(db, user, profile, goals, fire_plan)

    messages = build_messages(
        user_profile=profile,
        goals=goals,
        user_query=payload.query,
        chat_history=history,
        financial_analysis=financial_analysis,
        fire_plan=fire_plan,
        user_context=user_context,
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
