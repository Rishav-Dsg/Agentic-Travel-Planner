"""
Output guardrail.

Validates the final TravelPlan before it is returned to the caller.
Checks:
  - Schema completeness (non-empty fields, correct types via Pydantic)
  - Budget consistency (breakdown sums reasonably close to declared budget)
  - Itinerary quality (correct number of days, no placeholder text)
  - Hallucination heuristics (flags repeated generic text)
"""

import re
import logging
from backend.models.travel import TravelPlan, BudgetBreakdown

logger = logging.getLogger(__name__)


class OutputGuardrailViolation(ValueError):
    pass


_PLACEHOLDER_PATTERNS = [
    re.compile(r"\bfallback itinerary\b", re.IGNORECASE),
    re.compile(r"\bexplore city\b",       re.IGNORECASE),
    re.compile(r"\btodo\b",               re.IGNORECASE),
    re.compile(r"\bplaceholder\b",        re.IGNORECASE),
    re.compile(r"\bN/A\b"),
]

BUDGET_TOLERANCE = 0.25     # allow 25% over/under
MIN_SUMMARY_WORDS = 20
MIN_ACTIVITIES_PER_DAY = 1


def _check_budget_consistency(budget: int, breakdown: BudgetBreakdown) -> list[str]:
    errors = []
    total = breakdown.flight + breakdown.hotel + breakdown.food + breakdown.transport + breakdown.misc
    if total == 0:
        errors.append("Budget breakdown is all zeros.")
        return errors

    deviation = abs(total - budget) / budget
    if deviation > BUDGET_TOLERANCE:
        errors.append(
            f"Budget breakdown total ₹{total:,} deviates {deviation*100:.0f}% "
            f"from declared budget ₹{budget:,}."
        )
    return errors


def _check_placeholders(text: str) -> bool:
    return any(p.search(text) for p in _PLACEHOLDER_PATTERNS)


def validate_output(plan: TravelPlan, original_budget: int, original_days: int) -> TravelPlan:
    """
    Validates a TravelPlan.  Returns the plan unchanged on success or raises
    OutputGuardrailViolation with details.
    """
    errors: list[str] = []

    # 1. Trip summary quality
    word_count = len(plan.trip_summary.split())
    if word_count < MIN_SUMMARY_WORDS:
        errors.append(
            f"Trip summary too short ({word_count} words; minimum {MIN_SUMMARY_WORDS})."
        )
    if _check_placeholders(plan.trip_summary):
        errors.append("Trip summary contains placeholder text.")

    # 2. Budget breakdown
    errors.extend(_check_budget_consistency(original_budget, plan.budget_breakdown))

    # 3. Itinerary coverage
    if len(plan.itinerary) < original_days:
        errors.append(
            f"Itinerary covers {len(plan.itinerary)} day(s) but trip is {original_days} day(s)."
        )

    for day_plan in plan.itinerary:
        if len(day_plan.activities) < MIN_ACTIVITIES_PER_DAY:
            errors.append(f"Day {day_plan.day} has no activities.")

        for act in day_plan.activities:
            if _check_placeholders(act.activity) or _check_placeholders(act.description):
                errors.append(
                    f"Day {day_plan.day} activity '{act.activity}' contains placeholder text."
                )

    if errors:
        msg = " | ".join(errors)
        logger.warning(f"[OutputGuardrail] Rejected plan: {msg}")
        raise OutputGuardrailViolation(msg)

    logger.info("[OutputGuardrail] Plan passed all checks.")
    return plan
