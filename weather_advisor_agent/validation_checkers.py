from typing import AsyncGenerator
from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions


class EnvSnapshotValidationChecker(BaseAgent):
  async def _run_async_impl(self, context: InvocationContext) -> AsyncGenerator[Event, None]:
    if context.session.state.get("env_snapshot"):
      yield Event(author=self.name, actions=EventActions(escalate=True))
    else:
      yield Event(author=self.name)

class EnvRiskValidationChecker(BaseAgent):
  async def _run_async_impl(self, context: InvocationContext) -> AsyncGenerator[Event, None]:
    if context.session.state.get("env_risk_report"):
      yield Event(author=self.name, actions=EventActions(escalate=True))
    else:
      yield Event(author=self.name)

class EnvLocationGeoValidationChecker(BaseAgent):
  async def _run_async_impl(self, context: InvocationContext) -> AsyncGenerator[Event, None]:
    state = context.session.state
    locations = state.get("env_location_options")

    if not locations:
      yield Event(author=self.name, actions=EventActions(escalate=True))
      return

    if not isinstance(locations, list):
      locations = []

    cleaned = []
    seen_coords = set()

    for loc in locations:
      if not isinstance(loc, dict):
        continue

      lat = loc.get("latitude")
      lon = loc.get("longitude")
      name = loc.get("name")

      if lat is None or lon is None:
        continue

      try:
        lat_f = float(lat)
        lon_f = float(lon)
      except (TypeError, ValueError):
        continue

      key = (round(lat_f, 4), round(lon_f, 4))
      if key in seen_coords:
        continue
      seen_coords.add(key)

      cleaned.append(
        {
          "name": name or "unknown",
          "latitude": lat_f,
          "longitude": lon_f,
          "country": loc.get("country"),
          "admin1": loc.get("admin1"),
          "activity": loc.get("activity"),
          "source": loc.get("source", "google_search+geocode")
        }
      )

    state["env_location_options"] = cleaned
    yield Event(author=self.name, actions=EventActions(escalate=True))