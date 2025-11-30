from typing import Dict, Any, Optional
from datetime import datetime

def store_user_preference(tool_context,preference_type: str,value: str) -> Dict[str, Any]:
  """Store a user preference in session state (persists across sessions)."""
  preferences = tool_context.state.get("user:preferences", {})
  preferences[preference_type] = {"value": value,"timestamp": datetime.now().isoformat()}
  tool_context.state["user:preferences"] = preferences
  
  return {
    "status": "success",
    "message": f"Stored {preference_type}: {value}",
    "scope": "user (available in all future sessions)"
  }

def get_user_preferences(tool_context) -> Dict[str, Any]:
  """Retrieve all user preferences from session state."""
  preferences = tool_context.state.get("user:preferences", {})
  
  if not preferences:
    return {
      "status": "empty",
      "message": "No preferences stored yet",
      "preferences": {}
    }
  
  return {
    "status": "success",
    "preferences": preferences,
    "count": len(preferences)
  }

def add_to_query_history(tool_context,location: str,activity: Optional[str] = None, weather_summary: Optional[str] = None  ) -> Dict[str, Any]:
  """Add a location query to the history (persists across sessions)."""
  history = tool_context.state.get("user:query_history", [])
  
  query = {
    "timestamp": datetime.now().isoformat(),
    "location": location,
    "activity": activity,
    "weather_summary": weather_summary
  }
  history.append(query)
  history = history[-20:]
  tool_context.state["user:query_history"] = history
  
  return {
    "status": "success",
    "message": f"Added {location} to query history",
    "total_queries": len(history)
  }


def get_query_history(tool_context,limit: int = 10) -> Dict[str, Any]:
  """Get recent location queries (from all previous sessions)."""
  history = tool_context.state.get("user:query_history", [])
  
  if not history:
    return {
      "status": "empty",
      "message": "No query history yet",
      "queries": []
    }
  
  recent = history[-limit:] if limit > 0 else history
  
  return {
    "status": "success",
    "queries": recent,
    "count": len(recent),
    "total_in_history": len(history)
  }


def search_query_history(tool_context,search_term: str) -> Dict[str, Any]:
  """Search query history for a specific location or activity."""
  history = tool_context.state.get("user:query_history", [])
  
  if not history:
    return {
      "status": "empty",
      "message": "No query history yet",
      "matches": []
    }
  
  search_lower = search_term.lower()
  matches = []
  for query in history:
    if (search_lower in query.get("location", "").lower() or
      search_lower in query.get("activity", "").lower() or
      search_lower in query.get("weather_summary", "").lower()):
      matches.append(query)
  
  return {
    "status": "success",
    "matches": matches,
    "count": len(matches),
    "search_term": search_term
  }

def store_favorite_location(tool_context,location_name: str,notes: Optional[str] = None) -> Dict[str, Any]:
  """Store a favorite location (persists across sessions)."""
  favorites = tool_context.state.get("user:favorite_locations", {})
  
  favorites[location_name] = {"notes": notes,"added": datetime.now().isoformat()}
  tool_context.state["user:favorite_locations"] = favorites
  
  return {
    "status": "success",
    "message": f"Added {location_name} to favorites",
    "total_favorites": len(favorites)
  }


def get_favorite_locations(tool_context) -> Dict[str, Any]:
  """Get all favorite locations (from all previous sessions)."""
  favorites = tool_context.state.get("user:favorite_locations", {})
  
  if not favorites:
    return {
      "status": "empty",
      "message": "No favorite locations yet",
      "favorites": {}
    }
  
  return {
    "status": "success",
    "favorites": favorites,
    "count": len(favorites)
  }


def remove_favorite_location(tool_context,location_name: str) -> Dict[str, Any]:
  """Remove a location from favorites."""
  favorites = tool_context.state.get("user:favorite_locations", {})
  
  if location_name not in favorites:
    return {
      "status": "not_found",
      "message": f"{location_name} is not in favorites"
    }
  
  del favorites[location_name]
  tool_context.state["user:favorite_locations"] = favorites
  
  return {
    "status": "success",
    "message": f"Removed {location_name} from favorites",
    "remaining_favorites": len(favorites)
  }