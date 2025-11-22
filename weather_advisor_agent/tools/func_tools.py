import logging
from typing import Dict, Any

from .web_access_tools import fetch_env_snapshot_from_open_meteo


logger = logging.getLogger(__name__)
_last_snapshot = None


def fetch_and_store_snapshot(latitude: float, longitude: float) -> Dict[str, Any]:
  """Wrapper for fetch_env_snapshot_from_open_meteo"""
  global _last_snapshot
  _last_snapshot = fetch_env_snapshot_from_open_meteo(latitude, longitude)
  logger.debug(f"Stored snapshot in global cache for ({latitude}, {longitude})")
  return _last_snapshot


def get_last_snapshot() -> Dict[str, Any]:
  """Retrieve last snapshot"""
  global _last_snapshot
  snapshot = _last_snapshot
  _last_snapshot = None
  return snapshot