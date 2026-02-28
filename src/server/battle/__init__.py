"""Battle module for LLM Battle Game."""

from .logic import (
    calculate_damage,
    apply_ability_effect,
    resolve_turn,
    check_victory,
    get_action_order,
)

__all__ = [
    'calculate_damage',
    'apply_ability_effect',
    'resolve_turn',
    'check_victory',
    'get_action_order',
]
