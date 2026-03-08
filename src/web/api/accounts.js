/**
 * Account management API routes
 */

import express from 'express';
import { v4 as uuidv4 } from 'uuid';
import { query, run, get } from '../db.js';
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

    // Generate session ID and API key
    const sessionId = uuidv4();
    const apiKey = uuidv4();

    // Create account
    const result = await run(
      `INSERT INTO accounts (username, session_id, api_key, created_at, last_login)
       VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)`,
      [username, sessionId, apiKey]
    );

    const accountId = result.lastID;

    // Generate JWT token
    const token = generateToken(accountId, sessionId);

    res.status(201).json({
      account_id: accountId,
      session_id: sessionId,
      token: token,
      api_key: apiKey,
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

    // Generate new session ID; ensure api_key exists (migrate old accounts)
    const sessionId = uuidv4();
    const existingKey = await get('SELECT api_key FROM accounts WHERE id = ?', [accountId]);
    const apiKey = existingKey?.api_key || uuidv4();

    // Update session ID and last login time
    await run(
      `UPDATE accounts
       SET session_id = ?, api_key = COALESCE(api_key, ?), last_login = CURRENT_TIMESTAMP
       WHERE id = ?`,
      [sessionId, apiKey, accountId]
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
      api_key: apiKey,
      characters: characterList,
      message: `Welcome back, ${username}!`
    });

  } catch (error) {
    next(error);
  }
});

export default router;
