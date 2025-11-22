from weather_advisor_agent.config import config

from google.adk.agents import Agent, LoopAgent

from weather_advisor_agent.utils import aether_risk_callback

from weather_advisor_agent.validation_checkers import EnvRiskValidationChecker

from weather_advisor_agent.utils import observability

aether_env_risk_agent = Agent(
  model=config.critic_model,
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
  description="A robust risk analyst that retries if no valid risk report is produced.",
  sub_agents=[aether_env_risk_agent,EnvRiskValidationChecker(name="env_risk_validation_checker")],
  max_iterations=config.max_iterations
)

