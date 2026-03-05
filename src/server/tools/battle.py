"""Battle-related MCP tools (API client version)

マッチング、バトル進行はMCPサーバーがローカルで処理し、
結果をAPIサーバーに送信します。
"""

import random
from typing import Optional, Dict, Any
import logging

from ..api_client import ApiClient
from ..errors import ValidationError, BattleError

logger = logging.getLogger('llmbattle.tools.battle')


# グローバルインスタンス（main.pyで初期化される）
_api_client: ApiClient = None


def set_api_client(client: ApiClient):
    """Set API client instance"""
    global _api_client
    _api_client = client


def join_queue(character_id: int) -> Dict[str, Any]:
    """
    Join matchmaking queue (API経由)

    Args:
        character_id: Character ID to join queue

    Returns:
        Queue status with match info if matched
    """
    if not _api_client:
        raise RuntimeError("API client not initialized")

    return _api_client.join_queue(character_id)


def leave_queue(character_id: int) -> Dict[str, Any]:
    """
    Leave matchmaking queue (API経由)

    Args:
        character_id: Character ID

    Returns:
        Leave confirmation
    """
    if not _api_client:
        raise RuntimeError("API client not initialized")

    return _api_client.leave_queue(character_id)


def get_battle_status(battle_id: int) -> Dict[str, Any]:
    """
    Get current battle status (API経由)

    Args:
        battle_id: Battle ID

    Returns:
        Battle status including both players' current state
    """
    if not _api_client:
        raise RuntimeError("API client not initialized")

    return _api_client.get_battle(battle_id)


def get_battle_history(character_id: int, limit: int = 10) -> list[Dict[str, Any]]:
    """
    Get battle history for a character (API経由)

    Args:
        character_id: Character ID
        limit: Maximum number of battles to return

    Returns:
        List of battle records
    """
    if not _api_client:
        raise RuntimeError("API client not initialized")

    # Note: This endpoint may not exist yet in the API
    # For now, return empty list
    # TODO: Implement battle history API endpoint
    logger.warning("Battle history API not implemented yet")
    return []


# Note: Battle execution logic should remain local in MCP server
# but for this implementation, we're simplifying it to just call API
# In a full implementation, the MCP server would:
# 1. Get battle status from API
# 2. Decide action locally (potentially with LLM)
# 3. Compute results locally
# 4. Send results to API via record_turn
