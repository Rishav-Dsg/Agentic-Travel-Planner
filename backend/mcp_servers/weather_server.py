"""
MCP server: weather + geocoding

Uses Google Maps Geocoding API for city → coordinates (more accurate than
Open-Meteo geocoding), and Open-Meteo for the actual weather data (free,
no key needed).

Falls back to Open-Meteo geocoding if GOOGLE_MAPS_API_KEY is not set.
"""

import os
import json
import asyncio
import requests
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

server = Server("weather-server")

TOOLS = [
    Tool(
        name="get_weather",
        description=(
            "Returns current weather condition and temperature for a city. "
            "Result is one of: Sunny, Rainy, Hot, Cold."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "destination": {"type": "string", "description": "City name"}
            },
            "required": ["destination"],
        },
    ),
    Tool(
        name="get_coordinates",
        description="Returns latitude and longitude for a city name.",
        inputSchema={
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "City name"}
            },
            "required": ["city"],
        },
    ),
    Tool(
        name="get_places",
        description=(
            "Returns real tourist attractions, restaurants, and points of "
            "interest for a city using Google Maps Places API."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "city":    {"type": "string", "description": "City name"},
                "query":   {"type": "string", "description": "What to search for, e.g. 'temples', 'restaurants', 'beaches'"},
                "max":     {"type": "integer", "description": "Max results (default 5)"},
            },
            "required": ["city", "query"],
        },
    ),
]


# ── Geocoding ──────────────────────────────────────────────────────────────────

def _get_coordinates_google(city: str) -> tuple[float, float]:
    """Use Google Maps Geocoding API — more accurate city resolution."""
    key = os.getenv("GOOGLE_MAPS_API_KEY")
    resp = requests.get(
        "https://maps.googleapis.com/maps/api/geocode/json",
        params={"address": city, "key": key},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("status") != "OK" or not data.get("results"):
        raise ValueError(f"Google Geocoding failed for '{city}': {data.get('status')}")
    loc = data["results"][0]["geometry"]["location"]
    return loc["lat"], loc["lng"]


def _get_coordinates_fallback(city: str) -> tuple[float, float]:
    """Open-Meteo geocoding — no key needed."""
    resp = requests.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": city, "count": 1},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    if "results" not in data or not data["results"]:
        raise ValueError(f"City not found: {city}")
    r = data["results"][0]
    return r["latitude"], r["longitude"]


def _get_coordinates(city: str) -> tuple[float, float]:
    if os.getenv("GOOGLE_MAPS_API_KEY"):
        try:
            return _get_coordinates_google(city)
        except Exception:
            pass
    return _get_coordinates_fallback(city)


# ── Weather ────────────────────────────────────────────────────────────────────

def _get_weather(destination: str) -> str:
    lat, lon = _get_coordinates(destination)
    resp = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude":  lat,
            "longitude": lon,
            "current":   "temperature_2m,rain,weathercode",
        },
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    rain = data["current"].get("rain", 0)
    temp = data["current"].get("temperature_2m", 25)

    if rain > 0:   return "Rainy"
    if temp > 35:  return "Hot"
    if temp < 10:  return "Cold"
    return "Sunny"


# ── Google Places ──────────────────────────────────────────────────────────────

def _get_places(city: str, query: str, max_results: int = 5) -> list[dict]:
    """
    Returns real places from Google Maps Places API.
    Falls back to an empty list if no API key or quota exceeded.
    """
    key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not key:
        return []

    try:
        resp = requests.get(
            "https://maps.googleapis.com/maps/api/place/textsearch/json",
            params={
                "query": f"{query} in {city}",
                "key":   key,
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()

        places = []
        for p in data.get("results", [])[:max_results]:
            places.append({
                "name":    p.get("name", ""),
                "address": p.get("formatted_address", ""),
                "rating":  p.get("rating", None),
                "types":   p.get("types", [])[:3],
            })
        return places

    except Exception as exc:
        return []


# ── MCP handlers ───────────────────────────────────────────────────────────────

@server.list_tools()
async def list_tools():
    return TOOLS


@server.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "get_weather":
        result = _get_weather(arguments["destination"])
        return [TextContent(type="text", text=result)]

    if name == "get_coordinates":
        lat, lon = _get_coordinates(arguments["city"])
        return [TextContent(type="text", text=json.dumps({"latitude": lat, "longitude": lon}))]

    if name == "get_places":
        places = _get_places(
            arguments["city"],
            arguments["query"],
            arguments.get("max", 5),
        )
        return [TextContent(type="text", text=json.dumps(places))]

    raise ValueError(f"Unknown tool: {name}")


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
