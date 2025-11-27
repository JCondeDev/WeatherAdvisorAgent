import logging
import json
import re

from google.adk.agents.callback_context import CallbackContext
from google.genai.types import Content, Part

from weather_advisor_agent.utils.observability import observability

from weather_advisor_agent.utils import session_cache

logger = logging.getLogger(__name__)

def _parse_json_string(value: str) -> any:
  """Parse JSON string, removing markdown code blocks"""
  if not isinstance(value, str):
    return value
  
  value = re.sub(r'```json\s*', '', value)
  value = re.sub(r'```\s*', '', value)
  value = value.strip()
  
  try:
    parsed = json.loads(value)
    return parsed
  except json.JSONDecodeError as e:
    logger.debug(f"JSON parse failed: {e}.\n")
    return value
  
def zephyr_data_callback(callback_context: CallbackContext) -> Content:
  """Callback for Zephyr"""
  snapshot = callback_context.session.state.get("env_snapshot")
  
  if isinstance(snapshot, str):
    logger.warning("Zephyr returned string instead of dict/list.\n")
    parsed = _parse_json_string(snapshot)
    
    if isinstance(parsed, (dict, list)):
      callback_context.session.state["env_snapshot"] = parsed
      snapshot = parsed
      logger.info("Parsed JSON string.")
    else:
      logger.error(f"Could not parse snapshot.\n")
  
  if snapshot:
    if isinstance(snapshot, list):
      count = len(snapshot)
      observability.log_agent_complete("zephyr_env_data_agent","env_snapshot",success=True)
      logger.info(f"Fetched {count} location snapshot.\n")
    elif isinstance(snapshot, dict):
      observability.log_agent_complete("zephyr_env_data_agent","env_snapshot",success=True)
      logger.info("Fetched single location snapshot.\n")
    else:
      observability.log_agent_complete("zephyr_env_data_agent","env_snapshot",success=False)
      logger.error(f"Unexpected type: {type(snapshot).__name__}.\n")
    
    observability.log_state_change("env_snapshot","SET",f"Type: {type(snapshot).__name__}")
  else:
    observability.log_agent_complete("zephyr_env_data_agent","env_snapshot",success=False)
    logger.warning("No snapshot.\n")
  
  return Content()


def aether_risk_callback(*args, **kwargs):
    """Callback for aether risk agent - stores risk assessment"""
    ctx = kwargs.get("callback_context")
    if ctx is None and len(args) >= 2:
        ctx = args[1]
    if ctx is None:
        return None
    
    state = ctx.session.state
    risk_report = state.get("env_risk_report")
    
    # Handle string output from agent
    if isinstance(risk_report, str):
        logger.warning("Aether returned string instead of dict.")
        
        # CRITICAL FIX: Strip markdown code blocks
        risk_str = risk_report.strip()
        if risk_str.startswith("```json"):
            risk_str = risk_str[7:]
        elif risk_str.startswith("```"):
            risk_str = risk_str[3:]
        if risk_str.endswith("```"):
            risk_str = risk_str[:-3]
        risk_str = risk_str.strip()
        
        try:
            risk_report = json.loads(risk_str)
            logger.info("Parsed JSON string.")
        except json.JSONDecodeError as e:
            logger.error(f"Could not parse risk report: {e}")
            return None
    
    if isinstance(risk_report, dict):
        # Store in session state
        state["env_risk_report"] = json.dumps(risk_report)
        
        # CRITICAL: Store in global cache
        session_cache.store_evaluation_data(
            ctx.session.id,
            {"env_risk_report": risk_report}
        )
        
        observability.log_agent_complete("aether_env_risk_agent", "env_risk_report", success=True)
        logger.info("Risk assessment completed.")
        return None
    else:
        logger.warning("No risk report or invalid format.")
        observability.log_agent_complete("aether_env_risk_agent", "env_risk_report", success=False)
        return None


def atlas_location_callback(*args, **kwargs):
    """Callback for atlas location agent - stores location options"""
    ctx = kwargs.get("callback_context")
    if ctx is None and len(args) >= 2:
        ctx = args[1]
    if ctx is None:
        return None
    
    state = ctx.session.state
    locations = state.get("env_location_options")
    
    # Handle string output from agent
    if isinstance(locations, str):
        logger.warning("Atlas returned string instead of list.")
        
        # CRITICAL FIX: Strip markdown code blocks
        locations_str = locations.strip()
        if locations_str.startswith("```json"):
            locations_str = locations_str[7:]  # Remove ```json
        elif locations_str.startswith("```"):
            locations_str = locations_str[3:]   # Remove ```
        if locations_str.endswith("```"):
            locations_str = locations_str[:-3]  # Remove trailing ```
        locations_str = locations_str.strip()
        
        try:
            locations = json.loads(locations_str)
            logger.info("Successfully parsed locations from JSON string.")
        except json.JSONDecodeError as e:
            logger.error(f"Could not parse locations: {e}")
            return None
    
    if isinstance(locations, list) and locations:
        # Store in session state
        state["env_location_options"] = json.dumps(locations)
        
        # CRITICAL: Store in global cache
        session_cache.store_evaluation_data(
            ctx.session.id,
            {"env_location_options": locations}
        )
        
        observability.log_agent_complete("atlas_env_location_agent", "env_location_options", success=True)
        logger.info(f"Found {len(locations)} location option(s).")
        return None
    else:
        logger.warning("No location options or invalid format.")
        observability.log_agent_complete("atlas_env_location_agent", "env_location_options", success=False)
        return None


#Deprecated function, keeping for documentation and test porpuses
def aurora_advice_callback(callback_context: CallbackContext) -> Content:
  """Callback for Aurora"""
  advice = callback_context.session.state.get("env_advice_markdown")
  if advice and len(advice) > 100:
    observability.log_agent_complete("aurora_env_advice_writer","env_advice_markdown",success=True)
    logger.info(f"Generated advice report ({len(advice)} chars).\n")
    observability.log_state_change("env_advice_markdown","SET",f"{len(advice)} characters")
  else:
    observability.log_agent_complete("aurora_env_advice_writer","env_advice_markdown",success=False)
    logger.warning("Report too short or missing.\n")
  return Content()

def Theophrastus_root_callback(*args, **kwargs):
    ctx = kwargs.get("callback_context")
    if ctx is None and len(args) >= 2:
        ctx = args[1]
    if ctx is None:
        return None
    state = ctx.session.state

    
    # Store evaluation snapshot that persists
    evaluation_snapshot = {}
    for key in ["env_snapshot", "env_location_options", "env_risk_report", "env_advice_markdown"]:
        if key in state:
            evaluation_snapshot[key] = state[key]
    state["_evaluation_snapshot"] = evaluation_snapshot

    advice = state.get("env_advice_markdown")
    if advice:
        return Content(parts=[Part(text=advice)])

    last_msg = state.get("last_user_message", "").lower()
    if "weather" in last_msg and (state.get("env_snapshot") or state.get("env_risk_report")):
      return None

    locs = state.get("env_location_options")
    if isinstance(locs, list) and locs and isinstance(locs[0], dict):
        lines = [f"- {loc.get('name','Unknown')} — {loc.get('admin1','')}, {loc.get('country','')}" for loc in locs]
        msg = "Here are some options you might consider:\n" + "\n".join(lines)
        return Content(parts=[Part(text=msg)])

    return None