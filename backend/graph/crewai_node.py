"""
CrewAI crew node  (crewai >= 1.0.0)

Replaces the old planner_node + budget_node + itinerary nodes with a
proper multi-agent crew.

Agents:
  - PlannerAgent    — writes trip summary, uses weather MCP tool
  - BudgetAgent     — allocates budget, uses flights + hotels MCP tools
  - ItineraryAgent  — builds day-by-day plan, uses all MCP tools

Process: hierarchical (manager_llm coordinates agents).
"""

import json
import logging
import os
import re
from typing import Any

from crewai import Agent, Crew, Process, Task
from crewai.llm import LLM

from backend.graph.state import TravelState
from backend.mcp_servers.client import get_weather_tools, get_flight_tools, get_hotel_tools, get_places_tools

logger = logging.getLogger(__name__)

# ── LLM for CrewAI (v1 API: LLM(model=..., base_url=..., temperature=...)) ────

_MODEL = os.getenv("OLLAMA_MODEL",    "qwen2.5")
_BASE  = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

crewai_llm = LLM(
    model=f"ollama/{_MODEL}",
    base_url=_BASE,
    temperature=0.4,
)


# ── Tool loader ────────────────────────────────────────────────────────────────

def _safe_load(loader_fn, label: str) -> list:
    try:
        tools = loader_fn()
        logger.info(f"[CrewAI] Loaded {len(tools)} {label} tool(s)")
        return tools
    except Exception as exc:
        logger.warning(f"[CrewAI] Could not load {label} tools: {exc}")
        return []


# ── JSON extractor ─────────────────────────────────────────────────────────────

def _extract_json(text: str) -> Any:
    """Extract the first JSON object or array from a text blob."""
    match = re.search(r"\{[\s\S]*\}|\[[\s\S]*\]", text)
    if match:
        return json.loads(match.group())
    raise ValueError(f"No JSON found in: {text[:200]}")


# ── Crew builder ───────────────────────────────────────────────────────────────

def _build_crew(state: TravelState) -> Crew:
    weather_tools = _safe_load(get_weather_tools, "weather")
    flight_tools  = _safe_load(get_flight_tools,  "flights")
    hotel_tools   = _safe_load(get_hotel_tools,   "hotels")
    places_tools  = _safe_load(get_places_tools,  "places")

    destination = state["destination"]
    budget      = state["budget"]
    days        = state["days"]
    interests   = ", ".join(state["interests"])

    # ── Agents ────────────────────────────────────────────────────────────────

    planner_agent = Agent(
    role="Senior Travel Planner",
    goal=(
        "Create an engaging, accurate trip summary that captures the spirit "
        "of the destination and matches the traveller's interests."
    ),
    backstory=(
        "You are a seasoned travel planner with 15 years of experience crafting "
        "personalised itineraries. You always check real-time weather conditions "
        "before writing your summaries."
    ),
    tools=[],          # ← empty
    llm=crewai_llm,
    verbose=True,
    allow_delegation=False,
)

    budget_agent = Agent(
        role="Travel Budget Analyst",
        goal=(
            "Allocate the total travel budget across flight, hotel, food, "
            "transport, and miscellaneous categories using real price data."
        ),
        backstory=(
            "You specialise in making every rupee count. You use live flight and "
            "hotel pricing to produce accurate budget splits."
        ),
        tools=[],          # ← empty
        llm=crewai_llm,
        verbose=True,
        allow_delegation=False,
    )

    itinerary_agent = Agent(
        role="Itinerary Specialist",
        goal=(
            "Build a detailed, day-by-day itinerary using REAL place names from "
            "Google Maps. Every activity must be a real, visitable location."
        ),
        backstory=(
            "You have personally visited over 80 countries and know how to craft "
            "itineraries that feel local, not touristy."
        ),
        tools=[],          # ← empty
        llm=crewai_llm,
        verbose=True,
        allow_delegation=False,
    )

    # ── Tasks ─────────────────────────────────────────────────────────────────

    summary_task = Task(
        description=(
            f"Write a short (3-5 sentence) trip summary for:\n"
            f"  Destination : {destination}\n"
            f"  Duration    : {days} days\n"
            f"  Interests   : {interests}\n\n"
            f"Use the get_weather tool to check current conditions and mention "
            f"them briefly. Return ONLY the summary text — no JSON, no headings."
        ),
        expected_output="A plain-text trip summary of 3-5 sentences.",
        agent=planner_agent,
    )

    # Use real-time costs already fetched by cost_check_node
    rtc          = state.get("real_time_costs", {})
    flight_cost  = rtc.get("flight_cost",          int(budget * 0.30))
    hotel_cost   = rtc.get("hotel_total",           int(budget * 0.25))
    food_cost    = rtc.get("_food_total",           int(budget * 0.15))
    transport    = rtc.get("_transport_total",      int(budget * 0.10))
    misc_cost    = budget - flight_cost - hotel_cost - food_cost - transport
    misc_cost    = max(0, misc_cost)

    budget_task = Task(
        description=(
            f"Allocate this travel budget using the REAL costs already fetched:\n"
            f"  Total budget : Rs.{budget:,}\n"
            f"  Destination  : {destination}\n"
            f"  Days         : {days}\n\n"
            f"Real-time costs already confirmed:\n"
            f"  Flight (round-trip) : Rs.{flight_cost:,}  [{rtc.get('flight_source', 'estimated')}]\n"
            f"  Hotel ({days} nights): Rs.{hotel_cost:,}  [Rs.{rtc.get('hotel_cost_per_night', 0):,}/night]\n"
            f"  Food (estimated)    : Rs.{food_cost:,}  [Rs.{rtc.get('estimated_food_per_day', 0):,}/day]\n"
            f"  Transport           : Rs.{transport:,}\n"
            f"  Misc/leftover       : Rs.{misc_cost:,}\n\n"
            f"Use these EXACT numbers. Return ONLY valid JSON:\n"
            f'{{"flight": {flight_cost}, "hotel": {hotel_cost}, "food": {food_cost}, "transport": {transport}, "misc": {misc_cost}}}'
        ),
        expected_output="JSON object with keys: flight, hotel, food, transport, misc using the real costs provided.",
        agent=budget_agent,
    )

    itinerary_task = Task(
        description=(
            f"Create a {days}-day itinerary for:\n"
            f"  Destination : {destination}\n"
            f"  Interests   : {interests}\n\n"
            f"Steps you MUST follow:\n"
            f"1. Call get_weather(destination='{destination}') to check conditions.\n"
            f"2. For each interest, call search_landmarks or search_activities to find REAL places:\n"
            f"   - search_landmarks(city='{destination}', category='<relevant category>')\n"
            f"   - search_restaurants(city='{destination}', cuisine='<relevant cuisine>')\n"
            f"   - search_activities(city='{destination}', interest='<interest>')\n"
            f"3. For each day, call plan_day_route to order places efficiently:\n"
            f"   - plan_day_route(city='{destination}', places=['Place A', 'Place B', 'Place C'])\n"
            f"4. Optionally call get_place_details for key places to enrich descriptions.\n"
            f"5. Return ONLY valid JSON:\n"
            f'{{"itinerary": [{{"day": 1, "location": "{destination}", "activities": '
            f'[{{"activity": "Real place name from Google Maps", "description": "What to do, opening hours if known, travel tips"}}]}}]}}\n'
            f"Rules:\n"
            f"- Generate exactly {days} day entries\n"
            f"- Each day must have exactly 3 activities\n"
            f"- Use REAL place names returned by the tools — never generic text\n"
            f"- Spread different types across the days (landmarks, food, activities)\n"
            f"- If rainy, prefer indoor places (museums, cafes, shopping malls)"
        ),
        expected_output=(
            f'JSON with an "itinerary" array of exactly {days} entries. '
            f'Each entry has real Google Maps place names as activities.'
        ),
        agent=itinerary_agent,
        context=[summary_task],
    )

    return Crew(
        agents=[planner_agent, budget_agent, itinerary_agent],
        tasks=[summary_task, budget_task, itinerary_task],
        process=Process.hierarchical,
        manager_llm=crewai_llm,
        verbose=True,
    )


# ── Fallbacks ──────────────────────────────────────────────────────────────────

def _fallback_budget(budget: int, state: TravelState | None = None) -> dict:
    """Uses real-time costs from state if available, else percentage split."""
    if state:
        rtc = state.get("real_time_costs", {})
        if rtc:
            flight    = rtc.get("flight_cost",     int(budget * 0.30))
            hotel     = rtc.get("hotel_total",      int(budget * 0.25))
            food      = rtc.get("_food_total",      int(budget * 0.15))
            transport = rtc.get("_transport_total", int(budget * 0.10))
            misc      = max(0, budget - flight - hotel - food - transport)
            return {"flight": flight, "hotel": hotel, "food": food, "transport": transport, "misc": misc}
    return {
        "flight":    int(budget * 0.30),
        "hotel":     int(budget * 0.25),
        "food":      int(budget * 0.15),
        "transport": int(budget * 0.10),
        "misc":      int(budget * 0.20),
    }


def _fallback_itinerary(state: TravelState) -> list:
    """
    Generates a real itinerary using Google Maps Places + direct LLM call.
    Only falls back to generic text if both fail.
    """
    from backend.mcp_servers.weather_server import _get_places
    from backend.graph.llm import itinerary_llm

    # Fetch real places from Google Maps for each interest
    real_places_context = ""
    if os.getenv("GOOGLE_MAPS_API_KEY"):
        all_places = []
        for interest in state["interests"][:4]:
            try:
                places = _get_places(state["destination"], interest, max_results=4)
                if places:
                    all_places.extend([p["name"] for p in places])
            except Exception:
                pass
        if all_places:
            real_places_context = (
                f"\nUse these REAL places from Google Maps in your itinerary:\n"
                f"{', '.join(all_places[:15])}\n"
            )

    weather = state.get("weather", "Sunny")
    indoor_note = (
        "Focus on indoor activities since it is rainy."
        if weather == "Rainy"
        else "Include outdoor activities."
    )

    prompt = f"""
Return ONLY valid JSON with no extra text.

Create a {state['days']}-day itinerary for {state['destination']}.
Interests: {', '.join(state['interests'])}.
Weather: {weather}. {indoor_note}
{real_places_context}
Schema:
{{
  "itinerary": [
    {{
      "day": 1,
      "location": "{state['destination']}",
      "activities": [
        {{"activity": "Real place or activity name", "description": "Detailed description of what to do and why"}}
      ]
    }}
  ]
}}

Generate exactly {state['days']} day entries. Each day must have exactly 3 activities.
Use real, specific place names — not generic descriptions like 'Explore the city'.
"""

    try:
        result = itinerary_llm.invoke(prompt)
        if isinstance(result, dict):
            itinerary = result.get("itinerary", [])
        else:
            itinerary = getattr(result, "itinerary", [])
        parsed = [
            day.model_dump() if hasattr(day, "model_dump") else day
            for day in itinerary
        ]
        if parsed:
            return parsed
    except Exception as exc:
        logger.error(f"[Fallback] Direct itinerary generation failed: {exc}")

    # Last resort generic fallback
    return [
        {
            "day": d + 1,
            "location": state["destination"],
            "activities": [
                {
                    "activity":    f"Explore {state['destination']}",
                    "description": f"Day {d+1}: discover {', '.join(state['interests'][:2])} in {state['destination']}.",
                }
            ],
        }
        for d in range(state["days"])
    ]


def _generate_summary_directly(state: TravelState) -> str:
    """Generate trip summary via direct LLM call when crew output is unusable."""
    from backend.graph.llm import llm
    prompt = (
        f"Write a 4-5 sentence trip summary for a {state['days']}-day trip to "
        f"{state['destination']} with a budget of Rs.{state['budget']:,}. "
        f"The traveller is interested in: {', '.join(state['interests'])}. "
        f"Current weather: {state.get('weather', 'pleasant')}. "
        f"Make it engaging and specific to the destination."
    )
    try:
        response = llm.invoke(prompt)
        return str(response.content).strip()
    except Exception as exc:
        logger.error(f"[CrewAI] Direct summary generation failed: {exc}")
        return (
            f"Discover the magic of {state['destination']} on this carefully crafted "
            f"{state['days']}-day journey. With a budget of Rs.{state['budget']:,}, "
            f"you will explore {', '.join(state['interests'][:3])} and experience "
            f"the very best this destination has to offer. The weather is currently "
            f"{state.get('weather', 'pleasant')}, perfect for your adventures ahead."
        )



def _normalize_day(entry: dict) -> dict:
    """Normalize 'day' field — LLM sometimes returns 'Day 1' instead of 1."""
    day_val = entry.get("day", 1)
    if isinstance(day_val, str):
        nums = re.findall(r"\d+", day_val)
        day_val = int(nums[0]) if nums else 1
    entry["day"] = int(day_val)
    return entry


# ── LangGraph node ─────────────────────────────────────────────────────────────

def crewai_node(state: TravelState) -> TravelState:
    """
    LangGraph node that runs the CrewAI crew and writes results into TravelState.
    Falls back to direct LLM calls if crew output is empty or unparseable.
    """
    logger.info(f"[CrewAI] Starting crew for {state['destination']}")

    crew = _build_crew(state)

    try:
        result = crew.kickoff(
            inputs={
                "destination": state["destination"],
                "budget":      state["budget"],
                "days":        state["days"],
                "interests":   ", ".join(state["interests"]),
            }
        )

        task_outputs = getattr(result, "tasks_output", []) or []

        # Log raw outputs to help debug
        for i, t in enumerate(task_outputs):
            raw = str(getattr(t, "raw", "") or "")
            logger.info(f"[CrewAI] Task {i} raw ({len(raw)} chars): {raw[:200]}")

        def _raw(index: int) -> str:
            if index < len(task_outputs):
                return str(getattr(task_outputs[index], "raw", "") or "").strip()
            return ""

        # ── Summary (task 0) ──────────────────────────────────────────────────
        summary = _raw(0) or str(getattr(result, "raw", "") or "").strip()
        if not summary or len(summary.split()) < 20:
            logger.warning("[CrewAI] Summary too short — generating directly")
            summary = _generate_summary_directly(state)
        state["trip_summary"] = summary

        # ── Budget (task 1) ───────────────────────────────────────────────────
        budget_raw = _raw(1)
        if budget_raw:
            try:
                budget_data = _extract_json(budget_raw)
                state["budget_breakdown"] = {
                    "flight":    int(budget_data.get("flight",    0)),
                    "hotel":     int(budget_data.get("hotel",     0)),
                    "food":      int(budget_data.get("food",      0)),
                    "transport": int(budget_data.get("transport", 0)),
                    "misc":      int(budget_data.get("misc",      0)),
                }
            except Exception as exc:
                logger.warning(f"[CrewAI] Budget parse failed ({exc}); using fallback")
                state["budget_breakdown"] = _fallback_budget(state["budget"], state)
        else:
            state["budget_breakdown"] = _fallback_budget(state["budget"], state)

        # ── Itinerary (task 2) ────────────────────────────────────────────────
        itin_raw = _raw(2)
        if itin_raw:
            try:
                itin_data = _extract_json(itin_raw)
                itinerary  = itin_data.get("itinerary", [])
                # Reject if it has placeholder text
                first_act  = ""
                if itinerary:
                    first_act = itinerary[0].get("activities", [{}])[0].get("activity", "")
                if itinerary and "explore the city" not in first_act.lower():
                    state["itinerary"] = [_normalize_day(d) for d in itinerary]
                else:
                    raise ValueError("Placeholder itinerary detected")
            except Exception as exc:
                logger.warning(f"[CrewAI] Itinerary parse failed ({exc}); generating directly")
                state["itinerary"] = _fallback_itinerary(state)
        else:
            logger.warning("[CrewAI] No itinerary from crew; generating directly")
            state["itinerary"] = _fallback_itinerary(state)

    except Exception as exc:
        logger.error(f"[CrewAI] Crew execution failed: {exc}")
        state["trip_summary"]     = _generate_summary_directly(state)
        state["budget_breakdown"] = _fallback_budget(state["budget"], state)
        state["itinerary"]        = _fallback_itinerary(state)

    return state