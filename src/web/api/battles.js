/**
 * Battle API routes
 * Battle logic is handled server-side (Approach B)
 */

import express from 'express';
import { query, get, run, transaction } from '../db.js';
import { validatePositiveInteger, validateActionType } from '../utils/validation.js';
import { authMiddleware } from '../middleware/auth.js';
import {
  ValidationError,
  NotFoundError
} from '../middleware/error_handler.js';
import { io } from '../server.js';

const router = express.Router();

// In-memory store for pending actions per battle
// Map<battleId, { player1?: {action, ability_id}, player2?: {action, ability_id} }>
const pendingActions = new Map();

/**
 * Calculate damage dealt by attacker to defender
 */
function calculateDamage(attackerStats, defenderAction, defenderStats, actionType, ability = null) {
  // Handle dodge
  if (defenderAction === 'dodge') {
    const speedDiff = defenderStats.computed_speed - attackerStats.computed_speed;
    const dodgeRate = Math.max(0.1, Math.min(0.9, 0.5 + speedDiff / 200.0));
    if (Math.random() < dodgeRate) return 0;
  }

  let baseDamage;
  if (actionType === 'ability' && ability) {
    if (ability.effect_type !== 'damage') return 0;
    baseDamage = attackerStats.computed_attack * (ability.power / 100.0);
  } else if (actionType === 'attack') {
    baseDamage = attackerStats.computed_attack;
  } else {
    return 0;
  }

  // Defense reduction
  const defRatio = defenderStats.computed_defense / (defenderStats.computed_defense + 100);
  let finalDamage = baseDamage * (1 - defRatio);

  // Defend halves damage
  if (defenderAction === 'defend') finalDamage *= 0.5;

  // Random variation ±10%
  finalDamage *= 0.9 + Math.random() * 0.2;

  // Critical hit 10%
  if (Math.random() < 0.1) finalDamage *= 1.5;

  return Math.max(1, Math.floor(finalDamage));
}

/**
 * Resolve a battle turn with both players' actions.
 * Returns damage dealt/received and final HP values.
 */
function resolveTurn(char1Stats, char2Stats, p1Action, p2Action, ability1, ability2, battle) {
  const hp = {
    player1: battle.player1_hp,
    player2: battle.player2_hp
  };
  const result = {
    player1DamageDealt: 0,
    player1DamageReceived: 0,
    player2DamageDealt: 0,
    player2DamageReceived: 0,
    effects: []
  };

  // Determine action order by speed
  const p1GoesFirst = char1Stats.computed_speed > char2Stats.computed_speed ||
    (char1Stats.computed_speed === char2Stats.computed_speed && Math.random() < 0.5);

  const steps = p1GoesFirst
    ? [
        { attacker: char1Stats, defender: char2Stats, action: p1Action, defAction: p2Action.action, ability: ability1, aKey: 'player1', dKey: 'player2' },
        { attacker: char2Stats, defender: char1Stats, action: p2Action, defAction: p1Action.action, ability: ability2, aKey: 'player2', dKey: 'player1' }
      ]
    : [
        { attacker: char2Stats, defender: char1Stats, action: p2Action, defAction: p1Action.action, ability: ability2, aKey: 'player2', dKey: 'player1' },
        { attacker: char1Stats, defender: char2Stats, action: p1Action, defAction: p2Action.action, ability: ability1, aKey: 'player1', dKey: 'player2' }
      ];

  for (const { attacker, defender, action, defAction, ability, aKey, dKey } of steps) {
    if (hp[dKey] <= 0) continue; // opponent already defeated

    if (action.action === 'ability' && ability) {
      if (ability.effect_type === 'damage') {
        const dmg = calculateDamage(attacker, defAction, defender, 'ability', ability);
        result[`${aKey}DamageDealt`] += dmg;
        result[`${dKey}DamageReceived`] += dmg;
        hp[dKey] = Math.max(0, hp[dKey] - dmg);
        result.effects.push({ type: 'damage', by: aKey, ability: ability.name, damage: dmg });
      } else if (ability.effect_type === 'heal') {
        const maxHp = aKey === 'player1' ? battle.player1_max_hp : battle.player2_max_hp;
        const heal = Math.floor(maxHp * (ability.power / 100.0));
        hp[aKey] = Math.min(maxHp, hp[aKey] + heal);
        result.effects.push({ type: 'heal', by: aKey, ability: ability.name, heal });
      } else {
        result.effects.push({ type: ability.effect_type, by: aKey, ability: ability.name });
      }
    } else if (action.action === 'attack') {
      const dmg = calculateDamage(attacker, defAction, defender, 'attack');
      result[`${aKey}DamageDealt`] += dmg;
      result[`${dKey}DamageReceived`] += dmg;
      hp[dKey] = Math.max(0, hp[dKey] - dmg);
    }
    // defend/dodge: no direct damage, effect applied inside calculateDamage
  }

  result.player1HpAfter = hp.player1;
  result.player2HpAfter = hp.player2;
  return result;
}

/**
 * Create a new battle
 * POST /api/battles
 * Body: { player1_id: number, player2_id: number }
 */
router.post('/', authMiddleware, async (req, res, next) => {
  try {
    const { player1_id, player2_id } = req.body;

    validatePositiveInteger(player1_id, 'player1_id');
    validatePositiveInteger(player2_id, 'player2_id');

    if (player1_id === player2_id) {
      throw new ValidationError('Cannot battle against yourself');
    }

    const chars = await query(
      'SELECT id, computed_hp FROM characters WHERE id IN (?, ?)',
      [player1_id, player2_id]
    );

    if (chars.length !== 2) {
      throw new NotFoundError('One or both characters not found');
    }

    const char1 = chars.find(c => c.id === player1_id);
    const char2 = chars.find(c => c.id === player2_id);

    const result = await transaction(async () => {
      const battleResult = await run(
        `INSERT INTO battles (
          player1_id, player2_id, current_turn,
          player1_hp, player2_hp, player1_max_hp, player2_max_hp,
          status, started_at, updated_at
        )
        VALUES (?, ?, 0, ?, ?, ?, ?, 'in_progress', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)`,
        [player1_id, player2_id, char1.computed_hp, char2.computed_hp, char1.computed_hp, char2.computed_hp]
      );

      const battleId = battleResult.lastID;

      await run('DELETE FROM queue WHERE character_id IN (?, ?)', [player1_id, player2_id]);

      return { battle_id: battleId };
    });

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
 * Submit an action for a battle turn
 * POST /api/battles/:id/action
 * Body: { character_id: number, action: string, ability_id?: number }
 *
 * Each player submits their action independently.
 * When both players have submitted, the turn is resolved server-side.
 */
router.post('/:id/action', authMiddleware, async (req, res, next) => {
  try {
    const battleId = parseInt(req.params.id);
    validatePositiveInteger(battleId, 'battle_id');

    const { character_id, action, ability_id } = req.body;
    validatePositiveInteger(character_id, 'character_id');
    validateActionType(action);

    if (ability_id !== undefined && ability_id !== null) {
      validatePositiveInteger(ability_id, 'ability_id');
    }

    // Get battle with character stats
    const battle = await get(
      `SELECT b.*,
              c1.computed_attack as p1_attack, c1.computed_defense as p1_defense, c1.computed_speed as p1_speed,
              c2.computed_attack as p2_attack, c2.computed_defense as p2_defense, c2.computed_speed as p2_speed
       FROM battles b
       JOIN characters c1 ON b.player1_id = c1.id
       JOIN characters c2 ON b.player2_id = c2.id
       WHERE b.id = ?`,
      [battleId]
    );

    if (!battle) throw new NotFoundError('Battle');
    if (battle.status !== 'in_progress') throw new ValidationError('Battle is not in progress');

    // Determine player role
    let playerKey;
    if (character_id === battle.player1_id) playerKey = 'player1';
    else if (character_id === battle.player2_id) playerKey = 'player2';
    else throw new ValidationError('Character is not in this battle');

    // Store pending action
    if (!pendingActions.has(battleId)) {
      pendingActions.set(battleId, {});
    }
    const pending = pendingActions.get(battleId);
    pending[playerKey] = { action, ability_id: ability_id || null };

    // If only one player has submitted, wait for opponent
    if (!pending.player1 || !pending.player2) {
      return res.json({
        status: 'waiting',
        message: '相手の行動を待っています'
      });
    }

    // Both players submitted - resolve turn
    const p1ActionData = pending.player1;
    const p2ActionData = pending.player2;
    pendingActions.delete(battleId);

    // Fetch abilities if used
    let ability1 = null;
    let ability2 = null;
    if (p1ActionData.ability_id) {
      ability1 = await get('SELECT * FROM abilities WHERE id = ?', [p1ActionData.ability_id]);
    }
    if (p2ActionData.ability_id) {
      ability2 = await get('SELECT * FROM abilities WHERE id = ?', [p2ActionData.ability_id]);
    }

    const char1Stats = {
      computed_attack: battle.p1_attack,
      computed_defense: battle.p1_defense,
      computed_speed: battle.p1_speed
    };
    const char2Stats = {
      computed_attack: battle.p2_attack,
      computed_defense: battle.p2_defense,
      computed_speed: battle.p2_speed
    };

    const turnResult = resolveTurn(char1Stats, char2Stats, p1ActionData, p2ActionData, ability1, ability2, battle);
    const { player1HpAfter, player2HpAfter } = turnResult;
    const turnNumber = battle.current_turn + 1;

    // Determine winner
    let winnerId = null;
    let isDraw = false;

    if (player1HpAfter <= 0 || player2HpAfter <= 0 || turnNumber >= battle.max_turns) {
      if (player1HpAfter <= 0 && player2HpAfter <= 0) {
        isDraw = true;
      } else if (player1HpAfter <= 0) {
        winnerId = battle.player2_id;
      } else if (player2HpAfter <= 0) {
        winnerId = battle.player1_id;
      } else {
        // Max turns reached
        if (player1HpAfter > player2HpAfter) winnerId = battle.player1_id;
        else if (player2HpAfter > player1HpAfter) winnerId = battle.player2_id;
        else isDraw = true;
      }
    }

    const battleEnded = winnerId !== null || isDraw;

    const turnResultJson = JSON.stringify({
      turn_number: turnNumber,
      player1_action: p1ActionData.action,
      player2_action: p2ActionData.action,
      player1_damage_dealt: turnResult.player1DamageDealt,
      player2_damage_dealt: turnResult.player2DamageDealt,
      player1_hp_after: player1HpAfter,
      player2_hp_after: player2HpAfter,
      effects: turnResult.effects
    });

    // Record in DB
    const dbResult = await transaction(async () => {
      await run(
        `INSERT INTO battle_turns (
          battle_id, turn_number,
          player1_action, player1_ability_id, player1_damage_dealt, player1_damage_received, player1_hp_after,
          player2_action, player2_ability_id, player2_damage_dealt, player2_damage_received, player2_hp_after,
          turn_result
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
        [
          battleId, turnNumber,
          p1ActionData.action, p1ActionData.ability_id,
          turnResult.player1DamageDealt, turnResult.player1DamageReceived,
          player1HpAfter,
          p2ActionData.action, p2ActionData.ability_id,
          turnResult.player2DamageDealt, turnResult.player2DamageReceived,
          player2HpAfter,
          turnResultJson
        ]
      );

      if (battleEnded) {
        await run(
          `UPDATE battles SET current_turn = ?, player1_hp = ?, player2_hp = ?,
           winner_id = ?, status = 'finished', updated_at = CURRENT_TIMESTAMP WHERE id = ?`,
          [turnNumber, player1HpAfter, player2HpAfter, winnerId, battleId]
        );

        if (isDraw) {
          await run(
            `UPDATE stats SET total_battles = total_battles + 1, draws = draws + 1
             WHERE character_id IN (?, ?)`,
            [battle.player1_id, battle.player2_id]
          );
        } else {
          const loserId = winnerId === battle.player1_id ? battle.player2_id : battle.player1_id;
          await run(
            `UPDATE stats SET total_battles = total_battles + 1, wins = wins + 1, rating = rating + 25
             WHERE character_id = ?`,
            [winnerId]
          );
          await run(
            `UPDATE stats SET total_battles = total_battles + 1, losses = losses + 1,
             rating = CASE WHEN rating > 25 THEN rating - 25 ELSE rating END
             WHERE character_id = ?`,
            [loserId]
          );
        }

        return { status: 'finished', winner_id: winnerId, is_draw: isDraw };
      } else {
        await run(
          `UPDATE battles SET current_turn = ?, player1_hp = ?, player2_hp = ?,
           updated_at = CURRENT_TIMESTAMP WHERE id = ?`,
          [turnNumber, player1HpAfter, player2HpAfter, battleId]
        );
        return { status: 'in_progress' };
      }
    });

    // Emit WebSocket events
    io.to(`battle_${battleId}`).emit('turn_executed', {
      battle_id: battleId,
      turn_number: turnNumber,
      player1_action: p1ActionData.action,
      player2_action: p2ActionData.action,
      player1_hp: player1HpAfter,
      player2_hp: player2HpAfter,
      effects: turnResult.effects
    });

    if (battleEnded) {
      io.to(`battle_${battleId}`).emit('battle_ended', {
        battle_id: battleId,
        winner_id: winnerId,
        is_draw: isDraw
      });
    }

    let message;
    if (isDraw) message = '引き分け！';
    else if (winnerId) message = `バトル終了！勝者ID: ${winnerId}`;
    else message = `ターン${turnNumber}終了`;

    res.json({
      battle_id: battleId,
      turn_number: turnNumber,
      player1_action: p1ActionData.action,
      player2_action: p2ActionData.action,
      player1_damage_dealt: turnResult.player1DamageDealt,
      player2_damage_dealt: turnResult.player2DamageDealt,
      player1_hp: player1HpAfter,
      player2_hp: player2HpAfter,
      effects: turnResult.effects,
      ...dbResult,
      message
    });

  } catch (error) {
    next(error);
  }
});

/**
 * Record a turn result (legacy endpoint)
 * POST /api/battles/:id/turns
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
      turn_result,
      winner_id
    } = req.body;

    validatePositiveInteger(turn_number, 'turn_number');
    validateActionType(player1_action);
    validateActionType(player2_action);

    const battles = await query(
      'SELECT id, player1_id, player2_id, status FROM battles WHERE id = ?',
      [battleId]
    );

    if (battles.length === 0) throw new NotFoundError('Battle');
    const battle = battles[0];
    if (battle.status !== 'in_progress') throw new ValidationError('Battle is not in progress');

    const result = await transaction(async () => {
      await run(
        `INSERT INTO battle_turns (
          battle_id, turn_number,
          player1_action, player2_action,
          player1_damage_dealt, player1_damage_received,
          player2_damage_dealt, player2_damage_received,
          player1_hp_after, player2_hp_after,
          turn_result
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
        [
          battleId, turn_number,
          player1_action, player2_action,
          player1_damage || 0, player2_damage || 0,
          player2_damage || 0, player1_damage || 0,
          player1_hp_after, player2_hp_after,
          turn_result || JSON.stringify({ turn_number, player1_action, player2_action })
        ]
      );

      if (winner_id) {
        await run(
          `UPDATE battles SET current_turn = ?, player1_hp = ?, player2_hp = ?,
           winner_id = ?, status = 'finished', updated_at = CURRENT_TIMESTAMP WHERE id = ?`,
          [turn_number, player1_hp_after, player2_hp_after, winner_id, battleId]
        );

        const loser_id = winner_id === battle.player1_id ? battle.player2_id : battle.player1_id;
        await run(
          `UPDATE stats SET total_battles = total_battles + 1, wins = wins + 1, rating = rating + 25
           WHERE character_id = ?`,
          [winner_id]
        );
        await run(
          `UPDATE stats SET total_battles = total_battles + 1, losses = losses + 1,
           rating = CASE WHEN rating > 25 THEN rating - 25 ELSE rating END
           WHERE character_id = ?`,
          [loser_id]
        );

        return { status: 'finished', winner_id };
      } else {
        await run(
          `UPDATE battles SET current_turn = ?, player1_hp = ?, player2_hp = ?,
           updated_at = CURRENT_TIMESTAMP WHERE id = ?`,
          [turn_number, player1_hp_after, player2_hp_after, battleId]
        );
        return { status: 'in_progress' };
      }
    });

    io.to(`battle_${battleId}`).emit('turn_executed', {
      battle_id: battleId,
      turn_number,
      player1_action,
      player2_action,
      player1_hp: player1_hp_after,
      player2_hp: player2_hp_after
    });

    if (winner_id) {
      io.to(`battle_${battleId}`).emit('battle_ended', { battle_id: battleId, winner_id });
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

    const battle = await get(
      `SELECT b.*,
              c1.name as player1_name,
              c2.name as player2_name
       FROM battles b
       JOIN characters c1 ON b.player1_id = c1.id
       JOIN characters c2 ON b.player2_id = c2.id
       WHERE b.id = ?`,
      [battleId]
    );

    if (!battle) throw new NotFoundError('Battle');

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
      created_at: battle.started_at,
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
              turn_result, created_at
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
        turn_result: row.turn_result,
        created_at: row.created_at
      }))
    });

  } catch (error) {
    next(error);
  }
});

export default router;
