"""
LangGraph workflow (upgraded).

Graph topology:

  START
    └─► cost_check ──┬─(insufficient)─► END   (budget too low)
                     └─(plan)─► weather
                                  └─► crewai
                                        └─► evaluator ──┬─(approved)─► budget_node ──► END
                                                        └─(retry)─► reflection ──► crewai

The cost_check node fetches REAL flight + hotel prices before any planning.
If the budget cannot cover the trip, the workflow ends immediately and the
API route returns a BudgetInsufficientResponse instead of a TravelPlan.
"""

from langgraph.graph import StateGraph, START, END

from backend.graph.state import TravelState
from backend.graph.cost_check_node import cost_check_node, budget_insufficient_router
from backend.graph.nodes import (
    weather_node,
    replan_node,
    evaluator_node,
    evaluation_router,
    reflection_node,
    budget_router,
)
from backend.graph.crewai_node import crewai_node

# ── Build graph ────────────────────────────────────────────────────────────────

builder = StateGraph(TravelState)

builder.add_node("cost_check",  cost_check_node)
builder.add_node("weather",     weather_node)
builder.add_node("crewai",      crewai_node)
builder.add_node("evaluator",   evaluator_node)
builder.add_node("reflection",  reflection_node)
builder.add_node("budget_node", replan_node)

# ── Edges ──────────────────────────────────────────────────────────────────────

builder.add_edge(START, "cost_check")

# Budget gate — insufficient → end immediately, sufficient → proceed
builder.add_conditional_edges(
    "cost_check",
    budget_insufficient_router,
    {
        "plan":         "weather",
        "insufficient": END,
    },
)

builder.add_edge("weather", "crewai")
builder.add_edge("crewai",  "evaluator")

builder.add_conditional_edges(
    "evaluator",
    evaluation_router,
    {
        "approved": "budget_node",
        "retry":    "reflection",
    },
)

builder.add_edge("reflection", "crewai")

builder.add_conditional_edges(
    "budget_node",
    budget_router,
    {
        "evaluate": END,
        "replan":   END,
    },
)

graph = builder.compile()


# ── CLI smoke-test ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import pprint

    initial_state: TravelState = {
        "destination":      "Goa",
        "budget":           25000,
        "days":             3,
        "interests":        ["beach", "seafood", "nightlife"],
        "origin":           "Delhi",
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

    result = graph.invoke(initial_state)
    pprint.pprint(result)
