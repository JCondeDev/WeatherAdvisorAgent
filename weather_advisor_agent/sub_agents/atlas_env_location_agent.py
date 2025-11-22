from weather_advisor_agent.config import config

from google.adk.agents import LoopAgent
from google.adk.agents import Agent

from google.adk.tools import FunctionTool
from google.adk.tools import google_search

from weather_advisor_agent.validation_checkers import EnvLocationGeoValidationChecker

from weather_advisor_agent.utils import atlas_location_callback

from weather_advisor_agent.tools import geocode_place_name

from weather_advisor_agent.utils import observability


atlas_env_location_geocode_agent = Agent(
  model=config.worker_model,
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
  model=config.worker_model,
  name="atlas_env_location_discovery_agent",
  description="Finds nearby candidate locations for outdoor activities.",
  instruction="""
You are Atlas-Discovery, responsible for finding real outdoor locations worldwide.

INPUT:
- User's general location (city/region/country) from conversation
- Outdoor activity type (hiking, trail running, cycling, climbing, etc.)

YOUR TASK:
1. Identify the activity type and user's region from the user's request
2. Use google_search tool to find 3-7 REAL, VERIFIABLE locations nearby
3. Focus on: national parks, trails, mountains, forests, nature reserves, popular outdoor destinations

OUTPUT FORMAT (CRITICAL):
You MUST write to session state key `env_location_options` a valid JSON array:

[
  {
    "name": "Golden Gate Park",
    "region_hint": "San Francisco, California, United States",
    "activity": "running"
  },
  {
    "name": "Mount Tamalpais",
    "region_hint": "Marin County, California, United States",
    "activity": "hiking"
  }
]

IMPORTANT RULES:
1. Output ONLY a valid JSON array - no markdown, no code blocks, no explanations
2. Do NOT wrap in an object (don't do {"locations": [...]})
3. All locations MUST come from google_search results - no fabrication
4. Use the EXACT or simplified names from search results
5. Keep names concise but recognizable
6. Include 3-7 locations (more gives user choice)
7. CRITICAL: Include a detailed "region_hint" with city/state/country for better geocoding
   - Good: "Yosemite Valley, California, United States"
   - Bad: "Yosemite" (too vague)
   - Good: "Peak District, Derbyshire, England, UK"
   - Bad: "Peak District" (which country?)

SEARCH STRATEGY:
- Search for: "[activity] near [city/region]" or "best [activity] locations [region]"
- Examples: 
  * "hiking trails near Tokyo Japan"
  * "best cycling routes Paris France"
  * "trail running spots Sydney Australia"
- Look for official park names, popular trails, mountain peaks, nature reserves
- Verify locations are real and suitable for the activity
- Extract city/state/country context from search results

EXAMPLE OUTPUT:
[{"name": "Yosemite Valley", "region_hint": "California, United States", "activity": "hiking"}, {"name": "Sequoia National Park", "region_hint": "California, United States", "activity": "hiking"}]
  """,
  tools=[google_search],
  output_key="env_location_options",
  after_agent_callback=atlas_location_callback,
)


robust_env_location_agent = LoopAgent(
  name="atlas_env_location_loop_agent",
  description="Runs the Atlas location pipeline: discovery → geocode → validation.",
  sub_agents=[
    atlas_env_location_discovery_agent,
    atlas_env_location_geocode_agent,
    EnvLocationGeoValidationChecker(name="location_geo_validation_agent")
  ],
  max_iterations=3
)