from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional


class TravelRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    destination: str = Field(..., min_length=1, max_length=200)
    budget: int = Field(..., gt=0, description="Total budget in INR")
    days: int = Field(..., gt=0, le=30)
    interests: List[str] = Field(..., min_length=1)
    origin: str = Field(default="Delhi", description="Departure city for flight search")


class BudgetBreakdown(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    flight: int
    hotel: int
    food: int
    transport: int
    misc: int


class Activity(BaseModel):
    activity: str
    description: str


class DayPlan(BaseModel):
    day: int
    location: str
    activities: List[Activity]


class RealTimeCosts(BaseModel):
    """Actual costs fetched from live APIs before planning begins."""
    flight_cost: int = 0
    hotel_cost_per_night: int = 0
    hotel_total: int = 0
    estimated_food_per_day: int = 0
    estimated_transport_per_day: int = 0
    total_estimated_cost: int = 0
    flight_source: str = "estimated"
    hotel_source: str = "estimated"
    is_sufficient: bool = True
    shortfall: int = 0
    cheapest_flight_option: Optional[dict] = None
    cheapest_hotel_option: Optional[dict] = None


class TravelPlan(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    trip_summary: str
    budget_breakdown: BudgetBreakdown
    itinerary: List[DayPlan]
    real_time_costs: Optional[RealTimeCosts] = None
    evaluation_score: Optional[int] = None
    evaluation_reason: Optional[str] = None
    weather_condition: Optional[str] = None
    budget_sufficient: bool = True


class BudgetInsufficientResponse(BaseModel):
    """Returned when the budget cannot cover the minimum trip cost."""
    budget_sufficient: bool = False
    destination: str
    days: int
    your_budget: int
    minimum_required: int
    shortfall: int
    breakdown: dict                    # what each category actually costs
    cheapest_flight: Optional[dict] = None
    cheapest_hotel: Optional[dict] = None
    suggestions: List[str]             # actionable advice


class ItineraryOutput(BaseModel):
    itinerary: List[DayPlan]
