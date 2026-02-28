"""Statistics-related MCP tools for LLM Battle Game."""

import sqlite3
from typing import Dict, Any, List
import logging

from ..errors import ValidationError

logger = logging.getLogger('llmbattle.tools.stats')


def get_leaderboard(db: sqlite3.Connection, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Get leaderboard of top characters by rating.

    Args:
        limit: Maximum number of entries to return

    Returns:
        List of characters with stats, sorted by rating
    """
    cursor = db.cursor()

    leaderboard = cursor.execute("""
        SELECT
            c.id,
            c.name,
            c.level,
            s.rating,
            s.total_battles,
            s.wins,
            s.losses,
            s.draws,
            ROUND(CAST(s.wins AS REAL) / NULLIF(s.total_battles, 0) * 100, 2) as win_rate,
            s.current_win_streak,
            s.longest_win_streak
        FROM characters c
        JOIN stats s ON c.id = s.character_id
        WHERE s.total_battles > 0
        ORDER BY s.rating DESC, s.wins DESC
        LIMIT ?
    """, (limit,)).fetchall()

    result = []
    for idx, entry in enumerate(leaderboard, 1):
        entry_dict = dict(entry)
        entry_dict['rank'] = idx
        result.append(entry_dict)

    logger.debug(f"Leaderboard retrieved: {len(result)} entries")

    return result


def get_character_stats(db: sqlite3.Connection, character_id: int) -> Dict[str, Any]:
    """
    Get detailed statistics for a character.

    Args:
        character_id: Character ID

    Returns:
        Character stats including battles, wins, rating, etc.
    """
    cursor = db.cursor()

    # Get character
    character = cursor.execute(
        "SELECT * FROM characters WHERE id = ?",
        (character_id,)
    ).fetchone()

    if not character:
        raise ValidationError(f"Character {character_id} not found")

    # Get stats
    stats = cursor.execute(
        "SELECT * FROM stats WHERE character_id = ?",
        (character_id,)
    ).fetchone()

    if not stats:
        # No stats yet - return defaults
        return {
            "character_id": character_id,
            "name": character['name'],
            "level": character['level'],
            "rating": 1000,
            "total_battles": 0,
            "wins": 0,
            "losses": 0,
            "draws": 0,
            "win_rate": 0.0,
            "current_win_streak": 0,
            "longest_win_streak": 0,
            "total_damage_dealt": 0,
            "total_damage_received": 0
        }

    # Calculate win rate
    win_rate = (stats['wins'] / stats['total_battles'] * 100) if stats['total_battles'] > 0 else 0.0

    # Get rank
    rank_result = cursor.execute("""
        SELECT COUNT(*) + 1 as rank
        FROM stats
        WHERE rating > ? OR (rating = ? AND wins > ?)
    """, (stats['rating'], stats['rating'], stats['wins'])).fetchone()

    rank = rank_result['rank']

    return {
        "character_id": character_id,
        "name": character['name'],
        "level": character['level'],
        "rating": stats['rating'],
        "rank": rank,
        "total_battles": stats['total_battles'],
        "wins": stats['wins'],
        "losses": stats['losses'],
        "draws": stats['draws'],
        "win_rate": round(win_rate, 2),
        "current_win_streak": stats['current_win_streak'],
        "longest_win_streak": stats['longest_win_streak'],
        "total_damage_dealt": stats['total_damage_dealt'],
        "total_damage_received": stats['total_damage_received']
    }
