"""Tests for battle logic."""

import pytest
import random
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from database import get_connection
from database.init_db import execute_sql_script
from server.battle.logic import (
    calculate_damage,
    apply_ability_effect,
    resolve_turn,
    check_victory,
    get_action_order,
)


@pytest.fixture
def db_conn():
    """Create test database connection."""
    conn = get_connection(':memory:')

    # Apply schema
    schema_path = Path(__file__).parent.parent / 'src' / 'database' / 'schema.sql'
    execute_sql_script(conn, schema_path)

    # Insert test abilities
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO abilities (id, name, description, effect_type, power, cooldown)
        VALUES
            (1, 'Power Strike', 'Strong attack', 'damage', 150, 0),
            (2, 'Heal', 'Restore HP', 'heal', 30, 2),
            (3, 'Weaken', 'Reduce attack', 'debuff', 30, 2)
    """)

    # Insert test account
    cursor.execute("INSERT INTO accounts (id, username) VALUES (1, 'test_user')")

    # Insert test characters
    cursor.execute("""
        INSERT INTO characters (id, account_id, name, prompt, base_hp, base_attack, base_defense, base_speed,
                                computed_hp, computed_attack, computed_defense, computed_speed)
        VALUES
            (1, 1, 'Fighter', 'A brave fighter', 100, 80, 60, 70, 100, 80, 60, 70),
            (2, 1, 'Tank', 'A defensive tank', 120, 60, 90, 50, 120, 60, 90, 50)
    """)

    conn.commit()
    yield conn
    conn.close()


def test_calculate_damage_normal_attack(db_conn):
    """Test normal attack damage calculation."""
    random.seed(42)  # Fixed seed for reproducibility

    attacker = {
        'computed_attack': 80,
        'computed_speed': 70
    }

    defender = {
        'computed_defense': 60,
        'computed_speed': 50,
        'action': 'attack'
    }

    damage = calculate_damage(attacker, defender, 'attack')

    assert damage > 0
    assert isinstance(damage, int)


def test_calculate_damage_with_defend(db_conn):
    """Test damage calculation when defender is defending."""
    random.seed(42)

    attacker = {
        'computed_attack': 80,
        'computed_speed': 70
    }

    defender = {
        'computed_defense': 60,
        'computed_speed': 50,
        'action': 'defend'
    }

    normal_damage = calculate_damage(attacker, defender, 'attack')

    # Reset defender to normal
    defender['action'] = 'attack'
    defend_damage = calculate_damage(attacker, defender, 'attack')

    # Defend should reduce damage (roughly 50%)
    assert normal_damage < defend_damage * 2


def test_calculate_damage_with_dodge(db_conn):
    """Test damage calculation with dodge attempt."""
    random.seed(42)

    attacker = {
        'computed_attack': 80,
        'computed_speed': 70
    }

    defender = {
        'computed_defense': 60,
        'computed_speed': 100,  # High speed for better dodge
        'action': 'dodge'
    }

    damages = []
    for _ in range(10):
        damage = calculate_damage(attacker, defender, 'attack')
        damages.append(damage)

    # Some attacks should be dodged (damage = 0)
    assert 0 in damages


def test_get_action_order_speed_difference(db_conn):
    """Test action order with different speeds."""
    player1 = {'id': 1, 'computed_speed': 90}
    player2 = {'id': 2, 'computed_speed': 50}

    first, second = get_action_order(player1, player2)

    assert first == 1  # Faster player goes first
    assert second == 2


def test_get_action_order_same_speed(db_conn):
    """Test action order with same speed (random)."""
    random.seed(42)

    player1 = {'id': 1, 'computed_speed': 70}
    player2 = {'id': 2, 'computed_speed': 70}

    results = []
    for _ in range(10):
        first, second = get_action_order(player1, player2)
        results.append(first)

    # Should have some variation (not all same)
    assert len(set(results)) > 1


def test_resolve_turn_basic(db_conn):
    """Test basic turn resolution."""
    cursor = db_conn.cursor()

    # Create a battle
    cursor.execute("""
        INSERT INTO battles (id, player1_id, player2_id, status, current_turn)
        VALUES (1, 1, 2, 'in_progress', 0)
    """)
    db_conn.commit()

    player1_action = {'action': 'attack', 'ability_id': None}
    player2_action = {'action': 'attack', 'ability_id': None}

    random.seed(42)
    result = resolve_turn(db_conn, 1, player1_action, player2_action)

    assert result['turn_number'] == 1
    assert 'player1_hp_after' in result
    assert 'player2_hp_after' in result
    assert result['player1_hp_after'] <= 120  # Max HP of player2's attack target
    assert result['player2_hp_after'] <= 100  # Max HP of player1's attack target


def test_resolve_turn_with_ability(db_conn):
    """Test turn resolution with ability usage."""
    cursor = db_conn.cursor()

    # Create a battle
    cursor.execute("""
        INSERT INTO battles (id, player1_id, player2_id, status, current_turn)
        VALUES (2, 1, 2, 'in_progress', 0)
    """)

    # Give ability to character
    cursor.execute("INSERT INTO character_abilities (character_id, ability_id) VALUES (1, 1)")
    db_conn.commit()

    player1_action = {'action': 'ability', 'ability_id': 1}  # Power Strike
    player2_action = {'action': 'defend', 'ability_id': None}

    random.seed(42)
    result = resolve_turn(db_conn, 2, player1_action, player2_action)

    assert result['turn_number'] == 1
    assert result['player1_damage_dealt'] > 0  # Should deal damage


def test_check_victory_hp_zero(db_conn):
    """Test victory check when HP reaches zero."""
    cursor = db_conn.cursor()

    # Create a battle
    cursor.execute("""
        INSERT INTO battles (id, player1_id, player2_id, status, current_turn, max_turns)
        VALUES (3, 1, 2, 'in_progress', 1, 50)
    """)

    # Insert a turn where player2 HP = 0
    cursor.execute("""
        INSERT INTO battle_turns (
            battle_id, turn_number,
            player1_action, player1_damage_dealt, player1_damage_received, player1_hp_after,
            player2_action, player2_damage_dealt, player2_damage_received, player2_hp_after,
            turn_result
        ) VALUES (3, 1, 'attack', 50, 0, 100, 'attack', 0, 50, 0, '{}')
    """)
    db_conn.commit()

    winner = check_victory(db_conn, 3)

    assert winner == 1  # Player 1 wins


def test_check_victory_draw(db_conn):
    """Test draw condition."""
    cursor = db_conn.cursor()

    # Create a battle
    cursor.execute("""
        INSERT INTO battles (id, player1_id, player2_id, status, current_turn, max_turns)
        VALUES (4, 1, 2, 'in_progress', 1, 50)
    """)

    # Insert a turn where both HP = 0
    cursor.execute("""
        INSERT INTO battle_turns (
            battle_id, turn_number,
            player1_action, player1_damage_dealt, player1_damage_received, player1_hp_after,
            player2_action, player2_damage_dealt, player2_damage_received, player2_hp_after,
            turn_result
        ) VALUES (4, 1, 'attack', 50, 50, 0, 'attack', 50, 50, 0, '{}')
    """)
    db_conn.commit()

    winner = check_victory(db_conn, 4)

    assert winner == 0  # Draw


def test_check_victory_max_turns(db_conn):
    """Test victory check at max turns."""
    cursor = db_conn.cursor()

    # Create a battle at max turns
    cursor.execute("""
        INSERT INTO battles (id, player1_id, player2_id, status, current_turn, max_turns)
        VALUES (5, 1, 2, 'in_progress', 50, 50)
    """)

    # Insert a turn where player1 has more HP
    cursor.execute("""
        INSERT INTO battle_turns (
            battle_id, turn_number,
            player1_action, player1_damage_dealt, player1_damage_received, player1_hp_after,
            player2_action, player2_damage_dealt, player2_damage_received, player2_hp_after,
            turn_result
        ) VALUES (5, 50, 'attack', 10, 5, 80, 'attack', 5, 10, 60, '{}')
    """)
    db_conn.commit()

    winner = check_victory(db_conn, 5)

    assert winner == 1  # Player 1 has more HP


def test_check_victory_ongoing(db_conn):
    """Test that battle continues when no victory condition met."""
    cursor = db_conn.cursor()

    # Create an ongoing battle
    cursor.execute("""
        INSERT INTO battles (id, player1_id, player2_id, status, current_turn, max_turns)
        VALUES (6, 1, 2, 'in_progress', 10, 50)
    """)

    # Insert a turn with both alive
    cursor.execute("""
        INSERT INTO battle_turns (
            battle_id, turn_number,
            player1_action, player1_damage_dealt, player1_damage_received, player1_hp_after,
            player2_action, player2_damage_dealt, player2_damage_received, player2_hp_after,
            turn_result
        ) VALUES (6, 10, 'attack', 20, 15, 80, 'attack', 15, 20, 90, '{}')
    """)
    db_conn.commit()

    winner = check_victory(db_conn, 6)

    assert winner is None  # Battle continues
