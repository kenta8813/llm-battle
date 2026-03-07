/**
 * Matchmaking API routes (CRUD only)
 * Matching logic is handled by MCP server locally
 */

import express from 'express';
import { query, run, transaction } from '../db.js';
import { validatePositiveInteger } from '../utils/validation.js';
import { authMiddleware } from '../middleware/auth.js';
import {
  ValidationError,
  NotFoundError
} from '../middleware/error_handler.js';
import { io } from '../server.js';

const router = express.Router();

/**
 * Join matchmaking queue
 * POST /api/queue
 * Body: { character_id: number }
 */
router.post('/', authMiddleware, async (req, res, next) => {
  try {
    const { character_id } = req.body;

    validatePositiveInteger(character_id, 'character_id');

    // Verify character exists and belongs to authenticated user
    const characters = await query(
      'SELECT account_id FROM characters WHERE id = ?',
      [character_id]
    );

    if (characters.length === 0) {
      throw new NotFoundError('Character');
    }

    if (characters[0].account_id !== req.user.accountId) {
      throw new ValidationError('You can only queue your own characters');
    }

    // Check if already in queue
    const existing = await query(
      'SELECT id FROM queue WHERE character_id = ?',
      [character_id]
    );

    if (existing.length > 0) {
      throw new ValidationError('Character is already in queue');
    }

    // Get character rating
    const stats = await query(
      'SELECT rating FROM stats WHERE character_id = ?',
      [character_id]
    );

    const rating = stats.length > 0 ? stats[0].rating : 1000;

    // Add to queue
    const result = await run(
      'INSERT INTO queue (character_id, rating, joined_at) VALUES (?, ?, CURRENT_TIMESTAMP)',
      [character_id, rating]
    );

    // Try to find a match automatically
    const match = await findMatch(character_id, rating);

    if (match) {
      // Create battle automatically
      const battleResult = await createBattle(match.player1_id, match.player2_id);

      res.status(201).json({
        status: 'matched',
        battle_id: battleResult.battle_id,
        opponent_id: match.opponent_id,
        opponent_name: match.opponent_name,
        message: 'Match found! Battle created.'
      });
    } else {
      res.status(201).json({
        queue_id: result.lastID,
        character_id,
        rating,
        status: 'waiting',
        message: 'Added to matchmaking queue'
      });
    }

  } catch (error) {
    next(error);
  }
});

/**
 * Leave matchmaking queue
 * DELETE /api/queue/:characterId
 */
router.delete('/:characterId', authMiddleware, async (req, res, next) => {
  try {
    const characterId = parseInt(req.params.characterId);
    validatePositiveInteger(characterId, 'character_id');

    // Verify character belongs to authenticated user
    const characters = await query(
      'SELECT account_id FROM characters WHERE id = ?',
      [characterId]
    );

    if (characters.length === 0) {
      throw new NotFoundError('Character');
    }

    if (characters[0].account_id !== req.user.accountId) {
      throw new ValidationError('You can only remove your own characters from queue');
    }

    // Remove from queue
    const result = await run(
      'DELETE FROM queue WHERE character_id = ?',
      [characterId]
    );

    if (result.changes === 0) {
      throw new NotFoundError('Character not in queue');
    }

    res.json({
      status: 'left',
      message: 'Removed from matchmaking queue'
    });

  } catch (error) {
    next(error);
  }
});

/**
 * Get current queue status
 * GET /api/queue
 */
router.get('/', async (req, res, next) => {
  try {
    const queueEntries = await query(
      `SELECT q.id, q.character_id, q.rating, q.joined_at,
              c.name as character_name, c.account_id
       FROM queue q
       JOIN characters c ON q.character_id = c.id
       ORDER BY q.joined_at ASC`
    );

    res.json({
      queue: queueEntries.map(row => ({
        id: row.id,
        character_id: row.character_id,
        character_name: row.character_name,
        account_id: row.account_id,
        rating: row.rating,
        joined_at: row.joined_at
      })),
      total: queueEntries.length
    });

  } catch (error) {
    next(error);
  }
});

/**
 * Find a match for a character in the queue
 * @param {number} characterId - The character looking for a match
 * @param {number} rating - The character's rating
 * @returns {Promise<Object|null>} Match info or null if no match found
 */
async function findMatch(characterId, rating) {
  // For now, simple matching: find any other player in queue
  // Future: implement rating-based matching with range expansion
  const opponents = await query(
    `SELECT q.character_id, q.rating, c.name as character_name
     FROM queue q
     JOIN characters c ON q.character_id = c.id
     WHERE q.character_id != ?
     ORDER BY q.joined_at ASC
     LIMIT 1`,
    [characterId]
  );

  if (opponents.length === 0) {
    return null;
  }

  const opponent = opponents[0];

  return {
    player1_id: characterId,
    player2_id: opponent.character_id,
    opponent_id: opponent.character_id,
    opponent_name: opponent.character_name
  };
}

/**
 * Create a battle between two characters
 * @param {number} player1Id - First player character ID
 * @param {number} player2Id - Second player character ID
 * @returns {Promise<Object>} Battle creation result
 */
async function createBattle(player1Id, player2Id) {
  // Verify both characters exist and get HP
  const chars = await query(
    'SELECT id, computed_hp FROM characters WHERE id IN (?, ?)',
    [player1Id, player2Id]
  );

  if (chars.length !== 2) {
    throw new NotFoundError('One or both characters not found');
  }

  const char1 = chars.find(c => c.id === player1Id);
  const char2 = chars.find(c => c.id === player2Id);

  // Create battle in transaction
  const result = await transaction(async () => {
    const battleResult = await run(
      `INSERT INTO battles (
        player1_id, player2_id, current_turn,
        player1_hp, player2_hp, player1_max_hp, player2_max_hp,
        status, started_at, updated_at
      )
      VALUES (?, ?, 0, ?, ?, ?, ?, 'in_progress', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)`,
      [player1Id, player2Id, char1.computed_hp, char2.computed_hp, char1.computed_hp, char2.computed_hp]
    );

    const battleId = battleResult.lastID;

    // Remove both characters from queue
    await run('DELETE FROM queue WHERE character_id IN (?, ?)', [player1Id, player2Id]);

    return { battle_id: battleId };
  });

  // Emit WebSocket event
  io.emit('battle_started', {
    battle_id: result.battle_id,
    player1_id: player1Id,
    player2_id: player2Id
  });

  return result;
}

export default router;
