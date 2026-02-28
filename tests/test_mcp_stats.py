"""Tests for stats MCP tools."""

import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from database import get_connection
from database.init_db import execute_sql_script
from server.tools import stats
from server.errors import ValidationError


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
                                computed_hp, computed_attack, computed_defense, computed_speed, level)
        VALUES
            (1, 1, 'TopPlayer', 'Best player', 100, 80, 60, 70, 100, 80, 60, 70, 1),
            (2, 1, 'MidPlayer', 'Average player', 100, 80, 60, 70, 100, 80, 60, 70, 1),
            (3, 1, 'Newbie', 'New player', 100, 80, 60, 70, 100, 80, 60, 70, 1)
    """)

    cursor.execute("""
        INSERT INTO stats (character_id, rating, total_battles, wins, losses, draws,
                          current_win_streak, longest_win_streak, total_damage_dealt, total_damage_received)
        VALUES
            (1, 1500, 50, 35, 10, 5, 5, 12, 5000, 3000),
            (2, 1200, 30, 15, 12, 3, 2, 5, 3000, 2800),
            (3, 900, 10, 2, 7, 1, 0, 2, 800, 1200)
    """)

    conn.commit()
    yield conn
    conn.close()


def test_get_leaderboard(db_conn):
    """Test get_leaderboard tool."""
    result = stats.get_leaderboard(db_conn, limit=50)

    assert len(result) == 3
    assert result[0]['rank'] == 1
    assert result[0]['name'] == 'TopPlayer'
    assert result[0]['rating'] == 1500

    # Check ordering
    assert result[0]['rating'] >= result[1]['rating']
    assert result[1]['rating'] >= result[2]['rating']


def test_get_leaderboard_limit(db_conn):
    """Test leaderboard with limit."""
    result = stats.get_leaderboard(db_conn, limit=2)

    assert len(result) == 2
    assert result[0]['name'] == 'TopPlayer'
    assert result[1]['name'] == 'MidPlayer'


def test_get_leaderboard_win_rate(db_conn):
    """Test that leaderboard includes win rate."""
    result = stats.get_leaderboard(db_conn, limit=50)

    # TopPlayer: 35 wins / 50 battles = 70%
    assert result[0]['win_rate'] == 70.0

    # MidPlayer: 15 wins / 30 battles = 50%
    assert result[1]['win_rate'] == 50.0


def test_get_character_stats_existing(db_conn):
    """Test get_character_stats for existing character."""
    result = stats.get_character_stats(db_conn, 1)

    assert result['character_id'] == 1
    assert result['name'] == 'TopPlayer'
    assert result['rating'] == 1500
    assert result['total_battles'] == 50
    assert result['wins'] == 35
    assert result['losses'] == 10
    assert result['draws'] == 5
    assert result['win_rate'] == 70.0
    assert result['current_win_streak'] == 5
    assert result['longest_win_streak'] == 12
    assert 'rank' in result


def test_get_character_stats_no_battles(db_conn):
    """Test get_character_stats for character with no battles."""
    # Create character with no stats
    cursor = db_conn.cursor()
    cursor.execute("""
        INSERT INTO characters (id, account_id, name, prompt, base_hp, base_attack, base_defense, base_speed,
                                computed_hp, computed_attack, computed_defense, computed_speed)
        VALUES (4, 1, 'NoStats', 'No battles yet', 100, 80, 60, 70, 100, 80, 60, 70)
    """)
    db_conn.commit()

    result = stats.get_character_stats(db_conn, 4)

    assert result['character_id'] == 4
    assert result['rating'] == 1000  # Default rating
    assert result['total_battles'] == 0
    assert result['wins'] == 0
    assert result['win_rate'] == 0.0


def test_get_character_stats_not_found(db_conn):
    """Test get_character_stats for non-existent character."""
    with pytest.raises(ValidationError):
        stats.get_character_stats(db_conn, 999)


def test_get_character_stats_rank(db_conn):
    """Test that rank is calculated correctly."""
    result1 = stats.get_character_stats(db_conn, 1)
    result2 = stats.get_character_stats(db_conn, 2)
    result3 = stats.get_character_stats(db_conn, 3)

    assert result1['rank'] == 1  # Highest rating
    assert result2['rank'] == 2
    assert result3['rank'] == 3


def test_leaderboard_empty(db_conn):
    """Test leaderboard with no battles."""
    # Create new database with no stats
    conn = get_connection(':memory:')

    schema_path = Path(__file__).parent.parent / 'src' / 'database' / 'schema.sql'
    execute_sql_script(conn, schema_path)

    cursor = conn.cursor()
    cursor.execute("INSERT INTO accounts (id, username) VALUES (1, 'test')")
    cursor.execute("""
        INSERT INTO characters (id, account_id, name, prompt, base_hp, base_attack, base_defense, base_speed,
                                computed_hp, computed_attack, computed_defense, computed_speed)
        VALUES (1, 1, 'NewChar', 'New', 100, 80, 60, 70, 100, 80, 60, 70)
    """)
    conn.commit()

    result = stats.get_leaderboard(conn, limit=50)

    assert len(result) == 0  # No characters with battles

    conn.close()


def test_damage_stats_included(db_conn):
    """Test that damage statistics are included."""
    result = stats.get_character_stats(db_conn, 1)

    assert result['total_damage_dealt'] == 5000
    assert result['total_damage_received'] == 3000
