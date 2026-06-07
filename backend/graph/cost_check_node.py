"""
Cost check node.

Runs BEFORE CrewAI planning. Fetches real-time flight and hotel prices,
calculates minimum trip cost, and sets budget_sufficient = False if the
budget cannot cover the trip.

When budget_sufficient is False, the workflow skips planning entirely
and the API route returns a BudgetInsufficientResponse with specific
shortfall info and actionable suggestions.
"""

import logging
from backend.graph.state import TravelState
import re

def safe_int(value):

    if value is None:
        return 0

    if isinstance(value, int):
        return value

    value = str(value)

    value = re.sub(r"[^\d]", "", value)

    return int(value) if value else 0

logger = logging.getLogger(__name__)

# ── Minimum food + transport estimates (INR per day) ──────────────────────────

FOOD_PER_DAY: dict[str, int] = {
    "goa": 1200, "mumbai": 1500, "delhi": 1000, "bangalore": 1200,
    "bengaluru": 1200, "jaipur": 800, "kochi": 900, "hyderabad": 1000,
    "tokyo": 3000, "paris": 5000, "london": 5500, "new york": 6000,
    "dubai": 4000, "singapore": 3500, "bangkok": 1500, "bali": 1200,
    "default": 1500,
}

TRANSPORT_PER_DAY: dict[str, int] = {
    "goa": 600, "mumbai": 500, "delhi": 400, "bangalore": 500,
    "bengaluru": 500, "jaipur": 400, "kochi": 400, "hyderabad": 400,
    "tokyo": 1500, "paris": 2000, "london": 2200, "new york": 2500,
    "dubai": 1500, "singapore": 1200, "bangkok": 700, "bali": 600,
    "default": 800,
}

MISC_PER_DAY: dict[str, int] = {
    "default": 500,
}

# Minimum safety buffer (10% of budget)
SAFETY_BUFFER_PCT = 0.10


def _lookup(table: dict, destination: str) -> int:
    key = destination.lower().strip()
    for city, val in table.items():
        if city in key:
            return val
    return table["default"]


def _fetch_flight_cost(state: TravelState) -> dict:
    """Fetch real-time flight cost. Returns dict with price and metadata."""
    try:
        from backend.mcp_servers.flights_server import search_flights
        result = search_flights(
            destination=state["destination"],
            budget=state["budget"],
            days=state["days"],
            origin=state.get("origin", "Delhi"),
        )
        return result
    except Exception as exc:
        logger.warning(f"[CostCheck] Flight fetch failed: {exc}")
        return {
            "cheapest_price_inr": int(state["budget"] * 0.30),
            "options": [],
            "source": "estimated (fetch failed)",
        }


def _fetch_hotel_cost(state: TravelState) -> dict:
    """Fetch real-time hotel cost. Returns dict with per-night and total."""
    try:
        from backend.mcp_servers.hotels_server import search_hotels

        # Determine budget tier from budget per day
        cost_per_day = state["budget"] / state["days"]
        if cost_per_day < 3000:
            tier = "budget"
        elif cost_per_day < 8000:
            tier = "mid"
        else:
            tier = "luxury"

        result = search_hotels(
            destination=state["destination"],
            days=state["days"],
            budget_tier=tier,
        )
        return result
    except Exception as exc:
        logger.warning(f"[CostCheck] Hotel fetch failed: {exc}")
        per_night = _lookup({"default": 3000}, state["destination"])
        return {
            "cheapest_per_night_inr": per_night,
            "total_inr": per_night * state["days"],
            "nights": state["days"],
            "source": "estimated (fetch failed)",
        }


def cost_check_node(state: TravelState) -> TravelState:
    """
    Fetches real-time flight + hotel costs and determines if the budget
    is sufficient. Sets state['budget_sufficient'] accordingly.
    """
    logger.info(f"[CostCheck] Fetching real costs for {state['destination']}, {state['days']}d, ₹{state['budget']:,}")

    destination = state["destination"]
    days        = state["days"]
    budget      = state["budget"]

    # ── Fetch real-time costs ──────────────────────────────────────────────────
    flight_data = _fetch_flight_cost(state)
    hotel_data  = _fetch_hotel_cost(state)

    logger.info(f"[DEBUG] flight_data = {flight_data}")
    logger.info(f"[DEBUG] hotel_data = {hotel_data}")
    
    flight_cost  = safe_int(flight_data.get("cheapest_price_inr", 0))
    hotel_total  = safe_int(hotel_data.get("total_inr", 0))
    hotel_nightly = safe_int(hotel_data.get("cheapest_per_night_inr", 0)) 

    food_per_day      = _lookup(FOOD_PER_DAY,      destination)
    transport_per_day = _lookup(TRANSPORT_PER_DAY, destination)
    misc_per_day      = _lookup(MISC_PER_DAY,      destination)

    food_total      = food_per_day * days
    transport_total = transport_per_day * days
    misc_total      = misc_per_day * days
    buffer          = int(budget * SAFETY_BUFFER_PCT)

    total_estimated = (
        flight_cost
        + hotel_total
        + food_total
        + transport_total
        + misc_total
        + buffer
    )

    shortfall        = max(0, total_estimated - budget)
    is_sufficient    = shortfall == 0

    logger.info(
        f"[CostCheck] Flight: ₹{flight_cost:,} | Hotel: ₹{hotel_total:,} | "
        f"Food: ₹{food_total:,} | Transport: ₹{transport_total:,} | "
        f"Total: ₹{total_estimated:,} | Budget: ₹{budget:,} | "
        f"Sufficient: {is_sufficient}"
    )

    state["real_time_costs"] = {
        "flight_cost":              flight_cost,
        "hotel_cost_per_night":     hotel_nightly,
        "hotel_total":              hotel_total,
        "estimated_food_per_day":   food_per_day,
        "estimated_transport_per_day": transport_per_day,
        "total_estimated_cost":     total_estimated,
        "flight_source":            flight_data.get("source", "estimated"),
        "hotel_source":             hotel_data.get("hotels", [{}])[0].get("source", "estimated") if hotel_data.get("hotels") else "estimated",
        "is_sufficient":            is_sufficient,
        "shortfall":                shortfall,
        "cheapest_flight_option":   flight_data.get("options", [None])[0] if flight_data.get("options") else None,
        "cheapest_hotel_option":    hotel_data.get("hotels", [None])[0] if hotel_data.get("hotels") else None,
        # Raw breakdown for suggestions
        "_food_total":       food_total,
        "_transport_total":  transport_total,
        "_misc_total":       misc_total,
        "_buffer":           buffer,
    }

    state["budget_sufficient"] = is_sufficient
    return state


def budget_insufficient_router(state: TravelState) -> str:
    """Routes to planning if budget is sufficient, else to END."""
    return "plan" if state.get("budget_sufficient", True) else "insufficient"
