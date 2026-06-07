"""
Shared LLM instances.

All LangGraph nodes and CrewAI agents import from here so there is a
single configuration point for the local Ollama model.
"""

import os
from langchain_ollama import ChatOllama
from backend.models.travel import ItineraryOutput
from backend.models.evaluation import EvaluationResult

_MODEL  = os.getenv("OLLAMA_MODEL",    "qwen2.5")
_BASE   = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# General-purpose LLM (plain text output)
llm = ChatOllama(
    model=_MODEL,
    base_url=_BASE,
    temperature=0.4,
    num_ctx=8192,
)

# Structured output — itinerary JSON
itinerary_llm = llm.with_structured_output(
    ItineraryOutput,
    method="json_mode",
)

# Structured output — evaluation score + reason
evaluation_llm = llm.with_structured_output(
    EvaluationResult,
    method="json_mode",
)
