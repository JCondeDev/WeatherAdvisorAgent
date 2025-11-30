import json
import logging

from typing import AsyncGenerator

from google.genai.types import Content,Part
from google.adk.agents import BaseAgent, Agent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.agents.callback_context import CallbackContext
from google.adk.events import Event, EventActions

from weather_advisor_agent.utils import Theophrastus_Observability


logger = logging.getLogger(__name__)

class EnvSnapshotValidationChecker(BaseAgent):
  """Validates environmental snapshot data stored in session state."""
  async def _run_async_impl(self, context: InvocationContext) -> AsyncGenerator[Event, None]:
    Theophrastus_Observability.log_agent_start("EnvSnapshotValidationChecker", {"session_id": context.session.id})
    snapshot = context.session.state.get("env_snapshot")
    
    if isinstance(snapshot, str):
      try:
        snapshot = json.loads(snapshot)
        logger.debug("Parsed env_snapshot from JSON string")
      except json.JSONDecodeError as e:
        logger.error(f"Failed to parse env_snapshot JSON: {e}")
        snapshot = None
    
    def is_valid_snapshot(snap: dict) -> bool:
      if not isinstance(snap, dict):
        return False
      
      current = snap.get("current") or {}
      if not isinstance(current, dict):
        return False
      
      temp = current.get("temperature_c")
      feels_like = current.get("apparent_temperature_c")
      wind = current.get("wind_speed_10m_ms")
      humidity = current.get("relative_humidity_percent")
      
      has_data = any(v is not None for v in (temp, feels_like, wind, humidity))
      
      if has_data:
        logger.debug(f"Valid snapshot: temp={temp}, feels={feels_like}, wind={wind}, humidity={humidity}")
      
      return has_data
    
    is_valid = False
    validation_details = ""
    
    if isinstance(snapshot, dict):
      is_valid = is_valid_snapshot(snapshot)
      if is_valid:
        logger.info("Single location snapshot is valid.")
      else:
        logger.warning("Single location snapshot is invalid.")
    elif isinstance(snapshot, list):
      if not snapshot:
        logger.warning("Empty snapshot list.")
      else:
        valid_snapshots = [s for s in snapshot if isinstance(s, dict) and is_valid_snapshot(s)]
        valid_count = len(valid_snapshots)
        total_count = len(snapshot)
        is_valid = valid_count > 0
        logger.info(f"{valid_count}/{total_count} snapshots valid")
    else:
      logger.error(f"Unexpected snapshot type: {type(snapshot).__name__}.")
    
    Theophrastus_Observability.log_validation("EnvSnapshotValidationChecker", passed=is_valid, details=validation_details)
    Theophrastus_Observability.log_agent_complete("EnvSnapshotValidationChecker", "env_snapshot", success=is_valid)
    
    yield Event(author=self.name, actions=EventActions(escalate=is_valid))


class EnvRiskValidationChecker(BaseAgent):
  """Validates environmental risk assessment data stored in session state."""
  async def _run_async_impl(self,context: InvocationContext) -> AsyncGenerator[Event, None]:
    Theophrastus_Observability.log_agent_start("EnvRiskValidationChecker",{"session_id": context.session.id})
    risk_report = context.session.state.get("env_risk_report")
    
    is_valid = False
    validation_details = ""
    
    if not risk_report:
      logger.warning("No risk report found in state.")
    else:
      if isinstance(risk_report, str):
        try:
          risk_report = json.loads(risk_report)
          logger.debug("Parsed risk_report from JSON string.")
        except json.JSONDecodeError as e:
          logger.error(f"Failed to parse risk_report JSON: {e}.")
          validation_details = f"Invalid JSON: {str(e)}."
          Theophrastus_Observability.log_validation("EnvRiskValidationChecker",passed=False,details=validation_details)
          Theophrastus_Observability.log_agent_complete("EnvRiskValidationChecker","env_risk_report",success=False)

          yield Event(author=self.name, actions=EventActions(escalate=False))
          return
      
      if not isinstance(risk_report, dict):
        logger.error(f"risk_report is not a dict after parsing: {type(risk_report)}")
        validation_details = f"Expected dict, got {type(risk_report).__name__}"
      else:
        valid_levels = {"low", "moderate", "medium", "high", "unknown"}
        has_overall = "overall_risk" in risk_report
        overall_valid = (has_overall and risk_report["overall_risk"] in valid_levels)
        
        if overall_valid:
          is_valid = True
          logger.info(f"Risk report valid, overall_risk={risk_report['overall_risk']}")
        else:
          logger.warning("Risk report missing or invalid overall_risk")
          validation_details = "Missing or invalid overall_risk field"
    
    Theophrastus_Observability.log_validation("EnvRiskValidationChecker",passed=is_valid,details=validation_details)
    Theophrastus_Observability.log_agent_complete("EnvRiskValidationChecker","env_risk_report",success=is_valid)
    
    yield Event(author=self.name, actions=EventActions())



class EnvLocationGeoValidationChecker(BaseAgent):
  """Validates and cleans geographic location data stored in session state."""
  async def _run_async_impl(self, context: InvocationContext) -> AsyncGenerator[Event, None]:
    Theophrastus_Observability.log_agent_start("EnvLocationGeoValidationChecker", {"session_id": context.session.id})
    
    state = context.session.state
    locations = state.get("env_location_options")
    validation_details = ""
    
    if not locations:
      logger.info("No location options found - passing through to allow upstream handling")
      validation_details = "No locations to validate - empty list"
      Theophrastus_Observability.log_validation("EnvLocationGeoValidationChecker", passed=True, details=validation_details)
      
      yield Event(author=self.name, actions=EventActions(escalate=True))
      return
    
    if not isinstance(locations, list):
      logger.warning(f"Locations is not a list (type: {type(locations).__name__}), converting to empty list")
      locations = []
    
    cleaned = []
    seen_coords = set()
    invalid_count = 0
    
    for loc in locations:
      if not isinstance(loc, dict):
        logger.debug(f"Skipping non-dict location: {type(loc).__name__}")
        invalid_count += 1
        continue
      
      lat = loc.get("latitude")
      lon = loc.get("longitude")
      name = loc.get("name")
      
      if lat is None or lon is None:
        logger.debug(f"Skipping location without coordinates: {name}")
        invalid_count += 1
        continue
      
      try:
        lat_f = float(lat)
        lon_f = float(lon)

        if not (-90 <= lat_f <= 90) or not (-180 <= lon_f <= 180):
          logger.warning(f"Invalid coordinates for {name}: lat={lat_f}, lon={lon_f}")
          invalid_count += 1
          continue    
      except (TypeError, ValueError) as e:
        logger.warning(f"Could not parse coordinates for {name}: {e}")
        invalid_count += 1
        continue

      key = (round(lat_f, 4), round(lon_f, 4))

      if key in seen_coords:
        logger.debug(f"Duplicate coordinates detected for {name}, skipping")
        invalid_count += 1
        continue
      seen_coords.add(key)
      
      cleaned.append({
        "name": name or "unknown",
        "latitude": lat_f,
        "longitude": lon_f,
        "country": loc.get("country"),
        "admin1": loc.get("admin1"),
        "admin2": loc.get("admin2"),
        "activity": loc.get("activity"),
        "source": loc.get("source", "atlas+geocode")
      })
    
    state["env_location_options"] = cleaned
    
    validation_details = (f"Cleaned location list: {len(cleaned)} valid, {invalid_count} invalid/duplicate")
    
    passed = len(cleaned) > 0

    Theophrastus_Observability.log_validation("EnvLocationGeoValidationChecker", passed=passed, details=validation_details)
    Theophrastus_Observability.log_agent_complete("EnvLocationGeoValidationChecker", "env_location_options", success=passed)

    yield Event(author=self.name, actions=EventActions(escalate=passed))

#Deprecated functionality, keeping for documentation and test purposes.
#Prevented Aurora malfunction, current configuration allows it to work.
#Future implementation as a separate sub_agent to help aurora to devilver the advice report.
class EnvForceAuroraChecker(Agent):
  """Enforces that the Aurora advice generation agent runs when needed."""
  def __init__(self, **args):
    if "name" in args:
      args.pop("name")

    super().__init__(
      name="force_aurora_checker",
      model="gemini-2.0-flash-lite",
      description="Enforces Aurora execution - blocks until Aurora runs",
      instruction="""
      You are a validation checker that ENFORCES Aurora execution.
      Check the session state:
      - If env_risk_report exists but env_advice_markdown is missing or empty:
        Return AURORA_REQUIRED
      - If advice markdown exists:
        Return PASS
      """,
      after_agent_callback=self.enforce_aurora_callback,
      output_key="env_advice_check",**args
    )

  @staticmethod
  def enforce_aurora_callback(callback_context: CallbackContext) -> Content:
    state = callback_context.session.state
    
    has_risk = state.get("env_risk_report") is not None
    advice = state.get("env_advice_markdown")
    has_advice = advice is not None and len(str(advice)) > 50

    if has_risk and not has_advice:
      logger.warning("FORCING AURORA RESPONSE:\n")
      state["_aurora_required"] = True
      return Content(parts=[Part(text="AURORA_REQUIRED")])

    state["_aurora_required"] = False
    return Content(parts=[Part(text="PASS")])