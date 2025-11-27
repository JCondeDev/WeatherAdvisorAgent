import asyncio
import logging
import time
from pathlib import Path

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types

from weather_advisor_agent import Theophrastus_root_agent
from weather_advisor_agent.utils import observability
from weather_advisor_agent.evaluation.evaluator import TheophrastusEvaluator
from weather_advisor_agent.utils import session_cache

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
    # Initialize evaluator
    evaluator = TheophrastusEvaluator(output_dir=Path("weather_advisor_agent/data/evaluations"))
    
    # Setup session
    session_service = InMemorySessionService()
    await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=SESSION_ID
    )
    
    runner = Runner(
        agent=Theophrastus_root_agent,
        app_name=APP_NAME,
        session_service=session_service
    )
    
    # Define test queries with complexity labels
    test_cases = [
        {
            "query": "How is the weather in my city Sacramento, California?",
            "complexity": "simple",
            "description": "Simple weather query for known location"
        },
        {
            "query": "I want to go hiking this weekend near Mexico City. What are some good locations?",
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
    
    # Suppress verbose logging
    logging.getLogger("google_genai.types").setLevel(logging.ERROR)
    
    print("\n" + "="*80)
    print("THEOPHRASTUS AGENT TEST WITH EVALUATION")
    print("="*80 + "\n")
    
    # Run each test case
    for i, test_case in enumerate(test_cases, 1):
        query = test_case["query"]
        complexity = test_case["complexity"]
        description = test_case["description"]
        
        print(f"\n{'='*80}")
        print(f"TEST CASE {i}/{len(test_cases)}")
        print(f"Description: {description}")
        print(f"Complexity: {complexity}")
        print(f"{'='*80}")
        print(f"\n>>> USER: {query}\n")
        
        last_user_facing_text = None
        start_time = time.time()
        
        # FIX: Variable to capture final session state from within the event loop
        captured_session_state = None
        
        # Run the agent with observability tracking
        with observability.trace_operation(
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
                    
                    # Filter out raw environmental snapshots
                    if _looks_like_env_snapshot_json(text):
                        continue
                    
                    last_user_facing_text = text
            
            # FIX: Capture session state immediately after agent run completes
            session = await session_service.get_session(
                app_name=APP_NAME,
                user_id=USER_ID,
                session_id=SESSION_ID
            )
            # Create a deep copy of the state to avoid reference issues
            captured_session_state = dict(session.state)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Display response
        print(">>> THEOPHRASTUS:")
        if last_user_facing_text:
            print(f"{last_user_facing_text}\n")
        else:
            print("[No user-facing text in response]\n")
        
        print(f"⏱️  Response time: {duration:.2f} seconds")
        
        # CRITICAL: Get evaluation data from CACHE, not session state!
        evaluation_state = session_cache.get_evaluation_data(SESSION_ID)
        
        if evaluation_state:
            print(f"✅ Using cache with {len(evaluation_state)} keys: {list(evaluation_state.keys())}")
        else:
            print(f"⚠️  No evaluation snapshot found, using raw state")
            # Fallback to session state (will be empty but keep for debugging)
            session = await session_service.get_session(
                app_name=APP_NAME,
                user_id=USER_ID,
                session_id=SESSION_ID
            )
            evaluation_state = dict(session.state)
        print(f"\n📋 Session state has {len(evaluation_state)} keys: {list(evaluation_state.keys())}")

        print(f"="*80)

        # MANDATORY DEBUG: See what's actually in the captured state
        print(f"\n{'🔍'*40}")
        print("DEBUG: CAPTURED SESSION STATE ANALYSIS")
        print(f"{'🔍'*40}")
        
        if captured_session_state is None:
            print("❌ CRITICAL: captured_session_state is None!")
        elif not captured_session_state:
            print("❌ CRITICAL: captured_session_state is empty dict!")
        else:
            print(f"✓ State captured successfully")
            print(f"✓ Total keys in state: {len(captured_session_state)}")
            print(f"\n📋 All keys in state: {list(captured_session_state.keys())}\n")
            
            # Check each required key
            required_keys = ["env_snapshot", "env_risk_report", "env_advice_markdown"]
            for key in required_keys:
                if key in captured_session_state:
                    value = captured_session_state[key]
                    value_type = type(value).__name__
                    
                    if isinstance(value, dict):
                        if len(value) > 0:
                            print(f"✓ {key}: PRESENT - dict with {len(value)} keys")
                            print(f"  Keys: {list(value.keys())[:5]}")  # Show first 5 keys
                        else:
                            print(f"⚠️  {key}: PRESENT but EMPTY dict")
                    elif isinstance(value, list):
                        if len(value) > 0:
                            print(f"✓ {key}: PRESENT - list with {len(value)} items")
                        else:
                            print(f"⚠️  {key}: PRESENT but EMPTY list")
                    elif isinstance(value, str):
                        if len(value) > 0:
                            print(f"✓ {key}: PRESENT - string with {len(value)} chars")
                        else:
                            print(f"⚠️  {key}: PRESENT but EMPTY string")
                    else:
                        print(f"✓ {key}: PRESENT - {value_type}")
                else:
                    print(f"❌ {key}: MISSING from state")
            
            # Show ALL keys and their types
            print(f"\n📝 Complete state inventory:")
            for key, value in captured_session_state.items():
                value_type = type(value).__name__
                if isinstance(value, (dict, list)):
                    size = len(value)
                    print(f"   {key}: {value_type} (size: {size})")
                elif isinstance(value, str):
                    print(f"   {key}: {value_type} (length: {len(value)})")
                else:
                    print(f"   {key}: {value_type}")
        
        print(f"{'🔍'*40}\n")
        
        # Run evaluation with captured state
        print(f"{'─'*80}")
        print("RUNNING EVALUATION...")
        print(f"{'─'*80}")
        
        evaluation_report = evaluator.run_full_evaluation(
            session_id=f"{SESSION_ID}_test_{i}",
            session_state=evaluation_state,  # Use cache data!
            duration_seconds=duration,
            complexity=complexity
        )
        
        # Display evaluation results
        evaluator.print_evaluation_report(evaluation_report)
        
        # Save evaluation
        eval_file = evaluator.save_evaluation(evaluation_report)
        print(f"📄 Evaluation saved to: {eval_file}")
        
        # Short pause between test cases
        if i < len(test_cases):
            await asyncio.sleep(1)
    
    # Print overall statistics
    print("\n" + "="*80)
    print("OVERALL TEST STATISTICS")
    print("="*80 + "\n")
    
    stats = evaluator.get_evaluation_statistics()
    print(f"Total Test Cases: {stats.get('total_evaluations', 0)}")
    print(f"Passed: {stats.get('passed', 0)}/{stats.get('total_evaluations', 0)}")
    print(f"Pass Rate: {stats.get('pass_rate', 0):.1%}")
    print(f"Average Score: {stats.get('average_score', 0):.1%}")
    
    # Only print category performance if it exists
    if 'category_statistics' in stats:
        print("\n" + "-"*80)
        print("CATEGORY PERFORMANCE:")
        print("-"*80)
        
        for category, cat_stats in stats['category_statistics'].items():
            print(f"\n{category.replace('_', ' ').title()}:")
            print(f"  Average Score: {cat_stats['avg_score']:.1%}")
            print(f"  Pass Rate: {cat_stats['pass_rate']:.1%}")
    
    # Export observability data
    print("\n" + "="*80)
    print("EXPORTING OBSERVABILITY DATA")
    print("="*80 + "\n")
    
    print("METRICS & TRACES:")
    observability.print_metrics_summary()
    
    metrics_file = Path("weather_advisor_agent/data/observability_metrics_test.json")
    observability.export_metrics(str(metrics_file))

    traces_file = Path("weather_advisor_agent/data/observability_traces_test.json")
    observability.export_traces(str(traces_file))
    
    print("\n" + "="*80)
    print("✅ TEST RUN COMPLETE")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())