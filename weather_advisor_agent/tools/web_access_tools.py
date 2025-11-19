from typing import Dict, List, Any
import requests

def fetch_env_snapshot_from_open_meteo(latitude: float,longitude: float) -> Dict[str, Any]:
  base_url = "https://api.open-meteo.com/v1/forecast"
  params = {
    "latitude": latitude,
    "longitude": longitude,
    "current": [
      "temperature_2m",
      "apparent_temperature",
      "relative_humidity_2m",
      "wind_speed_10m"
    ],
    "hourly": [
      "pm10", 
      "pm2_5"
    ],
    "timezone": "auto"
  }

  resp = requests.get(base_url, params=params, timeout=10)
  resp.raise_for_status()
  data = resp.json()

  current = data.get("current", {})
  hourly = data.get("hourly", {})

  snapshot = {
    "location": {
      "latitude": latitude,
      "longitude": longitude
    },
    "current": {
      "temperature_c": current.get("temperature_2m"),
      "apparent_temperature_c": current.get("apparent_temperature"),
      "relative_humidity_percent": current.get("relative_humidity_2m"),
      "wind_speed_10m_ms": current.get("wind_speed_10m")
    },
    "hourly": {
      "pm10": hourly.get("pm10"),
      "pm2_5": hourly.get("pm2_5")
    },
    "raw": data
  }
  return snapshot

def geocode_place_name(place_name: str,region_hint: str = "",max_results: int = 3) -> Dict[str, Any]:
  if region_hint:
    query = f"{place_name}, {region_hint}"
  else:
    query = place_name

  url = "https://geocoding-api.open-meteo.com/v1/search"
  params =    {
    "name": query,
    "count": max_results,
    "language": "en",
    "format": "json"
  }

  resp = requests.get(url, params=params, timeout=10)
  resp.raise_for_status()
  data = resp.json()

  raw_results: List[Dict[str, Any]] = data.get("results") or []
  results: List[Dict[str, Any]] = []

  for r in raw_results:
    results.append(
      {
        "name": r.get("name"),
        "latitude": r.get("latitude"),
        "longitude": r.get("longitude"),
        "country": r.get("country"),
        "admin1": r.get("admin1")
      }
    )

  return {"query": place_name, "results": results}
