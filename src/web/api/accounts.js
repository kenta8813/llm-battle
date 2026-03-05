/**
 * Account management API routes
 */

import express from 'express';
import { v4 as uuidv4 } from 'uuid';
import { query, run } from '../db.js';
import { validateUsername } from '../utils/validation.js';
import { generateToken } from '../middleware/auth.js';
import {
  ValidationError,
  AuthenticationError,
  DatabaseError,
  ConflictError
} from '../middleware/error_handler.js';

const router = express.Router();

/**
 * Create a new account
 * POST /api/accounts
 * Body: { username: string }
 */
router.post('/', async (req, res, next) => {
  try {
    const { username } = req.body;

    // Validate username
    validateUsername(username);

    // Check for duplicate username
    const existing = await query(
      'SELECT id FROM accounts WHERE username = ?',
      [username]
    );

    if (existing.length > 0) {
      throw new ConflictError(`Username '${username}' is already taken`);
    }

    // Generate session ID
    const sessionId = uuidv4();

    // Create account
    const result = await run(
      `INSERT INTO accounts (username, session_id, created_at, last_login)
       VALUES (?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)`,
      [username, sessionId]
    );

    const accountId = result.lastID;

    // Generate JWT token
    const token = generateToken(accountId, sessionId);

    res.status(201).json({
      account_id: accountId,
      session_id: sessionId,
      token: token,
      message: `Account '${username}' created successfully`
    });

  } catch (error) {
    next(error);
  }
});

/**
 * Login to existing account
 * POST /api/accounts/login
 * Body: { username: string }
 */
router.post('/login', async (req, res, next) => {
  try {
    const { username } = req.body;

    // Validate username
    validateUsername(username);

    // Find account
    const accounts = await query(
      'SELECT id FROM accounts WHERE username = ?',
      [username]
    );

    if (accounts.length === 0) {
      throw new AuthenticationError(`Username '${username}' does not exist`);
    }

    const accountId = accounts[0].id;

    // Generate new session ID
    const sessionId = uuidv4();

    // Update session ID and last login time
    await run(
      `UPDATE accounts
       SET session_id = ?, last_login = CURRENT_TIMESTAMP
       WHERE id = ?`,
      [sessionId, accountId]
    );

    // Get owned characters
    const characters = await query(
      `SELECT id, name, level, computed_hp, computed_attack, computed_defense, computed_speed
       FROM characters
       WHERE account_id = ?
       ORDER BY created_at DESC`,
      [accountId]
    );

    const characterList = characters.map(row => ({
      id: row.id,
      name: row.name,
      level: row.level,
      hp: row.computed_hp,
      attack: row.computed_attack,
      defense: row.computed_defense,
      speed: row.computed_speed
    }));

    // Generate JWT token
    const token = generateToken(accountId, sessionId);

    res.status(200).json({
      account_id: accountId,
      session_id: sessionId,
      token: token,
      characters: characterList,
      message: `Welcome back, ${username}!`
    });

  } catch (error) {
    next(error);
  }
});

export default router;
