"""
MCP server: hotels

Returns real hotel prices using SerpAPI (Google Hotels scraper).
Falls back to estimate table when SERPAPI_KEY is not set.

Sign up free at https://serpapi.com — 100 searches/month, no credit card.
"""

import os
import json
import asyncio
import requests
import re
from datetime import datetime, timedelta
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from dotenv import load_dotenv
load_dotenv()

def normalize_price(value):
    if isinstance(value, int):
        return value
    if value is None:
        return 0

    value = str(value)
    value = re.sub(r"[^\d]", "", value)
    return int(value) if value else 0

server = Server("hotels-server")

TOOLS = [
    Tool(
        name="search_hotels",
        description=(
            "Returns real hotel prices and options for a destination. "
            "Prices are in INR per night. Uses Google Hotels data via SerpAPI."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "destination":   {"type": "string", "description": "City name"},
                "days":          {"type": "integer", "description": "Number of nights"},
                "budget_tier":   {
                    "type": "string",
                    "enum": ["budget", "mid", "luxury"],
                    "description": "Price range preference"
                },
            },
            "required": ["destination", "days"],
        },
    ),
]

# ── Fallback rates (INR per night) ─────────────────────────────────────────────

FALLBACK_RATES: dict[str, dict[str, int]] = {
    "goa":       {"budget": 1500, "mid": 4000, "luxury": 12000},
    "mumbai":    {"budget": 2000, "mid": 5000, "luxury": 15000},
    "bangalore": {"budget": 1800, "mid": 4500, "luxury": 13000},
    "bengaluru": {"budget": 1800, "mid": 4500, "luxury": 13000},
    "delhi":     {"budget": 1500, "mid": 4000, "luxury": 12000},
    "jaipur":    {"budget": 1200, "mid": 3500, "luxury": 10000},
    "kochi":     {"budget": 1200, "mid": 3000, "luxury": 9000},
    "tokyo":     {"budget": 2500, "mid": 6000, "luxury": 18000},
    "paris":     {"budget": 3500, "mid": 8000, "luxury": 25000},
    "london":    {"budget": 4000, "mid": 9000, "luxury": 28000},
    "new york":  {"budget": 5000, "mid": 11000, "luxury": 35000},
    "dubai":     {"budget": 2800, "mid": 7000, "luxury": 22000},
    "singapore": {"budget": 3200, "mid": 7500, "luxury": 20000},
    "bangkok":   {"budget": 1200, "mid": 3500, "luxury": 10000},
    "bali":      {"budget": 1000, "mid": 3000, "luxury": 9000},
    "default":   {"budget": 2000, "mid": 5000, "luxury": 15000},
}


def _travel_dates(days: int) -> tuple[str, str]:
    check_in  = datetime.now() + timedelta(days=30)
    check_out = check_in + timedelta(days=days)
    return check_in.strftime("%Y-%m-%d"), check_out.strftime("%Y-%m-%d")


# ── SerpAPI (Google Hotels) ────────────────────────────────────────────────────

def _search_hotels_serpapi(
    destination: str,
    check_in: str,
    check_out: str,
    budget_tier: str,
) -> list[dict] | None:
    key = os.getenv("SERPAPI_KEY")
    if not key:
        return None

    try:
        resp = requests.get(
            "https://serpapi.com/search",
            params={
                "engine":         "google_hotels",
                "q":              f"hotels in {destination}",
                "check_in_date":  check_in,
                "check_out_date": check_out,
                "currency":       "INR",
                "adults":         2,
                "api_key":        key,
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

        properties = data.get("properties", [])
        if not properties:
            return None

        # Sort by price
        properties.sort(key=lambda h: h.get("rate_per_night", {}).get("lowest", 999999))

        # Select based on tier
        if budget_tier == "budget":
            selection = properties[:3]
        elif budget_tier == "luxury":
            selection = properties[-3:]
        else:
            mid = len(properties) // 2
            selection = properties[max(0, mid-1): mid+2]

        hotels = []
        for h in selection[:3]:
            rate = h.get("rate_per_night", {})
            price = normalize_price(rate.get("lowest", 0))
            hotels.append({
                "name":          h.get("name", ""),
                "per_night_inr": price,
                "rating":        h.get("overall_rating", None),
                "reviews":       h.get("reviews", None),
                "description":   h.get("description", ""),
                "amenities":     h.get("amenities", [])[:5],
                "source":        "Google Hotels (live)",
            })
        return hotels

    except Exception as exc:
        return None


# ── Fallback ───────────────────────────────────────────────────────────────────

def _fallback_hotels(destination: str, days: int, budget_tier: str) -> list[dict]:
    key = destination.lower().strip()
    rates = FALLBACK_RATES["default"]
    for city, r in FALLBACK_RATES.items():
        if city in key:
            rates = r
            break

    per_night = rates.get(budget_tier, rates["mid"])
    return [{
        "name":          f"Estimated {budget_tier.title()} Hotel in {destination}",
        "per_night_inr": per_night,
        "total_inr":     per_night * days,
        "rating":        None,
        "source":        "Estimated (set SERPAPI_KEY for live prices)",
    }]


# ── Main search function ───────────────────────────────────────────────────────

def search_hotels(destination: str, days: int, budget_tier: str = "mid") -> dict:
    check_in, check_out = _travel_dates(days)

    live = _search_hotels_serpapi(destination, check_in, check_out, budget_tier)
    if live:
        cheapest_per_night = min(h["per_night_inr"] for h in live)
        return {
            "hotels":            live,
            "cheapest_per_night_inr": cheapest_per_night,
            "total_inr":         cheapest_per_night * days,
            "nights":            days,
            "check_in":          check_in,
            "check_out":         check_out,
        }

    fallback = _fallback_hotels(destination, days, budget_tier)
    return {
        "hotels":                 fallback,
        "cheapest_per_night_inr": fallback[0]["per_night_inr"],
        "total_inr":              fallback[0]["per_night_inr"] * days,
        "nights":                 days,
    }


# ── MCP handlers ───────────────────────────────────────────────────────────────

@server.list_tools()
async def list_tools():
    return TOOLS


@server.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "search_hotels":
        result = search_hotels(
            destination=arguments["destination"],
            days=arguments["days"],
            budget_tier=arguments.get("budget_tier", "mid"),
        )
        return [TextContent(type="text", text=json.dumps(result))]

    raise ValueError(f"Unknown tool: {name}")


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
