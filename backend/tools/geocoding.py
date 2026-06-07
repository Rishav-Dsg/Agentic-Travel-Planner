import requests


def get_coordinates(city: str) -> tuple[float, float]:
    response = requests.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": city, "count": 1},
        timeout=10,
    )
    response.raise_for_status()
    data = response.json()

    if "results" not in data or not data["results"]:
        raise ValueError(f"City not found: {city}")

    result = data["results"][0]
    return result["latitude"], result["longitude"]
