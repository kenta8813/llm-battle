/**
 * Battle API routes (CRUD only)
 * Battle logic is handled by MCP server locally
 */

import express from 'express';
import { query, run, transaction } from '../db.js';
import { validatePositiveInteger, validateActionType } from '../utils/validation.js';
import { authMiddleware } from '../middleware/auth.js';
import {
  ValidationError,
  NotFoundError
} from '../middleware/error_handler.js';
import { io } from '../server.js';

const router = express.Router();

/**
 * Create a new battle
 * POST /api/battles
 * Body: { player1_id: number, player2_id: number }
 *
 * Note: Called by MCP server after match is found
 */
router.post('/', authMiddleware, async (req, res, next) => {
  try {
    const { player1_id, player2_id } = req.body;

    validatePositiveInteger(player1_id, 'player1_id');
    validatePositiveInteger(player2_id, 'player2_id');

    if (player1_id === player2_id) {
      throw new ValidationError('Cannot battle against yourself');
    }

    // Verify characters exist
    const chars = await query(
      'SELECT id, computed_hp FROM characters WHERE id IN (?, ?)',
      [player1_id, player2_id]
    );

    if (chars.length !== 2) {
      throw new NotFoundError('One or both characters not found');
    }

    const char1 = chars.find(c => c.id === player1_id);
    const char2 = chars.find(c => c.id === player2_id);

    // Create battle in transaction
    const result = await transaction(async () => {
      // Create battle
      const battleResult = await run(
        `INSERT INTO battles (
          player1_id, player2_id, current_turn,
          player1_hp, player2_hp, player1_max_hp, player2_max_hp,
          status, created_at, updated_at
        )
        VALUES (?, ?, 0, ?, ?, ?, ?, 'in_progress', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)`,
        [player1_id, player2_id, char1.computed_hp, char2.computed_hp, char1.computed_hp, char2.computed_hp]
      );

      const battleId = battleResult.lastID;

      // Remove both characters from queue
      await run('DELETE FROM queue WHERE character_id IN (?, ?)', [player1_id, player2_id]);

      return { battle_id: battleId };
    });

    // Emit WebSocket event
    io.emit('battle_started', {
      battle_id: result.battle_id,
      player1_id,
      player2_id
    });

    res.status(201).json({
      ...result,
      message: 'Battle created successfully'
    });

  } catch (error) {
    next(error);
  }
});

/**
 * Record a turn result
 * POST /api/battles/:id/turns
 * Body: {
 *   turn_number: number,
 *   player1_action: string,
 *   player2_action: string,
 *   player1_damage: number,
 *   player2_damage: number,
 *   player1_hp_after: number,
 *   player2_hp_after: number,
 *   turn_log: string,
 *   winner_id?: number
 * }
 *
 * Note: Turn results are calculated by MCP server locally
 */
router.post('/:id/turns', authMiddleware, async (req, res, next) => {
  try {
    const battleId = parseInt(req.params.id);
    validatePositiveInteger(battleId, 'battle_id');

    const {
      turn_number,
      player1_action,
      player2_action,
      player1_damage,
      player2_damage,
      player1_hp_after,
      player2_hp_after,
      turn_log,
      winner_id
    } = req.body;

    validatePositiveInteger(turn_number, 'turn_number');
    validateActionType(player1_action);
    validateActionType(player2_action);

    // Verify battle exists
    const battles = await query(
      'SELECT id, player1_id, player2_id, status FROM battles WHERE id = ?',
      [battleId]
    );

    if (battles.length === 0) {
      throw new NotFoundError('Battle');
    }

    const battle = battles[0];

    if (battle.status !== 'in_progress') {
      throw new ValidationError('Battle is not in progress');
    }

    // Record turn in transaction
    const result = await transaction(async () => {
      // Insert turn
      await run(
        `INSERT INTO battle_turns (
          battle_id, turn_number,
          player1_action, player2_action,
          player1_damage_dealt, player2_damage_dealt,
          player1_hp_after, player2_hp_after,
          turn_log, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)`,
        [
          battleId, turn_number,
          player1_action, player2_action,
          player1_damage, player2_damage,
          player1_hp_after, player2_hp_after,
          turn_log
        ]
      );

      // Update battle
      if (winner_id) {
        // Battle ended
        await run(
          `UPDATE battles
           SET current_turn = ?,
               player1_hp = ?,
               player2_hp = ?,
               winner_id = ?,
               status = 'finished',
               updated_at = CURRENT_TIMESTAMP
           WHERE id = ?`,
          [turn_number, player1_hp_after, player2_hp_after, winner_id, battleId]
        );

        // Update stats
        const loser_id = winner_id === battle.player1_id ? battle.player2_id : battle.player1_id;

        await run(
          `UPDATE stats
           SET total_battles = total_battles + 1,
               wins = wins + 1,
               rating = rating + 25
           WHERE character_id = ?`,
          [winner_id]
        );

        await run(
          `UPDATE stats
           SET total_battles = total_battles + 1,
               losses = losses + 1,
               rating = CASE WHEN rating > 25 THEN rating - 25 ELSE rating END
           WHERE character_id = ?`,
          [loser_id]
        );

        return { status: 'finished', winner_id };
      } else {
        // Battle continues
        await run(
          `UPDATE battles
           SET current_turn = ?,
               player1_hp = ?,
               player2_hp = ?,
               updated_at = CURRENT_TIMESTAMP
           WHERE id = ?`,
          [turn_number, player1_hp_after, player2_hp_after, battleId]
        );

        return { status: 'in_progress' };
      }
    });

    // Emit WebSocket event
    io.to(`battle_${battleId}`).emit('turn_executed', {
      battle_id: battleId,
      turn_number,
      player1_action,
      player2_action,
      player1_hp: player1_hp_after,
      player2_hp: player2_hp_after,
      turn_log
    });

    if (winner_id) {
      io.to(`battle_${battleId}`).emit('battle_ended', {
        battle_id: battleId,
        winner_id
      });
    }

    res.json({
      battle_id: battleId,
      turn_number,
      ...result,
      message: winner_id ? 'Battle finished' : 'Turn recorded'
    });

  } catch (error) {
    next(error);
  }
});

/**
 * Get battle status
 * GET /api/battles/:id
 */
router.get('/:id', async (req, res, next) => {
  try {
    const battleId = parseInt(req.params.id);
    validatePositiveInteger(battleId, 'battle_id');

    // Get battle
    const battles = await query(
      `SELECT b.*,
              c1.name as player1_name,
              c2.name as player2_name
       FROM battles b
       JOIN characters c1 ON b.player1_id = c1.id
       JOIN characters c2 ON b.player2_id = c2.id
       WHERE b.id = ?`,
      [battleId]
    );

    if (battles.length === 0) {
      throw new NotFoundError('Battle');
    }

    const battle = battles[0];

    res.json({
      battle_id: battle.id,
      player1: {
        id: battle.player1_id,
        name: battle.player1_name,
        hp: battle.player1_hp,
        max_hp: battle.player1_max_hp
      },
      player2: {
        id: battle.player2_id,
        name: battle.player2_name,
        hp: battle.player2_hp,
        max_hp: battle.player2_max_hp
      },
      current_turn: battle.current_turn,
      status: battle.status,
      winner_id: battle.winner_id,
      created_at: battle.created_at,
      updated_at: battle.updated_at
    });

  } catch (error) {
    next(error);
  }
});

/**
 * Get battle turns
 * GET /api/battles/:id/turns
 */
router.get('/:id/turns', async (req, res, next) => {
  try {
    const battleId = parseInt(req.params.id);
    validatePositiveInteger(battleId, 'battle_id');

    const turns = await query(
      `SELECT turn_number, player1_action, player2_action,
              player1_damage_dealt, player2_damage_dealt,
              player1_hp_after, player2_hp_after,
              turn_log, created_at
       FROM battle_turns
       WHERE battle_id = ?
       ORDER BY turn_number ASC`,
      [battleId]
    );

    res.json({
      battle_id: battleId,
      turns: turns.map(row => ({
        turn_number: row.turn_number,
        player1_action: row.player1_action,
        player2_action: row.player2_action,
        player1_damage: row.player1_damage_dealt,
        player2_damage: row.player2_damage_dealt,
        player1_hp: row.player1_hp_after,
        player2_hp: row.player2_hp_after,
        turn_log: row.turn_log,
        created_at: row.created_at
      }))
    });

  } catch (error) {
    next(error);
  }
});

export default router;
