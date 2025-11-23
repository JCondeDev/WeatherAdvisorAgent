import logging
import json
import re

from google.adk.agents.callback_context import CallbackContext
from google.genai.types import Content, Part

from .observability import observability

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


def aether_risk_callback(callback_context: CallbackContext) -> Content:
  """Callback for Aether"""
  risk_report = callback_context.session.state.get("env_risk_report")
  
  if isinstance(risk_report, str):
    logger.warning("Aether returned string instead of dict.\n")
    parsed = _parse_json_string(risk_report)
    
    if isinstance(parsed, dict):
      callback_context.session.state["env_risk_report"] = parsed
      risk_report = parsed
      logger.info("Parsed JSON string.\n")
    else:
      logger.error("Could not parse risk report.\n")

  if risk_report and isinstance(risk_report, dict):
    overall_risk = risk_report.get("overall_risk", "unknown")
    observability.log_agent_complete("aether_env_risk_agent","env_risk_report",success=True)
    logger.info(f"Risk assessment completed.\n")
    observability.log_state_change("env_risk_report","SET",f"overall_risk={overall_risk}")
  else:
    observability.log_agent_complete("aether_env_risk_agent","env_risk_report",success=False)
    logger.warning("Not a valid risk report.\n")
  
  return Content()

def atlas_location_callback(callback_context: CallbackContext) -> Content:
  """Callback for Atlas - with improved JSON parsing"""
  locations = callback_context.session.state.get("env_location_options")

  if isinstance(locations, str):
    logger.warning("Atlas returned string instead of list.\n")
    parsed = _parse_json_string(locations)
    
    if isinstance(parsed, list):
      callback_context.session.state["env_location_options"] = parsed
      locations = parsed
      logger.info("Successfully parsed locations from JSON string.\n")
    elif isinstance(parsed, dict) and "locations" in parsed:
      # Handle case where LLM wraps list in an object
      locations = parsed["locations"]
      if isinstance(locations, list):
        callback_context.session.state["env_location_options"] = locations
        logger.info("Successfully extracted locations from wrapped object.\n")
      else:
        logger.error("Could not parse locations - 'locations' key doesn't contain a list.\n")
        locations = []
    else:
      logger.error("Could not parse locations - not a valid list or wrapped object.\n")
      locations = []
  
  if locations and isinstance(locations, list):
    count = len(locations)
    observability.log_agent_complete("atlas_env_location_agent","env_location_options",success=True)
    logger.info(f"Found {count} location option(s).\n")
    observability.log_state_change("env_location_options","SET",f"{count} location(s)")
  else:
    observability.log_agent_complete("atlas_env_location_agent","env_location_options",success=False)
    logger.warning("No location options or invalid format.\n")
  
  return Content()

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

def format_risk_summary(risk: any, snapshot: any) -> str:
  """Convert risk report"""
  if isinstance(risk, str):
    risk = _parse_json_string(risk)

  if not isinstance(risk, dict):
    return "Invalid data type"
  
  overall = risk.get("overall_risk", "unknown")
  rationale = risk.get("rationale", "")
  
  lines = ["## Weather & Safety Assessment\n"]
  lines.append(f"**Overall Risk Level:** {overall.upper()}\n")

  risk_factors = []
  risk_labels = {"heat_risk": "Heat Risk","cold_risk": "Cold Risk", "wind_risk": "Wind Risk","air_quality_risk": "Air Quality Risk"}
  
  for risk_type, label in risk_labels.items():
    level = risk.get(risk_type, "unknown")
    if level not in ["low", "unknown"]:
      risk_factors.append(f"**{label}:** {level.capitalize()}")
  
  if risk_factors:
    lines.append("\n**Risk Factors:**")
    lines.extend(risk_factors)
  
  if rationale:
    lines.append(f"\n**Analysis:** {rationale}")
  
  if snapshot:
    if isinstance(snapshot, dict) and "location_name" in snapshot:
      name = snapshot.get("location_name", "your location")
      current = snapshot.get("current", {})
      temp = current.get("temperature_c")
      feels = current.get("feels_like_c", temp)
      wind_ms = current.get("wind_speed_10m_ms")
      humidity = current.get("humidity_percent")
      
      lines.append("\n**Current Weather:**")
      if name:
        lines.append(f"- **Location:** {name}")
      if temp is not None:
        if feels is not None and feels != temp:
          lines.append(f"- **Temperature:** {temp}°C (feels like {feels}°C)")
        else:
          lines.append(f"- **Temperature:** {temp}°C")
      if wind_ms is not None:
        lines.append(f"- **Wind:** {wind_ms} m/s")
      if humidity is not None:
        lines.append(f"- **Humidity:** {humidity}%")
    
    elif isinstance(snapshot, list) and snapshot:
      lines.append("\n**Weather by Location:**\n")
      for loc in snapshot:
        if not isinstance(loc, dict):
            continue       
        name = loc.get("location_name", "Unknown")
        current = loc.get("current", {})
        temp = current.get("temperature_c", "?")
        wind = current.get("wind_speed_10m_ms", "?")
        humidity = current.get("humidity_percent", "?")
        
        lines.append(f"**{name}**")
        lines.append(f"  - Temperature: {temp}°C, Wind: {wind} m/s, Humidity: {humidity}%")

  return "\n".join(lines)


def format_weather_summary(snapshot: any) -> str:
  """Convert weather snapshot"""
  
  if isinstance(snapshot, str):
    snapshot = _parse_json_string(snapshot)
  
  if isinstance(snapshot, dict):
    name = snapshot.get("location_name", "your location")
    current = snapshot.get("current", {})
    temp = current.get("temperature_c", "?")
    feels = current.get("feels_like_c", temp)
    wind = current.get("wind_speed_10m_ms", "?")
    humidity = current.get("humidity_percent", "?")
    
    return (
      f"Current weather at {name}:"
      f" -Temperature: {temp}°C (feels like {feels}°C)"
      f" -Wind: {wind} m/s"
      f" -Humidity: {humidity}%"
    )

  elif isinstance(snapshot, list):
    lines = ["Current weather across your locations:\n"]
    for loc in snapshot:
      if not isinstance(loc, dict):
        continue
          
      name = loc.get("location_name", "Unknown")
      current = loc.get("current", {})
      temp = current.get("temperature_c", "?")
      wind = current.get("wind_speed_10m_ms", "?")
      humidity = current.get("humidity_percent", "?")
      
      lines.append(f"--{name}--")
      lines.append(f"| Temperature: {temp}°C | Wind: {wind} m/s | Humidity: {humidity}%\n")
    
    return "\n".join(lines)
  return "Null data.\n"

def Theophrastus_root_callback(*args, **kwargs):

    ctx = kwargs.get("callback_context")
    if ctx is None and len(args) >= 2:
        ctx = args[1]
    if ctx is None:
        return None
    state = ctx.session.state

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