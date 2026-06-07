
"""
LangGraph node functions.

The heavyweight planning work now lives in crewai_node.py.  These nodes
handle:
  - weather_node    — fetches weather via MCP (or direct call as fallback)
  - evaluator_node  — scores the generated itinerary
  - reflection_node — appends improvement hints before a retry
  - replan_node     — appends budget warning for low-budget trips
  - *_router        — conditional edge functions
"""

import logging
from backend.graph.state import TravelState
from backend.graph.llm import llm, evaluation_llm
from typing import cast
from backend.models.evaluation import EvaluationResult

logger = logging.getLogger(__name__)

MAX_RETRIES = 2   # reflection loop guard


# ── Weather ────────────────────────────────────────────────────────────────────

def weather_node(state: TravelState) -> TravelState:
    """Fetches weather using the MCP weather server (falls back to direct call)."""
    destination = state["destination"]

    try:
        from backend.mcp_servers.client import get_weather_tools
        tools = get_weather_tools()
        if tools:
            weather_tool = next((t for t in tools if t.name == "get_weather"), None)
            if weather_tool:
                result = weather_tool.invoke({"destination": destination})
                state["weather"] = str(result).strip()
                logger.info(f"[WeatherNode] {destination} → {state['weather']} (via MCP)")
                return state
    except Exception as exc:
        logger.warning(f"[WeatherNode] MCP call failed ({exc}); using direct API")

    # Direct fallback
    from backend.tools.weather import get_weather as _get_weather
    state["weather"] = _get_weather(destination)
    logger.info(f"[WeatherNode] {destination} → {state['weather']} (direct)")
    return state


# ── Routing helpers ────────────────────────────────────────────────────────────

def weather_router(state: TravelState) -> str:
    return "indoor" if state["weather"] == "Rainy" else "outdoor"


def budget_router(state: TravelState) -> str:
    cost_per_day = state["budget"] / state["days"]
    return "replan" if cost_per_day < 5000 else "evaluate"


def evaluation_router(state: TravelState) -> str:
    if state.get("retry_count", 0) >= MAX_RETRIES:
        logger.warning("[EvalRouter] Max retries reached; approving anyway.")
        return "approved"
    return "approved" if state.get("evaluation_score", 0) >= 7 else "retry"


# ── Replan (low budget) ────────────────────────────────────────────────────────

def replan_node(state: TravelState) -> TravelState:
    state["trip_summary"] = (
        state.get("trip_summary", "")
        + "\n\n⚠️  Budget is limited — budget-friendly options prioritised."
    )
    return state


# ── Evaluator ─────────────────────────────────────────────────────────────────

def evaluator_node(state: TravelState) -> TravelState:
    prompt = f"""
Evaluate this travel itinerary on a scale of 1–10.

User interests: {", ".join(state["interests"])}
Weather: {state.get("weather", "unknown")}
Itinerary:
{state["itinerary"]}

Scoring criteria:
- Relevance to interests (3 pts)
- Completeness — one entry per day (2 pts)
- Activity variety (2 pts)
- Weather appropriateness (2 pts)
- Quality of descriptions (1 pt)

Return ONLY valid JSON: {{"score": <int 1-10>, "reason": "<short explanation>"}}
"""

    try:
        result = cast(
            EvaluationResult,
            evaluation_llm.invoke(prompt)
        )

        state["evaluation_score"] = result.score
        state["evaluation_reason"] = result.reason

        logger.info(
            f"[Evaluator] Score: {result.score} — {result.reason}"
        )

    except Exception as exc:
        logger.error(f"[Evaluator] Failed: {exc}")

        state["evaluation_score"] = 5
        state["evaluation_reason"] = (
            "Evaluation failed; defaulting to 5."
        )

    return state


# ── Reflection ────────────────────────────────────────────────────────────────

def reflection_node(state: TravelState) -> TravelState:
    """Appends improvement guidance so the next CrewAI run does better."""
    score  = state.get("evaluation_score", 0)
    reason = state.get("evaluation_reason", "")

    guidance = (
        f"\n\n[Reflection — retry {state.get('retry_count', 0) + 1}] "
        f"Previous score: {score}/10. "
        f"Issues: {reason}. "
        f"Please improve activity variety, ensure every day is covered, "
        f"and align activities more closely with interests: {', '.join(state['interests'])}."
    )

    state["trip_summary"]  = state.get("trip_summary", "") + guidance
    state["retry_count"]   = state.get("retry_count", 0) + 1
    logger.info(f"[Reflection] Retry #{state['retry_count']} queued.")
    return state
