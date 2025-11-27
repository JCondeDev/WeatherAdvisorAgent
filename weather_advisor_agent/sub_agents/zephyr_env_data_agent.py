import json
import logging

from weather_advisor_agent.config import config

from google.genai.types import Content, Part
from google.adk.tools import FunctionTool
from google.adk.agents import Agent, LoopAgent
from google.adk.agents.callback_context import CallbackContext

from weather_advisor_agent.tools import (geocode_place_name,fetch_and_store_snapshot,get_last_snapshot)

from weather_advisor_agent.validation_checkers import EnvSnapshotValidationChecker

from weather_advisor_agent.utils import observability, session_cache

logger = logging.getLogger(__name__)

def zephyr_callback_from_global(callback_context: CallbackContext) -> Content:
    """Callback for zephyr agent - stores weather snapshot data"""
    print(f"\n🔍 ZEPHYR CALLBACK CALLED - Session: {callback_context.session.id}")
    
    last_snapshot = get_last_snapshot()
    print(f"🔍 Got snapshot: {last_snapshot is not None}")
    
    if last_snapshot:
        # Store in session state as JSON string
        callback_context.session.state["env_snapshot"] = json.dumps(last_snapshot)
        print(f"🔍 Stored in session.state as JSON")
        
        # CRITICAL: Store in global cache
        print(f"🔍 About to store in cache...")
        session_cache.store_evaluation_data(
            callback_context.session.id,
            {"env_snapshot": last_snapshot}
        )
        print(f"✅ STORED IN CACHE: env_snapshot")
        
        observability.log_agent_complete("zephyr_env_data_agent", "env_snapshot", success=True)
        logger.info("Stored snapshot. | ")
        
        current = last_snapshot.get("current", {})
        temp = current.get("temperature_c", "?")
        wind = current.get("wind_speed_10m_ms", "?")
        logger.info(f"Data: {temp}°C, {wind} m/s wind. |")
        
        return Content(parts=[])
    else:
        print(f"❌ NO SNAPSHOT DATA")
        logger.warning("No snapshot. | ")
        observability.log_agent_complete("zephyr_env_data_agent", "env_snapshot", success=False)
        return Content(parts=[Part(text="No weather data available.")])

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
  max_iterations=2
)