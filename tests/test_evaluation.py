import asyncio

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types

from weather_advisor_agent.evaluation import TheophrastusEvaluator
from weather_advisor_agent.sub_agents import (
  robust_env_data_agent,
  robust_env_risk_agent,
  aurora_env_advice_writer
)

async def run_evaluation_test():
  print("Theophrastus AGENT EVALUATION TEST")
  
  session_service = InMemorySessionService()
  await session_service.create_session(
    app_name="Theophrastus_test",
    user_id="test_user",
    session_id="test_session"
  )
  
  data_runner = Runner(
    agent=robust_env_data_agent,
    app_name="Theophrastus_eval",
    session_service=session_service
  )
  
  async for event in data_runner.run_async(
    user_id="eval_user",
    session_id="eval_session",
    new_message=genai_types.Content(
      role="user",
      parts=[genai_types.Part.from_text("Sacramento, California")]
    )
  ):
    pass
  
  session = await session_service.get_session(
    app_name="Theophrastus_eval",
    user_id="eval_user",
    session_id="eval_session"
  )
  
  env_snapshot = session.state.get("env_snapshot")
  eval_result = TheophrastusEvaluator.run_full_evaluation(env_snapshot=env_snapshot,env_risk_report={},advice_markdown="")
  
  print("[TEST] EVALUATION RESULTS:")
  print(f" -Overall Score: {eval_result['overall_score']:.2%}")
  print(f" -Status: {'PASSED' if eval_result['passed'] else 'FAILED'}")
  print("\nDetailed Results:")
  for result in eval_result['results']:
    status = "PASSED" if result['passed'] else "FAILED"
    print(f" -{status} {result['category']}: {result['score']:.2%}")
    print(f"  *{result['details']}")

if __name__ == "__main__":
    asyncio.run(run_evaluation_test())