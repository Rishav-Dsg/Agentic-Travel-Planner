"""
Input guardrail.

Validates and sanitises the raw TravelRequest before it enters the
LangGraph workflow. Two layers:

1. Pydantic layer   — already enforced by FastAPI, but re-run here for
                      defence-in-depth and to produce richer error messages.
2. Semantic layer   — checks for nonsensical values (budget too low for days,
                      suspicious strings, PII-like content in the destination).

Raises GuardrailViolation on failure so the API can return HTTP 422.
"""

import re
import logging
from backend.models.travel import TravelRequest

logger = logging.getLogger(__name__)

# ── Custom exception ───────────────────────────────────────────────────────────

class GuardrailViolation(ValueError):
    pass


# ── Patterns to reject ────────────────────────────────────────────────────────

_PII_PATTERNS = [
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),  # email
    re.compile(r"\b\d{10}\b"),                                              # phone
    re.compile(r"\b\d{12}\b"),                                              # Aadhaar-like
]

_INJECTION_PATTERNS = [
    re.compile(r"(ignore previous|disregard all|you are now|act as)", re.IGNORECASE),
    re.compile(r"(<script|javascript:|DROP TABLE)", re.IGNORECASE),
]

MIN_BUDGET_PER_DAY = 500   # INR — below this a meaningful trip is impossible
MAX_INTERESTS      = 20


# ── Main validator ─────────────────────────────────────────────────────────────

def validate_input(data: TravelRequest) -> TravelRequest:
    """
    Validates a TravelRequest.  Returns the (possibly normalised) request or
    raises GuardrailViolation with a human-readable message.
    """
    errors: list[str] = []

    # 1. Budget vs duration sanity
    cost_per_day = data.budget / data.days
    if cost_per_day < MIN_BUDGET_PER_DAY:
        errors.append(
            f"Budget ₹{data.budget:,} is too low for {data.days} days "
            f"(minimum ₹{MIN_BUDGET_PER_DAY}/day required)."
        )

    # 2. Destination checks
    dest = data.destination.strip()
    for pattern in _PII_PATTERNS:
        if pattern.search(dest):
            errors.append("Destination field contains PII-like content.")
            break

    for pattern in _INJECTION_PATTERNS:
        if pattern.search(dest):
            errors.append("Destination field contains potentially malicious content.")
            break

    if len(dest) < 2:
        errors.append("Destination must be at least 2 characters.")

    # 3. Interests
    if len(data.interests) > MAX_INTERESTS:
        errors.append(f"Too many interests ({len(data.interests)}); maximum is {MAX_INTERESTS}.")

    cleaned_interests = [i.strip() for i in data.interests if i.strip()]
    if not cleaned_interests:
        errors.append("At least one non-empty interest is required.")

    # 4. Raise or return
    if errors:
        msg = " | ".join(errors)
        logger.warning(f"[InputGuardrail] Rejected request: {msg}")
        raise GuardrailViolation(msg)

    logger.info(f"[InputGuardrail] Passed: {dest}, {data.days}d, ₹{data.budget:,}")

    # Return normalised copy
    return TravelRequest(
        destination=dest,
        budget=data.budget,
        days=data.days,
        interests=cleaned_interests,
    )
