from ..config import config
from google.adk.agents import Agent, LoopAgent
from ..utils.agent_utils import suppress_output_callback
from ..validation_checkers import EnvRiskValidationChecker

aether_env_risk_agent = Agent (
  model=config.critic_model,
  name="aether_env_risk_agent",
  description="Analyzes environmental data and produces a structured risk report.",
  instruction="""
  You are Aether, an environmental risk analyst.

  You will receive an environmental snapshot stored in the `env_snapshot`
  state key. Based on that information, you must:

  - Estimate qualitative risk levels: `heat_risk`, `cold_risk`, `wind_risk`,
    `air_quality_risk`, and `overall_risk` with values like "low",
    "moderate", or "high".
  - Provide a short natural language rationale.
  - Store the result as a JSON-like structure in the `env_risk_report`
    state key.

  Be conservative: when in doubt, mark risk as 'unknown' and explain why.
  Never invent numbers that are not present in the snapshot.
  """,
  output_key="env_risk_report",
  after_agent_callback=suppress_output_callback
)

robust_env_risk_agent = LoopAgent (
  name="robust_env_risk_agent",
  description="A robust risk analyst that retries if no valid risk report is produced.",
  sub_agents=[aether_env_risk_agent,EnvRiskValidationChecker(name="env_risk_validation_checker")],
  max_iterations=config.max_iterations,
  after_agent_callback=suppress_output_callback
)
