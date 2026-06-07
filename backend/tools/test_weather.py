import requests
from backend.tools.geocoding import get_coordinates


def get_weather(destination: str) -> str:
    lat, lon = get_coordinates(destination)

    response = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude":  lat,
            "longitude": lon,
            "current":   "temperature_2m,rain",
        },
        timeout=10,
    )
    response.raise_for_status()
    data = response.json()

    rain = data["current"].get("rain", 0)
    temp = data["current"].get("temperature_2m", 25)

    if rain > 0:
        return "Rainy"
    if temp > 35:
        return "Hot"
    if temp < 10:
        return "Cold"
    return "Sunny"
