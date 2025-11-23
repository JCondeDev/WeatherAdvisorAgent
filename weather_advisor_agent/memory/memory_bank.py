import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict, field

logger = logging.getLogger(__name__)

@dataclass
class UserPreference:
  """User preferences for environmental recommendations"""
  user_id: str
  preferred_activities: List[str] = field(default_factory=list)
  risk_tolerance: str = "medium" 
  favorite_locations: List[Dict[str, Any]] = field(default_factory=list)
  preferred_weather: Dict[str, Any] = field(default_factory=dict)
  last_updated: str = ""
  
  def __post_init__(self):
    if not self.last_updated:
      self.last_updated = datetime.now().isoformat()

@dataclass
class QueryHistory:
  """Historical query record"""
  timestamp: str
  location: str
  activity: Optional[str] = None
  conditions: Dict[str, Any] = field(default_factory=dict)
  user_feedback: Optional[str] = None 


@dataclass
class LocationMemory:
  """Memory about specific locations"""
  name: str
  coordinates: Dict[str, float]
  query_count: int = 0
  last_queried: str = ""
  typical_conditions: Dict[str, Any] = field(default_factory=dict)
  notes: str = ""


class TheophrastusMemoryBank:
  """Persistent memory storage for Theophrastus agent system."""
  def __init__(self, storage_path: Optional[str] = None):
    """Initialize Memory Bank"""
    self.storage_path = storage_path
    self.user_preferences: Dict[str, UserPreference] = {}
    self.query_history: Dict[str, List[QueryHistory]] = {}
    self.location_memories: Dict[str, LocationMemory] = {}
    
    if storage_path:
      self._load_from_disk()
    
    logger.info(f"TheophrastusMemoryBank initialized (storage: {storage_path or 'memory-only'})")
  
  def store_user_preference(
    self,
    user_id: str,
    activities: Optional[List[str]] = None,
    risk_tolerance: Optional[str] = None,
    favorite_location: Optional[Dict[str, Any]] = None,
    preferred_weather: Optional[Dict[str, Any]] = None
  ):
    """Store or update user preferences"""
    if user_id not in self.user_preferences:
      self.user_preferences[user_id] = UserPreference(user_id=user_id)
    pref = self.user_preferences[user_id]
    
    if activities:
      existing = set(pref.preferred_activities)
      existing.update(activities)
      pref.preferred_activities = list(existing)
    
    if risk_tolerance:
      pref.risk_tolerance = risk_tolerance
    
    if favorite_location:
      existing_names = {loc.get("name") for loc in pref.favorite_locations}
      if favorite_location.get("name") not in existing_names:
        pref.favorite_locations.append(favorite_location)
    
    if preferred_weather:
      pref.preferred_weather.update(preferred_weather)
    
    pref.last_updated = datetime.now().isoformat()
    logger.info(f"Updated preferences for {user_id}.")
    
    if self.storage_path:
      self._save_to_disk()
  
  def get_user_preference(self, user_id: str) -> Optional[UserPreference]:
    """Retrieve user preferences"""
    return self.user_preferences.get(user_id)

  def add_query_history(
    self,
    user_id: str,
    location: str,
    activity: Optional[str] = None,
    conditions: Optional[Dict[str, Any]] = None,
    feedback: Optional[str] = None
  ):
    """Add a query to history"""
    if user_id not in self.query_history:
      self.query_history[user_id] = []
    
    self.query_history[user_id].append(QueryHistory(
      timestamp=datetime.now().isoformat(),
      location=location,
      activity=activity,
      conditions=conditions or {},
      user_feedback=feedback
    ))
    
    self.query_history[user_id] = self.query_history[user_id][-100:]
    
    logger.info(f"Added query to history({user_id}: {location}).\n")
    
    if self.storage_path:
      self._save_to_disk()
  
  def get_query_history(self,user_id: str,limit: Optional[int] = None) -> List[QueryHistory]:
    """Get query history"""
    history = self.query_history.get(user_id, [])
    history_reversed = list(reversed(history))
    
    if limit:
      return history_reversed[:limit]
    return history_reversed
  
  def get_recent_locations(self, user_id: str, limit: int = 5) -> List[str]:
    """Get recent queried locations"""
    history = self.query_history.get(user_id, [])
    locations = [q.location for q in history]
    
    seen = set()
    unique_locations = []
    for loc in reversed(locations):
      if loc not in seen:
        seen.add(loc)
        unique_locations.append(loc)
    
    return unique_locations[:limit]
  
  def store_location_memory(
    self,
    name: str,
    coordinates: Dict[str, float],
    conditions: Optional[Dict[str, Any]] = None,
    notes: Optional[str] = None
  ):
    """Store memory about a location."""
    if name not in self.location_memories:
      self.location_memories[name] = LocationMemory(name=name,coordinates=coordinates)
    
    memo = self.location_memories[name]
    memo.query_count += 1
    memo.last_queried = datetime.now().isoformat()
    
    if conditions:
      if not memo.typical_conditions:
        memo.typical_conditions = conditions
      else:
        for key, value in conditions.items():
            if isinstance(value, (int, float)) and key in memo.typical_conditions:
              existing = memo.typical_conditions[key]
              memo.typical_conditions[key] = (existing + value) / 2
            else:
              memo.typical_conditions[key] = value
    if notes:
        memo.notes = notes
    
    logger.info(f"Updated memory for {name}.\n")
    
    if self.storage_path:
      self._save_to_disk()
  
  def get_location_memory(self, name: str) -> Optional[LocationMemory]:
    """Retrieve memory about a location"""
    return self.location_memories.get(name)
  
  def get_frequent_locations(self, limit: int = 5) -> List[LocationMemory]:
    """Get most frequently queried locations"""
    sorted_locations = sorted(self.location_memories.values(),key=lambda x: x.query_count,reverse=True)
    return sorted_locations[:limit]

  def get_user_insights(self, user_id: str) -> Dict[str, Any]:
    """Get insights"""
    pref = self.get_user_preference(user_id)
    history = self.get_query_history(user_id)
    recent_locations = self.get_recent_locations(user_id)
    
    activity_counts = {}
    for query in history:
      if query.activity:
        activity_counts[query.activity] = activity_counts.get(query.activity, 0) + 1
  
    return {
      "user_id": user_id,
      "has_preferences": pref is not None,
      "preferred_activities": pref.preferred_activities if pref else [],
      "risk_tolerance": pref.risk_tolerance if pref else "unknown",
      "total_queries": len(history),
      "recent_locations": recent_locations,
      "activity_pattern": activity_counts,
      "favorite_locations_count": len(pref.favorite_locations) if pref else 0
    }
  
  def _save_to_disk(self):
    """Save to JSON file."""
    if not self.storage_path:
      return
    
    try:
      data = {
        "preferences": {k: asdict(v) for k, v in self.user_preferences.items()},
        "history": {k: [asdict(q) for q in v] for k, v in self.query_history.items()},
        "locations": {k: asdict(v) for k, v in self.location_memories.items()}
      }
      
      Path(self.storage_path).parent.mkdir(parents=True, exist_ok=True)
      
      with open(self.storage_path, 'w') as f:
        json.dump(data, f, indent=2)
      
      logger.debug(f"Saved memory bank to {self.storage_path}.\n")
    
    except Exception as e:
      logger.error(f"Failed to save memory bank: {e}.\n")
  
  def _load_from_disk(self):
    """Load from JSON file"""
    if not self.storage_path or not Path(self.storage_path).exists():
      return
    
    try:
      with open(self.storage_path, 'r') as f:
        data = json.load(f)
      
      for user_id, pref_data in data.get("preferences", {}).items():
        self.user_preferences[user_id] = UserPreference(**pref_data)
      
      for user_id, history_data in data.get("history", {}).items():
        self.query_history[user_id] = [QueryHistory(**q) for q in history_data]
      
      for name, loc_data in data.get("locations", {}).items():
        self.location_memories[name] = LocationMemory(**loc_data)
      
      logger.info(f"Loaded memory bank from {self.storage_path}.")
  
    except Exception as e:
      logger.error(f"Failed to load memory bank: {e}.\n")
  
  def export_summary(self) -> Dict[str, Any]:
    """Export summary statistics"""
    return {
      "total_users": len(self.user_preferences),
      "total_queries": sum(len(h) for h in self.query_history.values()),
      "total_locations": len(self.location_memories),
      "users": list(self.user_preferences.keys()),
      "most_queried_locations": [
        loc.name for loc in self.get_frequent_locations(5)
      ]
    }

TheophrastusMemory = TheophrastusMemoryBank(storage_path="data/weather_advisor_agent/Theophrastus_memory.json")