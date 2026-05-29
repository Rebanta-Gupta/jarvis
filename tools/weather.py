import requests

WMO_CODES = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Foggy", 48: "Icy fog", 51: "Light drizzle", 53: "Drizzle",
    55: "Heavy drizzle", 61: "Light rain", 63: "Rain", 65: "Heavy rain",
    71: "Light snow", 73: "Snow", 75: "Heavy snow", 80: "Rain showers",
    81: "Heavy showers", 82: "Violent showers", 95: "Thunderstorm",
}

def _geocode(city: str) -> tuple[float, float, str] | None:
    """
    Resolve a city name to (lat, lon, display_name) using Open-Meteo geocoding.
    Returns None if not found.
    """
    try:
        resp = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": city, "count": 1, "language": "en", "format": "json"},
            timeout=5,
        )
        data = resp.json()
        results = data.get("results")
        if not results:
            return None
        r = results[0]
        # Build a clean display name: "Maple Ridge, British Columbia, Canada"
        parts = [r.get("name", city)]
        if r.get("admin1"):
            parts.append(r["admin1"])
        if r.get("country"):
            parts.append(r["country"])
        display = ", ".join(parts)
        return r["latitude"], r["longitude"], display
    except Exception:
        return None


def get_weather(city: str = "Vancouver") -> str:
    """Get current weather for any city worldwide."""
    geo = _geocode(city)
    if not geo:
        return f"Couldn't find a location called '{city}'. Try a different spelling or nearby city."

    lat, lon, display_name = geo

    try:
        resp = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,weathercode,windspeed_10m,relative_humidity_2m",
                "temperature_unit": "celsius",
                "windspeed_unit": "kmh",
                "timezone": "auto",
            },
            timeout=5,
        )
        data = resp.json()
        current = data["current"]

        temp_c = current["temperature_2m"]
        temp_f = round((temp_c * 9 / 5) + 32, 1)
        condition = WMO_CODES.get(current["weathercode"], "Unknown")
        wind = current["windspeed_10m"]
        humidity = current["relative_humidity_2m"]

        return (
            f"{condition} in {display_name}. "
            f"{temp_c}°C ({temp_f}°F), "
            f"wind {wind} km/h, "
            f"humidity {humidity}%."
        )
    except Exception as e:
        return f"Couldn't fetch weather right now: {e}"