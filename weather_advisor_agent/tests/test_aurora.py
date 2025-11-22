import asyncio
import json

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types

from weather_advisor_agent.sub_agents import aurora_env_advice_writer

APP_NAME = "envi_app"
USER_ID = "test_user"
SESSION_ID = "test_aurora_debug"

def print_section(title):
    """Print a formatted section header"""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)

def safe_get_attr(obj, attr_path, default=None):
    """Safely get nested attributes"""
    attrs = attr_path.split('.')
    current = obj
    for attr in attrs:
        if hasattr(current, attr):
            current = getattr(current, attr)
        else:
            return default
    return current

async def debug_query(runner, session_service, query):
    """Send a query with extensive debugging output"""
    print_section(f"QUERY: {query}")
    
    event_count = 0
    
    async for event in runner.run_async(
        user_id=USER_ID,
        session_id=SESSION_ID,
        new_message=genai_types.Content(
            role="user",
            parts=[genai_types.Part.from_text(text=query)]
        )
    ):
        event_count += 1
        print(f"\n--- Event #{event_count} ---")
        
        # Show event type and all attributes
        print(f"Type: {type(event).__name__}")
        print(f"Attributes: {[a for a in dir(event) if not a.startswith('_')]}")
        
        # Try to extract any content
        found_content = False
        
        # Method 1: event.content.parts
        if hasattr(event, 'content') and event.content:
            print(f"\n✓ event.content exists ({type(event.content).__name__})")
            
            if hasattr(event.content, 'parts') and event.content.parts:
                print(f"  ✓ event.content.parts exists (length: {len(event.content.parts)})")
                for i, part in enumerate(event.content.parts):
                    print(f"\n  Part {i}:")
                    print(f"    Type: {type(part).__name__}")
                    
                    if hasattr(part, 'text') and part.text:
                        print(f"    Text: {part.text[:200]}...")
                        found_content = True
                    
                    if hasattr(part, 'function_call'):
                        print(f"    Function Call: {part.function_call}")
                        found_content = True
                    
                    if hasattr(part, 'function_response'):
                        print(f"    Function Response: {part.function_response}")
                        found_content = True
            else:
                print(f"  ✗ event.content.parts is empty or doesn't exist")
        else:
            print(f"\n✗ event.content doesn't exist or is None")
        
        # Method 2: event.text
        if hasattr(event, 'text') and event.text:
            print(f"\n✓ event.text exists:")
            print(f"  {event.text[:200]}...")
            found_content = True
        
        # Method 3: event.data
        if hasattr(event, 'data'):
            print(f"\n✓ event.data exists:")
            print(f"  {str(event.data)[:200]}...")
            found_content = True
        
        # Method 4: Check for JSON-like attributes
        for attr in ['result', 'response', 'output', 'message']:
            if hasattr(event, attr):
                value = getattr(event, attr)
                if value:
                    print(f"\n✓ event.{attr} exists:")
                    print(f"  {str(value)[:200]}...")
                    found_content = True
        
        if not found_content:
            print("\n⚠ No content found in this event")
        
        # Check if final
        if hasattr(event, 'is_final_response'):
            if callable(event.is_final_response):
                is_final = event.is_final_response()
            else:
                is_final = event.is_final_response
                
            if is_final:
                print("\n🏁 FINAL RESPONSE DETECTED")
                
                # Get session state
                session = await session_service.get_session(
                    app_name=APP_NAME,
                    user_id=USER_ID,
                    session_id=SESSION_ID
                )
                
                print_section("SESSION STATE ANALYSIS")
                
                print("\nState Keys:")
                for key in session.state.keys():
                    value = session.state[key]
                    print(f"\n  📦 {key}")
                    print(f"     Type: {type(value).__name__}")
                    
                    # Show value preview
                    if isinstance(value, str):
                        preview = value[:150] + "..." if len(value) > 150 else value
                        print(f"     Content: {preview}")
                    elif isinstance(value, (dict, list)):
                        print(f"     Content: {json.dumps(value, indent=6)[:300]}...")
                    else:
                        print(f"     Value: {value}")
                
                # Show the key outputs
                print_section("FINAL OUTPUT")
                
                advice = session.state.get("env_advice_markdown")
                if advice:
                    print("\n📄 env_advice_markdown:")
                    print(advice)
                else:
                    print("\n❌ No env_advice_markdown found in state")
                
                break

async def main():
    session_service = InMemorySessionService()
    
    # Minimal initial state for testing
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

    print_section("AURORA DEBUG TEST")
    print("\nThis test will show you exactly what Aurora returns and where.")
    print("Watch for JSON vs text responses and state updates.")
    
    # Test with a simple weather query
    await debug_query(
        runner, 
        session_service, 
        "What is the weather like in those locations?"
    )

if __name__ == "__main__":
    asyncio.run(main())