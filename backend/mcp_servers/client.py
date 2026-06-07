"""
MCP client factory  (langchain-mcp-adapters >= 0.1.x)

Spawns each MCP server as a subprocess and wraps its tools as
LangChain BaseTool instances so they can be passed into CrewAI agents
or LangGraph nodes.

Usage:
    from backend.mcp_servers.client import get_weather_tools, get_flight_tools, get_hotel_tools
"""

import sys
import asyncio
import logging
from pathlib import Path
from typing import List

from langchain_core.tools import BaseTool

logger = logging.getLogger(__name__)

_ROOT   = Path(__file__).parent.parent.parent   # project root
_PYTHON = sys.executable


async def _load_mcp_tools(server_name: str, command: list[str]) -> List[BaseTool]:
    """
    Starts the named MCP server subprocess via stdio transport and returns
    its tools as LangChain BaseTool instances.

    Uses MultiServerMCPClient with the StdioConnection TypedDict format
    introduced in langchain-mcp-adapters 0.1.x.
    """
    try:
        from langchain_mcp_adapters.client import MultiServerMCPClient

        client = MultiServerMCPClient(
            connections={
                server_name: {
                    "transport": "stdio",
                    "command":   command[0],
                    "args":      command[1:],
                    "cwd":       str(_ROOT),
                }
            }
        )
        tools = await client.get_tools()
        logger.info(f"[MCP] Loaded {len(tools)} tool(s) from '{server_name}'")
        return tools

    except ImportError:
        logger.warning("[MCP] langchain-mcp-adapters not installed")
        return []
    except Exception as exc:
        logger.error(f"[MCP] Failed to load '{server_name}' tools: {exc}")
        return []


def _run_async(coro) -> list:
    """Run an async coroutine safely from synchronous code."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Running inside an existing event loop (e.g. Jupyter / some test runners)
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                return pool.submit(asyncio.run, coro).result(timeout=30)
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


def get_weather_tools() -> List[BaseTool]:
    return _run_async(_load_mcp_tools(
        "weather",
        [_PYTHON, "-m", "backend.mcp_servers.weather_server"],
    ))


def get_flight_tools() -> List[BaseTool]:
    return _run_async(_load_mcp_tools(
        "flights",
        [_PYTHON, "-m", "backend.mcp_servers.flights_server"],
    ))


def get_hotel_tools() -> List[BaseTool]:
    return _run_async(_load_mcp_tools(
        "hotels",
        [_PYTHON, "-m", "backend.mcp_servers.hotels_server"],
    ))


def get_places_tools() -> List[BaseTool]:
    return _run_async(_load_mcp_tools(
        "places",
        [_PYTHON, "-m", "backend.mcp_servers.places_server"],
    ))
