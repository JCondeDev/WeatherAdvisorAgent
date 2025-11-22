from ..config import config

import logging

from google.genai.types import Content
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents import Agent, LoopAgent
from google.adk.tools import FunctionTool

from weather_advisor_agent.tools import (geocode_place_name,fetch_and_store_snapshot,get_last_snapshot)

from weather_advisor_agent.validation_checkers import EnvSnapshotValidationChecker

from weather_advisor_agent.utils import observability

logger = logging.getLogger(__name__)

def zephyr_callback_from_global(callback_context: CallbackContext) -> Content:
  last_snapshot = get_last_snapshot()
  if last_snapshot:
    callback_context.session.state["env_snapshot"] = last_snapshot
    observability.log_agent_complete("zephyr_env_data_agent","env_snapshot",success=True)
    logger.info("Stored snapshot. | ")
    
    if isinstance(last_snapshot, dict) and "current" in last_snapshot:
      current = last_snapshot["current"]
      temp = current.get("temperature_c", "?")
      wind = current.get("wind_speed_10m_ms", "?")
      logger.info(f"Data: {temp}°C, {wind} m/s wind. | ")
    
    last_snapshot = None
  else:
    callback_context.session.state["env_snapshot"] = {}
    observability.log_agent_complete("zephyr_env_data_agent","env_snapshot",success=False)
    logger.warning("No snapshot. | ")
  
  return Content()


zephyr_env_data_agent = Agent(
  model=config.worker_model,
  name="zephyr_env_data_agent",
  description="Fetches live environmental data.",
  instruction="""
  Extract location from user message.
  Call geocode_place_name, then call fetch_and_store_snapshot with coordinates.
  """,
  tools=[FunctionTool(fetch_and_store_snapshot),FunctionTool(geocode_place_name)],
  after_agent_callback=zephyr_callback_from_global
)

robust_env_data_agent = LoopAgent(
  name="robust_env_data_agent",
  description="Robust environmental data fetcher with retries.",
  sub_agents=[zephyr_env_data_agent,EnvSnapshotValidationChecker(name="env_snapshot_validation_checker")],
  max_iterations=config.max_iterations
)