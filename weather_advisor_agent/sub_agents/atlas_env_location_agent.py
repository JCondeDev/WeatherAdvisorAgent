import json
import logging

from google.adk.agents import Agent, LoopAgent
from google.adk.tools import FunctionTool, google_search

from weather_advisor_agent.config import TheophrastusConfiguration

from weather_advisor_agent.tools import geocode_place_name

from weather_advisor_agent.utils import Theophrastus_Observability, session_cache

from weather_advisor_agent.utils.validation_checkers import EnvLocationGeoValidationChecker

logger = logging.getLogger(__name__)

def atlas_location_callback(*args, **kwargs):
  """Callback for atlas location agent - stores location options"""
  ctx = kwargs.get("callback_context")
  if ctx is None and len(args) >= 2:
    ctx = args[1]
  if ctx is None:
    return None
  
  state = ctx.session.state
  locations = state.get("env_location_options")
  
  if isinstance(locations, str):
    logger.warning("Atlas returned string instead of list.")
    
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
    state["env_location_options"] = locations
    session_cache.store_evaluation_data(ctx.session.id,{"env_location_options": locations})
    
    Theophrastus_Observability.log_agent_complete("atlas_env_location_agent", "env_location_options", success=True)
    logger.info(f"Found {len(locations)} location option(s).")

    return None
  else:
    logger.warning("No location options or invalid format.")
    Theophrastus_Observability.log_agent_complete("atlas_env_location_agent", "env_location_options", success=False)
    
    return None

atlas_env_location_geocode_agent = Agent(
  model=TheophrastusConfiguration.mapper_model,
  name="atlas_env_location_geocode_agent",
  description="Converts discovered location names into coordinates.",
  instruction="""
  You are Atlas-Geocoder, responsible for converting location names to precise coordinates.

  INPUT:
  - Read `env_location_options` from session state
  - Each entry has: {"name": "...", "region_hint": "...", "activity": "..."}

  YOUR TASK:
  For each location, call the geocode_place_name tool to obtain:
  - latitude (float)
  - longitude (float) 
  - country (string)
  - admin1 (state/province)

  IMPORTANT: Pass the "region_hint" parameter to geocode_place_name to improve accuracy.
  Example: geocode_place_name(place_name="Golden Gate Park", region_hint="San Francisco, California")

  OUTPUT FORMAT (CRITICAL):
  You MUST write to `env_location_options` a valid JSON array like this:

  [
    {
      "name": "Location Name",
      "latitude": 19.1234,
      "longitude": -99.5678,
      "country": "United States",
      "admin1": "California",
      "activity": "hiking",
      "source": "discovery+geocode"
    }
  ]

  IMPORTANT RULES:
  1. Output ONLY a valid JSON array - no markdown, no explanations, no code blocks
  2. Do NOT wrap the array in an object (don't do {"locations": [...]})
  3. Use ONLY real geocoding results - never guess coordinates
  4. If geocoding fails for a location, skip it (don't include it in output)
  5. Ensure latitude is between -90 and 90, longitude between -180 and 180
  6. Preserve the "activity" field from the input
  7. ALWAYS pass region_hint to geocode_place_name for better accuracy

  EXAMPLE OUTPUT:
  [{"name": "Yosemite Valley", "latitude": 37.7455, "longitude": -119.5936, "country": "United States", "admin1": "California", "activity": "hiking", "source": "discovery+geocode"}]
  """,
  tools=[FunctionTool(geocode_place_name)],
  output_key="env_location_options",
  after_agent_callback=atlas_location_callback
)


atlas_env_location_discovery_agent = Agent(
  model=TheophrastusConfiguration.mapper_model,
  name="atlas_env_location_discovery_agent",
  description="Finds nearby candidate locations for outdoor activities.",
  instruction="""
  You are Atlas-Discovery. Your job is to discover REAL outdoor locations near the user's requested area.

  IMPORTANT:
  You MUST extract two things from the user's message:
  1. ACTIVITY (one word: hiking, running, cycling, climbing, etc.)
  2. REGION (a city, state, country, or place)

  CRITICAL EXTRACTION RULES:
  - Parse the activity explicitly from the user message.
  - Parse the region explicitly from the user message.
  - If the user says "near Mexico City", extract: region="Mexico City"
  - If the user does not explicitly give a region, ask the LLM context for the last known location.

  SEARCH RULES:
  You MUST call google_search EXACTLY ONCE using this structured query format:

  "[activity] trails near [region] national park mountains forest"

  Examples:
  "hiking trails near Mexico City national park mountains forest"
  "cycling routes near Berlin national park forest"
  "running trails near Tokyo mountains forest"

  PRODUCTION RULES:
  1. From the google_search results, extract 3-7 REAL locations.
  2. For each location, produce:
    {
      "name": "Location Name",
      "region_hint": "City/State/Country",
      "activity": "<activity>"
    }
  3. Output ONLY a JSON array. No markdown, no commentary.

  IMPORTANT:
  - If google_search returns no results, output an EMPTY JSON ARRAY.
  - DO NOT fabricate locations.
  - DO NOT use fallback lists.
  - DO NOT guess coordinates (geocoder will handle that next).
  """,
  tools=[google_search],
  output_key="env_location_options",
  after_agent_callback=atlas_location_callback
)

robust_env_location_agent = LoopAgent(
  name="robust_env_location_agent",
  description="Runs the Atlas location pipeline: discovery → geocode → validation.",
  sub_agents=[atlas_env_location_discovery_agent,atlas_env_location_geocode_agent,EnvLocationGeoValidationChecker(name="location_geo_validation_agent")],
  max_iterations=2
)