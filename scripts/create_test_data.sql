-- Test data for Web API demonstration
-- Creates sample accounts, characters, battles, and stats

BEGIN TRANSACTION;

-- Create test accounts
INSERT INTO accounts (username, created_at) VALUES
  ('player1', datetime('now', '-30 days')),
  ('player2', datetime('now', '-25 days')),
  ('player3', datetime('now', '-20 days'));

-- Create test characters
INSERT INTO characters (
  account_id, name, prompt, level,
  base_hp, base_attack, base_defense, base_speed,
  computed_hp, computed_attack, computed_defense, computed_speed,
  created_at
) VALUES
  (1, '炎の戦士', 'あなたは熱き魂を持つ戦士です。勇敢に戦い、仲間を守ります。', 5,
   100, 80, 60, 70, 140, 112, 84, 98, datetime('now', '-30 days')),
  (2, '氷の魔法使い', 'あなたは冷静な魔法使いです。知恵と戦略で勝利を目指します。', 4,
   80, 90, 50, 85, 112, 126, 70, 119, datetime('now', '-25 days')),
  (3, '風の剣士', 'あなたは素早い剣士です。スピードを活かして戦います。', 6,
   90, 85, 55, 95, 135, 127, 82, 142, datetime('now', '-20 days')),
  (1, '大地の盾', 'あなたは堅牢な守護者です。仲間を守り抜きます。', 3,
   120, 60, 90, 50, 144, 72, 108, 60, datetime('now', '-15 days')),
  (2, '雷の槍使い', 'あなたは電撃の使い手です。一撃必殺を狙います。', 4,
   85, 95, 55, 80, 119, 133, 77, 112, datetime('now', '-10 days'));

-- Assign abilities to characters
INSERT INTO character_abilities (character_id, ability_id) VALUES
  (1, 1), (1, 3), -- 炎の戦士: 強打、必殺技
  (2, 4), (2, 7), -- 氷の魔法使い: 回復、弱体化
  (3, 2), (3, 6), -- 風の剣士: 連続攻撃、カウンター
  (4, 5), (4, 6), -- 大地の盾: 防御態勢、カウンター
  (5, 1), (5, 3); -- 雷の槍使い: 強打、必殺技

-- Create test battles
INSERT INTO battles (
  player1_id, player2_id, winner_id, max_turns, current_turn, status,
  started_at, ended_at
) VALUES
  -- Battle 1: 炎の戦士 vs 氷の魔法使い (炎の戦士の勝利)
  (1, 2, 1, 50, 15, 'finished',
   datetime('now', '-10 days'), datetime('now', '-10 days', '+30 minutes')),

  -- Battle 2: 風の剣士 vs 大地の盾 (風の剣士の勝利)
  (3, 4, 3, 50, 20, 'finished',
   datetime('now', '-8 days'), datetime('now', '-8 days', '+25 minutes')),

  -- Battle 3: 炎の戦士 vs 風の剣士 (風の剣士の勝利)
  (1, 3, 3, 50, 18, 'finished',
   datetime('now', '-5 days'), datetime('now', '-5 days', '+28 minutes')),

  -- Battle 4: 雷の槍使い vs 氷の魔法使い (雷の槍使いの勝利)
  (5, 2, 5, 50, 12, 'finished',
   datetime('now', '-3 days'), datetime('now', '-3 days', '+20 minutes')),

  -- Battle 5: 大地の盾 vs 炎の戦士 (炎の戦士の勝利)
  (4, 1, 1, 50, 25, 'finished',
   datetime('now', '-1 day'), datetime('now', '-1 day', '+35 minutes'));

-- Create sample turns for Battle 1 (炎の戦士 vs 氷の魔法使い)
INSERT INTO battle_turns (
  battle_id, turn_number,
  player1_action, player1_damage_dealt, player1_damage_received, player1_hp_after,
  player2_action, player2_damage_dealt, player2_damage_received, player2_hp_after,
  turn_result
) VALUES
  (1, 1, 'attack', 20, 15, 125, 'attack', 15, 20, 92, '{"summary": "両者が攻撃"}'),
  (1, 2, 'ability', 35, 0, 125, 'defend', 0, 17, 92, '{"summary": "炎の戦士が強打使用"}'),
  (1, 3, 'attack', 18, 25, 100, 'attack', 25, 18, 74, '{"summary": "両者が攻撃"}'),
  (1, 4, 'defend', 0, 10, 100, 'attack', 10, 0, 74, '{"summary": "炎の戦士が防御"}'),
  (1, 5, 'ability', 50, 20, 80, 'attack', 20, 50, 24, '{"summary": "炎の戦士が必殺技"}'),
  (1, 6, 'attack', 22, 0, 80, 'ability', 0, 0, 24, '{"summary": "氷の魔法使いが回復失敗"}');

-- Create stats for all characters
INSERT INTO stats (
  character_id, total_battles, wins, losses, draws,
  total_damage_dealt, total_damage_received,
  longest_win_streak, current_win_streak, rating
) VALUES
  -- 炎の戦士: 3戦2勝1敗
  (1, 3, 2, 1, 0, 450, 320, 2, 2, 1050),

  -- 氷の魔法使い: 2戦0勝2敗
  (2, 2, 0, 2, 0, 180, 380, 0, 0, 950),

  -- 風の剣士: 2戦2勝0敗
  (3, 2, 2, 0, 0, 420, 250, 2, 2, 1100),

  -- 大地の盾: 2戦0勝2敗
  (4, 2, 0, 2, 0, 200, 400, 0, 0, 940),

  -- 雷の槍使い: 1戦1勝0敗
  (5, 1, 1, 0, 0, 250, 120, 1, 1, 1025);

COMMIT;
