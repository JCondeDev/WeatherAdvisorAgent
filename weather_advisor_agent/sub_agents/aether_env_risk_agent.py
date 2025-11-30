import json
import logging

from google.adk.agents import Agent, LoopAgent

from weather_advisor_agent.config import TheophrastusConfiguration

from weather_advisor_agent.utils import Theophrastus_Observability, session_cache

from weather_advisor_agent.utils.validation_checkers import EnvRiskValidationChecker

from weather_advisor_agent.sub_agents.aurora_env_advice_writer import aurora_env_advice_writer

logger = logging.getLogger(__name__)

def aether_risk_callback(*args, **kwargs):
  """Callback for aether risk agent - stores risk assessment"""
  ctx = kwargs.get("callback_context")
  if ctx is None and len(args) >= 2:
    ctx = args[1]
  if ctx is None:
    return None
  
  state = ctx.session.state
  risk_report = state.get("env_risk_report")
  
  if isinstance(risk_report, str):
    logger.warning("Aether returned string instead of dict.")
    
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
      logger.error(f"Could not parse risk report JSON")
      return None
  
  if isinstance(risk_report, dict):
    state["env_risk_report"] = risk_report
    session_cache.store_evaluation_data(ctx.session.id, {"env_risk_report": risk_report})
    
    Theophrastus_Observability.log_agent_complete("aether_env_risk_agent", "env_risk_report", success=True)
    logger.info("Risk assessment completed.")

    return None
  else:
    logger.warning("No risk report or invalid format.")
    Theophrastus_Observability.log_agent_complete("aether_env_risk_agent", "env_risk_report", success=False)
    
    return None

aether_env_risk_agent = Agent(
  model=TheophrastusConfiguration.critic_model,
  name="aether_env_risk_agent",
  description="Analyzes environmental data and produces a structured risk report.",
  instruction="""
  You are Aether, an environmental risk analyst.

  INPUT:
  - You will receive an environmental snapshot stored in the `env_snapshot`
    state key. This is your ONLY data source.

  YOUR TASK:
  - Estimate qualitative risk levels:
    * heat_risk
    * cold_risk
    * wind_risk
    * air_quality_risk
    * overall_risk

    Use values such as "low", "moderate", "high", or "unknown".

  - Provide a short natural-language rationale string.

  - Package everything into a JSON-like structure, for example:
    {
      "heat_risk": "...",
      "cold_risk": "...",
      "wind_risk": "...",
      "air_quality_risk": "...",
      "overall_risk": "...",
      "rationale": "..."
    }

  - Your final model output will be stored as-is into the `env_risk_report`
    state key by the framework.

  VERY IMPORTANT:
  - You NEVER speak to the end user.
  - You MUST NOT include any explanations or prose outside of that JSON-like
    structure.
  - Do NOT wrap the JSON in a code block.
  - If information is insufficient, set a field to "unknown" and explain why
    in the rationale.

  CONSTRAINTS:
  - Be conservative in risk estimates.
  - Never invent numeric values; only classify what is present or clearly implied
    in `env_snapshot`.
  """,
  output_key="env_risk_report",
  after_agent_callback=aether_risk_callback
)

robust_env_risk_agent = LoopAgent(
  name="robust_env_risk_agent",
  description="Risk analysis pipeline that automatically generates advice",
  sub_agents=[
    aether_env_risk_agent,
    EnvRiskValidationChecker(name="env_risk_validation_checker"),
    aurora_env_advice_writer
  ],
  max_iterations=1
)