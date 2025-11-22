import asyncio
import logging
from pathlib import Path

from google.adk.runners import Runner

from google.adk.sessions import InMemorySessionService

from google.genai import types as genai_types

from weather_advisor_agent import envi_root_agent
from weather_advisor_agent.utils import observability

APP_NAME = "envi_app"
USER_ID = "test_user"
SESSION_ID = "test_envi"

def _looks_like_env_snapshot_json(text: str) -> bool:
  if not text:
    return False
  
  t = text.strip()

  if not t.startswith("{"):
    return False

  suspicious_keys = ['"current"', '"hourly"', '"location"', '"raw"']
  return any(k in t for k in suspicious_keys)


async def main():
  session_service = InMemorySessionService()
  await session_service.create_session(
    app_name=APP_NAME,
    user_id=USER_ID,
    session_id=SESSION_ID
  )
  runner = Runner(
    agent=envi_root_agent,
    app_name=APP_NAME,
    session_service=session_service
  )

  test = 3
  
  if test == 1:
    queries = [
      "I would like to know the current weather in my area.",
      "I am currently around Sacramento, California. What's the weather like?",
      "How is humidity today?",
      "How's the temperature outside?"
    ]
  elif test == 2:
    queries = [
      "I would like to know the current weather in my area.",
      "I am currently around Sacramento, California.",
      "Generate a recommendations report.",
      "Save it to reports/Envi_recomendations.md"
    ]
  elif test == 3:
    queries = [
      "I want to go hiking this weekend near Mexico City. What are some good locations?",
      "What is the weather like in those locations?",
      "Generate a recommendations report.",
      "Save it to reports/Envi_recomendations.md"
    ]

  logging.getLogger("google_genai.types").setLevel(logging.ERROR)

  for i, query in enumerate(queries, 1):
    print("=== USER INPUT ===")
    print(f"\n>>> {query}\n")
    last_user_facing_text = None

    with observability.trace_operation(f"user_query_{i}",attributes={"query": query[:50]}):
      async for event in runner.run_async(
        user_id=USER_ID,
        session_id=SESSION_ID,
        new_message=genai_types.Content(role="user",parts=[genai_types.Part.from_text(text=query)])
      ):
        if not event.is_final_response():
          continue
        content = getattr(event, "content", None)
        if not content:
          continue
        parts = getattr(content, "parts", None)
        if not parts:
          continue
        for part in parts:
          text = getattr(part, "text", None)
          if not text:
            continue
          if _looks_like_env_snapshot_json(text):
            continue

          last_user_facing_text = text

    print("=== ENVI RESPONSE ===")
    if last_user_facing_text:
      if len(last_user_facing_text) > 1000:
        print(f"{last_user_facing_text[:1000]} \n... (truncated)\n")
      else:
        print(f"{last_user_facing_text}\n")
    else:
      print("[No user-facing text in response]\n")

  print("METRICS & TRACES:")
  observability.print_metrics_summary()

  metrics_file = Path("weather_advisor_agent/data/observability_metrics_test.json")
  observability.export_metrics(str(metrics_file))

  traces_file = Path("weather_advisor_agent/data/observability_traces_test.json")
  observability.export_traces(str(traces_file))

if __name__ == "__main__":
    asyncio.run(main())