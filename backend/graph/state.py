from typing import TypedDict, List, Dict, Any, Optional


class TravelState(TypedDict):
    # ── Input fields ──────────────────────────────────────────────────────────
    destination: str
    budget: int
    days: int
    interests: List[str]
    origin: str                        # departure city for flights

    # ── Real-time cost data (fetched before planning) ─────────────────────────
    real_time_costs: Dict[str, Any]    # populated by cost_check_node
    budget_sufficient: bool            # False → skip planning, return error

    # ── Populated by nodes ────────────────────────────────────────────────────
    weather: str
    trip_summary: str
    budget_breakdown: Dict[str, int]
    itinerary: List[Dict[str, Any]]

    # ── Evaluation + reflection loop ──────────────────────────────────────────
    evaluation_score: int
    evaluation_reason: str
    retry_count: int
