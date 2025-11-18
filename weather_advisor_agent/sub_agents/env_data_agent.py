from google.adk.agents import Agent, LoopAgent
from google.adk.tools import FunctionTool

from ..config import config
from ..agent_utils import suppress_output_callback
from ..tools import fetch_env_snapshot_from_open_meteo
from ..validation_checkers import EnvSnapshotValidationChecker

env_data_agent = Agent(
    model=config.worker_model,
    name="env_data_agent",
    description="Fetches live environmental data (weather & basic air metrics) for a given location.",
    instruction="""
    You are Zephyr, a data-gathering specialist for environmental intelligence.
    Your job is to call the `fetch_env_snapshot_from_open_meteo` tool, given
    latitude and longitude, and store the resulting JSON snapshot in the
    `env_snapshot` state key.

    - Always ask the user for their location if it's not provided.
    - Prefer using numeric latitude/longitude if available.
    - Do not try to 'guess' or fabricate weather data; always use the tool.
    """,
    tools=[FunctionTool(fetch_env_snapshot_from_open_meteo)],
    output_key="env_snapshot",
    after_agent_callback=suppress_output_callback)

# LoopAgent que reintenta si la validación falla
loop_env_data_agent = LoopAgent(
    name="robust_env_data_agent",
    description="A robust environmental data fetcher that retries if it fails.",
    sub_agents=[env_data_agent,EnvSnapshotValidationChecker(name="env_snapshot_validation_checker")],
    max_iterations=config.max_iterations,
    after_agent_callback=suppress_output_callback)
