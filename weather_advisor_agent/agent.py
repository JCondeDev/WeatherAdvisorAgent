import json
import logging
import datetime

from google.genai.types import Content, Part
from google.adk.tools import FunctionTool
from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini

from weather_advisor_agent.config import TheophrastusConfiguration

from weather_advisor_agent.sub_agents import (robust_env_data_agent,
  robust_env_risk_agent,
  robust_env_location_agent
)

from weather_advisor_agent.tools import (save_env_report_to_file,
  store_user_preference,
  get_user_preferences,
  add_to_query_history,
  get_query_history,
  search_query_history,
  store_favorite_location,
  get_favorite_locations,
  remove_favorite_location
)

logger = logging.getLogger(__name__)

def Theophrastus_root_callback(*args, **kwargs):
  snapshot = {}
  ctx = kwargs.get("callback_context")
  if ctx is None and len(args) >= 2:
    ctx = args[1]
  if ctx is None:
    return None
  
  state = ctx.session.state
  current_invocation_id = getattr(ctx, 'invocation_id', None)
  last_advice_invocation = state.get("_last_advice_invocation_id")
  
  advice = state.get("env_advice_markdown")
  if advice and current_invocation_id and current_invocation_id == last_advice_invocation:
    state["_last_advice_invocation_id"] = current_invocation_id
    return Content(parts=[Part(text=advice)])

  for key in ["env_snapshot", "env_location_options", "env_risk_report", "env_advice_markdown"]:
    if key in state:
      snapshot[key] = state[key]
  state["_evaluation_snapshot"] = snapshot

  risk_report = state.get("env_risk_report")
  if risk_report and not advice:
    return None

  locs = state.get("env_location_options")
  if isinstance(locs, str):
    try:
      locs = json.loads(locs)
    except:
      pass
  
  if isinstance(locs, list) and locs and isinstance(locs[0], dict):
    last_msg = state.get("last_user_message", "").lower()
    report_keywords = ["generate", "create", "write", "make", "report", "recommendations", "analysis"]
    
    if not any(keyword in last_msg for keyword in report_keywords):
      lines = [f"- {loc.get('name','Unknown')} — {loc.get('admin1','')}, {loc.get('country','')}" for loc in locs]
      msg = "Here are some options you might consider:\n" + "\n".join(lines)
      return Content(parts=[Part(text=msg)])

  return None

root_agent = LlmAgent(
  name="envi_root_agent",
  model=Gemini(model=TheophrastusConfiguration.root_model,retry_options=TheophrastusConfiguration.retry_config),
  description="Interactive environmental intelligence assistant.",
  instruction=f"""
  You are Theophrastus, an environmental intelligence assistant.

  MEMORY CAPABILITIES:
    - Store user preferences: store_user_preference(tool_context, type, value)
    - Recall preferences: get_user_preferences(tool_context)
    - Track locations queried: add_to_query_history(tool_context, location, activity, weather)
    - Recall past queries: get_query_history(tool_context) or search_query_history(tool_context, term)
    - Save favorites: store_favorite_location(tool_context, location, notes)
    - List favorites: get_favorite_locations(tool_context)

  WHEN TO USE MEMORY:
    - User mentions preference: "I love hiking" → store_user_preference
    - User asks about preferences: "What do I like?" → get_user_preferences
    - After providing weather → add_to_query_history
    - User asks "Where have I asked about?" → get_query_history
    - User says "Save this as favorite" → store_favorite_location

  Your goals:
    - Help users understand weather and environmental conditions.
    - Estimate environmental risks (heat, cold, wind, air quality).
    - Provide safe, practical recommendations.
    - Suggest suitable outdoor activities when relevant.

  You have access to INTERNAL state fields (environmental snapshot, risk report,
  location options, markdown report). These MUST NEVER be mentioned to the user.

  ============================================================
  ================ CRITICAL AGENT SEQUENCE ===================
  ============================================================

  For ANY weather query (including simple ones like "What's the weather?"):
  
  STEP 1: Call robust_env_data_agent
  STEP 2: Call robust_env_risk_agent
  STEP 3: Call aurora_env_advice_writer
  STEP 4: Return nothing (callback handles response)

  This sequence is MANDATORY for:
  - "What's the weather in [place]?"
  - "How is the weather?"
  - "What are the conditions?"
  - "Generate a report"
  - "What's the weather like in those locations?"
  
  ALL weather queries require ALL THREE agents.

  ============================================================
  =================== LOCATION QUERIES =======================
  ============================================================

  For location queries ("find locations", "where to go"):
  
  STEP 1: Call robust_env_location_agent
  STEP 2: Return nothing (callback handles response)

  ============================================================
  ===================== ABSOLUTELY FORBIDDEN =================
  ============================================================

  You MUST NEVER:
  - Output raw JSON
  - Output weather data yourself
  - Output risk assessments yourself
  - Skip aurora_env_advice_writer after calling robust_env_risk_agent
  - Return anything after calling aurora_env_advice_writer

  The callback handles ALL user responses.
  Your ONLY job is to call the right agents in the right order.

  ============================================================
  ========================= EXAMPLES =========================
  ============================================================

  User: "How is the weather in Sacramento?"
  You: Call robust_env_data_agent → robust_env_risk_agent → aurora_env_advice_writer
  You: Return nothing
  Callback: Shows markdown report

  User: "What is the weather like in those locations?"
  You: Call robust_env_data_agent → robust_env_risk_agent → aurora_env_advice_writer
  You: Return nothing
  Callback: Shows markdown report

  User: "Generate a recommendations report"
  You: Call robust_env_data_agent → robust_env_risk_agent → aurora_env_advice_writer
  You: Return nothing
  Callback: Shows markdown report

  User: "Find hiking locations near Mexico City"
  You: Call robust_env_location_agent
  You: Return nothing
  Callback: Shows location list

  ============================================================

  Remember: EVERY weather query needs ALL THREE agents.
  After robust_env_risk_agent, ALWAYS call aurora_env_advice_writer.

  Current date: {datetime.datetime.now().strftime("%Y-%m-%d")}
  """,
  sub_agents=[
    robust_env_location_agent,
    robust_env_data_agent,
    robust_env_risk_agent  
  ],
  tools=[FunctionTool(save_env_report_to_file),
    FunctionTool(store_user_preference),
    FunctionTool(get_user_preferences),
    FunctionTool(add_to_query_history),
    FunctionTool(get_query_history),
    FunctionTool(search_query_history),
    FunctionTool(store_favorite_location),
    FunctionTool(get_favorite_locations),
    FunctionTool(remove_favorite_location)
  ],
  after_agent_callback=Theophrastus_root_callback
)