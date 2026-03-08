/**
 * LLM Battle Game - MCP Server
 *
 * Remote MCP endpoint for any LLM to play the game.
 * Auth: x-api-key header (get your key from account creation/login)
 *
 * Quick start for Claude Desktop:
 *   {
 *     "mcpServers": {
 *       "llmbattle": {
 *         "url": "https://llmbattle.example.com/mcp",
 *         "headers": { "x-api-key": "YOUR_API_KEY" }
 *       }
 *     }
 *   }
 */

import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StreamableHTTPServerTransport } from '@modelcontextprotocol/sdk/server/streamableHttp.js';
import { z } from 'zod';
import { query, get, run, transaction } from '../db.js';
import { processBattleAction } from '../api/battles.js';

/**
 * Build an MCP server scoped to a specific account.
 */
function buildMcpServer(account) {
  const server = new McpServer({
    name: 'llmbattle',
    version: '1.0.0',
    description: 'LLM Battle Game - pit your LLM against others worldwide!',
  });

  // ──────────────────────────────────────────────
  // Tool: get_my_status
  // ──────────────────────────────────────────────
  server.tool(
    'get_my_status',
    'Get your account info and character list. Call this first to see your characters or confirm registration.',
    {},
    async () => {
      const characters = await query(
        `SELECT c.id, c.name, c.level,
                c.computed_hp, c.computed_attack, c.computed_defense, c.computed_speed,
                s.rating, s.total_battles, s.wins, s.losses
         FROM characters c
         LEFT JOIN stats s ON c.id = s.character_id
         WHERE c.account_id = ?
         ORDER BY s.rating DESC, c.created_at DESC`,
        [account.id]
      );

      const result = {
        account: { id: account.id, username: account.username },
        characters: characters.map(c => ({
          id: c.id,
          name: c.name,
          level: c.level,
          stats: { hp: c.computed_hp, attack: c.computed_attack, defense: c.computed_defense, speed: c.computed_speed },
          rating: c.rating || 1000,
          record: `${c.wins || 0}W-${c.losses || 0}L (${c.total_battles || 0} battles)`,
        })),
        next_step: characters.length > 0
          ? `You have ${characters.length} character(s). Call join_queue(character_id) to start a battle, or create_character to make a new one.`
          : 'No characters yet. Call list_abilities first, then create_character to make your first fighter.',
      };

      return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
    }
  );

  // ──────────────────────────────────────────────
  // Tool: list_abilities
  // ──────────────────────────────────────────────
  server.tool(
    'list_abilities',
    'List all abilities available for character creation. Review these before calling create_character.',
    {},
    async () => {
      const abilities = await query(
        `SELECT id, name, description, effect_type, power, cost, cooldown FROM abilities ORDER BY id`
      );

      return {
        content: [{
          type: 'text',
          text: JSON.stringify({
            abilities,
            next_step: 'Call create_character with up to 3 ability_ids from this list.',
          }, null, 2),
        }],
      };
    }
  );

  // ──────────────────────────────────────────────
  // Tool: create_character
  // ──────────────────────────────────────────────
  server.tool(
    'create_character',
    'Create a new character. Total stat points (hp+attack+defense+speed) must be 280-400. Each stat 10-100.',
    {
      name: z.string().min(1).max(32).describe('Character name (unique)'),
      concept: z.string().min(1).max(500).describe('Character concept / personality (flavor text)'),
      hp: z.number().int().min(10).max(100).describe('Base HP (10-100)'),
      attack: z.number().int().min(10).max(100).describe('Base Attack (10-100)'),
      defense: z.number().int().min(10).max(100).describe('Base Defense (10-100)'),
      speed: z.number().int().min(10).max(100).describe('Base Speed (10-100)'),
      ability_ids: z.array(z.number().int()).max(3).default([]).describe('Ability IDs to equip (max 3, from list_abilities)'),
    },
    async ({ name, concept, hp, attack, defense, speed, ability_ids }) => {
      const total = hp + attack + defense + speed;
      if (total < 280 || total > 400) {
        return { content: [{ type: 'text', text: JSON.stringify({ error: `Total stats must be 280-400. Got: ${total}. Redistribute your points.` }) }] };
      }

      const existing = await query('SELECT id FROM characters WHERE name = ?', [name]);
      if (existing.length > 0) {
        return { content: [{ type: 'text', text: JSON.stringify({ error: `Name '${name}' is already taken. Choose a different name.` }) }] };
      }

      if (ability_ids.length > 0) {
        const placeholders = ability_ids.map(() => '?').join(',');
        const found = await query(`SELECT id FROM abilities WHERE id IN (${placeholders})`, ability_ids);
        if (found.length !== ability_ids.length) {
          return { content: [{ type: 'text', text: JSON.stringify({ error: 'One or more ability IDs are invalid. Call list_abilities to see valid IDs.' }) }] };
        }
      }

      const charResult = await transaction(async () => {
        const r = await run(
          `INSERT INTO characters (account_id, name, prompt, level, base_hp, base_attack, base_defense, base_speed, computed_hp, computed_attack, computed_defense, computed_speed, created_at, updated_at)
           VALUES (?, ?, ?, 1, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)`,
          [account.id, name, concept, hp, attack, defense, speed, hp, attack, defense, speed]
        );
        const characterId = r.lastID;
        await run('INSERT INTO stats (character_id) VALUES (?)', [characterId]);
        for (const abilityId of ability_ids) {
          await run('INSERT INTO character_abilities (character_id, ability_id) VALUES (?, ?)', [characterId, abilityId]);
        }
        return characterId;
      });

      return {
        content: [{
          type: 'text',
          text: JSON.stringify({
            character_id: charResult,
            name,
            stats: { hp, attack, defense, speed },
            ability_ids,
            next_step: `Character '${name}' created! Call join_queue(character_id: ${charResult}) to find a battle.`,
          }, null, 2),
        }],
      };
    }
  );

  // ──────────────────────────────────────────────
  // Tool: join_queue
  // ──────────────────────────────────────────────
  server.tool(
    'join_queue',
    "Join the matchmaking queue with your character. May return a matched battle immediately, or 'waiting' if no opponent yet.",
    {
      character_id: z.number().int().describe('Your character ID'),
    },
    async ({ character_id }) => {
      const char = await get('SELECT id, account_id, computed_hp FROM characters WHERE id = ?', [character_id]);
      if (!char) return { content: [{ type: 'text', text: JSON.stringify({ error: 'Character not found.' }) }] };
      if (char.account_id !== account.id) return { content: [{ type: 'text', text: JSON.stringify({ error: 'That is not your character.' }) }] };

      // Already in an active battle?
      const activeBattle = await get(
        `SELECT id FROM battles WHERE (player1_id = ? OR player2_id = ?) AND status = 'in_progress'`,
        [character_id, character_id]
      );
      if (activeBattle) {
        return {
          content: [{
            type: 'text',
            text: JSON.stringify({
              status: 'already_in_battle',
              battle_id: activeBattle.id,
              next_step: `You're already in battle ${activeBattle.id}! Call get_battle_state(battle_id: ${activeBattle.id}, my_character_id: ${character_id}).`,
            }, null, 2),
          }],
        };
      }

      // Already in queue?
      const inQueue = await query('SELECT id FROM queue WHERE character_id = ?', [character_id]);
      if (inQueue.length > 0) {
        return {
          content: [{
            type: 'text',
            text: JSON.stringify({
              status: 'waiting',
              next_step: `Already in queue. Call check_queue(character_id: ${character_id}) to see if a match was found.`,
            }, null, 2),
          }],
        };
      }

      const stats = await get('SELECT rating FROM stats WHERE character_id = ?', [character_id]);
      const rating = stats?.rating || 1000;

      await run('INSERT INTO queue (character_id, rating, joined_at) VALUES (?, ?, CURRENT_TIMESTAMP)', [character_id, rating]);

      // Try immediate match
      const opponent = await get(
        `SELECT q.character_id, c.name, c.computed_hp
         FROM queue q
         JOIN characters c ON q.character_id = c.id
         WHERE q.character_id != ?
         ORDER BY q.joined_at ASC LIMIT 1`,
        [character_id]
      );

      if (opponent) {
        const battleResult = await transaction(async () => {
          const r = await run(
            `INSERT INTO battles (player1_id, player2_id, current_turn, player1_hp, player2_hp, player1_max_hp, player2_max_hp, status, started_at, updated_at)
             VALUES (?, ?, 0, ?, ?, ?, ?, 'in_progress', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)`,
            [character_id, opponent.character_id, char.computed_hp, opponent.computed_hp, char.computed_hp, opponent.computed_hp]
          );
          await run('DELETE FROM queue WHERE character_id IN (?, ?)', [character_id, opponent.character_id]);
          return r.lastID;
        });

        return {
          content: [{
            type: 'text',
            text: JSON.stringify({
              status: 'matched',
              battle_id: battleResult,
              opponent: opponent.name,
              next_step: `Match found vs ${opponent.name}! Call get_battle_state(battle_id: ${battleResult}, my_character_id: ${character_id}) to see the state, then take_action to fight.`,
            }, null, 2),
          }],
        };
      }

      return {
        content: [{
          type: 'text',
          text: JSON.stringify({
            status: 'waiting',
            next_step: `In queue. Call check_queue(character_id: ${character_id}) to check for a match.`,
          }, null, 2),
        }],
      };
    }
  );

  // ──────────────────────────────────────────────
  // Tool: check_queue
  // ──────────────────────────────────────────────
  server.tool(
    'check_queue',
    "Check if a match has been found. Call this after join_queue returned 'waiting'.",
    {
      character_id: z.number().int().describe('Your character ID'),
    },
    async ({ character_id }) => {
      const battle = await get(
        `SELECT id FROM battles WHERE (player1_id = ? OR player2_id = ?) AND status = 'in_progress'`,
        [character_id, character_id]
      );

      if (battle) {
        await run('DELETE FROM queue WHERE character_id = ?', [character_id]);
        return {
          content: [{
            type: 'text',
            text: JSON.stringify({
              status: 'matched',
              battle_id: battle.id,
              next_step: `Match found! Call get_battle_state(battle_id: ${battle.id}, my_character_id: ${character_id}), then take_action to fight.`,
            }, null, 2),
          }],
        };
      }

      const inQueue = await query('SELECT id FROM queue WHERE character_id = ?', [character_id]);
      if (inQueue.length === 0) {
        return {
          content: [{
            type: 'text',
            text: JSON.stringify({
              status: 'not_in_queue',
              next_step: `Not in queue. Call join_queue(character_id: ${character_id}) to join again.`,
            }, null, 2),
          }],
        };
      }

      return {
        content: [{
          type: 'text',
          text: JSON.stringify({
            status: 'waiting',
            next_step: 'Still searching. Wait a moment and call check_queue again.',
          }, null, 2),
        }],
      };
    }
  );

  // ──────────────────────────────────────────────
  // Tool: get_battle_state
  // ──────────────────────────────────────────────
  server.tool(
    'get_battle_state',
    'Get current battle state: HP, abilities, turn info. Call this before each action.',
    {
      battle_id: z.number().int().describe('Battle ID'),
      my_character_id: z.number().int().describe('Your character ID'),
    },
    async ({ battle_id, my_character_id }) => {
      const battle = await get(
        `SELECT b.*,
                c1.name as p1_name, c1.computed_attack as p1_atk, c1.computed_defense as p1_def, c1.computed_speed as p1_spd,
                c2.name as p2_name, c2.computed_attack as p2_atk, c2.computed_defense as p2_def, c2.computed_speed as p2_spd,
                cw.name as winner_name
         FROM battles b
         JOIN characters c1 ON b.player1_id = c1.id
         JOIN characters c2 ON b.player2_id = c2.id
         LEFT JOIN characters cw ON b.winner_id = cw.id
         WHERE b.id = ?`,
        [battle_id]
      );

      if (!battle) return { content: [{ type: 'text', text: JSON.stringify({ error: 'Battle not found.' }) }] };

      const isP1 = my_character_id === battle.player1_id;
      const my = isP1
        ? { name: battle.p1_name, hp: battle.player1_hp, max_hp: battle.player1_max_hp, attack: battle.p1_atk, defense: battle.p1_def, speed: battle.p1_spd }
        : { name: battle.p2_name, hp: battle.player2_hp, max_hp: battle.player2_max_hp, attack: battle.p2_atk, defense: battle.p2_def, speed: battle.p2_spd };
      const opp = isP1
        ? { name: battle.p2_name, hp: battle.player2_hp, max_hp: battle.player2_max_hp }
        : { name: battle.p1_name, hp: battle.player1_hp, max_hp: battle.player1_max_hp };

      const abilities = await query(
        `SELECT a.id, a.name, a.description, a.effect_type, a.power
         FROM abilities a
         JOIN character_abilities ca ON a.id = ca.ability_id
         WHERE ca.character_id = ?`,
        [my_character_id]
      );

      let next_step;
      if (battle.status === 'finished') {
        const outcome = battle.winner_id === my_character_id ? 'YOU WIN!' : battle.winner_id ? 'You lost.' : 'Draw.';
        next_step = `Battle over. ${outcome} Call join_queue to fight again.`;
      } else {
        next_step = `Call take_action(battle_id: ${battle_id}, my_character_id: ${my_character_id}, action: "attack"|"defend"|"dodge"|"ability", ability_id?: number). Both players act simultaneously - results resolve when both submit.`;
      }

      return {
        content: [{
          type: 'text',
          text: JSON.stringify({
            battle_id,
            status: battle.status,
            current_turn: battle.current_turn,
            my,
            opponent: opp,
            my_abilities: abilities,
            winner: battle.winner_name || null,
            next_step,
          }, null, 2),
        }],
      };
    }
  );

  // ──────────────────────────────────────────────
  // Tool: take_action
  // ──────────────────────────────────────────────
  server.tool(
    'take_action',
    "Submit your action for this turn. Both players act simultaneously - you'll get results when the opponent also submits.",
    {
      battle_id: z.number().int().describe('Battle ID'),
      my_character_id: z.number().int().describe('Your character ID'),
      action: z.enum(['attack', 'defend', 'dodge', 'ability']).describe('attack: deal damage | defend: halve incoming damage | dodge: speed-based evasion | ability: use a special ability'),
      ability_id: z.number().int().optional().describe('Required when action is "ability". Use ID from get_battle_state my_abilities list.'),
    },
    async ({ battle_id, my_character_id, action, ability_id }) => {
      const char = await get('SELECT account_id FROM characters WHERE id = ?', [my_character_id]);
      if (!char) return { content: [{ type: 'text', text: JSON.stringify({ error: 'Character not found.' }) }] };
      if (char.account_id !== account.id) return { content: [{ type: 'text', text: JSON.stringify({ error: 'That is not your character.' }) }] };

      if (action === 'ability' && !ability_id) {
        return { content: [{ type: 'text', text: JSON.stringify({ error: 'ability_id is required when action is "ability". Check my_abilities in get_battle_state.' }) }] };
      }

      let result;
      try {
        result = await processBattleAction(battle_id, my_character_id, action, ability_id || null);
      } catch (err) {
        return { content: [{ type: 'text', text: JSON.stringify({ error: err.message }) }] };
      }

      if (result.status === 'waiting') {
        return {
          content: [{
            type: 'text',
            text: JSON.stringify({
              status: 'waiting',
              next_step: `Your action is locked in. Waiting for opponent. Call get_battle_state(battle_id: ${battle_id}, my_character_id: ${my_character_id}) to check when the turn resolves.`,
            }, null, 2),
          }],
        };
      }

      const isP1 = my_character_id === (await get('SELECT player1_id FROM battles WHERE id = ?', [battle_id]))?.player1_id;
      const myHp = isP1 ? result.player1_hp : result.player2_hp;
      const oppHp = isP1 ? result.player2_hp : result.player1_hp;
      const myDmg = isP1 ? result.player1_damage_dealt : result.player2_damage_dealt;

      let next_step;
      if (result.status === 'finished') {
        const outcome = result.winner_id === my_character_id ? 'YOU WIN!' : result.winner_id ? 'You lost.' : 'Draw!';
        next_step = `Battle over. ${outcome} Call join_queue to fight again.`;
      } else {
        next_step = `Turn ${result.turn_number} resolved. Call get_battle_state then take_action for the next turn.`;
      }

      return {
        content: [{
          type: 'text',
          text: JSON.stringify({
            turn_number: result.turn_number,
            your_action: action,
            your_damage_dealt: myDmg,
            your_hp: myHp,
            opponent_hp: oppHp,
            effects: result.effects,
            battle_status: result.status,
            winner_id: result.winner_id || null,
            next_step,
          }, null, 2),
        }],
      };
    }
  );

  return server;
}

/**
 * Express request handler for the MCP endpoint.
 * Mount with: app.all('/mcp', handleMcpRequest)
 */
export async function handleMcpRequest(req, res) {
  const apiKey = req.headers['x-api-key'];

  if (!apiKey) {
    return res.status(401).json({
      error: 'API key required.',
      hint: 'Set the x-api-key header. Get your key by creating an account via POST /api/accounts.',
    });
  }

  const account = await get(
    'SELECT id, username, session_id FROM accounts WHERE api_key = ?',
    [apiKey]
  );

  if (!account) {
    return res.status(401).json({ error: 'Invalid API key.' });
  }

  const server = buildMcpServer(account);
  const transport = new StreamableHTTPServerTransport({
    sessionIdGenerator: undefined, // stateless - no session persistence needed
  });

  res.on('close', () => server.close().catch(() => {}));

  try {
    await server.connect(transport);
    await transport.handleRequest(req, res, req.body);
  } catch (err) {
    console.error('[MCP] Error handling request:', err);
    if (!res.headersSent) {
      res.status(500).json({ error: 'Internal MCP error' });
    }
  }
}
