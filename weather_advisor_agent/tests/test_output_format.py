"""
Aurora Output Format Validator

This test checks whether Aurora is outputting JSON in places where
natural language should be used (like env_advice_markdown).
"""

import asyncio
import json
import re
from typing import Dict, Any, Tuple

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types

from weather_advisor_agent.sub_agents import aurora_env_advice_writer

APP_NAME = "envi_app"
USER_ID = "test_user"
SESSION_ID = "test_output_format"


def validate_json_structure(text: str) -> Tuple[bool, str]:
    """Check if text is JSON"""
    text = text.strip()
    
    # Try to parse as JSON
    try:
        json.loads(text)
        return True, "Valid JSON object"
    except:
        pass
    
    # Check for JSON patterns
    if text.startswith('{') and text.endswith('}'):
        return True, "Looks like JSON object (malformed)"
    
    if text.startswith('[') and text.endswith(']'):
        return True, "Looks like JSON array"
    
    # Check for common JSON field patterns
    json_field_patterns = [
        r'"recommendation"\s*:',
        r'"advice"\s*:',
        r'"risk_level"\s*:',
        r'"location"\s*:',
        r'"reasoning"\s*:',
        r'"conditions"\s*:',
    ]
    
    for pattern in json_field_patterns:
        if re.search(pattern, text):
            return True, f"Contains JSON field pattern: {pattern}"
    
    return False, "Not JSON"


def validate_natural_language(text: str) -> Tuple[bool, str]:
    """Check if text is natural language markdown/text"""
    
    # Good indicators of natural language
    markdown_indicators = [
        r'^#\s+',           # Headers
        r'\*\*.*\*\*',      # Bold
        r'\*.*\*',          # Italic
        r'^-\s+',           # Lists
        r'^\d+\.\s+',       # Numbered lists
    ]
    
    natural_language_indicators = [
        r'\b(you|your|I|we)\b',  # Personal pronouns
        r'\b(should|would|could|might)\b',  # Modal verbs
        r'[.!?]\s+[A-Z]',  # Sentences
        r'\b(the|a|an)\b',  # Articles
    ]
    
    has_markdown = any(re.search(p, text, re.MULTILINE) for p in markdown_indicators)
    has_natural_language = any(re.search(p, text, re.IGNORECASE) for p in natural_language_indicators)
    
    if has_markdown:
        return True, "Contains markdown formatting"
    
    if has_natural_language:
        return True, "Contains natural language patterns"
    
    # Check if it's mostly alphanumeric text with spaces
    words = text.split()
    if len(words) >= 10:
        return True, "Has multiple words (likely natural language)"
    
    return False, "Doesn't look like natural language"


def print_section(title, char="="):
    print(f"\n{char*70}")
    print(f"  {title}")
    print(f"{char*70}")


def print_validation_result(is_valid: bool, message: str, severity: str = "info"):
    """Print a formatted validation result"""
    if severity == "error":
        icon = "❌"
    elif severity == "warning":
        icon = "⚠️ "
    elif severity == "success":
        icon = "✅"
    else:
        icon = "ℹ️ "
    
    status = "PASS" if is_valid else "FAIL"
    print(f"{icon} {status}: {message}")


async def test_advice_output_format():
    """Test that Aurora outputs natural language, not JSON, in env_advice_markdown"""
    
    print_section("AURORA OUTPUT FORMAT VALIDATION TEST")
    
    session_service = InMemorySessionService()
    
    # Set up initial state
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
            "max_travel_hours": 2.0,
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

    # Test 1: Ask Aurora to generate advice
    print_section("TEST 1: Generate Environmental Advice")
    
    query = "Generate a friendly environmental advice report for my swimming plans."
    print(f"\nQuery: {query}\n")

    async for event in runner.run_async(
        user_id=USER_ID,
        session_id=SESSION_ID,
        new_message=genai_types.Content(
            role="user",
            parts=[genai_types.Part.from_text(text=query)]
        )
    ):
        if hasattr(event, 'is_final_response') and event.is_final_response():
            break

    # Get the session state
    session = await session_service.get_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=SESSION_ID
    )

    print_section("VALIDATION RESULTS", "-")

    # Check env_advice_markdown
    advice = session.state.get("env_advice_markdown")
    
    if not advice:
        print_validation_result(False, "No env_advice_markdown found in state", "error")
        print("\nAvailable state keys:")
        for key in session.state.keys():
            print(f"  - {key}")
        return

    print("\n📄 env_advice_markdown content:")
    print("-" * 70)
    print(advice[:500] + "..." if len(advice) > 500 else advice)
    print("-" * 70)

    # Validate format
    is_json, json_msg = validate_json_structure(advice)
    is_natural, natural_msg = validate_natural_language(advice)

    print_section("FORMAT ANALYSIS", "-")

    if is_json:
        print_validation_result(False, f"Output is JSON: {json_msg}", "error")
        print("\n🔧 FIX NEEDED:")
        print("   Aurora's instructions should specify:")
        print("   'Write env_advice_markdown in natural language markdown,")
        print("    NOT as a JSON object.'")
    else:
        print_validation_result(True, "Output is NOT JSON", "success")

    if is_natural:
        print_validation_result(True, f"Output is natural language: {natural_msg}", "success")
    else:
        print_validation_result(False, f"Output doesn't look like natural language: {natural_msg}", "warning")

    # Overall verdict
    print_section("OVERALL VERDICT", "=")

    if is_json:
        print("\n❌ FAILED: Aurora is outputting JSON in env_advice_markdown")
        print("\nThis is the problem you need to fix!")
        print("\nRecommended actions:")
        print("1. Run: python diagnose_aurora.py")
        print("2. Check Aurora's agent instructions")
        print("3. Look for 'output as JSON' or 'return JSON object' phrases")
        print("4. Update instructions to specify natural language output")
        print("5. Re-run this test to verify the fix")
        
    elif not is_natural:
        print("\n⚠️  WARNING: Output is not JSON, but also doesn't look like natural language")
        print("\nThis might be plain text without markdown formatting.")
        print("Consider adding markdown formatting for better readability.")
        
    else:
        print("\n✅ SUCCESS: Aurora is outputting natural language!")
        print("\nThe output looks correct - it's natural language with")
        print("markdown formatting, not JSON.")

    # Check internal state is still JSON (this is correct)
    print_section("INTERNAL STATE FORMAT CHECK", "-")
    
    snapshot = session.state.get("env_snapshot")
    risk_report = session.state.get("env_risk_report")
    
    if isinstance(snapshot, list):
        print_validation_result(True, "env_snapshot is a list (correct)", "success")
    else:
        print_validation_result(False, f"env_snapshot is {type(snapshot)}", "warning")
    
    if isinstance(risk_report, dict):
        print_validation_result(True, "env_risk_report is a dict (correct)", "success")
    else:
        print_validation_result(False, f"env_risk_report is {type(risk_report)}", "warning")

    print("\n" + "="*70)


async def main():
    try:
        await test_advice_output_format()
    except Exception as e:
        print(f"\n❌ Error during test: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())