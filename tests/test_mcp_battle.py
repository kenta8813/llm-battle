"""Tests for battle MCP tools."""

import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from database import get_connection
from database.init_db import execute_sql_script
from server.tools import battle
from server.errors import ValidationError, BattleError


@pytest.fixture
def db_conn():
    """Create test database connection."""
    conn = get_connection(':memory:')

    # Apply schema
    schema_path = Path(__file__).parent.parent / 'src' / 'database' / 'schema.sql'
    execute_sql_script(conn, schema_path)

    # Insert test data
    cursor = conn.cursor()
    cursor.execute("INSERT INTO accounts (id, username) VALUES (1, 'test_user')")

    cursor.execute("""
        INSERT INTO characters (id, account_id, name, prompt, base_hp, base_attack, base_defense, base_speed,
                                computed_hp, computed_attack, computed_defense, computed_speed)
        VALUES
            (1, 1, 'Fighter1', 'A brave fighter', 100, 80, 60, 70, 100, 80, 60, 70),
            (2, 1, 'Fighter2', 'A strong fighter', 100, 80, 60, 70, 100, 80, 60, 70)
    """)

    cursor.execute("""
        INSERT INTO stats (character_id, rating) VALUES (1, 1000), (2, 1000)
    """)

    # Insert abilities
    cursor.execute("""
        INSERT INTO abilities (id, name, description, effect_type, power, cooldown)
        VALUES (1, 'Power Strike', 'Strong attack', 'damage', 150, 0)
    """)

    cursor.execute("INSERT INTO character_abilities (character_id, ability_id) VALUES (1, 1)")

    conn.commit()
    yield conn
    conn.close()


def test_join_queue(db_conn):
    """Test join_queue tool."""
    result = battle.join_queue(db_conn, 1)

    assert result['status'] == 'waiting'


def test_join_queue_with_match(db_conn):
    """Test join_queue that results in immediate match."""
    # First player joins
    battle.join_queue(db_conn, 1)

    # Second player joins and should match
    result = battle.join_queue(db_conn, 2)

    assert result['status'] == 'matched'
    assert 'battle_id' in result
    assert result['opponent_id'] == 1


def test_leave_queue(db_conn):
    """Test leave_queue tool."""
    battle.join_queue(db_conn, 1)
    result = battle.leave_queue(db_conn, 1)

    assert result['status'] == 'left'


def test_get_battle_status(db_conn):
    """Test get_battle_status tool."""
    # Create a battle
    cursor = db_conn.cursor()
    cursor.execute("""
        INSERT INTO battles (id, player1_id, player2_id, status, current_turn)
        VALUES (1, 1, 2, 'in_progress', 0)
    """)
    db_conn.commit()

    result = battle.get_battle_status(db_conn, 1)

    assert result['battle_id'] == 1
    assert result['status'] == 'in_progress'
    assert result['current_turn'] == 0
    assert 'player1' in result
    assert 'player2' in result
    assert result['player1']['id'] == 1
    assert result['player2']['id'] == 2


def test_get_battle_status_not_found(db_conn):
    """Test get_battle_status with invalid battle ID."""
    with pytest.raises(BattleError):
        battle.get_battle_status(db_conn, 999)


def test_execute_turn(db_conn):
    """Test execute_turn tool."""
    import random
    random.seed(42)

    # Create a battle
    cursor = db_conn.cursor()
    cursor.execute("""
        INSERT INTO battles (id, player1_id, player2_id, status, current_turn)
        VALUES (1, 1, 2, 'in_progress', 0)
    """)
    db_conn.commit()

    result = battle.execute_turn(db_conn, 1, 1, 'attack')

    assert 'battle_status' in result
    assert result['battle_status'] in ['in_progress', 'finished', 'draw']
    assert 'turn_result' in result


def test_execute_turn_with_ability(db_conn):
    """Test execute_turn with ability usage."""
    import random
    random.seed(42)

    # Create a battle
    cursor = db_conn.cursor()
    cursor.execute("""
        INSERT INTO battles (id, player1_id, player2_id, status, current_turn)
        VALUES (2, 1, 2, 'in_progress', 0)
    """)
    db_conn.commit()

    result = battle.execute_turn(db_conn, 2, 1, 'ability', ability_id=1)

    assert 'battle_status' in result
    assert 'turn_result' in result


def test_execute_turn_invalid_action(db_conn):
    """Test execute_turn with invalid action."""
    cursor = db_conn.cursor()
    cursor.execute("""
        INSERT INTO battles (id, player1_id, player2_id, status, current_turn)
        VALUES (3, 1, 2, 'in_progress', 0)
    """)
    db_conn.commit()

    with pytest.raises(ValidationError):
        battle.execute_turn(db_conn, 3, 1, 'invalid_action')


def test_execute_turn_battle_not_found(db_conn):
    """Test execute_turn with invalid battle ID."""
    with pytest.raises(BattleError):
        battle.execute_turn(db_conn, 999, 1, 'attack')


def test_get_battle_history(db_conn):
    """Test get_battle_history tool."""
    # Create some battles
    cursor = db_conn.cursor()
    cursor.execute("""
        INSERT INTO battles (id, player1_id, player2_id, status, winner_id)
        VALUES
            (1, 1, 2, 'finished', 1),
            (2, 1, 2, 'finished', 2),
            (3, 1, 2, 'in_progress', NULL)
    """)
    db_conn.commit()

    result = battle.get_battle_history(db_conn, 1, limit=10)

    assert len(result) == 3
    assert result[0]['result'] in ['won', 'lost', 'in_progress']


def test_get_battle_history_empty(db_conn):
    """Test get_battle_history with no battles."""
    result = battle.get_battle_history(db_conn, 1, limit=10)

    assert len(result) == 0


def test_full_battle_flow(db_conn):
    """Test complete battle flow from queue to finish."""
    import random
    random.seed(42)

    # Both join queue
    result1 = battle.join_queue(db_conn, 1)
    result2 = battle.join_queue(db_conn, 2)

    # Should have matched
    assert result2['status'] == 'matched'
    battle_id = result2['battle_id']

    # Execute turns until battle ends
    max_turns = 10
    for turn in range(max_turns):
        status = battle.get_battle_status(db_conn, battle_id)

        if status['status'] != 'in_progress':
            break

        # Alternate between characters
        char_id = 1 if turn % 2 == 0 else 2
        result = battle.execute_turn(db_conn, battle_id, char_id, 'attack')

        if result['battle_status'] != 'in_progress':
            break

    # Battle should have ended or be in progress
    final_status = battle.get_battle_status(db_conn, battle_id)
    assert final_status['status'] in ['in_progress', 'finished']
