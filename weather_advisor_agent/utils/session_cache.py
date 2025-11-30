"""
Had a few problems when trying to implement my local evaluator, keys were missing so i developed this 
module to implement a simple in-memory cache per session. It is not persistent; the data lives only 
while the process is running.
"""
import logging
from typing import Dict, Any


logger = logging.getLogger(__name__)

_session_cache: Dict[str, Dict[str, Any]] = {}

def store_evaluation_data(session_id: str, data: Dict[str, Any]) -> None:
  """Store evaluation data for a session"""
  if session_id not in _session_cache:
    _session_cache[session_id] = {}
  
  _session_cache[session_id].update(data)
  logger.debug(f"Cached {list(data.keys())} for session {session_id}.")


def get_evaluation_data(session_id: str) -> Dict[str, Any]:
  """Retrieve evaluation data for a session"""
  data = _session_cache.get(session_id, {}).copy()
  logger.info(f"Retrieved {len(data)} keys from cache for session {session_id}.")
  return data