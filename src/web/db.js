/**
 * Database module - PostgreSQL via Supabase
 * Wraps pg.Pool with a SQLite-compatible API (query/get/run/transaction).
 * ? placeholders are auto-converted to $1, $2, ... for pg.
 */

import pkg from 'pg';
import { AsyncLocalStorage } from 'async_hooks';

const { Pool } = pkg;

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: process.env.NODE_ENV === 'production' ? { rejectUnauthorized: false } : false,
});

pool.on('connect', () => {
  console.log('Connected to PostgreSQL database');
});

pool.on('error', (err) => {
  console.error('PostgreSQL pool error:', err);
});

// Propagates the transaction client through async context
const txStorage = new AsyncLocalStorage();

/**
 * Convert ? placeholders to $1, $2, ... for pg
 */
function convertPlaceholders(sql) {
  let i = 0;
  return sql.replace(/\?/g, () => `$${++i}`);
}

/**
 * Tables that have an auto-generated `id` column (SERIAL PRIMARY KEY).
 * Used to decide whether to append RETURNING id after INSERT.
 */
const TABLES_WITH_ID = [
  'accounts', 'characters', 'battles', 'battle_turns',
  'queue', 'abilities', 'schema_version',
];

function getClient() {
  return txStorage.getStore() || pool;
}

/**
 * Execute a SELECT that returns multiple rows.
 */
export function query(sql, params = []) {
  return getClient().query(convertPlaceholders(sql), params).then(r => r.rows);
}

/**
 * Execute a SELECT that returns a single row (or null).
 */
export function get(sql, params = []) {
  return getClient().query(convertPlaceholders(sql), params).then(r => r.rows[0] || null);
}

/**
 * Execute an INSERT / UPDATE / DELETE.
 * Returns { lastID, changes } for compatibility with sqlite3 callers.
 * For INSERT into tables with an `id` column, appends RETURNING id.
 */
export async function run(sql, params = []) {
  const trimmed = sql.trim().toUpperCase();
  const isInsert = trimmed.startsWith('INSERT');
  const needsReturning = isInsert &&
    TABLES_WITH_ID.some(t => trimmed.includes(`INTO ${t.toUpperCase()}`));

  const convertedSql = convertPlaceholders(sql);
  const finalSql = needsReturning ? `${convertedSql} RETURNING id` : convertedSql;

  const result = await getClient().query(finalSql, params);
  return { lastID: result.rows[0]?.id, changes: result.rowCount };
}

/**
 * Execute a callback inside a transaction.
 * Any query/get/run calls made within the callback automatically use the
 * same pg client (via AsyncLocalStorage), so no callsite changes needed.
 */
export async function transaction(callback) {
  const client = await pool.connect();
  try {
    await client.query('BEGIN');
    const result = await txStorage.run(client, callback);
    await client.query('COMMIT');
    return result;
  } catch (error) {
    await client.query('ROLLBACK');
    throw error;
  } finally {
    client.release();
  }
}

export default pool;
