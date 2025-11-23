from pathlib import Path

from weather_advisor_agent.memory import memory_bank

def test_user_preferences():
  print("\n[TEST] USER PREFERENCES")

  user_id = "user_test_01"
  
  memory_bank.store_user_preference(
    user_id=user_id,
    activities=["hiking", "cycling"],
    risk_tolerance="low",
    favorite_location={
      "name": "Sacramento, California",
      "coordinates": {"latitude": 38.58, "longitude": -121.49}
    },
    preferred_weather={
      "min_temp_c": 15,
      "max_wind_ms": 5,
      "prefers_sunny": True
    }
  )
  
  print(f"\n[TEST] UPDATING USER PREFERENCES TO SWIMMING")
  memory_bank.store_user_preference(
    user_id=user_id,
    activities=["swimming"],
    favorite_location={
      "name": "Lake Tahoe",
      "coordinates": {"latitude": 39.09, "longitude": -120.03}
    }
  )
  
  pref = memory_bank.get_user_preference(user_id)

  if pref:
    print(f"\n[TEST] SHOWING USER PREFERENCES")
    print(f" -Activities: {', '.join(pref.preferred_activities)}")
    print(f" -Risk Tolerance: {pref.risk_tolerance}")
    print(f" -Favorite Locations: {len(pref.favorite_locations)}")
    for loc in pref.favorite_locations:
      print(f"  *{loc['name']}")
    print(f" -Weather Prefs: {pref.preferred_weather}")
    print(f" -Last Updated: {pref.last_updated}")
  else:
    print(f"No preferences found")


def test_query_history():
  print("\n[TEST] QUERY HISTORY")

  user_id = "user_test_01"
  
  queries = [
    ("Sacramento, California", "hiking", {"temp": 18, "wind": 3}),
    ("Lake Tahoe", "swimming", {"temp": 22, "wind": 2}),
    ("San Francisco", "cycling", {"temp": 16, "wind": 8}),
    ("Sacramento, California", "hiking", {"temp": 20, "wind": 4})
  ]
  
  print(f"\n[TEST] ADDING {len(queries)} QUERIES")
  for location, activity, conditions in queries:
    memory_bank.add_query_history(
      user_id=user_id,
      location=location,
      activity=activity,
      conditions=conditions
    )
    print(f" *{location} ({activity})\n")

  print(f"\n[TEST] SHOWING QUERY HISTORY:")
  history = memory_bank.get_query_history(user_id, limit=5)
  for i, query in enumerate(history, 1):
    print(f"{i}. {query.location} - {query.activity}")
    print(f" -Conditions: {query.conditions}")
    print(f" -Timestamp: {query.timestamp}")
  
  print(f"\n[TEST] SHOWING RECENT LOCATIONS:")
  recent = memory_bank.get_recent_locations(user_id, limit=3)
  for i, loc in enumerate(recent, 1):
    print(f"{i}. {loc}")


def test_location_memories():
  print("\n[TEST] LOCATION MEMORIES")

  locations = [
    ("Sacramento, California", {"latitude": 38.58, "longitude": -121.49}, {"temp": 19, "wind": 3.5}),
    ("Lake Tahoe", {"latitude": 39.09, "longitude": -120.03}, {"temp": 22, "wind": 2.0}),
    ("San Francisco", {"latitude": 37.77, "longitude": -122.41}, {"temp": 16, "wind": 7.0})
  ]
  
  print(f"\n[TEST] STORING MEMORIES")
  for name, coords, conditions in locations:
    memory_bank.store_location_memory(
      name=name,
      coordinates=coords,
      conditions=conditions,
      notes=f"Queried by user multiple times"
    )
    memory_bank.store_location_memory(name, coords)
    print(f" *{name}\n")
  
  print(f"\n[TEST] MOST FREQUENT LOCATIONS")
  frequent = memory_bank.get_frequent_locations(limit=3)
  for i, loc_mem in enumerate(frequent, 1):
    print(f"{i}. {loc_mem.name}")
    print(f" -Query Count: {loc_mem.query_count}")
    print(f" -Coordinates: {loc_mem.coordinates}")
    print(f" -Typical Conditions: {loc_mem.typical_conditions}")


def test_user_insights():
  print("\n[TEST] USER INSIGHTS")

  user_id = "user_test_01"
  
  insights = memory_bank.get_user_insights(user_id)
  
  print(f"\n[TEST] {user_id} INSIGHTS")
  print(f" -Has Preferences: {insights['has_preferences']}")
  print(f" -Preferred Activities: {', '.join(insights['preferred_activities'])}")
  print(f" -Risk Tolerance: {insights['risk_tolerance']}")
  print(f" -Total Queries: {insights['total_queries']}")
  print(f" -Recent Locations: {', '.join(insights['recent_locations'][:3])}")
  print(f" -Activity Pattern:")
  for activity, count in insights['activity_pattern'].items():
    print(f"  *{activity}: {count} queries")
  print(f" -Favorite Locations: {insights['favorite_locations_count']}")


def test_persistence():
  print("\n[TEST] PERSISTANCE")

  summary = memory_bank.export_summary()
  
  print(f"\n[TEST] Memory Bank:")
  print(f" -Total Users: {summary['total_users']}")
  print(f" -Total Queries: {summary['total_queries']}")
  print(f" -Total Locations: {summary['total_locations']}")
  print(f" -Users: {', '.join(summary['users'])}")
  print(f" -Most Queried: {', '.join(summary['most_queried_locations'])}")
  
  storage_path = Path("TESTS/Theophrastus_memory_bank_test.json")
  if storage_path.exists():
    size_kb = storage_path.stat().st_size / 1024
    print(f"\n[TEST] Memory persisted to disk:")
    print(f" -File: {storage_path}")
    print(f" -Size: {size_kb:.2f} KB")
  else:
    print(f"\n[TEST] Memory file not created")


def main():
  print("\nTheophrastus MEMORY TEST")
  try:
    test_user_preferences()
    test_query_history()
    test_location_memories()
    test_user_insights()
    test_persistence()
  except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()

if __name__ == "__main__":
    main()