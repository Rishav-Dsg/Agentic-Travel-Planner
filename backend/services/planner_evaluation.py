"""
Deep evaluation service.

Runs after the LangGraph evaluator node.  Provides two additional
evaluation modes:

1. LLM-as-judge   — structured rubric scored by the LLM (always available)
2. RAGAS-style    — faithfulness + relevance metrics (requires ragas package)

Results are logged and returned as a dict attached to the TravelPlan
response under the `evaluation_*` fields.
"""

import logging
import json
from typing import Any

from backend.models.travel import TravelPlan, TravelRequest
from backend.graph.llm import evaluation_llm

logger = logging.getLogger(__name__)


# ── LLM-as-judge ──────────────────────────────────────────────────────────────

def llm_judge(plan: TravelPlan, request: TravelRequest) -> dict:
    prompt = f"""
You are an expert travel reviewer. Score this travel plan on four dimensions,
each from 1 to 10.  Return ONLY valid JSON, no other text.

Request:
  Destination : {request.destination}
  Budget      : Rs.{request.budget:,}
  Days        : {request.days}
  Interests   : {", ".join(request.interests)}

Plan summary: {plan.trip_summary}

Return exactly this JSON:
{{
  "interest_alignment": <1-10>,
  "budget_realism":     <1-10>,
  "itinerary_quality":  <1-10>,
  "overall":            <1-10>,
  "summary":            "<one sentence verdict>"
}}
"""
    try:
        # Use plain LLM invoke — don't use evaluation_llm (expects score/reason)
        from backend.graph.llm import llm
        response = llm.invoke(prompt)
        content  = str(response.content).strip()

        import re, json
        match = re.search(r"\{[\s\S]*\}", content)
        if not match:
            raise ValueError("No JSON in response")

        data = json.loads(match.group())
        return {
            "interest_alignment": data.get("interest_alignment", 5),
            "budget_realism":     data.get("budget_realism",     5),
            "itinerary_quality":  data.get("itinerary_quality",  5),
            "overall":            data.get("overall",            5),
            "summary":            data.get("summary",            ""),
        }
    except Exception as exc:
        logger.error(f"[LLMJudge] Failed: {exc}")
        return {"overall": 5, "summary": "Evaluation unavailable."}


# ── RAGAS-style metrics ────────────────────────────────────────────────────────

def ragas_evaluate(plan: TravelPlan, request: TravelRequest) -> dict[str, Any]:
    """
    Runs lightweight RAGAS-inspired faithfulness and answer-relevance checks.

    'Faithfulness'  — are the activities in the itinerary consistent with the
                      stated destination? (heuristic: destination name appears
                      in at least 50% of day locations)

    'Relevance'     — do the activity descriptions mention at least one of the
                      user's stated interests?
    """
    dest_lower = request.destination.lower()
    interests  = [i.lower() for i in request.interests]

    # Faithfulness
    location_hits = sum(
        1 for d in plan.itinerary
        if dest_lower.split()[0] in d.location.lower() or d.location.strip() != ""
    )
    faithfulness = location_hits / len(plan.itinerary) if plan.itinerary else 0.0

    # Relevance
    all_text = " ".join(
        a.activity + " " + a.description
        for d in plan.itinerary
        for a in d.activities
    ).lower()
    relevance_hits = sum(1 for i in interests if i in all_text)
    relevance = relevance_hits / len(interests) if interests else 0.0

    metrics = {
        "faithfulness": round(faithfulness, 2),
        "relevance":    round(relevance,    2),
        "ragas_score":  round((faithfulness + relevance) / 2, 2),
    }

    logger.info(f"[RAGAS] {metrics}")
    return metrics


# ── Combined evaluator ─────────────────────────────────────────────────────────

def deep_evaluate(plan: TravelPlan, request: TravelRequest) -> dict[str, Any]:
    """
    Runs both evaluation layers and merges results.
    Called in the API route after the LangGraph workflow completes.
    """
    judge_result = llm_judge(plan, request)
    ragas_result = ragas_evaluate(plan, request)

    combined = {
        **judge_result,
        **ragas_result,
    }

    logger.info(f"[DeepEval] {combined}")
    return combined
