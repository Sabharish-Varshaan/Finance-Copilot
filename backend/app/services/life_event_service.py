from datetime import date
from math import ceil
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.goal import Goal
from app.models.user import User
from app.models.user_investment import UserInvestment
from app.schemas.life_event import LifeEventRequest, LifeEventResponse
from app.services.finance_service import get_financial_profile
from app.services.fire.fire_planner import DEFAULT_MULTIPLIER, DEFAULT_RETIREMENT_AGE, generate_fire_plan
from app.services.fire_service import get_current_fire_plan
from app.services.goal_service import calculate_monthly_sip, list_goals
from app.services.goals.goal_planner import get_expected_return


def _years_from_target_date(target_date: date) -> int:
    days_remaining = (target_date - date.today()).days
    if days_remaining <= 0:
        return 0
    return max(ceil(days_remaining / 365), 1)


def _add_years_safe(start: date, years: int) -> date:
    try:
        return start.replace(year=start.year + years)
    except ValueError:
        # Handles Feb 29 for non-leap target years.
        return start.replace(month=2, day=28, year=start.year + years)


def _current_fire_plan_or_none(db: Session, user: User):
    try:
        return get_current_fire_plan(db, user)
    except HTTPException as exc:
        if exc.status_code == 404:
            return None
        raise


def _goals_for_planner(goals: list[Goal]) -> list[dict[str, Any]]:
    return [
        {
            "name": str(goal.title),
            "amount": float(goal.target_amount),
            "years": _years_from_target_date(goal.target_date),
        }
        for goal in goals
    ]


def _simulate_fire(
    profile_payload: dict[str, Any],
    goals_payload: list[dict[str, Any]],
    investment_portfolio_current: float,
    investment_breakdown: dict[str, float],
    current_fire_plan: Any,
) -> dict[str, Any]:
    retirement_age = int(current_fire_plan.retirement_age) if current_fire_plan else DEFAULT_RETIREMENT_AGE
    multiplier = float(current_fire_plan.multiplier) if current_fire_plan else DEFAULT_MULTIPLIER
    expected_return_input = (
        float(current_fire_plan.expected_return)
        if current_fire_plan and str(current_fire_plan.return_source) == "user"
        else None
    )

    total_assets = float(profile_payload.get("current_savings", 0.0)) + investment_portfolio_current

    return generate_fire_plan(
        profile=profile_payload,
        goals=goals_payload,
        retirement_age=retirement_age,
        multiplier=multiplier,
        expected_return_input=expected_return_input,
        investment_portfolio_current=investment_portfolio_current,
        total_assets=total_assets,
        investment_breakdown=investment_breakdown,
    )


def _calculate_allocation(
    amount: float, 
    emergency_gap: float, 
    outstanding_debt: float
) -> dict[str, float]:
    """
    Allocate event amount using MIN logic:
    - Emergency: MIN(amount * 0.2, emergency_gap)
    - Debt: MIN(amount * 0.3, outstanding_debt)
    - Investment: remainder (not exceeding amount * 0.5)
    - Discretionary: rest
    """
    emergency = round(min(amount * 0.2, emergency_gap), 2)
    debt = round(min(amount * 0.3, outstanding_debt), 2)
    available_for_investment = amount - emergency - debt
    investment = round(min(available_for_investment, amount * 0.5), 2)
    discretionary = round(max(amount - emergency - debt - investment, 0.0), 2)
    return {
        "emergency_fund": emergency,
        "debt_repayment": debt,
        "investments": investment,
        "discretionary": discretionary,
    }


def _simplify_small_event_allocation(
    amount: float,
    outstanding_debt: float,
) -> dict[str, float]:
    """
    Simplified allocation for small events (< ₹50,000).
    Prioritizes either debt payoff or savings without micro-splits.
    """
    if outstanding_debt > 0:
        # Prioritize debt: pay as much as possible, rest to savings
        debt_payment = min(amount, outstanding_debt)
        savings = max(amount - debt_payment, 0.0)
        return {
            "emergency_fund": savings,
            "debt_repayment": debt_payment,
            "investments": 0.0,
            "discretionary": 0.0,
        }
    else:
        # No debt: allocate everything to savings
        return {
            "emergency_fund": amount,
            "debt_repayment": 0.0,
            "investments": 0.0,
            "discretionary": 0.0,
        }


def _allocate_investment_by_risk(
    investment_amount: float,
    risk_profile: str
) -> dict[str, float]:
    """
    Split investment amount by risk profile.
    - aggressive: 90/5/5 (equity/debt/gold)
    - moderate: 70/20/10 (equity/debt/gold)
    - conservative: 50/40/10 (equity/debt/gold)
    """
    if risk_profile == "aggressive":
        equity_pct, debt_pct, gold_pct = 0.90, 0.05, 0.05
    elif risk_profile == "conservative":
        equity_pct, debt_pct, gold_pct = 0.50, 0.40, 0.10
    else:  # moderate or default
        equity_pct, debt_pct, gold_pct = 0.70, 0.20, 0.10
    
    return {
        "equity": round(investment_amount * equity_pct, 2),
        "debt": round(investment_amount * debt_pct, 2),
        "gold": round(investment_amount * gold_pct, 2),
    }


def _validate_financial_consistency(
    profile: dict[str, Any],
    surplus: float,
    total_sip: float
) -> bool:
    """
    Validate that total SIP does not exceed available surplus.
    Returns True if valid, False otherwise.
    """
    return total_sip <= surplus if surplus > 0 else True


def _format_inr(amount: float) -> str:
    """
    Format amount as INR with Lakh/Crore notation.
    Returns both short (₹1L) and long (₹1,00,000) formats as needed.
    """
    if amount >= 10_000_000:
        crores = amount / 10_000_000
        return f"₹{crores:.1f}Cr"
    elif amount >= 100_000:
        lakhs = amount / 100_000
        return f"₹{lakhs:.1f}L"
    else:
        return f"₹{amount:,.0f}"


def _render_ai_response(summary: str, allocations: dict[str, float], impact: str, action_steps: list[str]) -> str:
    allocation_lines = [
        f"- {_format_inr(allocations.get('emergency_fund', 0.0))} → emergency fund",
        f"- {_format_inr(allocations.get('debt_repayment', 0.0))} → debt repayment",
        f"- {_format_inr(allocations.get('investments', 0.0))} → investments",
        f"- {_format_inr(allocations.get('discretionary', 0.0))} → personal use",
    ]
    action_lines = [f"- {item}" for item in action_steps]
    return (
        f"1. Summary: {summary}\n\n"
        "2. Allocation:\n"
        + "\n".join(allocation_lines)
        + "\n\n"
        f"3. Impact: {impact}\n\n"
        "4. Actions:\n"
        + "\n".join(action_lines)
    )


def analyze_life_event(db: Session, user: User, payload: LifeEventRequest) -> LifeEventResponse:
    profile = get_financial_profile(db, user)
    goals = list_goals(db, user, status="active")
    current_fire_plan = _current_fire_plan_or_none(db, user)

    latest_investment = (
        db.query(UserInvestment)
        .filter(UserInvestment.user_id == user.id)
        .order_by(UserInvestment.created_at.desc())
        .first()
    )
    investment_portfolio_current = float(latest_investment.total_amount) if latest_investment else 0.0
    investment_breakdown = {
        "equity": float(latest_investment.equity_amount) if latest_investment else 0.0,
        "debt": float(latest_investment.debt_amount) if latest_investment else 0.0,
        "gold": float(latest_investment.gold_amount) if latest_investment else 0.0,
    }

    profile_payload = {
        "age": int(profile.age),
        "monthly_income": float(profile.income),
        "monthly_expenses": float(profile.expenses),
        "current_savings": float(profile.savings),
        "insurance_coverage": float(profile.insurance_coverage),
        "monthly_emi": float(profile.emi),
        "risk_profile": str(profile.risk_profile),
    }
    goals_payload = _goals_for_planner(goals)

    baseline_plan = _simulate_fire(
        profile_payload=profile_payload,
        goals_payload=goals_payload,
        investment_portfolio_current=investment_portfolio_current,
        investment_breakdown=investment_breakdown,
        current_fire_plan=current_fire_plan,
    )

    has_debt = float(profile.loans) > 0.0 or float(profile.emi) > 0.0
    recommended_allocation = {
        "emergency_fund": 0.0,
        "debt_repayment": 0.0,
        "investments": 0.0,
        "discretionary": 0.0,
    }
    action_steps: list[str] = []
    impact = ""

    updated_profile = dict(profile_payload)
    updated_goals_payload = list(goals_payload)
    updated_investment_portfolio = investment_portfolio_current

    if payload.event_type in {"bonus", "inheritance"}:
        event_amount = float(payload.amount)
        outstanding_debt = max(float(profile.loans), 0.0)
        
        # Use simplified allocation for small events (< ₹50,000)
        if event_amount < 50000:
            recommended_allocation = _simplify_small_event_allocation(
                amount=event_amount,
                outstanding_debt=outstanding_debt
            )
        else:
            emergency_gap = max(float(profile.savings) * 3 - float(profile.savings), 0.0)
            recommended_allocation = _calculate_allocation(
                amount=event_amount,
                emergency_gap=emergency_gap,
                outstanding_debt=outstanding_debt
            )

        debt_payoff = min(recommended_allocation["debt_repayment"], float(profile.loans))
        updated_loans = max(float(profile.loans) - debt_payoff, 0.0)
        if float(profile.loans) > 0:
            updated_emi = float(profile.emi) * (updated_loans / float(profile.loans))
        else:
            updated_emi = float(profile.emi)

        updated_profile["current_savings"] = float(profile.savings) + recommended_allocation["emergency_fund"]
        updated_profile["monthly_emi"] = round(updated_emi, 2)
        updated_investment_portfolio += recommended_allocation["investments"]
        
        # Apply investment breakdown by risk profile
        risk_allocation = _allocate_investment_by_risk(
            recommended_allocation["investments"],
            str(profile.risk_profile)
        )
        investment_breakdown["equity"] = float(investment_breakdown.get("equity", 0.0)) + risk_allocation["equity"]
        investment_breakdown["debt"] = float(investment_breakdown.get("debt", 0.0)) + risk_allocation["debt"]
        investment_breakdown["gold"] = float(investment_breakdown.get("gold", 0.0)) + risk_allocation["gold"]

        event_label = "bonus" if payload.event_type == "bonus" else "inheritance"
        
        if event_amount < 50000:
            action_steps = []
            if recommended_allocation["debt_repayment"] > 0:
                action_steps.append(f"Repay {_format_inr(recommended_allocation['debt_repayment'])} towards outstanding debt")
            if recommended_allocation["emergency_fund"] > 0:
                action_steps.append(f"Add {_format_inr(recommended_allocation['emergency_fund'])} to emergency savings")
            action_steps.append("This small allocation is optimized for immediate debt reduction or savings")
        else:
            action_steps = [
                f"Transfer {_format_inr(recommended_allocation['emergency_fund'])} into emergency fund",
                f"Repay {_format_inr(debt_payoff)} high-cost debt",
                f"Invest {_format_inr(recommended_allocation['investments'])} using your current risk profile",
                "Keep discretionary spending capped to preserve long-term goals",
            ]
        
        impact = (
            f"Your {event_label} improves liquidity and investable assets while reducing debt pressure. "
            "FIRE and goal feasibility are recalculated with this allocation."
        )

    elif payload.event_type == "marriage":
        estimated_expense = max(500000.0, min(float(payload.amount or 1000000.0), 2000000.0))
        liquid_available = float(profile.savings)
        affordable = liquid_available >= estimated_expense
        shortfall = max(estimated_expense - liquid_available, 0.0)
        wedding_sip = round(shortfall / 24, 2) if shortfall > 0 else 0.0

        updated_profile["current_savings"] = max(liquid_available - estimated_expense, 0.0)

        action_steps = [
            f"Set marriage budget at INR {estimated_expense:,.0f}",
            "Protect emergency fund while funding marriage expenses",
            f"Start temporary savings SIP of INR {wedding_sip:,.0f}/month for 24 months" if wedding_sip > 0 else "No additional wedding SIP needed",
            "Review discretionary goals and push non-essential targets if needed",
        ]
        impact = (
            f"Marriage expense is {'affordable' if affordable else 'not fully affordable'} from current savings. "
            "Plan adjusts near-term liquidity and recalculates FIRE/goal timeline impact."
        )

    elif payload.event_type == "child":
        education_target = max(1000000.0, min(float(payload.amount or 1500000.0), 2500000.0))
        child_goal_years = 18
        expected_return = get_expected_return(str(profile.risk_profile))
        child_goal_sip = calculate_monthly_sip(
            target_amount=education_target,
            current_amount=0.0,
            expected_annual_return=expected_return,
            target_date=_add_years_safe(date.today(), child_goal_years),
        )

        updated_goals_payload.append(
            {
                "name": "Child Education",
                "amount": education_target,
                "years": child_goal_years,
            }
        )

        action_steps = [
            "Add Child Education as a dedicated long-term goal",
            f"Start SIP of INR {child_goal_sip:,.0f}/month for child education",
            "Increase insurance coverage to protect dependent goals",
            "Rebalance equity/debt annually as child goal progresses",
        ]
        impact = (
            f"A new Child Education goal (INR {education_target:,.0f}) is added with calculated SIP needs. "
            "FIRE and other goals are re-simulated with this added liability."
        )

    elif payload.event_type == "job_loss":
        monthly_outflow = float(profile.expenses) + float(profile.emi)
        liquid_corpus = float(profile.savings) + (investment_portfolio_current * 0.7)
        survivable_months = round((liquid_corpus / monthly_outflow), 1) if monthly_outflow > 0 else 0.0

        updated_profile["monthly_income"] = 0.0

        action_steps = [
            "Pause discretionary SIPs and preserve cash runway",
            "Prioritize EMI, rent, utilities, and insurance premiums",
            "Cut variable expenses by at least 20% immediately",
            "Resume goal SIPs only after stable income restart",
        ]
        impact = (
            f"With current liquidity, you can sustain about {survivable_months} months of essential outflow. "
            "The simulation halts SIP capacity and recalculates FIRE delay risk."
        )

    else:  # salary_increase
        monthly_increment = float(payload.amount)
        sip_increment = round(monthly_increment * 0.4, 2)
        sip_increment = max(sip_increment, 0.0)

        updated_profile["monthly_income"] = float(profile.income) + monthly_increment

        action_steps = [
            f"Increase monthly SIPs by about INR {sip_increment:,.0f} (40% of raise)",
            "Route most of the raise to long-term investments before lifestyle inflation",
            "Review FIRE target annually and accelerate equity allocation if risk allows",
            "Increase goal SIPs for underfunded goals",
        ]
        impact = (
            "Salary growth increases surplus and enables 30-50% SIP uplift from incremental income. "
            "FIRE timeline and goal feasibility are recalculated using new income."
        )

    updated_plan = _simulate_fire(
        profile_payload=updated_profile,
        goals_payload=updated_goals_payload,
        investment_portfolio_current=updated_investment_portfolio,
        investment_breakdown=investment_breakdown,
        current_fire_plan=current_fire_plan,
    )

    years_before = int(baseline_plan.get("years_to_retire", 0)) if baseline_plan else None
    years_after = int(updated_plan.get("years_to_retire", 0)) if updated_plan else None

    if payload.event_type == "bonus":
        summary = f"You received INR {payload.amount:,.0f} as bonus."
    elif payload.event_type == "inheritance":
        summary = f"You received INR {payload.amount:,.0f} as inheritance."
    elif payload.event_type == "marriage":
        summary = "You are planning for marriage-related expenses."
    elif payload.event_type == "child":
        summary = "You are planning for a new child and future education expenses."
    elif payload.event_type == "job_loss":
        summary = "You reported a job-loss event and need cashflow protection."
    else:
        summary = f"Your monthly salary increased by INR {payload.amount:,.0f}."

    if years_before is not None and years_after is not None:
        timeline_delta = years_before - years_after
        abs_delta = abs(timeline_delta)
        
        if abs_delta < 1:
            impact += " No significant impact on your FIRE timeline."
        elif timeline_delta > 0:
            impact += f" This can reduce your FIRE timeline by about {timeline_delta} year{'s' if timeline_delta != 1 else ''}."
        elif timeline_delta < 0:
            impact += f" This may delay your FIRE timeline by about {abs_delta} year{'s' if abs_delta != 1 else ''}."

    ai_response = _render_ai_response(
        summary=summary,
        allocations=recommended_allocation,
        impact=impact,
        action_steps=action_steps,
    )

    # Calculate before/after state for display
    total_assets_before = float(profile.savings) + investment_portfolio_current
    total_assets_after = float(updated_profile.get("current_savings", 0.0)) + updated_investment_portfolio
    debt_before = float(profile.loans)
    debt_after = max(debt_before - recommended_allocation.get("debt_repayment", 0.0), 0.0)
    
    return LifeEventResponse(
        mode="simulation",
        total_assets_before=total_assets_before,
        total_assets_after=total_assets_after,
        debt_before=debt_before,
        debt_after=debt_after,
        investments_before=investment_breakdown,
        investments_after={
            "equity": float(investment_breakdown.get("equity", 0.0)) + (_allocate_investment_by_risk(
                recommended_allocation.get("investments", 0.0),
                str(profile.risk_profile)
            )["equity"] if payload.event_type in {"bonus", "inheritance"} else 0.0),
            "debt": float(investment_breakdown.get("debt", 0.0)) + (_allocate_investment_by_risk(
                recommended_allocation.get("investments", 0.0),
                str(profile.risk_profile)
            )["debt"] if payload.event_type in {"bonus", "inheritance"} else 0.0),
            "gold": float(investment_breakdown.get("gold", 0.0)) + (_allocate_investment_by_risk(
                recommended_allocation.get("investments", 0.0),
                str(profile.risk_profile)
            )["gold"] if payload.event_type in {"bonus", "inheritance"} else 0.0),
        },
        event_analysis={
            "impact": impact,
            "recommended_allocation": recommended_allocation,
            "updated_plan": {
                "fire_years_before": years_before,
                "fire_years_after": years_after,
                "monthly_sip_fire_before": float(baseline_plan.get("monthly_sip_fire", 0.0)),
                "monthly_sip_fire_after": float(updated_plan.get("monthly_sip_fire", 0.0)),
                "goal_sip_total_before": float(baseline_plan.get("goal_sip_total", 0.0)),
                "goal_sip_total_after": float(updated_plan.get("goal_sip_total", 0.0)),
                "available_surplus_before": float(baseline_plan.get("available_surplus", 0.0)),
                "available_surplus_after": float(updated_plan.get("available_surplus", 0.0)),
            },
            "action_steps": action_steps,
            "ai_response": ai_response,
            "fire_timeline": {
                "years_before": years_before,
                "years_after": years_after,
            },
        }
    )


def apply_life_event(
    db: Session,
    user: User,
    payload: LifeEventRequest,
    analysis: LifeEventResponse
) -> LifeEventResponse:
    """
    Apply the life event changes to the user's profile and investment portfolio.
    Persists emergency fund, debt repayment, and new investment allocation.
    Returns updated LifeEventResponse with mode='applied'.
    """
    profile = get_financial_profile(db, user)
    
    # Get current investment breakdown
    latest_investment = (
        db.query(UserInvestment)
        .filter(UserInvestment.user_id == user.id)
        .order_by(UserInvestment.created_at.desc())
        .first()
    )
    current_equity = float(latest_investment.equity_amount) if latest_investment else 0.0
    current_debt = float(latest_investment.debt_amount) if latest_investment else 0.0
    current_gold = float(latest_investment.gold_amount) if latest_investment else 0.0
    
    # Update profile with changes
    new_savings = float(profile.savings) + analysis.event_analysis["recommended_allocation"].get("emergency_fund", 0.0)
    debt_reduction = min(
        analysis.event_analysis["recommended_allocation"].get("debt_repayment", 0.0),
        float(profile.loans)
    )
    new_loans = max(float(profile.loans) - debt_reduction, 0.0)
    
    # Update EMI proportionally
    if float(profile.loans) > 0:
        new_emi = float(profile.emi) * (new_loans / float(profile.loans))
    else:
        new_emi = 0.0
    
    profile.savings = new_savings
    profile.loans = new_loans
    profile.emi = new_emi
    db.add(profile)
    db.flush()
    
    # Create new investment record with updated allocation
    new_equity = current_equity + analysis.investments_after.get("equity", 0.0) - current_equity
    new_debt = current_debt + analysis.investments_after.get("debt", 0.0) - current_debt
    new_gold = current_gold + analysis.investments_after.get("gold", 0.0) - current_gold
    
    new_investment = UserInvestment(
        user_id=user.id,
        equity_amount=max(new_equity, 0.0),
        debt_amount=max(new_debt, 0.0),
        gold_amount=max(new_gold, 0.0),
        total_amount=max(new_equity + new_debt + new_gold, 0.0)
    )
    db.add(new_investment)
    db.commit()
    
    # Return response with applied mode
    return LifeEventResponse(
        mode="applied",
        total_assets_before=analysis.total_assets_before,
        total_assets_after=analysis.total_assets_after,
        debt_before=analysis.debt_before,
        debt_after=analysis.debt_after,
        investments_before=analysis.investments_before,
        investments_after=analysis.investments_after,
        event_analysis=analysis.event_analysis
    )
