"""
FastAPI routes.

POST /api/plan-trip
  1. Input guardrail
  2. LangGraph workflow (cost_check → weather → crewai → evaluator)
  3. If budget insufficient → return BudgetInsufficientResponse (HTTP 200)
  4. Output guardrail
  5. Deep evaluation
  6. Return TravelPlan

Both TravelPlan and BudgetInsufficientResponse share the same endpoint so
the client always gets a structured, actionable JSON response.
"""

import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from backend.models.travel import (
    TravelRequest,
    TravelPlan,
    BudgetInsufficientResponse,
)
from backend.graph.workflow import graph
from backend.guardrails.input_guard import validate_input, GuardrailViolation
from backend.guardrails.output_guard import validate_output, OutputGuardrailViolation
from backend.services.planner_evaluation import deep_evaluate

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Budget insufficient response builder ───────────────────────────────────────

def _build_insufficient_response(
    request: TravelRequest,
    result: dict,
) -> BudgetInsufficientResponse:
    """Builds a helpful BudgetInsufficientResponse from the graph state."""

    rtc = result.get("real_time_costs", {})
    budget = request.budget
    days   = request.days
    dest   = request.destination

    flight    = rtc.get("flight_cost", 0)
    hotel     = rtc.get("hotel_total", 0)
    food      = rtc.get("_food_total", 0)
    transport = rtc.get("_transport_total", 0)
    misc      = rtc.get("_misc_total", 0)
    buffer    = rtc.get("_buffer", 0)
    total     = rtc.get("total_estimated_cost", 0)
    shortfall = rtc.get("shortfall", total - budget)

    breakdown = {
        "flight":    {"cost": flight,    "source": rtc.get("flight_source", "estimated")},
        "hotel":     {"cost": hotel,     "per_night": rtc.get("hotel_cost_per_night", 0), "nights": days},
        "food":      {"cost": food,      "per_day": rtc.get("estimated_food_per_day", 0)},
        "transport": {"cost": transport, "per_day": rtc.get("estimated_transport_per_day", 0)},
        "misc":      {"cost": misc},
        "safety_buffer": {"cost": buffer},
        "total_required": total,
    }

    # Generate smart suggestions
    suggestions = _generate_suggestions(
        budget=budget,
        total=total,
        shortfall=shortfall,
        days=days,
        dest=dest,
        flight=flight,
        hotel=hotel,
    )

    return BudgetInsufficientResponse(
        budget_sufficient=False,
        destination=dest,
        days=days,
        your_budget=budget,
        minimum_required=total,
        shortfall=shortfall,
        breakdown=breakdown,
        cheapest_flight=rtc.get("cheapest_flight_option"),
        cheapest_hotel=rtc.get("cheapest_hotel_option"),
        suggestions=suggestions,
    )


def _generate_suggestions(
    budget: int,
    total: int,
    shortfall: int,
    days: int,
    dest: str,
    flight: int,
    hotel: int,
) -> list[str]:
    """Generates specific, actionable suggestions based on the cost breakdown."""
    suggestions = []

    # How much more budget is needed
    pct_short = (shortfall / total) * 100 if total else 0

    if pct_short <= 15:
        suggestions.append(
            f"You are only ₹{shortfall:,} short ({pct_short:.0f}%). "
            f"A small top-up to ₹{total:,} would make this trip possible."
        )

    # Fewer days suggestion
    if days > 2:
        # Estimate cost for fewer days (hotel + food + transport scale with days)
        variable_per_day = (total - flight) / days if days else 0
        for fewer_days in range(days - 1, 1, -1):
            reduced_total = int(flight + variable_per_day * fewer_days)
            if reduced_total <= budget:
                suggestions.append(
                    f"Reducing to {fewer_days} days would bring the cost to "
                    f"approximately ₹{reduced_total:,}, which fits your budget."
                )
                break

    # Budget tier suggestion
    if hotel > budget * 0.35:
        suggestions.append(
            f"Hotel costs (₹{hotel:,}) are high. Choosing a budget hotel "
            f"could save ₹{int(hotel * 0.4):,}–₹{int(hotel * 0.6):,}."
        )

    # Flight suggestion
    if flight > budget * 0.40:
        suggestions.append(
            f"Flight cost (₹{flight:,}) is taking up a large share. "
            f"Consider booking 6–8 weeks in advance or travelling mid-week for lower fares."
        )

    # Nearby cheaper destination
    suggestions.append(
        f"Consider a closer destination to reduce flight costs, "
        f"or increase your budget to ₹{total:,} to cover {dest} comfortably."
    )

    # Generic increase budget
    suggestions.append(
        f"Your current budget of ₹{budget:,} covers "
        f"{int((budget / total) * 100)}% of the estimated trip cost."
    )

    return suggestions[:5]   # max 5 suggestions


# ── Route ──────────────────────────────────────────────────────────────────────

@router.post(
    "/plan-trip",
    responses={
        200: {"description": "Travel plan or budget insufficient response"},
        422: {"description": "Validation error"},
        500: {"description": "Internal server error"},
    },
)
def plan_trip(data: TravelRequest):
    """
    Generate a personalised travel plan.

    Returns either:
    - **TravelPlan** — full itinerary with budget breakdown (budget_sufficient: true)
    - **BudgetInsufficientResponse** — cost breakdown + suggestions (budget_sufficient: false)
    """

    # ── 1. Input guardrail ─────────────────────────────────────────────────────
    try:
        data = validate_input(data)
    except GuardrailViolation as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    # ── 2. Run LangGraph workflow ──────────────────────────────────────────────
    try:
        result = graph.invoke(
            {
                "destination":      data.destination,
                "budget":           data.budget,
                "days":             data.days,
                "interests":        data.interests,
                "origin":           data.origin,
                "weather":          "",
                "trip_summary":     "",
                "budget_breakdown": {},
                "itinerary":        [],
                "real_time_costs":  {},
                "budget_sufficient": True,
                "evaluation_score": 0,
                "evaluation_reason": "",
                "retry_count":      0,
            }
        )
    except Exception as exc:
        logger.error(f"[Route] Graph execution failed: {exc}")
        raise HTTPException(status_code=500, detail="Travel plan generation failed.")

    # ── 3. Budget insufficient → return structured error response ──────────────
    if not result.get("budget_sufficient", True):
        insufficient = _build_insufficient_response(data, result)
        logger.info(
            f"[Route] Budget insufficient for {data.destination}: "
            f"₹{data.budget:,} vs ₹{insufficient.minimum_required:,} required"
        )
        return JSONResponse(
            status_code=200,
            content=insufficient.model_dump(),
        )

    # ── 4. Build TravelPlan ────────────────────────────────────────────────────
    try:
        rtc = result.get("real_time_costs", {})
        plan = TravelPlan.model_validate(
            {
                "trip_summary":     result["trip_summary"],
                "budget_breakdown": result["budget_breakdown"],
                "itinerary":        result["itinerary"],
                "evaluation_score": result.get("evaluation_score"),
                "evaluation_reason": result.get("evaluation_reason"),
                "weather_condition": result.get("weather"),
                "budget_sufficient": True,
                "real_time_costs": {
                    "flight_cost":                rtc.get("flight_cost", 0),
                    "hotel_cost_per_night":        rtc.get("hotel_cost_per_night", 0),
                    "hotel_total":                 rtc.get("hotel_total", 0),
                    "estimated_food_per_day":      rtc.get("estimated_food_per_day", 0),
                    "estimated_transport_per_day": rtc.get("estimated_transport_per_day", 0),
                    "total_estimated_cost":        rtc.get("total_estimated_cost", 0),
                    "flight_source":               rtc.get("flight_source", "estimated"),
                    "hotel_source":                rtc.get("hotel_source", "estimated"),
                    "is_sufficient":               True,
                    "shortfall":                   0,
                    "cheapest_flight_option":      rtc.get("cheapest_flight_option"),
                    "cheapest_hotel_option":       rtc.get("cheapest_hotel_option"),
                } if rtc else None,
            }
        )
    except Exception as exc:
        logger.error(f"[Route] TravelPlan validation failed: {exc}")
        raise HTTPException(status_code=500, detail="Failed to build travel plan response.")

    # ── 5. Output guardrail ────────────────────────────────────────────────────
    try:
        plan = validate_output(plan, data.budget, data.days)
    except OutputGuardrailViolation as exc:
        logger.warning(f"[Route] Output guardrail: {exc}")
        plan.trip_summary += f"\n\n[Note: {exc}]"

    # ── 6. Deep evaluation (non-fatal) ─────────────────────────────────────────
    try:
        deep_evaluate(plan, data)
    except Exception as exc:
        logger.warning(f"[Route] Deep evaluation failed: {exc}")

    return plan
