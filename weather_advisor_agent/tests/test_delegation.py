"""
Aurora Delegation Detection Test

This test checks if Aurora is improperly delegating to other agents
when she should just be reading from state and writing advice.
"""

import asyncio
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types

from weather_advisor_agent.sub_agents import aurora_env_advice_writer

APP_NAME = "envi_app"
USER_ID = "test_user"
SESSION_ID = "test_delegation"


def print_section(title, char="="):
    print(f"\n{char*70}")
    print(f"  {title}")
    print(f"{char*70}")


async def test_delegation_detection():
    """Test if Aurora delegates when she shouldn't"""
    
    print_section("AURORA DELEGATION TEST")
    
    session_service = InMemorySessionService()
    
    # Pre-populate state with ALL the data Aurora needs
    # She should NOT need to call other agents
    initial_state = {
        "env_snapshot": [
            {
                "location_name": "Lago de Tequesquitengo",
                "region": "Morelos, Mexico",
                "temperature_c": 27.0,
                "wind_ms": 3.5,
                "humidity_percent": 65,
                "notes": "Warm and windy"
            },
            {
                "location_name": "Desierto de los Leones",
                "region": "CDMX, México",
                "temperature_c": 16.0,
                "wind_ms": 2.0,
                "humidity_percent": 70,
                "notes": "Cool and cloudy"
            }
        ],
        "env_risk_report": {
            "overall_risk": "medium",
            "heat_risk": "low",
            "cold_risk": "low",
            "wind_risk": "moderate",
            "rationale": "Moderate wind at some locations. Temperature is comfortable."
        },
        "env_activity_profile": {
            "activity": "swim",
            "activity_label": "Swimming",
            "date": "2025-11-22",
            "time_window": "afternoon",
            "group_type": "friends",
            "risk_tolerance": "low",
            "notes": "Dislikes cold water"
        }
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

    # Test with a simple weather query
    query = "What is the weather like in those locations?"
    
    print(f"\nQuery: {query}")
    print("\nExpected behavior:")
    print("  ✅ Aurora reads from env_snapshot (already in state)")
    print("  ✅ Aurora writes natural language to env_advice_markdown")
    print("  ❌ Aurora does NOT call robust_env_data_agent")
    print("  ❌ Aurora does NOT call any other agents")
    
    print_section("EVENT STREAM ANALYSIS", "-")
    
    delegation_detected = False
    function_calls = []
    agent_transfers = []
    
    async for event in runner.run_async(
        user_id=USER_ID,
        session_id=SESSION_ID,
        new_message=genai_types.Content(
            role="user",
            parts=[genai_types.Part.from_text(text=query)]
        )
    ):
        # Check for function calls
        if hasattr(event, 'content') and event.content:
            if hasattr(event.content, 'parts') and event.content.parts:
                for part in event.content.parts:
                    if hasattr(part, 'function_call') and part.function_call:
                        fc = part.function_call
                        function_calls.append(fc)
                        
                        # Check if it's a delegation
                        if hasattr(fc, 'name') and fc.name == 'transfer_to_agent':
                            delegation_detected = True
                            agent_name = fc.args.get('agent_name', 'unknown')
                            agent_transfers.append(agent_name)
                            print(f"\n⚠️  DELEGATION DETECTED!")
                            print(f"    Aurora is calling: {agent_name}")
        
        if hasattr(event, 'is_final_response') and event.is_final_response():
            break
    
    # Get final state
    session = await session_service.get_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=SESSION_ID
    )
    
    print_section("TEST RESULTS", "=")
    
    # Check 1: Was there delegation?
    if delegation_detected:
        print("\n❌ FAIL: Aurora delegated to other agents")
        print(f"   Transferred to: {', '.join(agent_transfers)}")
        print("\n   This is WRONG! Aurora should:")
        print("   - Read from env_snapshot (already in state)")
        print("   - Write natural language to env_advice_markdown")
        print("   - NOT call other agents")
    else:
        print("\n✅ PASS: No delegation detected")
        print("   Aurora correctly stayed in her lane")
    
    # Check 2: Were there any function calls?
    if function_calls:
        print(f"\n⚠️  WARNING: {len(function_calls)} function call(s) detected")
        for fc in function_calls:
            print(f"   - {fc.name if hasattr(fc, 'name') else fc}")
        print("\n   Aurora should NOT call functions - she should only read state")
    else:
        print("\n✅ PASS: No function calls")
        print("   Aurora correctly used only session state")
    
    # Check 3: Did Aurora write output?
    advice = session.state.get("env_advice_markdown")
    if advice:
        print("\n✅ PASS: env_advice_markdown was written")
        
        # Check if it's natural language or JSON
        advice_preview = advice[:200] if len(advice) > 200 else advice
        
        if advice.strip().startswith('{') or advice.strip().startswith('['):
            print("   ❌ But it's JSON (wrong format)!")
            print(f"   Preview: {advice_preview}")
        else:
            print("   ✅ And it's natural language (correct format)")
            print(f"\n   Preview:\n   {advice_preview}...")
    else:
        print("\n❌ FAIL: No env_advice_markdown written")
        print("   Available state keys:", list(session.state.keys()))
    
    print_section("OVERALL VERDICT", "=")
    
    if delegation_detected:
        print("\n❌ TEST FAILED: Delegation Issue Detected")
        print("\nPROBLEM: Aurora is delegating to other agents when she shouldn't.")
        print("\nFIX: Update Aurora's instructions to include:")
        print('  "⚠️ CRITICAL: You NEVER call other agents or fetch data."')
        print('  "You ONLY read from session state and write natural language."')
        print("\nSee: DELEGATION_ISSUE.md for detailed fix instructions")
        print("Use: aurora_fixed.py for the corrected agent definition")
        
    elif function_calls:
        print("\n⚠️  TEST WARNING: Function Calls Detected")
        print("\nAurora shouldn't call functions - she should only read state.")
        print("Check that Aurora has no tools defined in her agent configuration.")
        
    elif not advice:
        print("\n❌ TEST FAILED: No Output Generated")
        print("\nAurora didn't write to env_advice_markdown.")
        print("This might be a different issue - check Aurora's instructions.")
        
    elif advice.strip().startswith('{'):
        print("\n❌ TEST FAILED: JSON Output")
        print("\nAurora wrote JSON instead of natural language.")
        print("See: FIX_JSON_OUTPUT.md for instructions")
        
    else:
        print("\n✅ TEST PASSED: Aurora Behaving Correctly!")
        print("\nAurora:")
        print("  ✅ Did not delegate to other agents")
        print("  ✅ Did not call functions")
        print("  ✅ Wrote natural language output")
        print("  ✅ Used data from session state")
        print("\nGreat job! The issue is fixed.")


async def main():
    try:
        await test_delegation_detection()
    except Exception as e:
        print(f"\n❌ Error during test: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())