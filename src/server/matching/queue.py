"""Matching queue management for LLM Battle Game."""

import sqlite3
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import logging

from ..errors import ValidationError, BattleError

logger = logging.getLogger('llmbattle.matching')


def get_rating_range(wait_time: float) -> Optional[int]:
    """
    Get rating range based on wait time.

    Args:
        wait_time: Wait time in seconds

    Returns:
        Rating range (None means no limit)
    """
    if wait_time < 15:
        return 100
    elif wait_time < 30:
        return 200
    elif wait_time < 45:
        return 400
    else:
        return None  # No limit


def join_queue(db: sqlite3.Connection, character_id: int) -> Dict[str, Any]:
    """
    Join matchmaking queue.

    Args:
        db: Database connection
        character_id: Character ID

    Returns:
        Queue join result
    """
    cursor = db.cursor()

    # Get character and rating
    character = cursor.execute(
        "SELECT * FROM characters WHERE id = ?",
        (character_id,)
    ).fetchone()

    if not character:
        raise ValidationError(f"Character {character_id} not found")

    # Get rating (default 1000)
    stats = cursor.execute(
        "SELECT rating FROM stats WHERE character_id = ?",
        (character_id,)
    ).fetchone()

    rating = stats['rating'] if stats else 1000

    # Check if already in queue
    existing = cursor.execute(
        "SELECT id FROM queue WHERE character_id = ?",
        (character_id,)
    ).fetchone()

    if existing:
        raise ValidationError("Already in queue")

    # Add to queue
    cursor.execute(
        "INSERT INTO queue (character_id, rating) VALUES (?, ?)",
        (character_id, rating)
    )
    db.commit()

    logger.info(f"Character {character_id} joined queue (rating={rating})")

    # Immediately try to find match
    opponent_id = find_match(db, character_id, rating, 0.0)

    if opponent_id:
        # Match found
        battle_id = create_battle(db, character_id, opponent_id)

        opponent = cursor.execute(
            "SELECT * FROM characters WHERE id = ?",
            (opponent_id,)
        ).fetchone()

        logger.info(f"Match found: {character_id} vs {opponent_id} (battle_id={battle_id})")

        return {
            "status": "matched",
            "battle_id": battle_id,
            "opponent_id": opponent_id,
            "opponent_name": opponent['name'],
            "message": "Match found!"
        }
    else:
        # Wait in queue
        return {
            "status": "waiting",
            "message": "Searching for opponent..."
        }


def leave_queue(db: sqlite3.Connection, character_id: int) -> Dict[str, Any]:
    """
    Leave matchmaking queue.

    Args:
        db: Database connection
        character_id: Character ID

    Returns:
        Leave result
    """
    cursor = db.cursor()

    result = cursor.execute(
        "DELETE FROM queue WHERE character_id = ?",
        (character_id,)
    )
    db.commit()

    if result.rowcount == 0:
        raise ValidationError("Not in queue")

    logger.info(f"Character {character_id} left queue")

    return {
        "status": "left",
        "message": "Left the queue"
    }


def find_match(
    db: sqlite3.Connection,
    character_id: int,
    my_rating: int,
    wait_time: float
) -> Optional[int]:
    """
    Find a match for the character.

    Args:
        db: Database connection
        character_id: Character ID
        my_rating: Character's rating
        wait_time: Time spent waiting in seconds

    Returns:
        Opponent character ID, or None if not found
    """
    cursor = db.cursor()

    rating_range = get_rating_range(wait_time)

    if rating_range is None:
        # No limit
        query = """
            SELECT character_id, rating
            FROM queue
            WHERE character_id != ?
            ORDER BY joined_at ASC
            LIMIT 1
        """
        params = (character_id,)
    else:
        # With rating range
        min_rating = my_rating - rating_range
        max_rating = my_rating + rating_range

        query = """
            SELECT character_id, rating
            FROM queue
            WHERE character_id != ?
              AND rating BETWEEN ? AND ?
            ORDER BY ABS(rating - ?), joined_at ASC
            LIMIT 1
        """
        params = (character_id, min_rating, max_rating, my_rating)

    result = cursor.execute(query, params).fetchone()

    return result['character_id'] if result else None


def atomic_match_attempt(
    db: sqlite3.Connection,
    character_id: int,
    opponent_id: int
) -> Optional[int]:
    """
    Atomically attempt to match two characters.

    Args:
        db: Database connection
        character_id: Character ID
        opponent_id: Opponent character ID

    Returns:
        Battle ID if successful, None if failed
    """
    cursor = db.cursor()

    try:
        cursor.execute("BEGIN IMMEDIATE TRANSACTION")

        # Check both still in queue
        player1 = cursor.execute(
            "SELECT character_id FROM queue WHERE character_id = ?",
            (character_id,)
        ).fetchone()

        player2 = cursor.execute(
            "SELECT character_id FROM queue WHERE character_id = ?",
            (opponent_id,)
        ).fetchone()

        if not player1 or not player2:
            cursor.execute("ROLLBACK")
            return None

        # Create battle
        battle_id = create_battle(db, character_id, opponent_id)

        cursor.execute("COMMIT")
        return battle_id

    except sqlite3.IntegrityError:
        cursor.execute("ROLLBACK")
        return None
    except Exception as e:
        cursor.execute("ROLLBACK")
        logger.error(f"Match attempt failed: {e}")
        return None


def create_battle(
    db: sqlite3.Connection,
    player1_id: int,
    player2_id: int
) -> int:
    """
    Create a new battle between two characters.

    Args:
        db: Database connection
        player1_id: Player 1 character ID
        player2_id: Player 2 character ID

    Returns:
        Battle ID
    """
    cursor = db.cursor()

    try:
        # Verify both characters still in queue
        p1_in_queue = cursor.execute(
            "SELECT id FROM queue WHERE character_id = ?",
            (player1_id,)
        ).fetchone()

        p2_in_queue = cursor.execute(
            "SELECT id FROM queue WHERE character_id = ?",
            (player2_id,)
        ).fetchone()

        if not p1_in_queue or not p2_in_queue:
            raise BattleError("One or both players no longer in queue")

        # Create battle
        cursor.execute("""
            INSERT INTO battles (player1_id, player2_id, status, current_turn)
            VALUES (?, ?, 'in_progress', 0)
        """, (player1_id, player2_id))

        battle_id = cursor.lastrowid

        # Remove both from queue
        cursor.execute(
            "DELETE FROM queue WHERE character_id IN (?, ?)",
            (player1_id, player2_id)
        )

        db.commit()

        logger.info(f"Battle created: id={battle_id}, players={player1_id} vs {player2_id}")

        return battle_id

    except BattleError:
        # Re-raise BattleError without wrapping
        raise
    except Exception as e:
        db.rollback()
        raise BattleError(f"Failed to create battle: {str(e)}")


def cleanup_expired_queue_entries(db: sqlite3.Connection, timeout_minutes: int = 10):
    """
    Clean up queue entries older than timeout.

    Args:
        db: Database connection
        timeout_minutes: Timeout in minutes
    """
    cursor = db.cursor()

    cursor.execute(
        "DELETE FROM queue WHERE joined_at < datetime('now', ?)",
        (f'-{timeout_minutes} minutes',)
    )
    db.commit()

    if cursor.rowcount > 0:
        logger.info(f"Cleaned up {cursor.rowcount} expired queue entries")
