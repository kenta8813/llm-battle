"""Battle logic implementation for LLM Battle Game."""

import random
import sqlite3
from typing import Optional, Dict, Any, Tuple
import logging

logger = logging.getLogger('llmbattle.battle')


def calculate_damage(
    attacker: Dict[str, Any],
    defender: Dict[str, Any],
    action_type: str,
    ability: Optional[Dict[str, Any]] = None
) -> int:
    """
    Calculate damage dealt by attacker to defender.

    Args:
        attacker: Attacker character stats
        defender: Defender character stats
        action_type: Type of action ('attack', 'defend', 'dodge', 'ability')
        ability: Ability data if using ability

    Returns:
        Final damage amount (0 if dodged or no damage)
    """
    # Handle dodge
    if defender.get('action') == 'dodge':
        dodge_base_rate = 0.5
        speed_diff = defender['computed_speed'] - attacker['computed_speed']
        dodge_rate = dodge_base_rate + (speed_diff / 200.0)
        dodge_rate = max(0.1, min(0.9, dodge_rate))

        if random.random() < dodge_rate:
            logger.debug(f"Dodge successful! Rate: {dodge_rate:.2%}")
            return 0

    # Calculate base damage
    if action_type == 'ability' and ability:
        # Ability damage
        if ability['effect_type'] != 'damage':
            return 0

        power_multiplier = ability['power'] / 100.0
        base_damage = attacker['computed_attack'] * power_multiplier
    elif action_type == 'attack':
        # Normal attack
        base_damage = attacker['computed_attack'] * 1.0
    else:
        # Defend or other non-damaging actions
        return 0

    # Defense calculation
    defense_ratio = defender['computed_defense'] / (defender['computed_defense'] + 100)
    damage_reduction = base_damage * defense_ratio
    final_damage = base_damage - damage_reduction

    # Apply defend modifier
    if defender.get('action') == 'defend':
        final_damage = final_damage * 0.5

    # Random variation (±10%)
    random_factor = random.uniform(0.9, 1.1)
    final_damage = final_damage * random_factor

    # Critical hit (10% chance)
    if random.random() < 0.1:
        final_damage = final_damage * 1.5
        logger.debug("Critical hit!")

    # Minimum damage
    final_damage = max(1, int(final_damage))

    return final_damage


def apply_ability_effect(
    db: sqlite3.Connection,
    battle_id: int,
    character_id: int,
    ability: Dict[str, Any],
    target_id: int,
    battle_state: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Apply ability effect to battle state.

    Args:
        db: Database connection
        battle_id: Battle ID
        character_id: Character using ability
        ability: Ability data
        target_id: Target character ID
        battle_state: Current battle state

    Returns:
        Result of ability application
    """
    result = {
        'ability_name': ability['name'],
        'effect_type': ability['effect_type'],
        'success': True,
        'effects': []
    }

    effect_type = ability['effect_type']
    power = ability['power']

    if effect_type == 'heal':
        # Heal HP
        character_key = 'player1' if character_id == battle_state['player1_id'] else 'player2'
        current_hp = battle_state[f'{character_key}_hp']
        max_hp = battle_state[f'{character_key}_max_hp']

        heal_amount = int(max_hp * (power / 100.0))
        new_hp = min(current_hp + heal_amount, max_hp)

        battle_state[f'{character_key}_hp'] = new_hp
        result['heal_amount'] = heal_amount
        result['effects'].append(f"Healed {heal_amount} HP")

    elif effect_type == 'buff':
        # Apply buff (stored in battle state)
        buff_key = f"{ability['name'].lower().replace(' ', '_')}_buff"
        battle_state.setdefault('buffs', {})[character_id] = {
            'type': buff_key,
            'power': power,
            'duration': 1
        }
        result['effects'].append(f"Buff applied: {ability['name']}")

    elif effect_type == 'debuff':
        # Apply debuff to target
        debuff_key = f"{ability['name'].lower().replace(' ', '_')}_debuff"
        battle_state.setdefault('debuffs', {})[target_id] = {
            'type': debuff_key,
            'power': power,
            'duration': 1
        }
        result['effects'].append(f"Debuff applied to opponent: {ability['name']}")

    # Set cooldown
    cooldown_key = f"cooldown_{character_id}_{ability['id']}"
    battle_state.setdefault('cooldowns', {})[cooldown_key] = ability.get('cooldown', 0)

    return result


def get_action_order(player1: Dict[str, Any], player2: Dict[str, Any]) -> Tuple[int, int]:
    """
    Determine action order based on speed.

    Args:
        player1: Player 1 data with speed
        player2: Player 2 data with speed

    Returns:
        Tuple of (first_player_id, second_player_id)
    """
    speed1 = player1['computed_speed']
    speed2 = player2['computed_speed']

    if speed1 > speed2:
        return (player1['id'], player2['id'])
    elif speed2 > speed1:
        return (player2['id'], player1['id'])
    else:
        # Same speed - random
        if random.random() < 0.5:
            return (player1['id'], player2['id'])
        else:
            return (player2['id'], player1['id'])


def resolve_turn(
    db: sqlite3.Connection,
    battle_id: int,
    player1_action: Dict[str, Any],
    player2_action: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Resolve a battle turn with both players' actions.

    Args:
        db: Database connection
        battle_id: Battle ID
        player1_action: Player 1's action {'action': str, 'ability_id': Optional[int]}
        player2_action: Player 2's action {'action': str, 'ability_id': Optional[int]}

    Returns:
        Turn result with damage dealt, HP changes, etc.
    """
    cursor = db.cursor()

    # Get battle state
    battle = cursor.execute(
        "SELECT * FROM battles WHERE id = ?",
        (battle_id,)
    ).fetchone()

    if not battle:
        raise ValueError(f"Battle {battle_id} not found")

    # Get character data
    player1 = cursor.execute(
        "SELECT * FROM characters WHERE id = ?",
        (battle['player1_id'],)
    ).fetchone()

    player2 = cursor.execute(
        "SELECT * FROM characters WHERE id = ?",
        (battle['player2_id'],)
    ).fetchone()

    # Initialize battle state if first turn
    if battle['current_turn'] == 0:
        battle_state = {
            'player1_id': player1['id'],
            'player2_id': player2['id'],
            'player1_hp': player1['computed_hp'],
            'player2_hp': player2['computed_hp'],
            'player1_max_hp': player1['computed_hp'],
            'player2_max_hp': player2['computed_hp'],
            'cooldowns': {},
            'buffs': {},
            'debuffs': {}
        }
    else:
        # Get latest turn state
        last_turn = cursor.execute(
            "SELECT * FROM battle_turns WHERE battle_id = ? ORDER BY turn_number DESC LIMIT 1",
            (battle_id,)
        ).fetchone()

        battle_state = {
            'player1_id': player1['id'],
            'player2_id': player2['id'],
            'player1_hp': last_turn['player1_hp_after'],
            'player2_hp': last_turn['player2_hp_after'],
            'player1_max_hp': player1['computed_hp'],
            'player2_max_hp': player2['computed_hp'],
            'cooldowns': {},
            'buffs': {},
            'debuffs': {}
        }

    # Prepare character data for damage calculation
    char1_data = dict(player1)
    char1_data['action'] = player1_action['action']

    char2_data = dict(player2)
    char2_data['action'] = player2_action['action']

    # Get abilities if used
    ability1 = None
    ability2 = None

    if player1_action.get('ability_id'):
        ability1 = cursor.execute(
            "SELECT * FROM abilities WHERE id = ?",
            (player1_action['ability_id'],)
        ).fetchone()

    if player2_action.get('ability_id'):
        ability2 = cursor.execute(
            "SELECT * FROM abilities WHERE id = ?",
            (player2_action['ability_id'],)
        ).fetchone()

    # Determine action order
    first_id, second_id = get_action_order(char1_data, char2_data)

    # Initialize turn result
    turn_result = {
        'turn_number': battle['current_turn'] + 1,
        'player1_action': player1_action['action'],
        'player2_action': player2_action['action'],
        'player1_damage_dealt': 0,
        'player1_damage_received': 0,
        'player2_damage_dealt': 0,
        'player2_damage_received': 0,
        'effects': []
    }

    # Resolve actions in order
    for i, attacker_id in enumerate([first_id, second_id]):
        if attacker_id == player1['id']:
            attacker_data = char1_data
            defender_data = char2_data
            action = player1_action
            ability = ability1
            attacker_key = 'player1'
            defender_key = 'player2'
        else:
            attacker_data = char2_data
            defender_data = char1_data
            action = player2_action
            ability = ability2
            attacker_key = 'player2'
            defender_key = 'player1'

        # Check if defender is already defeated
        if battle_state[f'{defender_key}_hp'] <= 0:
            continue

        # Apply action
        if action['action'] == 'ability' and ability:
            # Apply ability effect
            effect_result = apply_ability_effect(
                db, battle_id, attacker_id, dict(ability),
                battle_state[f'{defender_key}_id'], battle_state
            )
            turn_result['effects'].append(effect_result)

            # Calculate damage if damage ability
            if ability['effect_type'] == 'damage':
                damage = calculate_damage(attacker_data, defender_data, 'ability', dict(ability))
                battle_state[f'{defender_key}_hp'] -= damage

                turn_result[f'{attacker_key}_damage_dealt'] += damage
                turn_result[f'{defender_key}_damage_received'] += damage

        elif action['action'] == 'attack':
            # Normal attack
            damage = calculate_damage(attacker_data, defender_data, 'attack')
            battle_state[f'{defender_key}_hp'] -= damage

            turn_result[f'{attacker_key}_damage_dealt'] += damage
            turn_result[f'{defender_key}_damage_received'] += damage

    # Update HP bounds
    battle_state['player1_hp'] = max(0, min(battle_state['player1_max_hp'], battle_state['player1_hp']))
    battle_state['player2_hp'] = max(0, min(battle_state['player2_max_hp'], battle_state['player2_hp']))

    # Save turn to database
    turn_number = battle['current_turn'] + 1

    cursor.execute("""
        INSERT INTO battle_turns (
            battle_id, turn_number,
            player1_action, player1_ability_id, player1_damage_dealt, player1_damage_received, player1_hp_after,
            player2_action, player2_ability_id, player2_damage_dealt, player2_damage_received, player2_hp_after,
            turn_result
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        battle_id, turn_number,
        player1_action['action'], player1_action.get('ability_id'),
        turn_result['player1_damage_dealt'], turn_result['player1_damage_received'], battle_state['player1_hp'],
        player2_action['action'], player2_action.get('ability_id'),
        turn_result['player2_damage_dealt'], turn_result['player2_damage_received'], battle_state['player2_hp'],
        str(turn_result)
    ))

    # Update battle current turn
    cursor.execute(
        "UPDATE battles SET current_turn = ? WHERE id = ?",
        (turn_number, battle_id)
    )

    db.commit()

    # Add HP info to result
    turn_result['player1_hp_after'] = battle_state['player1_hp']
    turn_result['player2_hp_after'] = battle_state['player2_hp']

    logger.info(f"Turn {turn_number} resolved: P1 HP={battle_state['player1_hp']}, P2 HP={battle_state['player2_hp']}")

    return turn_result


def check_victory(db: sqlite3.Connection, battle_id: int) -> Optional[int]:
    """
    Check if battle has a winner.

    Args:
        db: Database connection
        battle_id: Battle ID

    Returns:
        Winner character ID, or None if battle continues, or 0 for draw
    """
    cursor = db.cursor()

    battle = cursor.execute(
        "SELECT * FROM battles WHERE id = ?",
        (battle_id,)
    ).fetchone()

    if not battle:
        raise ValueError(f"Battle {battle_id} not found")

    # Get latest turn
    last_turn = cursor.execute(
        "SELECT * FROM battle_turns WHERE battle_id = ? ORDER BY turn_number DESC LIMIT 1",
        (battle_id,)
    ).fetchone()

    if not last_turn:
        return None

    player1_hp = last_turn['player1_hp_after']
    player2_hp = last_turn['player2_hp_after']

    # Check HP-based victory
    if player1_hp <= 0 and player2_hp <= 0:
        return 0  # Draw
    elif player1_hp <= 0:
        return battle['player2_id']
    elif player2_hp <= 0:
        return battle['player1_id']

    # Check max turns
    if battle['current_turn'] >= battle['max_turns']:
        if player1_hp > player2_hp:
            return battle['player1_id']
        elif player2_hp > player1_hp:
            return battle['player2_id']
        else:
            return 0  # Draw

    return None  # Battle continues
