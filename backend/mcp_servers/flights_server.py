"""
MCP server: flights

Returns real flight prices using SearchAPI (Google Flights scraper).
Falls back to estimate table when SEARCHAPI_KEY is not set.

Sign up free at https://www.searchapi.io — 100 searches/month, no credit card.
"""

import os
import json
import asyncio
import requests
from datetime import datetime, timedelta
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from dotenv import load_dotenv
load_dotenv()

server = Server("flights-server")


TOOLS = [
    Tool(
        name="search_flights",
        description=(
            "Returns real round-trip flight prices and options for a destination. "
            "Prices are in INR. Uses Google Flights data via SearchAPI."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "origin":      {"type": "string", "description": "Origin city or airport code, e.g. 'Delhi' or 'DEL'"},
                "destination": {"type": "string", "description": "Destination city or airport code, e.g. 'Goa' or 'GOI'"},
                "budget":      {"type": "integer", "description": "Total trip budget in INR"},
                "days":        {"type": "integer", "description": "Trip duration in days"},
            },
            "required": ["destination", "budget", "days"],
        },
    ),
]

# ── Airport code lookup (common Indian + international cities) ─────────────────

AIRPORT_CODES: dict[str, str] = {
    "delhi": "DEL", "new delhi": "DEL",
    "mumbai": "BOM", "bombay": "BOM",
    "bangalore": "BLR", "bengaluru": "BLR",
    "goa": "GOI",
    "hyderabad": "HYD",
    "chennai": "MAA", "madras": "MAA",
    "kolkata": "CCU", "calcutta": "CCU",
    "pune": "PNQ",
    "ahmedabad": "AMD",
    "jaipur": "JAI",
    "kochi": "COK", "cochin": "COK",
    "tokyo": "TYO", "japan": "TYO",
    "paris": "CDG",
    "london": "LHR",
    "new york": "JFK",
    "dubai": "DXB",
    "singapore": "SIN",
    "bangkok": "BKK",
    "bali": "DPS",
}

FALLBACK_PRICES: dict[str, int] = {
    "goa": 6000, "mumbai": 5000, "bangalore": 5500, "bengaluru": 5500,
    "hyderabad": 5000, "chennai": 5500, "kolkata": 6000, "jaipur": 5500,
    "kochi": 6000, "tokyo": 35000, "paris": 45000, "london": 42000,
    "new york": 55000, "dubai": 18000, "singapore": 22000,
    "bangkok": 12000, "bali": 15000,
}


def _city_to_airport(city: str) -> str:
    """Convert city name to IATA airport code."""
    return AIRPORT_CODES.get(city.lower().strip(), city.upper()[:3])


def _travel_dates(days: int) -> tuple[str, str]:
    """Returns a realistic future travel date pair."""
    depart = datetime.now() + timedelta(days=30)
    return depart.strftime("%Y-%m-%d"), (depart + timedelta(days=days)).strftime("%Y-%m-%d")


# ── SearchAPI (Google Flights) ─────────────────────────────────────────────────

def _search_flights_searchapi(
    origin_code: str,
    dest_code: str,
    outbound_date: str,
    return_date: str,
) -> dict | None:
    key = os.getenv("SEARCHAPI_KEY")
    if not key:
        return None

    try:
        resp = requests.get(
            "https://www.searchapi.io/api/v1/search",
            params={
                "engine":        "google_flights",
                "departure_id":  origin_code,
                "arrival_id":    dest_code,
                "outbound_date": outbound_date,
                "return_date":   return_date,
                "currency":      "INR",
                "type":          "1",
                "api_key":       key,
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

        # SearchAPI nests price differently depending on response shape
        all_flights = data.get("best_flights", []) + data.get("other_flights", [])
        if not all_flights:
            return None

        flights_info = []
        for f in all_flights[:3]:
            # Price can be at top level OR inside price_breakdown
            price = (
                f.get("price")
                or f.get("price_breakdown", {}).get("total", 0)
                or 0
            )
            # Convert string prices like "₹35,000" safely
            if isinstance(price, str):
                import re
                price = int(re.sub(r"[^\d]", "", price) or 0)

            legs = f.get("flights", [{}])
            flights_info.append({
                "price_inr": int(price),
                "airline":   legs[0].get("airline", "") if legs else "",
                "duration":  f.get("total_duration", 0),
                "stops":     len(legs) - 1 if legs else 0,
            })

        if not flights_info:
            return None

        cheapest = min(flights_info, key=lambda x: x["price_inr"])

        return {
            "cheapest_price_inr": cheapest["price_inr"],
            "options":            flights_info,
            "outbound_date":      outbound_date,
            "return_date":        return_date,
            "source":             "Google Flights (live)",
        }

    except Exception as exc:
        print(f"[SearchAPI ERROR] {exc}")
        return None


# ── Fallback estimate ──────────────────────────────────────────────────────────

def _fallback_price(destination: str, budget: int) -> dict:
    key = destination.lower().strip()
    for city, price in FALLBACK_PRICES.items():
        if city in key:
            final = min(price, int(budget * 0.35))
            return {
                "cheapest_price_inr": final,
                "options": [{"price_inr": final, "airline": "Estimated", "duration": 0, "stops": 0}],
                "source": "Estimated (set SEARCHAPI_KEY for live prices)",
            }
    fallback = min(25000, int(budget * 0.35))
    return {
        "cheapest_price_inr": fallback,
        "options": [{"price_inr": fallback, "airline": "Estimated", "duration": 0, "stops": 0}],
        "source": "Estimated (set SEARCHAPI_KEY for live prices)",
    }


# ── Main search function ───────────────────────────────────────────────────────

def search_flights(destination: str, budget: int, days: int, origin: str = "Delhi") -> dict:
    origin_code = _city_to_airport(origin)
    dest_code   = _city_to_airport(destination)
    outbound, return_date = _travel_dates(days)

    live = _search_flights_searchapi(origin_code, dest_code, outbound, return_date)
    if live:
        return live

    return _fallback_price(destination, budget)


# ── MCP handlers ───────────────────────────────────────────────────────────────

@server.list_tools()
async def list_tools():
    return TOOLS


@server.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "search_flights":
        result = search_flights(
            destination=arguments["destination"],
            budget=arguments.get("budget", 50000),
            days=arguments.get("days", 5),
            origin=arguments.get("origin", "Delhi"),
        )
        return [TextContent(type="text", text=json.dumps(result))]

    raise ValueError(f"Unknown tool: {name}")


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
