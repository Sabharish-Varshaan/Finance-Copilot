from __future__ import annotations

import math
from typing import Any


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def enforce_goal_sip_constraints(*, calculated_sip: float, max_allowed: float, existing_sip: float) -> dict[str, Any]:
    sip = max(_safe_float(calculated_sip), 0.0)
    allowed = max(_safe_float(max_allowed), 0.0)
    existing = max(_safe_float(existing_sip), 0.0)

    def _round_up_2(value: float) -> float:
        return math.ceil(value * 100) / 100

    if sip <= allowed:
        final_sip = _round_up_2(sip)
        print(
            {
                "calculated_sip": round(sip, 2),
                "max_allowed": round(allowed, 2),
                "existing_sip": round(existing, 2),
                "final_sip": final_sip,
            }
        )
        return {
            "final_sip": final_sip,
            "adjusted": False,
            "reason": "Within safe investment limit",
        }

    final_sip = _round_up_2(allowed)
    print(
        {
            "calculated_sip": round(sip, 2),
            "max_allowed": round(allowed, 2),
            "existing_sip": round(existing, 2),
            "final_sip": final_sip,
        }
    )
    return {
        "final_sip": final_sip,
        "adjusted": True,
        "reason": "Adjusted to maintain financial safety",
    }
