import asyncio
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types
from weather_advisor_agent.sub_agents import aurora_env_advice_writer

APP_NAME = "enviro_app"
USER_ID = "test_user"
SESSION_ID = "test_aurora"

async def main():
  session_service = InMemorySessionService()

  initial_state = {
    "env_snapshot": [
      {
        "location_name": "Lago de Tequesquitengo",
        "region": "Morelos, Mexico",
        "temperature_c": 27.0,
        "wind_ms": 3.5,
        "notes": "Warm and windy"
      },
      {
        "location_name": "Desierto de los Leones",
        "region": "CDMX, México",
        "temperature_c": 16.0,
        "wind_ms": 2.0,
        "notes": "Cool and cloudy"
      }
    ],
    "env_risk_report": [
      {"location_name": "Lago de Tequesquitengo", "overall_risk": "medium"},
      {"location_name": "Desierto de los Leones", "overall_risk": "low"}
    ],
    "env_activity_profile": {
      "activity": "swim",
      "activity_label": "swim",
      "date": "2025-11-22",
      "time_window": "afternoon",
      "group_type": "friends",
      "risk_tolerance": "low",
      "max_travel_hours": 2.0,
      "notes": "Dislikes cold water"
    },
    "env_location_options": [
      {
        "name": "Lago de Tequesquitengo",
        "country": "Mexico",
        "admin1": "Morelos",
        "latitude": 18.6,
        "longitude": -99.3,
        "activity": "swim"
      },
      {
        "name": "Desierto de los Leones",
        "country": "Mexico",
        "admin1": "Ciudad de Mexico",
        "latitude": 19.3,
        "longitude": -99.3,
        "activity": "hike"
      }
    ]
  }

  await session_service.create_session(
    app_name=APP_NAME,
    user_id=USER_ID,
    session_id=SESSION_ID,
    state=initial_state,
  )

  runner = Runner(
    agent=aurora_env_advice_writer,
    app_name=APP_NAME,
    session_service=session_service,
  )

  query = "Generate the final report."

  async for event in runner.run_async(
    user_id=USER_ID,
    session_id=SESSION_ID,
    new_message=genai_types.Content(
      role="user",
      parts=[genai_types.Part.from_text(text=query)]
    )
  ):
    if event.is_final_response() and event.content:
      print("=== AURORA OUTPUT ===")
      for part in event.content.parts:
        if getattr(part, "text", None):
          print(part.text)

if __name__ == "__main__":
  asyncio.run(main())
