"""Tests for matching logic."""

import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from database import get_connection
from database.init_db import execute_sql_script
from server.matching.queue import (
    join_queue,
    leave_queue,
    find_match,
    get_rating_range,
    create_battle,
)
from server.errors import ValidationError, BattleError


@pytest.fixture
def db_conn():
    """Create test database connection."""
    conn = get_connection(':memory:')

    # Apply schema
    schema_path = Path(__file__).parent.parent / 'src' / 'database' / 'schema.sql'
    execute_sql_script(conn, schema_path)

    # Insert test account
    cursor = conn.cursor()
    cursor.execute("INSERT INTO accounts (id, username) VALUES (1, 'test_user')")

    # Insert test characters
    cursor.execute("""
        INSERT INTO characters (id, account_id, name, prompt, base_hp, base_attack, base_defense, base_speed,
                                computed_hp, computed_attack, computed_defense, computed_speed)
        VALUES
            (1, 1, 'Fighter1', 'A fighter', 100, 80, 60, 70, 100, 80, 60, 70),
            (2, 1, 'Fighter2', 'Another fighter', 100, 80, 60, 70, 100, 80, 60, 70),
            (3, 1, 'Fighter3', 'Third fighter', 100, 80, 60, 70, 100, 80, 60, 70)
    """)

    # Insert stats with different ratings
    cursor.execute("""
        INSERT INTO stats (character_id, rating) VALUES
            (1, 1000),
            (2, 1050),
            (3, 1500)
    """)

    conn.commit()
    yield conn
    conn.close()


def test_get_rating_range():
    """Test rating range calculation based on wait time."""
    assert get_rating_range(0) == 100
    assert get_rating_range(10) == 100
    assert get_rating_range(15) == 200
    assert get_rating_range(20) == 200
    assert get_rating_range(30) == 400
    assert get_rating_range(40) == 400
    assert get_rating_range(45) is None
    assert get_rating_range(60) is None


def test_join_queue_success(db_conn):
    """Test successful queue join."""
    result = join_queue(db_conn, 1)

    assert result['status'] == 'waiting'
    assert 'message' in result

    # Verify in database
    cursor = db_conn.cursor()
    queue_entry = cursor.execute(
        "SELECT * FROM queue WHERE character_id = ?", (1,)
    ).fetchone()

    assert queue_entry is not None
    assert queue_entry['rating'] == 1000


def test_join_queue_duplicate(db_conn):
    """Test duplicate queue join."""
    join_queue(db_conn, 1)

    with pytest.raises(ValidationError, match="Already in queue"):
        join_queue(db_conn, 1)


def test_join_queue_immediate_match(db_conn):
    """Test immediate match when joining queue."""
    # First player joins
    result1 = join_queue(db_conn, 1)
    assert result1['status'] == 'waiting'

    # Second player with similar rating joins - should match
    result2 = join_queue(db_conn, 2)

    assert result2['status'] == 'matched'
    assert 'battle_id' in result2
    assert result2['opponent_id'] == 1


def test_leave_queue_success(db_conn):
    """Test successful queue leave."""
    join_queue(db_conn, 1)
    result = leave_queue(db_conn, 1)

    assert result['status'] == 'left'

    # Verify removed from database
    cursor = db_conn.cursor()
    queue_entry = cursor.execute(
        "SELECT * FROM queue WHERE character_id = ?", (1,)
    ).fetchone()

    assert queue_entry is None


def test_leave_queue_not_in_queue(db_conn):
    """Test leaving queue when not in queue."""
    with pytest.raises(ValidationError, match="Not in queue"):
        leave_queue(db_conn, 1)


def test_find_match_no_match(db_conn):
    """Test find_match when no suitable opponent."""
    join_queue(db_conn, 3)  # Rating 1500

    # Try to find match for character 1 (rating 1000) with tight range
    opponent = find_match(db_conn, 1, 1000, 0)

    assert opponent is None  # No match within ±100 range


def test_find_match_with_range_expansion(db_conn):
    """Test find_match with expanded rating range."""
    join_queue(db_conn, 3)  # Rating 1500

    # Try to find match for character 1 (rating 1000) with expanded range
    opponent = find_match(db_conn, 1, 1000, 50)  # No limit

    assert opponent == 3  # Should find match with any rating


def test_find_match_priority(db_conn):
    """Test that closer rating is prioritized."""
    # Add both to queue
    join_queue(db_conn, 2)  # Rating 1050
    join_queue(db_conn, 3)  # Rating 1500

    # Find match for character 1 (rating 1000)
    opponent = find_match(db_conn, 1, 1000, 50)  # No limit

    assert opponent == 2  # Should match with closer rating


def test_create_battle_success(db_conn):
    """Test successful battle creation."""
    # Manually add both to queue (bypass automatic matching)
    cursor = db_conn.cursor()
    cursor.execute("INSERT INTO queue (character_id, rating) VALUES (1, 1000)")
    cursor.execute("INSERT INTO queue (character_id, rating) VALUES (2, 1000)")
    db_conn.commit()

    battle_id = create_battle(db_conn, 1, 2)

    assert battle_id > 0

    # Verify battle created
    battle = cursor.execute(
        "SELECT * FROM battles WHERE id = ?", (battle_id,)
    ).fetchone()

    assert battle is not None
    assert battle['player1_id'] == 1
    assert battle['player2_id'] == 2
    assert battle['status'] == 'in_progress'

    # Verify both removed from queue
    queue_count = cursor.execute("SELECT COUNT(*) as count FROM queue").fetchone()['count']
    assert queue_count == 0


def test_create_battle_player_not_in_queue(db_conn):
    """Test battle creation fails when player not in queue."""
    join_queue(db_conn, 1)

    # Try to create battle without player 2 in queue
    with pytest.raises(BattleError):
        create_battle(db_conn, 1, 2)


def test_matchmaking_flow(db_conn):
    """Test complete matchmaking flow."""
    # Player 1 joins, waits
    result1 = join_queue(db_conn, 1)
    assert result1['status'] == 'waiting'

    # Player 2 joins, matches with player 1
    result2 = join_queue(db_conn, 2)
    assert result2['status'] == 'matched'
    assert result2['opponent_id'] == 1

    # Verify battle was created
    cursor = db_conn.cursor()
    battle = cursor.execute(
        "SELECT * FROM battles WHERE id = ?", (result2['battle_id'],)
    ).fetchone()

    assert battle is not None
    assert battle['status'] == 'in_progress'

    # Verify queue is empty
    queue_count = cursor.execute("SELECT COUNT(*) as count FROM queue").fetchone()['count']
    assert queue_count == 0
