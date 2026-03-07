/**
 * Character management API routes (CRUD only)
 * Game logic and LLM calls are handled by MCP server locally
 */

import express from 'express';
import { query, run, transaction } from '../db.js';
import {
  validateCharacterName,
  validateCharacterPrompt,
  validateStat,
  validateTotalPoints,
  validateAbilityIds,
  validatePositiveInteger
} from '../utils/validation.js';
import { authMiddleware } from '../middleware/auth.js';
import {
  ValidationError,
  NotFoundError,
  DatabaseError
} from '../middleware/error_handler.js';

const router = express.Router();

/**
 * Get all abilities
 * GET /api/abilities
 */
router.get('/abilities', async (req, res, next) => {
  try {
    const abilities = await query(
      `SELECT id, name, description, effect_type, power, cost, cooldown
       FROM abilities
       ORDER BY id`
    );

    res.json({
      abilities: abilities.map(row => ({
        id: row.id,
        name: row.name,
        description: row.description,
        effect_type: row.effect_type,
        power: row.power,
        cost: row.cost,
        cooldown: row.cooldown
      }))
    });
  } catch (error) {
    next(error);
  }
});

/**
 * Create a new character
 * POST /api/characters
 * Body: {
 *   account_id: number,
 *   name: string,
 *   prompt: string,
 *   base_hp: number,
 *   base_attack: number,
 *   base_defense: number,
 *   base_speed: number,
 *   ability_ids?: number[]
 * }
 *
 * Note: MCP server calculates stats locally and sends computed values
 */
router.post('/', authMiddleware, async (req, res, next) => {
  try {
    const {
      account_id,
      name,
      prompt,
      base_hp,
      base_attack,
      base_defense,
      base_speed,
      ability_ids = []
    } = req.body;

    // Validate account ownership
    if (parseInt(account_id) !== req.user.accountId) {
      throw new ValidationError('You can only create characters for your own account');
    }

    // Validate inputs
    validateCharacterName(name);
    validateCharacterPrompt(prompt);
    validateStat(base_hp, 10, 100, 'base_hp');
    validateStat(base_attack, 10, 100, 'base_attack');
    validateStat(base_defense, 10, 100, 'base_defense');
    validateStat(base_speed, 10, 100, 'base_speed');
    validateTotalPoints({ base_hp, base_attack, base_defense, base_speed },
                        base_hp + base_attack + base_defense + base_speed);

    // Validate total is within range
    const total = base_hp + base_attack + base_defense + base_speed;
    if (total < 280 || total > 400) {
      throw new ValidationError(`Total stat points must be between 280-400 (current: ${total})`);
    }

    // Validate abilities
    validateAbilityIds(ability_ids, 3);

    // Verify ability IDs exist
    if (ability_ids.length > 0) {
      const placeholders = ability_ids.map(() => '?').join(',');
      const existingAbilities = await query(
        `SELECT id FROM abilities WHERE id IN (${placeholders})`,
        ability_ids
      );

      const existingIds = new Set(existingAbilities.map(row => row.id));
      for (const abilityId of ability_ids) {
        if (!existingIds.has(abilityId)) {
          throw new ValidationError(`Ability ID ${abilityId} does not exist`);
        }
      }
    }

    // Compute stats (level 1)
    const level = 1;
    const multiplier = 1 + (level - 1) * 0.1;
    const computed_hp = Math.floor(base_hp * multiplier);
    const computed_attack = Math.floor(base_attack * multiplier);
    const computed_defense = Math.floor(base_defense * multiplier);
    const computed_speed = Math.floor(base_speed * multiplier);

    // Create character in transaction
    const result = await transaction(async () => {
      // Insert character
      const charResult = await run(
        `INSERT INTO characters (
          account_id, name, prompt, level,
          base_hp, base_attack, base_defense, base_speed,
          computed_hp, computed_attack, computed_defense, computed_speed,
          created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)`,
        [
          account_id, name, prompt, level,
          base_hp, base_attack, base_defense, base_speed,
          computed_hp, computed_attack, computed_defense, computed_speed
        ]
      );

      const characterId = charResult.lastID;

      // Initialize stats
      await run(
        'INSERT INTO stats (character_id) VALUES (?)',
        [characterId]
      );

      // Insert abilities
      if (ability_ids.length > 0) {
        for (const abilityId of ability_ids) {
          await run(
            'INSERT INTO character_abilities (character_id, ability_id) VALUES (?, ?)',
            [characterId, abilityId]
          );
        }
      }

      // Get abilities info
      let abilities = [];
      if (ability_ids.length > 0) {
        const placeholders = ability_ids.map(() => '?').join(',');
        abilities = await query(
          `SELECT id, name, description, effect_type, power
           FROM abilities
           WHERE id IN (${placeholders})`,
          ability_ids
        );
      }

      return {
        character_id: characterId,
        name,
        level,
        computed_stats: {
          hp: computed_hp,
          attack: computed_attack,
          defense: computed_defense,
          speed: computed_speed
        },
        abilities: abilities.map(row => ({
          id: row.id,
          name: row.name,
          description: row.description,
          effect_type: row.effect_type,
          power: row.power
        }))
      };
    });

    res.status(201).json({
      ...result,
      message: `Character '${name}' created successfully`
    });

  } catch (error) {
    next(error);
  }
});

/**
 * Get character info
 * GET /api/characters/:id
 */
router.get('/:id', async (req, res, next) => {
  try {
    const characterId = parseInt(req.params.id);
    validatePositiveInteger(characterId, 'character_id');

    // Get character
    const characters = await query(
      `SELECT id, account_id, name, prompt, level,
              base_hp, base_attack, base_defense, base_speed,
              computed_hp, computed_attack, computed_defense, computed_speed,
              created_at
       FROM characters
       WHERE id = ?`,
      [characterId]
    );

    if (characters.length === 0) {
      throw new NotFoundError('Character');
    }

    const character = characters[0];

    // Get abilities
    const abilities = await query(
      `SELECT a.id, a.name, a.description, a.effect_type, a.power
       FROM abilities a
       JOIN character_abilities ca ON a.id = ca.ability_id
       WHERE ca.character_id = ?`,
      [characterId]
    );

    res.json({
      character_id: character.id,
      account_id: character.account_id,
      name: character.name,
      prompt: character.prompt,
      level: character.level,
      base_stats: {
        hp: character.base_hp,
        attack: character.base_attack,
        defense: character.base_defense,
        speed: character.base_speed
      },
      computed_stats: {
        hp: character.computed_hp,
        attack: character.computed_attack,
        defense: character.computed_defense,
        speed: character.computed_speed
      },
      abilities: abilities.map(row => ({
        id: row.id,
        name: row.name,
        description: row.description,
        effect_type: row.effect_type,
        power: row.power
      })),
      created_at: character.created_at
    });

  } catch (error) {
    next(error);
  }
});

/**
 * Get battle history for a character
 * GET /api/characters/:id/battles?limit=10
 */
router.get('/:id/battles', async (req, res, next) => {
  try {
    const characterId = parseInt(req.params.id);
    validatePositiveInteger(characterId, 'character_id');

    const limit = Math.min(parseInt(req.query.limit) || 10, 50);

    const chars = await query('SELECT id FROM characters WHERE id = ?', [characterId]);
    if (chars.length === 0) throw new NotFoundError('Character');

    const battles = await query(
      `SELECT b.id, b.player1_id, b.player2_id, b.winner_id, b.status,
              b.current_turn, b.started_at,
              c1.name as player1_name, c2.name as player2_name,
              CASE
                WHEN b.winner_id = ? THEN 'win'
                WHEN b.status = 'finished' AND b.winner_id IS NULL THEN 'draw'
                WHEN b.status = 'finished' THEN 'loss'
                ELSE b.status
              END as result
       FROM battles b
       JOIN characters c1 ON b.player1_id = c1.id
       JOIN characters c2 ON b.player2_id = c2.id
       WHERE (b.player1_id = ? OR b.player2_id = ?)
       ORDER BY b.started_at DESC
       LIMIT ?`,
      [characterId, characterId, characterId, limit]
    );

    res.json({
      character_id: characterId,
      battles: battles.map(row => ({
        battle_id: row.id,
        opponent_id: row.player1_id === characterId ? row.player2_id : row.player1_id,
        opponent_name: row.player1_id === characterId ? row.player2_name : row.player1_name,
        result: row.result,
        turns: row.current_turn,
        status: row.status,
        started_at: row.started_at
      }))
    });

  } catch (error) {
    next(error);
  }
});

/**
 * List characters by account
 * GET /api/characters?account_id=1
 */
router.get('/', async (req, res, next) => {
  try {
    const accountId = req.query.account_id;

    if (!accountId) {
      throw new ValidationError('account_id query parameter is required');
    }

    validatePositiveInteger(parseInt(accountId), 'account_id');

    const characters = await query(
      `SELECT id, name, level,
              computed_hp, computed_attack, computed_defense, computed_speed,
              created_at
       FROM characters
       WHERE account_id = ?
       ORDER BY created_at DESC`,
      [accountId]
    );

    res.json({
      characters: characters.map(row => ({
        id: row.id,
        name: row.name,
        level: row.level,
        hp: row.computed_hp,
        attack: row.computed_attack,
        defense: row.computed_defense,
        speed: row.computed_speed,
        created_at: row.created_at
      }))
    });

  } catch (error) {
    next(error);
  }
});

export default router;
