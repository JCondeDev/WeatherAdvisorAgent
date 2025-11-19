# atlas_env_location_discovery_agent.py
from google.adk.agents import Agent
from google.adk.tools import google_search

from ..config import config
from ..utils.agent_utils import suppress_output_callback

atlas_env_location_discovery_agent = Agent(
  model=config.worker_model,
  name="atlas_env_location_discovery_agent",
  description="Finds nearby candidate locations for outdoor activities.",
  instruction="""
  You are Atlas-Discovery.

  Input:
  - A user's general location (city/region/country).
  - An outdoor activity (hiking, trail running, cycling, etc).

  Task:
  1. Infer the activity.
  2. Use google_search to find **real, verifiable locations nearby**.
  3. Produce 3–7 candidate locations.
  4. Write to session state key `env_location_options` a list like:

      [
        {"name": "...", "region_hint": "...", "activity": "..."},
        ...
      ]

  Notes:
  - Do not fabricate locations.
  - Results must come from the search tool.
  """,
  tools=[google_search],
  output_key="env_location_options",
  after_agent_callback=suppress_output_callback,
)

