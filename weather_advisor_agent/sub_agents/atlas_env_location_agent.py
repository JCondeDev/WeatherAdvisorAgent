# atlas_env_location_agent.py
from google.adk.agents import LoopAgent

from .atlas_env_location_discovery_agent import atlas_env_location_discovery_agent
from .atlas_env_location_geocode_agent import atlas_env_location_geocode_agent

from ..validation_checkers import EnvLocationGeoValidationChecker
from ..utils.agent_utils import suppress_output_callback

atlas_env_location_loop_agent = LoopAgent(
  name="atlas_env_location_agent",
  description="Runs the Atlas location pipeline: discovery → geocode → validation.",
  sub_agents=[atlas_env_location_discovery_agent,atlas_env_location_geocode_agent,EnvLocationGeoValidationChecker(name="location_geo_validation_agent")],
  max_iterations=3,
  after_agent_callback=suppress_output_callback
)
