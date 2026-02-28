-- LLMバトルゲーム 初期データ投入スクリプト
-- 作成日: 2026-02-28

-- ==================================================
-- デフォルトアビリティの登録
-- ==================================================

-- 1. 強打（通常攻撃の1.5倍のダメージ）
INSERT OR IGNORE INTO abilities (name, description, effect_type, power, cost, cooldown)
VALUES ('強打', '通常攻撃の1.5倍のダメージを与える', 'damage', 150, 0, 0);

-- 2. 連続攻撃（2回攻撃、各70%のダメージ）
INSERT OR IGNORE INTO abilities (name, description, effect_type, power, cost, cooldown)
VALUES ('連続攻撃', '2回攻撃を行う（各70%のダメージ）', 'damage', 140, 0, 1);

-- 3. 必殺技（通常攻撃の2倍、クールダウン3ターン）
INSERT OR IGNORE INTO abilities (name, description, effect_type, power, cost, cooldown)
VALUES ('必殺技', '通常攻撃の2倍のダメージ（クールダウン3ターン）', 'damage', 200, 0, 3);

-- 4. 回復（HPを最大値の30%回復）
INSERT OR IGNORE INTO abilities (name, description, effect_type, power, cost, cooldown)
VALUES ('回復', 'HPを最大値の30%回復', 'heal', 30, 0, 2);

-- 5. 防御態勢（次のターンの被ダメージを50%軽減）
INSERT OR IGNORE INTO abilities (name, description, effect_type, power, cost, cooldown)
VALUES ('防御態勢', '次のターンの被ダメージを50%軽減', 'buff', 50, 0, 1);

-- 6. カウンター（攻撃を受けた時に50%のダメージで反撃）
INSERT OR IGNORE INTO abilities (name, description, effect_type, power, cost, cooldown)
VALUES ('カウンター', '攻撃を受けた時に50%のダメージで反撃', 'buff', 50, 0, 2);

-- 7. 弱体化（相手の攻撃力を1ターン30%下げる）
INSERT OR IGNORE INTO abilities (name, description, effect_type, power, cost, cooldown)
VALUES ('弱体化', '相手の攻撃力を1ターン30%下げる', 'debuff', 30, 0, 2);
