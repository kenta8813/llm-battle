/**
 * Database module with SQLite concurrent access improvements
 */

import sqlite3 from 'sqlite3';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Get database path from environment variable or use default
const DB_PATH = process.env.DB_PATH || path.join(__dirname, '../database/llmbattle.db');

// Create database connection
const db = new sqlite3.Database(DB_PATH, (err) => {
  if (err) {
    console.error('Error connecting to database:', err.message);
  } else {
    console.log('Connected to SQLite database at:', DB_PATH);

    // Enable WAL mode for better concurrent access
    db.run('PRAGMA journal_mode = WAL', (err) => {
      if (err) {
        console.error('Error enabling WAL mode:', err.message);
      } else {
        console.log('WAL mode enabled for concurrent access');
      }
    });

    // Set busy timeout to 5 seconds
    db.run('PRAGMA busy_timeout = 5000', (err) => {
      if (err) {
        console.error('Error setting busy timeout:', err.message);
      }
    });

    // Enable foreign key constraints
    db.run('PRAGMA foreign_keys = ON', (err) => {
      if (err) {
        console.error('Error enabling foreign keys:', err.message);
      }
    });
  }
});

// Promise-based query execution (SELECT)
export function query(sql, params = []) {
  return new Promise((resolve, reject) => {
    db.all(sql, params, (err, rows) => {
      if (err) {
        reject(err);
      } else {
        resolve(rows);
      }
    });
  });
}

// Get a single row (SELECT)
export function get(sql, params = []) {
  return new Promise((resolve, reject) => {
    db.get(sql, params, (err, row) => {
      if (err) {
        reject(err);
      } else {
        resolve(row);
      }
    });
  });
}

// Run a query (INSERT, UPDATE, DELETE)
export function run(sql, params = []) {
  return new Promise((resolve, reject) => {
    db.run(sql, params, function(err) {
      if (err) {
        reject(err);
      } else {
        resolve({ lastID: this.lastID, changes: this.changes });
      }
    });
  });
}

/**
 * Execute a transaction with retry logic
 * @param {Function} callback - Async function that performs database operations
 * @param {number} maxRetries - Maximum number of retries on SQLITE_BUSY
 * @returns {Promise} Result of the callback
 */
export async function transaction(callback, maxRetries = 3) {
  let retries = maxRetries;

  while (retries > 0) {
    try {
      // Begin transaction
      await run('BEGIN IMMEDIATE TRANSACTION');

      // Execute callback
      const result = await callback();

      // Commit transaction
      await run('COMMIT');

      return result;

    } catch (error) {
      // Rollback on error
      try {
        await run('ROLLBACK');
      } catch (rollbackError) {
        console.error('Error during rollback:', rollbackError);
      }

      // Retry on SQLITE_BUSY
      if (error.code === 'SQLITE_BUSY' && retries > 1) {
        retries--;
        console.warn(`SQLite busy, retrying... (${maxRetries - retries}/${maxRetries})`);
        await new Promise(resolve => setTimeout(resolve, 100)); // Wait 100ms
        continue;
      }

      // Throw error if not retrying
      throw error;
    }
  }
}

export default db;
