# Agentic AI Travel Planner

An end-to-end Agentic AI Travel Planning System built using LangGraph, CrewAI, FastAPI, Streamlit, Ollama, MCP Servers, and Guardrails.

The system generates personalized travel plans using real-time flight prices, hotel prices, weather information, budget analysis, itinerary generation, and AI-based travel recommendations.

---

# Features

## Intelligent Travel Planning

Generate complete travel plans based on:

* Destination
* Budget
* Number of travel days
* Interests and preferences

Examples:

* Anime Tourism
* Food Tourism
* Historical Tourism
* Adventure Tourism
* Nature Tourism
* Nightlife Tourism

---

## Real-Time Cost Analysis

Before generating a travel plan, the system estimates actual trip costs using:

### Flights

Uses SearchAPI Google Flights integration to fetch:

* Flight prices
* Airlines
* Flight duration
* Number of stops

### Hotels

Uses SerpAPI Google Hotels integration to fetch:

* Hotel prices
* Hotel ratings
* Reviews
* Amenities

---

## Weather-Aware Itinerary Generation

The system automatically adjusts recommendations according to weather.

### Sunny Weather

Recommended:

* Temples
* Parks
* Walking tours
* Landmarks
* Outdoor sightseeing

### Rainy Weather

Recommended:

* Museums
* Shopping malls
* Anime cafes
* Aquariums
* Indoor attractions

---

## Budget Feasibility Analysis

Before planning, the system calculates:

Flight Cost
+
Hotel Cost
+
Food Cost
+
Transport Cost
+
Miscellaneous Cost
+
Safety Buffer

If the budget is insufficient:

* Planning is stopped
* User receives budget analysis
* Alternative suggestions are generated

Example:

* Reduce trip duration
* Increase budget
* Choose budget hotels
* Select a cheaper destination

---

## Multi-Agent AI System

CrewAI powers specialized agents.

### Travel Planner Agent

Responsible for:

* Travel summary generation
* Trip overview
* Destination recommendations

### Itinerary Agent

Responsible for:

* Day-wise itinerary generation
* Activity planning
* Weather-aware recommendations

---

## Guardrails

### Input Guardrails

Validate:

* Destination
* Budget
* Number of days
* Interests

Reject invalid requests before processing.

### Output Guardrails

Validate:

* Budget consistency
* Itinerary completeness
* Placeholder content
* Summary quality

Ensures production-quality responses.

---

# System Architecture

User
|
v
Streamlit Frontend
|
v
FastAPI Backend
|
v
LangGraph Workflow
|
+--------------------+
| Input Guardrail |
+--------------------+
|
v
+--------------------+
| Cost Check Node |
+--------------------+
|
v
+--------------------+
| Weather Node |
+--------------------+
|
v
+--------------------+
| CrewAI Agents |
+--------------------+
|
v
+--------------------+
| Evaluation Node |
+--------------------+
|
v
+--------------------+
| Output Guardrail |
+--------------------+
|
v
Travel Plan

---

# LangGraph Workflow

## 1. Input Validation

Validates:

* Destination
* Budget
* Travel duration
* Interests

---

## 2. Cost Check Node

Fetches:

### Flights

Using SearchAPI

Returns:

* Cheapest flight
* Airline information
* Estimated trip flight cost

### Hotels

Using SerpAPI

Returns:

* Hotel options
* Hotel ratings
* Price per night
* Total hotel cost

Calculates:

Minimum required trip budget.

---

## 3. Budget Routing

If:

budget >= required_cost

Continue planning.

Else:

Return budget insufficiency report.

---

## 4. Weather Node

Determines destination weather.

Returns:

* Sunny
* Rainy
* Cloudy

---

## 5. CrewAI Planning

Generates:

### Trip Summary

Destination overview.

### Budget Allocation

Breakdown of:

* Flights
* Hotels
* Food
* Transport
* Miscellaneous

### Itinerary

Day-wise travel schedule.

---

## 6. Evaluation Node

Scores generated plans.

Checks:

* Relevance
* Completeness
* Quality

---

## 7. Output Guardrail

Final validation before API response.

---

# Technology Stack

## Backend

* FastAPI
* LangGraph
* CrewAI
* Pydantic

## AI

* Ollama
* Qwen 2.5

## Frontend

* Streamlit

## External APIs

### SearchAPI

Google Flights

### SerpAPI

Google Hotels

### Google Maps API

Places and attractions

## Validation

* Input Guardrails
* Output Guardrails

---

# Project Structure

backend/

├── api/

├── graph/

│ ├── workflow.py

│ ├── state.py

│ ├── nodes.py

│ ├── crewai_node.py

│ └── evaluator_node.py

│

├── models/

│ └── travel.py

│

├── guardrails/

│ ├── input_guard.py

│ └── output_guard.py

│

├── mcp_servers/

│ ├── flights_server.py

│ ├── hotels_server.py

│ ├── weather_server.py

│ └── places_server.py

│

└── main.py

frontend/

└── streamlit_app.py

---

# Installation

## Clone Repository

git clone https://github.com/YOUR_USERNAME/agentic-ai-travel-planner.git

cd agentic-ai-travel-planner

---

## Create Virtual Environment

python -m venv travel_llm

travel_llm\Scripts\activate

---

## Install Dependencies

pip install -r requirements.txt

---

# Environment Variables

Create .env

SEARCHAPI_KEY=your_searchapi_key

SERPAPI_KEY=your_serpapi_key

GOOGLE_MAPS_API_KEY=your_google_maps_key

OLLAMA_MODEL=qwen2.5

OLLAMA_BASE_URL=http://localhost:11434

---

# Start Ollama

ollama run qwen2.5

---

# Run Backend

uvicorn backend.main:app --reload

---

# Run Frontend

streamlit run frontend/streamlit_app.py

---

# Example Request

{
"destination": "Japan",
"budget": 150000,
"days": 7,
"interests": [
"anime",
"food",
"temples"
]
}

---

# Example Response

{
"trip_summary": "...",
"budget_breakdown": {
"flight": 25000,
"hotel": 58247,
"food": 10500,
"transport": 5600,
"misc": 50653
},
"itinerary": [
{
"day": 1,
"location": "Tokyo",
"activities": [
{
"activity": "Visit Akihabara",
"description": "Explore anime culture."
}
]
}
]
}

---

# Future Improvements

* Flight booking integration
* Hotel booking integration
* Visa recommendations
* Currency conversion
* Restaurant reservation system
* Travel chatbot
* Multi-language support
* PDF itinerary export
* Calendar integration
* Mobile application

---

# Resume Highlights

* Built a production-style Agentic AI system using LangGraph and CrewAI.
* Integrated real-time flight and hotel pricing APIs.
* Designed multi-agent travel planning workflows.
* Implemented input and output guardrails for reliability.
* Developed a full-stack application with FastAPI and Streamlit.
* Used local LLMs through Ollama for privacy and cost efficiency.
