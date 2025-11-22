import asyncio

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types

from weather_advisor_agent.sub_agents import robust_env_data_agent
from weather_advisor_agent.utils import observability

APP_NAME = "envi_app"
USER_ID = "test_user"
SESSION_ID = "test_zephyr"

async def main():
  session_service = InMemorySessionService()

  await session_service.create_session(
    app_name=APP_NAME,
    user_id=USER_ID,
    session_id=SESSION_ID
  )
  runner = Runner(
    agent=robust_env_data_agent,
    app_name=APP_NAME,
    session_service=session_service
  )

  query = "Please fetch the current environmental snapshot for Sacramento, California, USA."

  print("\n=== QUERY ===\n")
  print(f">>> {query}\n")

  with observability.trace_operation(f"user_query",attributes={"query": query[:50]}):
    async for event in runner.run_async(
      user_id=USER_ID,
      session_id=SESSION_ID,
      new_message=genai_types.Content(
        role="user",
        parts=[genai_types.Part.from_text(text=query)]
      )
    ):
      if event.content and event.content.parts:
        print("\n=== ZEPHYR RESPONSE ===\n")
        for part in event.content.parts:
          if getattr(part, "function_call", None):
            print(f"FUNC CALL: {part.function_call}\n")
          if getattr(part, "function_response", None):
            print(f"FUNC RESP: { part.function_response}\n")
          if getattr(part, "text", None):
            print(f"TEXT:{part.text}\n")

if __name__ == "__main__":
    asyncio.run(main())
