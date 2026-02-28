# データベース設計書

**プロジェクト**: LLMバトルゲーム
**作成日**: 2026-02-28
**担当**: Director
**DBMS**: SQLite 3.51.2

---

## 1. データベース概要

### 1.1 データベースファイル
- **パス**: `src/database/llmbattle.db`
- **形式**: SQLite 3
- **文字エンコーディング**: UTF-8
- **外部キー制約**: 有効

### 1.2 設計原則
- 正規化: 第3正規形まで適用
- シンプル性: 必要最小限のテーブル構成
- 拡張性: 将来の機能追加を考慮
- パフォーマンス: 適切なインデックス配置

---

## 2. テーブル一覧

| テーブル名 | 説明 | レコード数見積 |
|-----------|------|--------------|
| accounts | プレイヤーアカウント | 100-1000 |
| characters | キャラクター | 500-5000 |
| battles | バトル履歴 | 1000-10000 |
| battle_turns | ターンごとの行動記録 | 10000-100000 |
| stats | キャラクター戦績 | 500-5000 |
| queue | マッチング待機キュー | 0-50 |
| abilities | アビリティマスター | 20-100 |

---

## 3. テーブル定義

### 3.1 accounts（アカウント）

プレイヤーのアカウント情報を管理。

```sql
CREATE TABLE accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    session_id TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_login DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_accounts_username ON accounts(username);
CREATE INDEX idx_accounts_session_id ON accounts(session_id);
```

| カラム名 | 型 | NULL | デフォルト | 説明 |
|---------|---|------|----------|------|
| id | INTEGER | NO | AUTO | アカウントID（主キー） |
| username | TEXT | NO | - | ユーザー名（一意） |
| session_id | TEXT | YES | NULL | セッションID（認証用） |
| created_at | DATETIME | NO | 現在時刻 | アカウント作成日時 |
| last_login | DATETIME | NO | 現在時刻 | 最終ログイン日時 |

---

### 3.2 characters（キャラクター）

プレイヤーが作成したキャラクター情報。

```sql
CREATE TABLE characters (
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

CREATE INDEX idx_characters_account_id ON characters(account_id);
CREATE INDEX idx_characters_level ON characters(level);
```

| カラム名 | 型 | NULL | デフォルト | 説明 |
|---------|---|------|----------|------|
| id | INTEGER | NO | AUTO | キャラクターID（主キー） |
| account_id | INTEGER | NO | - | アカウントID（外部キー） |
| name | TEXT | NO | - | キャラクター名 |
| prompt | TEXT | NO | - | キャラクター設定プロンプト（最大2000文字） |
| level | INTEGER | NO | 1 | レベル（1-100） |
| base_hp | INTEGER | NO | - | 基礎HP（10-100） |
| base_attack | INTEGER | NO | - | 基礎攻撃力（10-100） |
| base_defense | INTEGER | NO | - | 基礎防御力（10-100） |
| base_speed | INTEGER | NO | - | 基礎速度（10-100） |
| computed_hp | INTEGER | NO | - | 計算済みHP |
| computed_attack | INTEGER | NO | - | 計算済み攻撃力 |
| computed_defense | INTEGER | NO | - | 計算済み防御力 |
| computed_speed | INTEGER | NO | - | 計算済み速度 |
| created_at | DATETIME | NO | 現在時刻 | 作成日時 |
| updated_at | DATETIME | NO | 現在時刻 | 更新日時 |

**ステータス計算ルール**:
```
computed_hp = base_hp * (1 + (level - 1) * 0.1)
computed_attack = base_attack * (1 + (level - 1) * 0.1)
computed_defense = base_defense * (1 + (level - 1) * 0.1)
computed_speed = base_speed * (1 + (level - 1) * 0.1)
```

---

### 3.3 abilities（アビリティマスター）

キャラクターが使用できるアビリティの定義。

```sql
CREATE TABLE abilities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    description TEXT NOT NULL,
    effect_type TEXT NOT NULL CHECK(effect_type IN ('damage', 'heal', 'buff', 'debuff')),
    power INTEGER NOT NULL CHECK(power >= 0),
    cost INTEGER DEFAULT 0,
    cooldown INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_abilities_effect_type ON abilities(effect_type);
```

| カラム名 | 型 | NULL | デフォルト | 説明 |
|---------|---|------|----------|------|
| id | INTEGER | NO | AUTO | アビリティID（主キー） |
| name | TEXT | NO | - | アビリティ名（一意） |
| description | TEXT | NO | - | 説明 |
| effect_type | TEXT | NO | - | 効果タイプ（damage/heal/buff/debuff） |
| power | INTEGER | NO | - | 威力・効果量 |
| cost | INTEGER | NO | 0 | コスト（将来的に使用） |
| cooldown | INTEGER | NO | 0 | クールダウンターン数 |
| created_at | DATETIME | NO | 現在時刻 | 作成日時 |

---

### 3.4 character_abilities（キャラクター-アビリティ関連）

キャラクターが習得しているアビリティの中間テーブル。

```sql
CREATE TABLE character_abilities (
    character_id INTEGER NOT NULL,
    ability_id INTEGER NOT NULL,
    acquired_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (character_id, ability_id),
    FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE,
    FOREIGN KEY (ability_id) REFERENCES abilities(id) ON DELETE CASCADE
);

CREATE INDEX idx_char_abilities_character ON character_abilities(character_id);
CREATE INDEX idx_char_abilities_ability ON character_abilities(ability_id);
```

---

### 3.5 battles（バトル）

バトルの基本情報と結果を記録。

```sql
CREATE TABLE battles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player1_id INTEGER NOT NULL,
    player2_id INTEGER NOT NULL,
    winner_id INTEGER,

    -- バトル設定
    max_turns INTEGER DEFAULT 50,
    current_turn INTEGER DEFAULT 0,

    -- 状態
    status TEXT NOT NULL DEFAULT 'waiting' CHECK(status IN ('waiting', 'in_progress', 'finished', 'cancelled')),

    -- 時刻
    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    ended_at DATETIME,

    FOREIGN KEY (player1_id) REFERENCES characters(id) ON DELETE CASCADE,
    FOREIGN KEY (player2_id) REFERENCES characters(id) ON DELETE CASCADE,
    FOREIGN KEY (winner_id) REFERENCES characters(id) ON DELETE SET NULL
);

CREATE INDEX idx_battles_player1 ON battles(player1_id);
CREATE INDEX idx_battles_player2 ON battles(player2_id);
CREATE INDEX idx_battles_status ON battles(status);
CREATE INDEX idx_battles_started_at ON battles(started_at DESC);
```

| カラム名 | 型 | NULL | デフォルト | 説明 |
|---------|---|------|----------|------|
| id | INTEGER | NO | AUTO | バトルID（主キー） |
| player1_id | INTEGER | NO | - | プレイヤー1のキャラクターID |
| player2_id | INTEGER | NO | - | プレイヤー2のキャラクターID |
| winner_id | INTEGER | YES | NULL | 勝者のキャラクターID |
| max_turns | INTEGER | NO | 50 | 最大ターン数 |
| current_turn | INTEGER | NO | 0 | 現在のターン数 |
| status | TEXT | NO | waiting | バトル状態 |
| started_at | DATETIME | NO | 現在時刻 | 開始日時 |
| ended_at | DATETIME | YES | NULL | 終了日時 |

**status値**:
- `waiting`: マッチング待機中
- `in_progress`: バトル進行中
- `finished`: バトル終了
- `cancelled`: キャンセル

---

### 3.6 battle_turns（バトルターン）

各ターンの詳細な行動記録。

```sql
CREATE TABLE battle_turns (
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

CREATE INDEX idx_battle_turns_battle ON battle_turns(battle_id, turn_number);
```

| カラム名 | 型 | NULL | デフォルト | 説明 |
|---------|---|------|----------|------|
| id | INTEGER | NO | AUTO | ターンID（主キー） |
| battle_id | INTEGER | NO | - | バトルID（外部キー） |
| turn_number | INTEGER | NO | - | ターン番号 |
| player1_action | TEXT | NO | - | プレイヤー1の行動 |
| player1_ability_id | INTEGER | YES | NULL | 使用アビリティID |
| player1_target | TEXT | YES | NULL | ターゲット情報 |
| player1_damage_dealt | INTEGER | NO | 0 | 与えたダメージ |
| player1_damage_received | INTEGER | NO | 0 | 受けたダメージ |
| player1_hp_after | INTEGER | NO | - | ターン後のHP |
| player2_action | TEXT | NO | - | プレイヤー2の行動 |
| player2_ability_id | INTEGER | YES | NULL | 使用アビリティID |
| player2_target | TEXT | YES | NULL | ターゲット情報 |
| player2_damage_dealt | INTEGER | NO | 0 | 与えたダメージ |
| player2_damage_received | INTEGER | NO | 0 | 受けたダメージ |
| player2_hp_after | INTEGER | NO | - | ターン後のHP |
| turn_result | TEXT | NO | - | ターン結果サマリー（JSON形式） |
| created_at | DATETIME | NO | 現在時刻 | 作成日時 |

---

### 3.7 stats（戦績）

キャラクターごとの戦績を集計。

```sql
CREATE TABLE stats (
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

CREATE INDEX idx_stats_rating ON stats(rating DESC);
CREATE INDEX idx_stats_wins ON stats(wins DESC);
```

| カラム名 | 型 | NULL | デフォルト | 説明 |
|---------|---|------|----------|------|
| character_id | INTEGER | NO | - | キャラクターID（主キー・外部キー） |
| total_battles | INTEGER | NO | 0 | 総バトル数 |
| wins | INTEGER | NO | 0 | 勝利数 |
| losses | INTEGER | NO | 0 | 敗北数 |
| draws | INTEGER | NO | 0 | 引き分け数 |
| total_damage_dealt | INTEGER | NO | 0 | 総与ダメージ |
| total_damage_received | INTEGER | NO | 0 | 総被ダメージ |
| longest_win_streak | INTEGER | NO | 0 | 最長連勝記録 |
| current_win_streak | INTEGER | NO | 0 | 現在の連勝数 |
| rating | INTEGER | NO | 1000 | レーティング（MMR） |
| updated_at | DATETIME | NO | 現在時刻 | 更新日時 |

**レーティング計算**:
- 初期値: 1000
- 勝利: +25 + (相手レーティング - 自分レーティング) / 20
- 敗北: -25 + (相手レーティング - 自分レーティング) / 20
- 引き分け: ±0

---

### 3.8 queue（マッチング待機キュー）

マッチング待機中のプレイヤーを管理。

```sql
CREATE TABLE queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    character_id INTEGER UNIQUE NOT NULL,
    rating INTEGER NOT NULL,
    joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
);

CREATE INDEX idx_queue_rating ON queue(rating);
CREATE INDEX idx_queue_joined_at ON queue(joined_at);
```

| カラム名 | 型 | NULL | デフォルト | 説明 |
|---------|---|------|----------|------|
| id | INTEGER | NO | AUTO | キューID（主キー） |
| character_id | INTEGER | NO | - | キャラクターID（一意・外部キー） |
| rating | INTEGER | NO | - | レーティング（マッチング用） |
| joined_at | DATETIME | NO | 現在時刻 | キュー参加日時 |

---

## 4. ER図

```
┌─────────────┐
│  accounts   │
│─────────────│
│ id (PK)     │
│ username    │
│ session_id  │
│ created_at  │
└──────┬──────┘
       │ 1
       │
       │ N
┌──────▼──────────┐
│   characters    │
│─────────────────│
│ id (PK)         │
│ account_id (FK) │◄──┐
│ name            │   │
│ prompt          │   │
│ level           │   │
│ base_hp         │   │
│ ...             │   │
└──────┬──────────┘   │
       │ 1            │
       │              │
       │ N            │
┌──────▼──────────┐   │
│character_       │   │
│abilities        │   │
│─────────────────│   │
│character_id(FK) │   │
│ability_id (FK)  │   │
└──────┬──────────┘   │
       │              │
       │ N            │
┌──────▼──────────┐   │
│   abilities     │   │
│─────────────────│   │
│ id (PK)         │   │
│ name            │   │
│ effect_type     │   │
│ ...             │   │
└─────────────────┘   │
                      │
       ┌──────────────┘
       │ 1
       │
       │ 2 (player1, player2)
┌──────▼──────────┐
│    battles      │
│─────────────────│
│ id (PK)         │
│ player1_id (FK) │
│ player2_id (FK) │
│ winner_id (FK)  │
│ status          │
│ ...             │
└──────┬──────────┘
       │ 1
       │
       │ N
┌──────▼──────────┐
│ battle_turns    │
│─────────────────│
│ id (PK)         │
│ battle_id (FK)  │
│ turn_number     │
│ ...             │
└─────────────────┘

┌─────────────────┐
│     stats       │
│─────────────────│
│character_id(PK) │◄─── characters.id
│ total_battles   │
│ wins            │
│ rating          │
│ ...             │
└─────────────────┘

┌─────────────────┐
│     queue       │
│─────────────────│
│ id (PK)         │
│character_id(FK) │◄─── characters.id
│ rating          │
│ joined_at       │
└─────────────────┘
```

---

## 5. 初期データ

### 5.1 デフォルトアビリティ

```sql
INSERT INTO abilities (name, description, effect_type, power) VALUES
('強打', '通常攻撃の1.5倍のダメージを与える', 'damage', 150),
('防御態勢', '次のターンの被ダメージを50%軽減', 'buff', 50),
('回復', 'HPを最大値の30%回復', 'heal', 30),
('連続攻撃', '2回攻撃を行う（各70%のダメージ）', 'damage', 140),
('カウンター', '攻撃を受けた時に50%のダメージで反撃', 'buff', 50),
('弱体化', '相手の攻撃力を1ターン30%下げる', 'debuff', 30),
('必殺技', '通常攻撃の2倍のダメージ（クールダウン3ターン）', 'damage', 200);

UPDATE abilities SET cooldown = 3 WHERE name = '必殺技';
```

---

## 6. クエリ例

### 6.1 キャラクター作成

```sql
-- トランザクション開始
BEGIN TRANSACTION;

-- キャラクター作成
INSERT INTO characters (account_id, name, prompt, base_hp, base_attack, base_defense, base_speed)
VALUES (1, '炎の戦士', 'あなたは熱き魂を持つ戦士です...', 100, 80, 60, 70);

-- ステータス計算（レベル1の場合は同じ値）
UPDATE characters SET
    computed_hp = base_hp,
    computed_attack = base_attack,
    computed_defense = base_defense,
    computed_speed = base_speed
WHERE id = last_insert_rowid();

-- 戦績初期化
INSERT INTO stats (character_id) VALUES (last_insert_rowid());

COMMIT;
```

### 6.2 マッチング

```sql
-- キューに参加
INSERT INTO queue (character_id, rating)
SELECT id, COALESCE((SELECT rating FROM stats WHERE character_id = ?), 1000)
FROM characters WHERE id = ?;

-- マッチング相手を検索（レーティング差100以内）
SELECT q.character_id, q.rating, c.name
FROM queue q
JOIN characters c ON q.character_id = c.id
WHERE q.character_id != ?
  AND ABS(q.rating - ?) <= 100
ORDER BY ABS(q.rating - ?)
LIMIT 1;
```

### 6.3 バトル開始

```sql
BEGIN TRANSACTION;

-- バトルレコード作成
INSERT INTO battles (player1_id, player2_id, status)
VALUES (?, ?, 'in_progress');

-- キューから削除
DELETE FROM queue WHERE character_id IN (?, ?);

COMMIT;
```

### 6.4 ターン記録

```sql
INSERT INTO battle_turns (
    battle_id, turn_number,
    player1_action, player1_damage_dealt, player1_damage_received, player1_hp_after,
    player2_action, player2_damage_dealt, player2_damage_received, player2_hp_after,
    turn_result
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);

-- バトルの現在ターンを更新
UPDATE battles SET current_turn = ? WHERE id = ?;
```

### 6.5 バトル終了・戦績更新

```sql
BEGIN TRANSACTION;

-- バトル終了
UPDATE battles SET
    status = 'finished',
    winner_id = ?,
    ended_at = CURRENT_TIMESTAMP
WHERE id = ?;

-- 勝者の戦績更新
UPDATE stats SET
    total_battles = total_battles + 1,
    wins = wins + 1,
    current_win_streak = current_win_streak + 1,
    longest_win_streak = MAX(longest_win_streak, current_win_streak + 1),
    rating = rating + ?,
    updated_at = CURRENT_TIMESTAMP
WHERE character_id = ?;

-- 敗者の戦績更新
UPDATE stats SET
    total_battles = total_battles + 1,
    losses = losses + 1,
    current_win_streak = 0,
    rating = rating + ?,
    updated_at = CURRENT_TIMESTAMP
WHERE character_id = ?;

COMMIT;
```

### 6.6 リーダーボード取得

```sql
SELECT
    c.id,
    c.name,
    c.level,
    s.rating,
    s.total_battles,
    s.wins,
    s.losses,
    s.draws,
    ROUND(CAST(s.wins AS REAL) / NULLIF(s.total_battles, 0) * 100, 2) as win_rate,
    s.current_win_streak,
    s.longest_win_streak
FROM characters c
JOIN stats s ON c.id = s.character_id
WHERE s.total_battles > 0
ORDER BY s.rating DESC, s.wins DESC
LIMIT 100;
```

---

## 7. パフォーマンス最適化

### 7.1 インデックス戦略

- 外部キー全てにインデックス作成済み
- 頻繁な検索条件（rating, status, created_at）にインデックス
- 複合インデックスは必要に応じて追加

### 7.2 定期メンテナンス

```sql
-- 古いキューエントリの削除（10分以上前）
DELETE FROM queue WHERE joined_at < datetime('now', '-10 minutes');

-- 終了したバトルの古いターン詳細の削除（オプション、30日以上前）
DELETE FROM battle_turns
WHERE battle_id IN (
    SELECT id FROM battles
    WHERE status = 'finished'
    AND ended_at < datetime('now', '-30 days')
);

-- VACUUM実行（週次推奨）
VACUUM;

-- ANALYZE実行（統計情報更新）
ANALYZE;
```

---

## 8. データ整合性

### 8.1 外部キー制約

- すべての外部キーに `ON DELETE CASCADE` または `ON DELETE SET NULL`
- 孤立レコードの防止

### 8.2 CHECK制約

- ステータス値の妥当性チェック（正の整数）
- ENUM相当の値チェック（status, action等）

### 8.3 トランザクション管理

- 複数テーブルの更新は必ずトランザクション内で実行
- バトル開始・終了時の整合性保証

---

## 9. バックアップ戦略

### 9.1 定期バックアップ

```bash
# 日次バックアップ（オペレーティングシステムレベル）
cp src/database/llmbattle.db backups/llmbattle_$(date +%Y%m%d).db
```

### 9.2 エクスポート

```bash
# SQL形式でエクスポート
sqlite3 src/database/llmbattle.db .dump > backup.sql

# インポート
sqlite3 src/database/llmbattle.db < backup.sql
```

---

## 10. マイグレーション計画

### 10.1 スキーマバージョン管理

```sql
CREATE TABLE schema_version (
    version INTEGER PRIMARY KEY,
    applied_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);

INSERT INTO schema_version (version, description)
VALUES (1, 'Initial schema');
```

### 10.2 将来の拡張（例）

**レベルアップ機能追加**:
```sql
ALTER TABLE characters ADD COLUMN experience INTEGER DEFAULT 0;
```

**チーム戦機能追加**:
```sql
CREATE TABLE teams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE team_members (
    team_id INTEGER NOT NULL,
    character_id INTEGER NOT NULL,
    role TEXT,
    PRIMARY KEY (team_id, character_id),
    FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE,
    FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
);
```

---

## 11. 関連ドキュメント

- [システムアーキテクチャ](./architecture.md)
- [MCPサーバー設計](./mcp-server.md)
- [バトルロジック設計](./battle-logic.md)

---

**設計承認**: 待機中
**次のステップ**: MCPサーバー設計の詳細化
