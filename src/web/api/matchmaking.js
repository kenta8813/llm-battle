/**
 * Matchmaking API routes (CRUD only)
 * Matching logic is handled by MCP server locally
 */

import express from 'express';
import { query, run } from '../db.js';
import { validatePositiveInteger } from '../utils/validation.js';
import { authMiddleware } from '../middleware/auth.js';
import {
  ValidationError,
  NotFoundError
} from '../middleware/error_handler.js';

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

    res.status(201).json({
      queue_id: result.lastID,
      character_id,
      rating,
      status: 'waiting',
      message: 'Added to matchmaking queue'
    });

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

export default router;
