import asyncio
import logging
from pathlib import Path

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types

from weather_advisor_agent import envi_root_agent
from weather_advisor_agent.utils import observability

logging.basicConfig(level=logging.DEBUG,format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

APP_NAME = "envi_test"
USER_ID = "test_user"
SESSION_ID = "test_session"

async def test_data_fetching_with_observability():
  """Test the data fetching pipeline with full observability."""
  print("[TEST] SINGLE LOCATION")
  
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
  
  with observability.trace_operation("fetch_weather_data",attributes={"location": "Sacramento, California", "test": True}) as span:
    query = "Please fetch the current environmental snapshot for Sacramento, California, USA."
    
    print(f"\nUSER: {query}\n")
    print("EXECUTION LOG:\n")
    
    async for event in runner.run_async(
        user_id=USER_ID,
        session_id=SESSION_ID,
        new_message=genai_types.Content(
          role="user",
          parts=[genai_types.Part.from_text(text=query)]
        ),
    ):
      pass
    
    if span:
      span.attributes["completed"] = True

  final_session = await session_service.get_session(
    app_name=APP_NAME,
    user_id=USER_ID,
    session_id=SESSION_ID
  )
  
  env_snapshot = final_session.state.get("env_snapshot")

  if env_snapshot:
      print("[TEST] ENVIROMENTAL SNAPSHOT")
      if isinstance(env_snapshot, dict):
        current = env_snapshot.get("current", {})
        temp = current.get("temperature_c")
        wind = current.get("wind_speed_10m_ms")
        humidity = current.get("relative_humidity_percent")
        
        print(f" -Temperature: {temp}°C")
        print(f" -Wind Speed: {wind} m/s")
        print(f" -Humidity: {humidity}%")
      else:
        print("[TEST] Retrieved data in unexpected format")
  else:
    print("[TEST] No environmental snapshot in state")
  
  print("[TEST] METRICS SUMMARY")
  
  observability.print_metrics_summary()
  
  print("[TEST] TRACES SUMMARY")
  
  trace_summary = observability.get_trace_summary()
  print(f" -Total Traces: {trace_summary.get('total_traces', 0)}")
  print(f" -Successful: {trace_summary.get('successful', 0)}")
  print(f" -Failed: {trace_summary.get('failed', 0)}")
  print(f" -Avg Duration: {trace_summary.get('avg_duration_ms', 0):.2f}ms")
  print(f" -Max Duration: {trace_summary.get('max_duration_ms', 0):.2f}ms")
  
  metrics_file = Path("weather_advisor_agent/data/observability_metrics_test.json")
  observability.export_metrics(str(metrics_file))
  if metrics_file.exists():
    size_kb = metrics_file.stat().st_size / 1024
    print(f"\n[TEST] METRICS SAVED:")
    print(f" -File: {metrics_file}")
    print(f" -Size: {size_kb:.2f} KB")
  else:
    print(f"\n[TEST] Memory file not created")
  
  traces_file = Path("weather_advisor_agent/data/observability_traces_test.json")
  observability.export_traces(str(traces_file))
  if traces_file.exists():
    size_kb = traces_file.stat().st_size / 1024
    print(f"\n[TEST] TRACES SAVED:")
    print(f" -File: {traces_file}")
    print(f" -Size: {size_kb:.2f} KB")
  else:
    print(f"\n[TEST] Memory file not created")
  
  return {
    "metrics": observability.get_metrics_summary(),
    "traces": trace_summary,
    "snapshot_retrieved": env_snapshot is not None
  }


async def test_multiple_locations():
  """Test with multiple locations to generate more interesting metrics."""
  print("\n[TEST] Multiple Locations")
  
  session_service = InMemorySessionService()
  
  locations = ["Sacramento, California","Mexico City, Mexico","Berlin, Germany"]
  
  for location in locations:
    print(f"\n[TEST] Location: {location}")
    
    session_id = f"test_{location.replace(' ', '_').replace(',', '')}"
    
    await session_service.create_session(
      app_name=APP_NAME,
      user_id=USER_ID,
      session_id=session_id
    )
    
    runner = Runner(
      agent=envi_root_agent,
      app_name=APP_NAME,
      session_service=session_service
    )
    
    with observability.trace_operation(f"fetch_{location}"):
      async for event in runner.run_async(
        user_id=USER_ID,
        session_id=session_id,
        new_message=genai_types.Content(
          role="user",
          parts=[genai_types.Part.from_text(
            text=f"Fetch weather for {location}"
          )],
        ),
      ):
        pass
  
  print("[TEST] FINAL METRICS")
  
  observability.print_metrics_summary()

async def main():
    """Main test runner"""
    print("ENVI OBSERVABILITY TEST")
    print("-Logging, Tracing & Metrics-")
       
    try:
      await test_data_fetching_with_observability()
      
      await test_multiple_locations()
    except Exception as e:
      print(f"ERROR: {e}")
      import traceback
      traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())