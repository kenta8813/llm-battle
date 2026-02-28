import express from 'express';
import { query, get } from './db.js';

const router = express.Router();

/**
 * GET /api/leaderboard
 * レーティング上位のキャラクター一覧を取得
 * Query params:
 *   - limit: 取得件数 (default: 50)
 */
router.get('/leaderboard', async (req, res) => {
  try {
    const limit = parseInt(req.query.limit) || 50;

    const sql = `
      SELECT
        c.id,
        c.name,
        c.level,
        c.computed_hp,
        c.computed_attack,
        c.computed_defense,
        c.computed_speed,
        s.rating,
        s.total_battles,
        s.wins,
        s.losses,
        s.draws,
        ROUND(CAST(s.wins AS REAL) / NULLIF(s.total_battles, 0) * 100, 2) as win_rate,
        s.current_win_streak,
        s.longest_win_streak,
        s.total_damage_dealt,
        s.total_damage_received
      FROM characters c
      JOIN stats s ON c.id = s.character_id
      WHERE s.total_battles > 0
      ORDER BY s.rating DESC, s.wins DESC
      LIMIT ?
    `;

    const characters = await query(sql, [limit]);
    res.json(characters);
  } catch (error) {
    console.error('Error fetching leaderboard:', error);
    res.status(500).json({ error: 'Failed to fetch leaderboard' });
  }
});

/**
 * GET /api/characters/:id
 * 指定したキャラクターの詳細情報を取得
 */
router.get('/characters/:id', async (req, res) => {
  try {
    const characterId = parseInt(req.params.id);

    // キャラクター基本情報
    const characterSql = `
      SELECT
        c.*,
        a.username as owner_username
      FROM characters c
      JOIN accounts a ON c.account_id = a.id
      WHERE c.id = ?
    `;
    const character = await get(characterSql, [characterId]);

    if (!character) {
      return res.status(404).json({ error: 'Character not found' });
    }

    // 戦績情報
    const statsSql = `
      SELECT * FROM stats WHERE character_id = ?
    `;
    const stats = await get(statsSql, [characterId]);

    // アビリティ情報
    const abilitiesSql = `
      SELECT
        a.id,
        a.name,
        a.description,
        a.effect_type,
        a.power,
        a.cost,
        a.cooldown,
        ca.acquired_at
      FROM abilities a
      JOIN character_abilities ca ON a.id = ca.ability_id
      WHERE ca.character_id = ?
    `;
    const abilities = await query(abilitiesSql, [characterId]);

    // バトル履歴（最新10件）
    const battlesSql = `
      SELECT
        b.id,
        b.player1_id,
        b.player2_id,
        b.winner_id,
        b.status,
        b.started_at,
        b.ended_at,
        c1.name as player1_name,
        c2.name as player2_name,
        CASE
          WHEN b.winner_id = ? THEN 'win'
          WHEN b.winner_id IS NULL THEN 'draw'
          ELSE 'loss'
        END as result
      FROM battles b
      JOIN characters c1 ON b.player1_id = c1.id
      JOIN characters c2 ON b.player2_id = c2.id
      WHERE (b.player1_id = ? OR b.player2_id = ?)
        AND b.status = 'finished'
      ORDER BY b.ended_at DESC
      LIMIT 10
    `;
    const battleHistory = await query(battlesSql, [characterId, characterId, characterId]);

    // レスポンス
    res.json({
      character,
      stats,
      abilities,
      battleHistory
    });
  } catch (error) {
    console.error('Error fetching character:', error);
    res.status(500).json({ error: 'Failed to fetch character details' });
  }
});

/**
 * GET /api/character/:id
 * 後方互換性のためのエイリアス
 */
router.get('/character/:id', async (req, res) => {
  req.url = `/characters/${req.params.id}`;
  router.handle(req, res);
});

/**
 * GET /api/battles/:id
 * 指定したバトルの詳細情報を取得
 */
router.get('/battles/:id', async (req, res) => {
  try {
    const battleId = parseInt(req.params.id);

    // バトル基本情報
    const battleSql = `
      SELECT
        b.*,
        c1.name as player1_name,
        c1.computed_hp as player1_max_hp,
        c1.computed_attack as player1_attack,
        c1.computed_defense as player1_defense,
        c1.computed_speed as player1_speed,
        c2.name as player2_name,
        c2.computed_hp as player2_max_hp,
        c2.computed_attack as player2_attack,
        c2.computed_defense as player2_defense,
        c2.computed_speed as player2_speed,
        cw.name as winner_name
      FROM battles b
      JOIN characters c1 ON b.player1_id = c1.id
      JOIN characters c2 ON b.player2_id = c2.id
      LEFT JOIN characters cw ON b.winner_id = cw.id
      WHERE b.id = ?
    `;
    const battle = await get(battleSql, [battleId]);

    if (!battle) {
      return res.status(404).json({ error: 'Battle not found' });
    }

    // ターンログ
    const turnsSql = `
      SELECT
        t.*,
        a1.name as player1_ability_name,
        a2.name as player2_ability_name
      FROM battle_turns t
      LEFT JOIN abilities a1 ON t.player1_ability_id = a1.id
      LEFT JOIN abilities a2 ON t.player2_ability_id = a2.id
      WHERE t.battle_id = ?
      ORDER BY t.turn_number ASC
    `;
    const turns = await query(turnsSql, [battleId]);

    // レスポンス
    res.json({
      battle,
      turns
    });
  } catch (error) {
    console.error('Error fetching battle:', error);
    res.status(500).json({ error: 'Failed to fetch battle details' });
  }
});

/**
 * GET /api/battle/:id
 * 後方互換性のためのエイリアス
 */
router.get('/battle/:id', async (req, res) => {
  req.url = `/battles/${req.params.id}`;
  router.handle(req, res);
});

/**
 * GET /api/battles
 * バトル一覧を取得
 * Query params:
 *   - status: フィルタリング（'waiting', 'in_progress', 'finished', 'cancelled'）
 *   - limit: 取得件数 (default: 20, max: 50)
 *   - offset: オフセット (default: 0)
 */
router.get('/battles', async (req, res) => {
  try {
    const status = req.query.status;
    const limit = Math.min(parseInt(req.query.limit) || 20, 50);
    const offset = parseInt(req.query.offset) || 0;

    let sql = `
      SELECT
        b.id,
        b.player1_id,
        b.player2_id,
        b.winner_id,
        b.status,
        b.started_at,
        b.ended_at,
        c1.name as player1_name,
        c2.name as player2_name,
        cw.name as winner_name
      FROM battles b
      JOIN characters c1 ON b.player1_id = c1.id
      JOIN characters c2 ON b.player2_id = c2.id
      LEFT JOIN characters cw ON b.winner_id = cw.id
    `;

    const params = [];

    // ステータスでフィルタリング
    if (status) {
      sql += ' WHERE b.status = ?';
      params.push(status);
    }

    // ソートとページング
    sql += ' ORDER BY b.started_at DESC LIMIT ? OFFSET ?';
    params.push(limit, offset);

    const battles = await query(sql, params);
    res.json(battles);
  } catch (error) {
    console.error('Error fetching battles:', error);
    res.status(500).json({ error: 'Failed to fetch battles' });
  }
});

/**
 * GET /api/battles/:id/turns
 * 指定したバトルのターン履歴を取得
 */
router.get('/battles/:id/turns', async (req, res) => {
  try {
    const battleId = parseInt(req.params.id);

    // バトルの存在確認
    const battleCheckSql = `SELECT id FROM battles WHERE id = ?`;
    const battle = await get(battleCheckSql, [battleId]);

    if (!battle) {
      return res.status(404).json({ error: 'Battle not found' });
    }

    // ターン履歴取得
    const turnsSql = `
      SELECT
        t.turn_number,
        t.player1_action,
        t.player2_action,
        t.player1_hp_after as player1_hp,
        t.player2_hp_after as player2_hp,
        t.turn_result as log_text,
        a1.name as player1_ability_name,
        a2.name as player2_ability_name
      FROM battle_turns t
      LEFT JOIN abilities a1 ON t.player1_ability_id = a1.id
      LEFT JOIN abilities a2 ON t.player2_ability_id = a2.id
      WHERE t.battle_id = ?
      ORDER BY t.turn_number ASC
    `;
    const turns = await query(turnsSql, [battleId]);

    res.json(turns);
  } catch (error) {
    console.error('Error fetching battle turns:', error);
    res.status(500).json({ error: 'Failed to fetch battle turns' });
  }
});

/**
 * GET /api/characters
 * キャラクター一覧を取得
 * Query params:
 *   - limit: 取得件数 (default: 50, max: 100)
 *   - offset: オフセット (default: 0)
 */
router.get('/characters', async (req, res) => {
  try {
    const limit = Math.min(parseInt(req.query.limit) || 50, 100);
    const offset = parseInt(req.query.offset) || 0;

    const sql = `
      SELECT
        c.id,
        c.name,
        c.level,
        c.computed_hp,
        c.computed_attack,
        c.computed_defense,
        c.computed_speed,
        s.rating,
        s.total_battles,
        s.wins,
        s.losses
      FROM characters c
      LEFT JOIN stats s ON c.id = s.character_id
      ORDER BY c.created_at DESC
      LIMIT ? OFFSET ?
    `;

    const characters = await query(sql, [limit, offset]);
    res.json(characters);
  } catch (error) {
    console.error('Error fetching characters:', error);
    res.status(500).json({ error: 'Failed to fetch characters' });
  }
});

/**
 * GET /api/characters/:id/stats
 * 指定したキャラクターの戦績を取得
 */
router.get('/characters/:id/stats', async (req, res) => {
  try {
    const characterId = parseInt(req.params.id);

    // キャラクターの存在確認
    const characterCheckSql = `SELECT id FROM characters WHERE id = ?`;
    const character = await get(characterCheckSql, [characterId]);

    if (!character) {
      return res.status(404).json({ error: 'Character not found' });
    }

    // 戦績取得
    const statsSql = `
      SELECT
        character_id,
        rating,
        total_battles,
        wins,
        losses,
        current_win_streak as current_streak,
        longest_win_streak as best_streak,
        0 as worst_streak
      FROM stats
      WHERE character_id = ?
    `;
    const stats = await get(statsSql, [characterId]);

    // 戦績が存在しない場合はデフォルト値を返す
    if (!stats) {
      return res.json({
        character_id: characterId,
        rating: 1000,
        total_battles: 0,
        wins: 0,
        losses: 0,
        current_streak: 0,
        best_streak: 0,
        worst_streak: 0
      });
    }

    res.json(stats);
  } catch (error) {
    console.error('Error fetching character stats:', error);
    res.status(500).json({ error: 'Failed to fetch character stats' });
  }
});

/**
 * GET /api/stats
 * 全体統計を取得
 */
router.get('/stats', async (req, res) => {
  try {
    // 総バトル数
    const totalBattlesSql = `
      SELECT COUNT(*) as count FROM battles WHERE status = 'finished'
    `;
    const totalBattlesResult = await get(totalBattlesSql);
    const totalBattles = totalBattlesResult.count;

    // 総キャラクター数
    const totalCharactersSql = `
      SELECT COUNT(*) as count FROM characters
    `;
    const totalCharactersResult = await get(totalCharactersSql);
    const totalCharacters = totalCharactersResult.count;

    // 今日のバトル数
    const todayBattlesSql = `
      SELECT COUNT(*) as count
      FROM battles
      WHERE status = 'finished'
        AND DATE(started_at) = DATE('now')
    `;
    const todayBattlesResult = await get(todayBattlesSql);
    const todayBattles = todayBattlesResult.count;

    // 進行中のバトル数
    const activeBattlesSql = `
      SELECT COUNT(*) as count FROM battles WHERE status = 'in_progress'
    `;
    const activeBattlesResult = await get(activeBattlesSql);
    const activeBattles = activeBattlesResult.count;

    // 待機中のプレイヤー数
    const queueSql = `
      SELECT COUNT(*) as count FROM queue
    `;
    const queueResult = await get(queueSql);
    const playersInQueue = queueResult.count;

    // 最高レーティング
    const topRatingSql = `
      SELECT MAX(rating) as max_rating FROM stats
    `;
    const topRatingResult = await get(topRatingSql);
    const topRating = topRatingResult.max_rating || 0;

    // 平均レーティング
    const avgRatingSql = `
      SELECT AVG(rating) as avg_rating FROM stats WHERE total_battles > 0
    `;
    const avgRatingResult = await get(avgRatingSql);
    const avgRating = Math.round(avgRatingResult.avg_rating || 1000);

    // レスポンス
    res.json({
      totalBattles,
      totalCharacters,
      todayBattles,
      activeBattles,
      playersInQueue,
      topRating,
      avgRating
    });
  } catch (error) {
    console.error('Error fetching stats:', error);
    res.status(500).json({ error: 'Failed to fetch statistics' });
  }
});

export default router;
