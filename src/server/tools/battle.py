"""Battle-related MCP tools for LLM Battle Game."""

import random
import sqlite3
from typing import Optional, Dict, Any
import logging

from ..errors import ValidationError, BattleError
from ..matching import join_queue as matching_join_queue, leave_queue as matching_leave_queue
from ..battle import resolve_turn, check_victory

logger = logging.getLogger('llmbattle.tools.battle')


def join_queue(db: sqlite3.Connection, character_id: int) -> Dict[str, Any]:
    """
    Join matchmaking queue.

    Args:
        character_id: Character ID to join queue

    Returns:
        Queue status: 'waiting' or 'matched' with battle info
    """
    return matching_join_queue(db, character_id)


def leave_queue(db: sqlite3.Connection, character_id: int) -> Dict[str, Any]:
    """
    Leave matchmaking queue.

    Args:
        character_id: Character ID

    Returns:
        Leave confirmation
    """
    return matching_leave_queue(db, character_id)


def get_battle_status(db: sqlite3.Connection, battle_id: int) -> Dict[str, Any]:
    """
    Get current battle status.

    Args:
        battle_id: Battle ID

    Returns:
        Battle status including both players' current state
    """
    cursor = db.cursor()

    battle = cursor.execute(
        "SELECT * FROM battles WHERE id = ?",
        (battle_id,)
    ).fetchone()

    if not battle:
        raise BattleError(f"Battle {battle_id} not found")

    # Get character data
    player1 = cursor.execute(
        "SELECT * FROM characters WHERE id = ?",
        (battle['player1_id'],)
    ).fetchone()

    player2 = cursor.execute(
        "SELECT * FROM characters WHERE id = ?",
        (battle['player2_id'],)
    ).fetchone()

    # Get latest turn
    latest_turn = cursor.execute(
        "SELECT * FROM battle_turns WHERE battle_id = ? ORDER BY turn_number DESC LIMIT 1",
        (battle_id,)
    ).fetchone()

    if latest_turn:
        player1_hp = latest_turn['player1_hp_after']
        player2_hp = latest_turn['player2_hp_after']
    else:
        player1_hp = player1['computed_hp']
        player2_hp = player2['computed_hp']

    return {
        "battle_id": battle_id,
        "status": battle['status'],
        "current_turn": battle['current_turn'],
        "max_turns": battle['max_turns'],
        "player1": {
            "id": player1['id'],
            "name": player1['name'],
            "hp": player1_hp,
            "max_hp": player1['computed_hp'],
            "attack": player1['computed_attack'],
            "defense": player1['computed_defense'],
            "speed": player1['computed_speed']
        },
        "player2": {
            "id": player2['id'],
            "name": player2['name'],
            "hp": player2_hp,
            "max_hp": player2['computed_hp'],
            "attack": player2['computed_attack'],
            "defense": player2['computed_defense'],
            "speed": player2['computed_speed']
        },
        "latest_turn": dict(latest_turn) if latest_turn else None
    }


def get_opponent_action(
    db: sqlite3.Connection,
    battle_id: int,
    character_id: int
) -> Dict[str, Any]:
    """
    Get opponent's action (mock implementation - random for now).

    In production, this would call Claude API with character prompt.

    Args:
        db: Database connection
        battle_id: Battle ID
        character_id: Opponent character ID

    Returns:
        Opponent's action
    """
    cursor = db.cursor()

    # Get character and abilities
    character = cursor.execute(
        "SELECT * FROM characters WHERE id = ?",
        (character_id,)
    ).fetchone()

    abilities = cursor.execute("""
        SELECT a.* FROM abilities a
        JOIN character_abilities ca ON a.id = ca.ability_id
        WHERE ca.character_id = ?
    """, (character_id,)).fetchall()

    # Mock implementation - random action
    # TODO: Replace with actual LLM API call
    action_type = random.choice(['attack', 'defend', 'dodge', 'ability'])

    action = {
        'action': action_type,
        'ability_id': None
    }

    if action_type == 'ability' and abilities:
        # Random ability
        ability = random.choice(abilities)
        action['ability_id'] = ability['id']
    elif action_type == 'ability':
        # No abilities - fallback to attack
        action['action'] = 'attack'

    logger.debug(f"Opponent {character_id} chose action: {action}")

    return action


def execute_turn(
    db: sqlite3.Connection,
    battle_id: int,
    character_id: int,
    action: str,
    ability_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Execute a battle turn.

    Args:
        battle_id: Battle ID
        character_id: Your character ID
        action: Action type ('attack', 'defend', 'dodge', 'ability')
        ability_id: Ability ID if action is 'ability'

    Returns:
        Turn result with damage, HP changes, and battle status
    """
    cursor = db.cursor()

    # Validate battle
    battle = cursor.execute(
        "SELECT * FROM battles WHERE id = ?",
        (battle_id,)
    ).fetchone()

    if not battle:
        raise BattleError(f"Battle {battle_id} not found")

    if battle['status'] != 'in_progress':
        raise BattleError(f"Battle is not in progress (status: {battle['status']})")

    # Determine player roles
    if battle['player1_id'] == character_id:
        player_num = 1
        opponent_id = battle['player2_id']
    elif battle['player2_id'] == character_id:
        player_num = 2
        opponent_id = battle['player1_id']
    else:
        raise BattleError("Character is not part of this battle")

    # Validate action
    valid_actions = ['attack', 'defend', 'dodge', 'ability']
    if action not in valid_actions:
        raise ValidationError(f"Invalid action: {action}")

    if action == 'ability' and not ability_id:
        raise ValidationError("ability_id required when action is 'ability'")

    # Prepare player action
    player_action = {
        'action': action,
        'ability_id': ability_id
    }

    # Get opponent action
    opponent_action = get_opponent_action(db, battle_id, opponent_id)

    # Resolve turn
    if player_num == 1:
        turn_result = resolve_turn(db, battle_id, player_action, opponent_action)
    else:
        turn_result = resolve_turn(db, battle_id, opponent_action, player_action)

    # Check victory
    winner_id = check_victory(db, battle_id)

    if winner_id is not None:
        # Battle ended
        if winner_id == 0:
            # Draw
            cursor.execute(
                "UPDATE battles SET status = 'finished', winner_id = NULL, ended_at = CURRENT_TIMESTAMP WHERE id = ?",
                (battle_id,)
            )
            db.commit()

            result_status = "draw"
            winner = None
        else:
            # Winner found
            cursor.execute(
                "UPDATE battles SET status = 'finished', winner_id = ?, ended_at = CURRENT_TIMESTAMP WHERE id = ?",
                (winner_id, battle_id)
            )

            # Update stats
            loser_id = battle['player1_id'] if winner_id == battle['player2_id'] else battle['player2_id']
            update_battle_stats(db, winner_id, loser_id)

            db.commit()

            result_status = "finished"
            winner = winner_id

        return {
            "battle_status": result_status,
            "winner_id": winner,
            "turn_result": turn_result,
            "message": "Draw!" if winner_id == 0 else f"Battle finished! Winner: {winner_id}"
        }
    else:
        # Battle continues
        return {
            "battle_status": "in_progress",
            "turn_result": turn_result,
            "message": f"Turn {turn_result['turn_number']} completed"
        }


def update_battle_stats(db: sqlite3.Connection, winner_id: int, loser_id: int):
    """
    Update battle statistics for winner and loser.

    Args:
        db: Database connection
        winner_id: Winner character ID
        loser_id: Loser character ID
    """
    cursor = db.cursor()

    # Get current ratings
    winner_stats = cursor.execute(
        "SELECT * FROM stats WHERE character_id = ?",
        (winner_id,)
    ).fetchone()

    loser_stats = cursor.execute(
        "SELECT * FROM stats WHERE character_id = ?",
        (loser_id,)
    ).fetchone()

    winner_rating = winner_stats['rating'] if winner_stats else 1000
    loser_rating = loser_stats['rating'] if loser_stats else 1000

    # Calculate rating changes (Elo-like)
    rating_diff = loser_rating - winner_rating
    winner_change = 25 + (rating_diff / 20)
    loser_change = -25 - (rating_diff / 20)

    # Update winner stats
    if winner_stats:
        cursor.execute("""
            UPDATE stats SET
                total_battles = total_battles + 1,
                wins = wins + 1,
                current_win_streak = current_win_streak + 1,
                longest_win_streak = MAX(longest_win_streak, current_win_streak + 1),
                rating = rating + ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE character_id = ?
        """, (winner_change, winner_id))
    else:
        cursor.execute("""
            INSERT INTO stats (character_id, total_battles, wins, current_win_streak, longest_win_streak, rating)
            VALUES (?, 1, 1, 1, 1, ?)
        """, (winner_id, 1000 + winner_change))

    # Update loser stats
    if loser_stats:
        cursor.execute("""
            UPDATE stats SET
                total_battles = total_battles + 1,
                losses = losses + 1,
                current_win_streak = 0,
                rating = rating + ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE character_id = ?
        """, (loser_change, loser_id))
    else:
        cursor.execute("""
            INSERT INTO stats (character_id, total_battles, losses, rating)
            VALUES (?, 1, 1, ?)
        """, (loser_id, 1000 + loser_change))

    logger.info(f"Stats updated: winner {winner_id} (+{winner_change:.1f}), loser {loser_id} ({loser_change:.1f})")


def get_battle_history(
    db: sqlite3.Connection,
    character_id: int,
    limit: int = 10
) -> list[Dict[str, Any]]:
    """
    Get battle history for a character.

    Args:
        character_id: Character ID
        limit: Maximum number of battles to return

    Returns:
        List of battle records
    """
    cursor = db.cursor()

    battles = cursor.execute("""
        SELECT
            b.*,
            p1.name as player1_name,
            p2.name as player2_name
        FROM battles b
        JOIN characters p1 ON b.player1_id = p1.id
        JOIN characters p2 ON b.player2_id = p2.id
        WHERE b.player1_id = ? OR b.player2_id = ?
        ORDER BY b.started_at DESC
        LIMIT ?
    """, (character_id, character_id, limit)).fetchall()

    history = []
    for battle in battles:
        battle_dict = dict(battle)

        # Determine if won/lost
        if battle['winner_id']:
            battle_dict['result'] = 'won' if battle['winner_id'] == character_id else 'lost'
        else:
            battle_dict['result'] = 'draw' if battle['status'] == 'finished' else 'in_progress'

        # Determine opponent
        if battle['player1_id'] == character_id:
            battle_dict['opponent_id'] = battle['player2_id']
            battle_dict['opponent_name'] = battle['player2_name']
        else:
            battle_dict['opponent_id'] = battle['player1_id']
            battle_dict['opponent_name'] = battle['player1_name']

        history.append(battle_dict)

    return history
