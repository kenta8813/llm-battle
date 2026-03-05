"""Statistics-related MCP tools (API client version)"""

from typing import Dict, Any, List
import logging

from ..api_client import ApiClient
from ..errors import ValidationError

logger = logging.getLogger('llmbattle.tools.stats')


# グローバルインスタンス（main.pyで初期化される）
_api_client: ApiClient = None


def set_api_client(client: ApiClient):
    """Set API client instance"""
    global _api_client
    _api_client = client


def get_leaderboard(limit: int = 50) -> List[Dict[str, Any]]:
    """
    Get leaderboard of top characters by rating (API経由)

    Args:
        limit: Maximum number of entries to return

    Returns:
        List of characters with stats, sorted by rating
    """
    if not _api_client:
        raise RuntimeError("API client not initialized")

    result = _api_client.get_leaderboard(limit)
    return result.get('leaderboard', [])


def get_character_stats(character_id: int) -> Dict[str, Any]:
    """
    Get detailed statistics for a character (API経由)

    Args:
        character_id: Character ID

    Returns:
        Character stats including battles, wins, rating, etc.
    """
    if not _api_client:
        raise RuntimeError("API client not initialized")

    return _api_client.get_character_stats(character_id)
