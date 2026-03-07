-- LLMバトルゲーム データベーススキーマ
-- DBMS: SQLite 3.51.2
-- 作成日: 2026-02-28

-- 外部キー制約を有効化
PRAGMA foreign_keys = ON;

-- ==================================================
-- 1. accounts（アカウント）
-- ==================================================
CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    session_id TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_login DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_accounts_username ON accounts(username);
CREATE INDEX IF NOT EXISTS idx_accounts_session_id ON accounts(session_id);

-- ==================================================
-- 2. characters（キャラクター）
-- ==================================================
CREATE TABLE IF NOT EXISTS characters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    prompt TEXT NOT NULL,
    level INTEGER DEFAULT 1,

    -- 基礎ステータス（プレイヤーが設定）
    base_hp INTEGER NOT NULL CHECK(base_hp > 0),
    base_attack INTEGER NOT NULL CHECK(base_attack > 0),
    base_defense INTEGER NOT NULL CHECK(base_defense > 0),
    base_speed INTEGER NOT NULL CHECK(base_speed > 0),

    -- 計算済みステータス（レベル補正後）
    computed_hp INTEGER NOT NULL,
    computed_attack INTEGER NOT NULL,
    computed_defense INTEGER NOT NULL,
    computed_speed INTEGER NOT NULL,

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_characters_account_id ON characters(account_id);
CREATE INDEX IF NOT EXISTS idx_characters_level ON characters(level);

-- ==================================================
-- 3. abilities（アビリティマスター）
-- ==================================================
CREATE TABLE IF NOT EXISTS abilities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    description TEXT NOT NULL,
    effect_type TEXT NOT NULL CHECK(effect_type IN ('damage', 'heal', 'buff', 'debuff')),
    power INTEGER NOT NULL CHECK(power >= 0),
    cost INTEGER DEFAULT 0,
    cooldown INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_abilities_effect_type ON abilities(effect_type);

-- ==================================================
-- 4. character_abilities（キャラクター-アビリティ関連）
-- ==================================================
CREATE TABLE IF NOT EXISTS character_abilities (
    character_id INTEGER NOT NULL,
    ability_id INTEGER NOT NULL,
    acquired_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (character_id, ability_id),
    FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE,
    FOREIGN KEY (ability_id) REFERENCES abilities(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_char_abilities_character ON character_abilities(character_id);
CREATE INDEX IF NOT EXISTS idx_char_abilities_ability ON character_abilities(ability_id);

-- ==================================================
-- 5. battles（バトル）
-- ==================================================
CREATE TABLE IF NOT EXISTS battles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player1_id INTEGER NOT NULL,
    player2_id INTEGER NOT NULL,
    winner_id INTEGER,

    -- バトル設定
    max_turns INTEGER DEFAULT 50,
    current_turn INTEGER DEFAULT 0,

    -- 現在のHP
    player1_hp INTEGER,
    player2_hp INTEGER,
    player1_max_hp INTEGER,
    player2_max_hp INTEGER,

    -- 状態
    status TEXT NOT NULL DEFAULT 'waiting' CHECK(status IN ('waiting', 'in_progress', 'finished', 'cancelled')),

    -- 時刻
    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    ended_at DATETIME,

    FOREIGN KEY (player1_id) REFERENCES characters(id) ON DELETE CASCADE,
    FOREIGN KEY (player2_id) REFERENCES characters(id) ON DELETE CASCADE,
    FOREIGN KEY (winner_id) REFERENCES characters(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_battles_player1 ON battles(player1_id);
CREATE INDEX IF NOT EXISTS idx_battles_player2 ON battles(player2_id);
CREATE INDEX IF NOT EXISTS idx_battles_status ON battles(status);
CREATE INDEX IF NOT EXISTS idx_battles_started_at ON battles(started_at DESC);

-- ==================================================
-- 6. battle_turns（バトルターン）
-- ==================================================
CREATE TABLE IF NOT EXISTS battle_turns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    battle_id INTEGER NOT NULL,
    turn_number INTEGER NOT NULL,

    -- プレイヤー1のアクション
    player1_action TEXT NOT NULL CHECK(player1_action IN ('attack', 'defend', 'dodge', 'ability')),
    player1_ability_id INTEGER,
    player1_target TEXT,
    player1_damage_dealt INTEGER DEFAULT 0,
    player1_damage_received INTEGER DEFAULT 0,
    player1_hp_after INTEGER NOT NULL,

    -- プレイヤー2のアクション
    player2_action TEXT NOT NULL CHECK(player2_action IN ('attack', 'defend', 'dodge', 'ability')),
    player2_ability_id INTEGER,
    player2_target TEXT,
    player2_damage_dealt INTEGER DEFAULT 0,
    player2_damage_received INTEGER DEFAULT 0,
    player2_hp_after INTEGER NOT NULL,

    -- ターン結果
    turn_result TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (battle_id) REFERENCES battles(id) ON DELETE CASCADE,
    FOREIGN KEY (player1_ability_id) REFERENCES abilities(id),
    FOREIGN KEY (player2_ability_id) REFERENCES abilities(id)
);

CREATE INDEX IF NOT EXISTS idx_battle_turns_battle ON battle_turns(battle_id, turn_number);

-- ==================================================
-- 7. stats（戦績）
-- ==================================================
CREATE TABLE IF NOT EXISTS stats (
    character_id INTEGER PRIMARY KEY,
    total_battles INTEGER DEFAULT 0 CHECK(total_battles >= 0),
    wins INTEGER DEFAULT 0 CHECK(wins >= 0),
    losses INTEGER DEFAULT 0 CHECK(losses >= 0),
    draws INTEGER DEFAULT 0 CHECK(draws >= 0),
    total_damage_dealt INTEGER DEFAULT 0,
    total_damage_received INTEGER DEFAULT 0,
    longest_win_streak INTEGER DEFAULT 0,
    current_win_streak INTEGER DEFAULT 0,
    rating INTEGER DEFAULT 1000,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_stats_rating ON stats(rating DESC);
CREATE INDEX IF NOT EXISTS idx_stats_wins ON stats(wins DESC);

-- ==================================================
-- 8. queue（マッチング待機キュー）
-- ==================================================
CREATE TABLE IF NOT EXISTS queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    character_id INTEGER UNIQUE NOT NULL,
    rating INTEGER NOT NULL,
    joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_queue_rating ON queue(rating);
CREATE INDEX IF NOT EXISTS idx_queue_joined_at ON queue(joined_at);

-- ==================================================
-- 9. schema_version（スキーマバージョン管理）
-- ==================================================
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);

-- スキーマバージョンの初期値挿入
INSERT OR IGNORE INTO schema_version (version, description)
VALUES (1, 'Initial schema - LLM Battle Game');
