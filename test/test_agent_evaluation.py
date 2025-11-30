import asyncio
import logging
import time
from pathlib import Path

from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.genai import types as genai_types

from weather_advisor_agent.agent import root_agent
from weather_advisor_agent.utils import Theophrastus_Observability
from weather_advisor_agent.utils import TheophrastusEvaluator
from weather_advisor_agent.utils import session_cache

DATA_DIR = Path("weather_advisor_agent/data")
DATA_DIR.mkdir(parents=True, exist_ok=True)

db_url = f"sqlite:///{DATA_DIR / 'theophrastus_sessions.db'}"
session_service = InMemorySessionService()

APP_NAME = "Theophrastus_app"
USER_ID = "test_user"
SESSION_ID = "test_Theophrastus"

def _looks_like_env_snapshot_json(text: str) -> bool:
  """Filter out raw environmental snapshot JSON from display"""
  if not text:
    return False
  
  t = text.strip()
  if not t.startswith("{"):
    return False
  
  suspicious_keys = ['"current"', '"hourly"', '"location"', '"raw"']
  return any(k in t for k in suspicious_keys)


async def main():
  evaluator = TheophrastusEvaluator(output_dir=Path("weather_advisor_agent/data/evaluations"))

  await session_service.create_session(
    app_name=APP_NAME,
    user_id=USER_ID,
    session_id=SESSION_ID
  )

  runner = Runner(
    agent=root_agent,
    app_name=APP_NAME,
    session_service=session_service
  )

  test_cases = [
    {
      "query": "I love hiking and camping. Can you remember that for me?",
      "complexity": "simple",
      "description": "Store user preferences - should call store_user_preference"
    },
    {
      "query": "What outdoor activities do I enjoy?",
      "complexity": "simple",
      "description": "Recall preferences - should call get_user_preferences"
    },
    {
      "query": "How is the weather in my city Nezahualcoyotl, Mexico State?",
      "complexity": "simple",
      "description": "Simple weather query for known location"
    },
    {
      "query": "I want to go hiking this weekend near Madrid. What are some good locations?",
      "complexity": "medium",
      "description": "Location search with activity context"
    },
    {
      "query": "What is the weather like in those locations?",
      "complexity": "medium",
      "description": "Weather data for multiple locations"
    },
    {
      "query": "Generate a recommendations report.",
      "complexity": "complex",
      "description": "Full report generation with risk analysis"
    }
  ]
  
  logging.getLogger("google_genai.types").setLevel(logging.ERROR)
  
  print("\n" + "="*80)
  print("THEOPHRASTUS AGENT TEST WITH EVALUATION")
  print("="*80 + "\n")
  
  for i, test_case in enumerate(test_cases, 1):
    query = test_case["query"]
    complexity = test_case["complexity"]
    description = test_case["description"]
    
    print(f"\n{'='*80}\n")
    print(f"TEST CASE {i}/{len(test_cases)}")
    print(f"Description: {description}")
    print(f"Complexity: {complexity}")
    print(f"\n{'='*80}")
    print(f"\n>>> USER: {query}\n")
    print(f"{'='*80}")
    
    last_user_facing_text = None
    start_time = time.time()

    captured_session_state = None
    with Theophrastus_Observability.trace_operation(
      f"test_case_{i}",
      attributes={
        "query": query[:50],
        "complexity": complexity,
        "description": description
      }
    ):
      async for event in runner.run_async(
        user_id=USER_ID,
        session_id=SESSION_ID,
        new_message=genai_types.Content(
          role="user",
          parts=[genai_types.Part.from_text(text=query)]
        )
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
      
      session = await session_service.get_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=SESSION_ID
      )
      captured_session_state = dict(session.state)
    
    end_time = time.time()
    duration = end_time - start_time
    
    print(f"\n{"="*80}\n")
    if last_user_facing_text:
        print(f">>> THEOPHRASTUS: {last_user_facing_text}")
    else:
      print(">>> THEOPHRASTUS: [No user-facing text in response]\n")
    print(f"\n{"="*80}\n")
    
    print(f"Response time: {duration:.2f} seconds")
    
    evaluation_state = session_cache.get_evaluation_data(SESSION_ID)
    
    print(f"="*80)
    print("RUNNING EVALUATION...")
    print(f"="*80)
    
    evaluation_report = evaluator.run_full_evaluation(
      session_id=f"{SESSION_ID}_test_{i}",
      session_state=evaluation_state,
      duration_seconds=duration,
      complexity=complexity
    )
    
    evaluator.print_evaluation_report(evaluation_report)
    eval_file = evaluator.save_evaluation(evaluation_report)
    print(f"Evaluation saved to: {eval_file}.")
    
    if i < len(test_cases):
      await asyncio.sleep(1)
  
  print("\n" + "="*80)
  print("OVERALL TEST STATISTICS")
  print("="*80 + "\n")
  
  stats = evaluator.get_evaluation_statistics()
  print(f"Total Test Cases: {stats.get('total_evaluations', 0)}")
  print(f"Passed: {stats.get('passed', 0)}/{stats.get('total_evaluations', 0)}")
  print(f"Pass Rate: {stats.get('pass_rate', 0):.1%}")
  print(f"Average Score: {stats.get('average_score', 0):.1%}")
  
  if 'category_statistics' in stats:
    print("\n" + "="*80)
    print("CATEGORY PERFORMANCE:")
    
    for category, cat_stats in stats['category_statistics'].items():
      print(f"\n{category.replace('_', ' ').title()}:")
      print(f"  Average Score: {cat_stats['avg_score']:.1%}.")
      print(f"  Pass Rate: {cat_stats['pass_rate']:.1%}.")
  
  print("\n" + "="*80)
  print("OBSERVABILITY DATA")
  print("="*80 + "\n")
  
  Theophrastus_Observability.print_metrics_summary()
  
  Theophrastus_Observability.export_metrics("test")

  Theophrastus_Observability.export_traces("test")
  
  print("\n" + "="*80)
  print("SESSION MEMORY INSPECTION")
  print("="*80 + "\n")
  
  final_session = await session_service.get_session(
    app_name=APP_NAME,
    user_id=USER_ID,
    session_id=SESSION_ID
  )
  
  # Show user-scoped memory (persists across sessions with user: prefix)
  print("User Memory (would persist with DatabaseSessionService):")
  user_memory = {k: v for k, v in final_session.state.items() if k.startswith("user:")}
  if user_memory:
    for key, value in user_memory.items():
      print(f"\n  {key}:")
      if isinstance(value, dict):
        for sub_key, sub_value in value.items():
          print(f"    {sub_key}: {str(sub_value)[:100]}...")
      elif isinstance(value, list):
        print(f"    {len(value)} items")
        for idx, item in enumerate(value[:3]):  # Show first 3
          print(f"      [{idx}]: {str(item)[:80]}...")
      else:
        print(f"    {str(value)[:100]}...")
  else:
    print("  (No user memory stored - memory tools were not called)")
  
  # Show all state keys for debugging
  print("\n" + "="*80)
  print("All Session State Keys:")
  print("="*80)
  for key in final_session.state.keys():
    print(f"  - {key}")

  print("\n" + "="*80)
  print("TEST RUN COMPLETE")
  print("="*80)

if __name__ == "__main__":
  asyncio.run(main())