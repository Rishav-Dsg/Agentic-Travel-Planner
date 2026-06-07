import logging
from fastapi import FastAPI
from backend.api.routes import router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
)

app = FastAPI(
    title="Agentic AI Travel Planner",
    description=(
        "AI-powered travel planning using LangGraph, CrewAI, MCP tool servers, "
        "Guardrails AI, and deep evaluation."
    ),
    version="2.0.0",
    docs_url="/docs",
)

app.include_router(router, prefix="/api")


@app.get("/")
async def root():
    return {
        "status":  "ok",
        "message": "Travel Planner API v2 is running",
        "docs":    "/docs",
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}
