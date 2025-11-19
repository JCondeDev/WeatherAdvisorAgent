from google.adk.agents import Agent
from google.adk.tools import FunctionTool

# atlas_env_location_geocode_agent.py
from google.adk.agents import Agent
from google.adk.tools import FunctionTool

from ..config import config
from ..utils.agent_utils import suppress_output_callback
from ..tools.web_access_tools import geocode_place_name

atlas_env_location_geocode_agent = Agent(
  model=config.worker_model,
  name="atlas_env_location_geocode_agent",
  description="Converts discovered location names into coordinates.",
  instruction="""
  You are Atlas-Geocoder.

  Steps:
  1. Read `env_location_options` from session state.
      Each entry looks like:
        { "name": "...", "region_hint": "...", "activity": "..." }

  2. For each entry, call geocode_place_name to get:
      - latitude, longitude
      - region info
      - country
      - admin1 (state)

  3. Rewrite env_location_options to:

      [
        {
          "name": <place>,
          "latitude": <float>,
          "longitude": <float>,
          "country": <str or None>,
          "admin1": <str or None>,
          "activity": <original activity>,
          "source": "discovery+geocode"
        },
        ...
      ]

  Rules:
  - Produce no guesses.
  - Use ONLY real geocode results.
  """,
  tools=[FunctionTool(geocode_place_name)],
  output_key="env_location_options",
  after_agent_callback=suppress_output_callback
)

