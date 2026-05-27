import requests

# Map of common city names to coordinates
CITY_COORDS = {
    "vancouver": (49.2827, -123.1207),
    "victoria": (48.4284, -123.3656),
    "toronto": (43.6532, -79.3832),
    "montreal": (45.5017, -73.5673),
    "calgary": (51.0447, -114.0719),
    "new york": (40.7128, -74.0060),
    "london": (51.5074, -0.1278),
    "los angeles": (34.0522, -118.2437),
    "chicago": (41.8781, -87.6298),
    "seattle": (47.6062, -122.3321),
}

WMO_CODES = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Foggy", 48: "Icy fog", 51: "Light drizzle", 53: "Drizzle",
    55: "Heavy drizzle", 61: "Light rain", 63: "Rain", 65: "Heavy rain",
    71: "Light snow", 73: "Snow", 75: "Heavy snow", 80: "Rain showers",
    81: "Heavy showers", 82: "Violent showers", 95: "Thunderstorm",
}

def get_weather(city: str = "vancouver") -> str:
    """Get current weather for a city."""
    city_lower = city.lower().strip()
    coords = CITY_COORDS.get(city_lower)

    if not coords:
        return f"Sorry, I don't have coordinates for '{city}'. Try a major city name."

    lat, lon = coords
    try:
        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            f"&current=temperature_2m,weathercode,windspeed_10m,relative_humidity_2m"
            f"&temperature_unit=celsius&windspeed_unit=kmh&timezone=auto"
        )
        response = requests.get(url, timeout=5)
        data = response.json()
        current = data["current"]

        temp_c = current["temperature_2m"]
        temp_f = round((temp_c * 9/5) + 32, 1)
        condition = WMO_CODES.get(current["weathercode"], "Unknown")
        wind = current["windspeed_10m"]
        humidity = current["relative_humidity_2m"]

        return (
            f"{condition} in {city.title()}. "
            f"{temp_c}°C ({temp_f}°F), "
            f"wind {wind} km/h, "
            f"humidity {humidity}%."
        )
    except Exception as e:
        return f"Couldn't fetch weather right now: {str(e)}"