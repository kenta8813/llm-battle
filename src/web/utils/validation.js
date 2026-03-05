/**
 * Common validation utilities
 */

import { ValidationError } from '../middleware/error_handler.js';

/**
 * Validate username
 * @param {string} username - Username to validate
 * @throws {ValidationError} If validation fails
 */
export function validateUsername(username) {
  if (!username) {
    throw new ValidationError('Username is required');
  }

  if (typeof username !== 'string') {
    throw new ValidationError('Username must be a string');
  }

  if (username.length < 1 || username.length > 50) {
    throw new ValidationError('Username must be between 1 and 50 characters');
  }

  // Allow only alphanumeric characters and underscores
  if (!/^[a-zA-Z0-9_]+$/.test(username)) {
    throw new ValidationError('Username can only contain letters, numbers, and underscores');
  }

  return true;
}

/**
 * Validate character name
 * @param {string} name - Character name to validate
 * @throws {ValidationError} If validation fails
 */
export function validateCharacterName(name) {
  if (!name) {
    throw new ValidationError('Character name is required');
  }

  if (typeof name !== 'string') {
    throw new ValidationError('Character name must be a string');
  }

  if (name.length < 1 || name.length > 50) {
    throw new ValidationError('Character name must be between 1 and 50 characters');
  }

  return true;
}

/**
 * Validate character prompt
 * @param {string} prompt - Character prompt to validate
 * @throws {ValidationError} If validation fails
 */
export function validateCharacterPrompt(prompt) {
  if (!prompt) {
    throw new ValidationError('Character prompt is required');
  }

  if (typeof prompt !== 'string') {
    throw new ValidationError('Character prompt must be a string');
  }

  if (prompt.length < 1 || prompt.length > 1000) {
    throw new ValidationError('Character prompt must be between 1 and 1000 characters');
  }

  return true;
}

/**
 * Validate stat value
 * @param {number} value - Stat value to validate
 * @param {number} min - Minimum allowed value
 * @param {number} max - Maximum allowed value
 * @param {string} name - Name of the stat (for error message)
 * @throws {ValidationError} If validation fails
 */
export function validateStat(value, min, max, name) {
  if (value === undefined || value === null) {
    throw new ValidationError(`${name} is required`);
  }

  if (typeof value !== 'number' || isNaN(value)) {
    throw new ValidationError(`${name} must be a number`);
  }

  if (!Number.isInteger(value)) {
    throw new ValidationError(`${name} must be an integer`);
  }

  if (value < min || value > max) {
    throw new ValidationError(`${name} must be between ${min} and ${max}`);
  }

  return true;
}

/**
 * Validate total points for character stats
 * @param {Object} stats - Character stats object
 * @param {number} expectedTotal - Expected total points
 * @throws {ValidationError} If validation fails
 */
export function validateTotalPoints(stats, expectedTotal) {
  const { base_hp, base_attack, base_defense, base_speed } = stats;

  if ([base_hp, base_attack, base_defense, base_speed].some(v => v === undefined || v === null)) {
    throw new ValidationError('All stats (hp, attack, defense, speed) are required');
  }

  const total = base_hp + base_attack + base_defense + base_speed;

  if (total !== expectedTotal) {
    throw new ValidationError(
      `Total stat points must equal ${expectedTotal} (current: ${total})`
    );
  }

  return true;
}

/**
 * Validate ability IDs
 * @param {Array<number>} abilityIds - Array of ability IDs
 * @param {number} maxCount - Maximum number of abilities allowed
 * @throws {ValidationError} If validation fails
 */
export function validateAbilityIds(abilityIds, maxCount = 3) {
  if (!Array.isArray(abilityIds)) {
    throw new ValidationError('ability_ids must be an array');
  }

  if (abilityIds.length > maxCount) {
    throw new ValidationError(`Cannot select more than ${maxCount} abilities`);
  }

  // Check for duplicates
  const uniqueIds = new Set(abilityIds);
  if (uniqueIds.size !== abilityIds.length) {
    throw new ValidationError('Duplicate ability IDs are not allowed');
  }

  // Validate each ID is a positive integer
  for (const id of abilityIds) {
    if (typeof id !== 'number' || !Number.isInteger(id) || id < 1) {
      throw new ValidationError('Each ability ID must be a positive integer');
    }
  }

  return true;
}

/**
 * Validate action type
 * @param {string} actionType - Action type to validate
 * @throws {ValidationError} If validation fails
 */
export function validateActionType(actionType) {
  const validActions = ['attack', 'defend', 'dodge', 'ability'];

  if (!actionType) {
    throw new ValidationError('Action type is required');
  }

  if (!validActions.includes(actionType)) {
    throw new ValidationError(
      `Invalid action type. Must be one of: ${validActions.join(', ')}`
    );
  }

  return true;
}

/**
 * Validate positive integer
 * @param {*} value - Value to validate
 * @param {string} name - Name of the value (for error message)
 * @throws {ValidationError} If validation fails
 */
export function validatePositiveInteger(value, name) {
  if (value === undefined || value === null) {
    throw new ValidationError(`${name} is required`);
  }

  if (typeof value !== 'number' || !Number.isInteger(value) || value < 1) {
    throw new ValidationError(`${name} must be a positive integer`);
  }

  return true;
}

/**
 * Validate boolean
 * @param {*} value - Value to validate
 * @param {string} name - Name of the value (for error message)
 * @param {boolean} required - Whether the value is required
 * @throws {ValidationError} If validation fails
 */
export function validateBoolean(value, name, required = false) {
  if (value === undefined || value === null) {
    if (required) {
      throw new ValidationError(`${name} is required`);
    }
    return true;
  }

  if (typeof value !== 'boolean') {
    throw new ValidationError(`${name} must be a boolean`);
  }

  return true;
}
