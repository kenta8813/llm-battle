# マッチングロジック設計書

**プロジェクト**: LLMバトルゲーム
**作成日**: 2026-02-28
**担当**: Director

---

## 1. マッチングシステム概要

### 1.1 基本コンセプト
- レーティングベースの公平なマッチング
- 待機時間に応じた条件緩和
- シンプルで実装しやすいアルゴリズム
- ローカル環境での動作を前提

### 1.2 設計原則
- レーティング差を最小化して公平性を確保
- 長時間待機を避けるための段階的条件緩和
- データベース負荷を最小化
- 同時マッチング競合の適切な処理

### 1.3 マッチング目標
- 平均待機時間: 5秒以内
- レーティング差: ±100以内（理想）
- 最大待機時間: 60秒（条件緩和後）
- 同時参加者数: 最大50キャラクター

---

## 2. マッチングアルゴリズム

### 2.1 基本フロー

```
[キュー参加]
    ↓
[即座にマッチング試行]
    ↓
[相手が見つかった?]
    ├─ YES → [マッチング成立] → [バトル開始]
    └─ NO → [キュー待機] → [定期的にマッチング再試行]
                              ↓
                       [条件緩和ロジック適用]
```

### 2.2 マッチング条件

#### 初期条件（待機時間 0-15秒）
```python
rating_range = 100  # レーティング差±100以内
min_rating = my_rating - rating_range
max_rating = my_rating + rating_range
```

#### 第1段階緩和（待機時間 15-30秒）
```python
rating_range = 200  # レーティング差±200以内
```

#### 第2段階緩和（待機時間 30-45秒）
```python
rating_range = 400  # レーティング差±400以内
```

#### 最終段階（待機時間 45秒以上）
```python
rating_range = None  # 制限なし（誰とでもマッチング）
```

### 2.3 マッチング検索クエリ

```python
def find_match(character_id: int, my_rating: int, wait_time: float) -> Optional[int]:
    """
    マッチング相手を検索する。

    Args:
        character_id: 自分のキャラクターID
        my_rating: 自分のレーティング
        wait_time: 待機時間（秒）

    Returns:
        マッチング相手のキャラクターID（見つからない場合はNone）
    """
    # 待機時間に応じた条件範囲を決定
    rating_range = get_rating_range(wait_time)

    # SQLクエリ
    if rating_range is None:
        # 制限なし
        query = """
            SELECT character_id, rating
            FROM queue
            WHERE character_id != ?
            ORDER BY joined_at ASC
            LIMIT 1
        """
        params = (character_id,)
    else:
        # レーティング範囲内で検索
        query = """
            SELECT character_id, rating
            FROM queue
            WHERE character_id != ?
              AND rating BETWEEN ? AND ?
            ORDER BY ABS(rating - ?), joined_at ASC
            LIMIT 1
        """
        min_rating = my_rating - rating_range
        max_rating = my_rating + rating_range
        params = (character_id, min_rating, max_rating, my_rating)

    result = db.execute(query, params).fetchone()
    return result['character_id'] if result else None


def get_rating_range(wait_time: float) -> Optional[int]:
    """
    待機時間に応じたレーティング範囲を返す。

    Args:
        wait_time: 待機時間（秒）

    Returns:
        レーティング範囲（Noneは制限なし）
    """
    if wait_time < 15:
        return 100
    elif wait_time < 30:
        return 200
    elif wait_time < 45:
        return 400
    else:
        return None  # 制限なし
```

### 2.4 優先順位アルゴリズム

複数の候補がいる場合の優先順位:

1. **レーティング差が最小**
2. **待機時間が長い**（先着順）

```python
ORDER BY ABS(rating - my_rating) ASC, joined_at ASC
```

---

## 3. キュー管理システム

### 3.1 キューのデータ構造

データベーステーブル `queue` を使用（database.mdで定義済み）:

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

### 3.2 キュー操作

#### キューに追加

```python
async def join_queue(character_id: int) -> dict:
    """
    キューに参加する。

    Args:
        character_id: キャラクターID

    Returns:
        キュー参加結果
    """
    # キャラクター情報とレーティングを取得
    character = get_character(character_id)
    rating = get_character_rating(character_id)

    # すでにキューに参加していないかチェック
    existing = db.execute(
        "SELECT id FROM queue WHERE character_id = ?",
        (character_id,)
    ).fetchone()

    if existing:
        raise ValidationError("すでにキューに参加しています")

    # キューに追加
    db.execute(
        "INSERT INTO queue (character_id, rating) VALUES (?, ?)",
        (character_id, rating)
    )
    db.commit()

    # 即座にマッチング試行
    opponent_id = find_match(character_id, rating, 0.0)

    if opponent_id:
        # マッチング成立
        battle_id = create_battle(character_id, opponent_id)
        return {
            "status": "matched",
            "battle_id": battle_id,
            "opponent_id": opponent_id,
            "message": "マッチングが成立しました"
        }
    else:
        # キュー待機
        return {
            "status": "waiting",
            "message": "マッチング相手を探しています..."
        }
```

#### キューから削除

```python
async def leave_queue(character_id: int) -> dict:
    """
    キューから離脱する。

    Args:
        character_id: キャラクターID

    Returns:
        離脱結果
    """
    result = db.execute(
        "DELETE FROM queue WHERE character_id = ?",
        (character_id,)
    )
    db.commit()

    if result.rowcount == 0:
        raise ValidationError("キューに参加していません")

    return {
        "status": "left",
        "message": "キューから離脱しました"
    }
```

#### キュー検索

```python
async def get_queue_status(character_id: int) -> dict:
    """
    キューの状態を取得する。

    Args:
        character_id: キャラクターID

    Returns:
        キュー状態情報
    """
    queue_entry = db.execute(
        "SELECT id, rating, joined_at FROM queue WHERE character_id = ?",
        (character_id,)
    ).fetchone()

    if not queue_entry:
        return {
            "in_queue": False,
            "message": "キューに参加していません"
        }

    # 待機時間計算
    joined_at = datetime.fromisoformat(queue_entry['joined_at'])
    wait_time = (datetime.now() - joined_at).total_seconds()

    # キュー内の人数
    queue_count = db.execute("SELECT COUNT(*) as count FROM queue").fetchone()['count']

    return {
        "in_queue": True,
        "wait_time": wait_time,
        "queue_position": queue_count,
        "rating_range": get_rating_range(wait_time)
    }
```

### 3.3 タイムアウト処理

古いキューエントリの自動削除:

```python
async def cleanup_expired_queue_entries():
    """
    10分以上前のキューエントリを削除する。

    定期的にバックグラウンドで実行。
    """
    db.execute(
        "DELETE FROM queue WHERE joined_at < datetime('now', '-10 minutes')"
    )
    db.commit()
```

実行タイミング:
- マッチング処理の前に毎回実行
- または、5分ごとにバックグラウンドタスクで実行

---

## 4. マッチング成立処理

### 4.1 ペアリングロジック

```python
async def create_battle(player1_id: int, player2_id: int) -> int:
    """
    マッチング成立後、バトルを作成する。

    Args:
        player1_id: プレイヤー1のキャラクターID
        player2_id: プレイヤー2のキャラクターID

    Returns:
        作成されたバトルID
    """
    try:
        db.execute("BEGIN TRANSACTION")

        # 両方のキャラクターがまだキューに存在するか確認
        player1_in_queue = db.execute(
            "SELECT id FROM queue WHERE character_id = ?",
            (player1_id,)
        ).fetchone()

        player2_in_queue = db.execute(
            "SELECT id FROM queue WHERE character_id = ?",
            (player2_id,)
        ).fetchone()

        if not player1_in_queue or not player2_in_queue:
            # どちらかがすでにキューから離脱している
            db.execute("ROLLBACK")
            raise BattleError("マッチング相手がキューから離脱しました")

        # バトルレコード作成
        cursor = db.execute(
            """
            INSERT INTO battles (player1_id, player2_id, status, current_turn)
            VALUES (?, ?, 'in_progress', 0)
            """,
            (player1_id, player2_id)
        )
        battle_id = cursor.lastrowid

        # 両方のキャラクターをキューから削除
        db.execute(
            "DELETE FROM queue WHERE character_id IN (?, ?)",
            (player1_id, player2_id)
        )

        db.execute("COMMIT")

        # WebSocketで通知（将来実装）
        # await notify_battle_started(battle_id, player1_id, player2_id)

        return battle_id

    except Exception as e:
        db.execute("ROLLBACK")
        raise BattleError(f"バトル作成に失敗しました: {str(e)}")
```

### 4.2 バトル初期化フロー

```python
async def initialize_battle(battle_id: int):
    """
    バトルの初期状態を設定する。

    Args:
        battle_id: バトルID
    """
    # キャラクター情報を取得
    battle = get_battle(battle_id)
    player1 = get_character(battle['player1_id'])
    player2 = get_character(battle['player2_id'])

    # 初期状態をログに記録
    initial_state = {
        "battle_id": battle_id,
        "player1": {
            "id": player1['id'],
            "name": player1['name'],
            "hp": player1['computed_hp'],
            "attack": player1['computed_attack'],
            "defense": player1['computed_defense'],
            "speed": player1['computed_speed']
        },
        "player2": {
            "id": player2['id'],
            "name": player2['name'],
            "hp": player2['computed_hp'],
            "attack": player2['computed_attack'],
            "defense": player2['computed_defense'],
            "speed": player2['computed_speed']
        },
        "max_turns": battle['max_turns'],
        "started_at": battle['started_at']
    }

    logger.info(f"Battle initialized: {initial_state}")

    return initial_state
```

### 4.3 通知システム

マッチング成立時の通知:

```python
async def notify_match_found(character_id: int, battle_id: int, opponent_id: int):
    """
    マッチング成立をクライアントに通知する。

    Args:
        character_id: 通知対象のキャラクターID
        battle_id: バトルID
        opponent_id: 対戦相手のキャラクターID
    """
    opponent = get_character(opponent_id)

    notification = {
        "event": "match_found",
        "battle_id": battle_id,
        "opponent": {
            "id": opponent['id'],
            "name": opponent['name'],
            "level": opponent['level'],
            "rating": get_character_rating(opponent_id)
        },
        "message": f"{opponent['name']}とのバトルが開始されます"
    }

    # WebSocket経由で送信（将来実装）
    # await ws_notifier.send(character_id, notification)

    # ログ出力
    logger.info(f"Match found: character_id={character_id}, opponent_id={opponent_id}, battle_id={battle_id}")

    return notification
```

---

## 5. エッジケース対応

### 5.1 同時マッチング競合の解決

**問題**: 2つのキャラクターが同時に同じ相手とマッチングしようとする

**解決策**: トランザクションとUNIQUE制約で対応

```python
async def atomic_match_attempt(character_id: int, opponent_id: int) -> Optional[int]:
    """
    アトミックにマッチングを試行する。

    Args:
        character_id: 自分のキャラクターID
        opponent_id: 相手のキャラクターID

    Returns:
        バトルID（失敗時はNone）
    """
    try:
        db.execute("BEGIN IMMEDIATE TRANSACTION")

        # 両方がまだキューに存在するか確認（FOR UPDATE相当）
        player1 = db.execute(
            "SELECT character_id FROM queue WHERE character_id = ?",
            (character_id,)
        ).fetchone()

        player2 = db.execute(
            "SELECT character_id FROM queue WHERE character_id = ?",
            (opponent_id,)
        ).fetchone()

        if not player1 or not player2:
            # どちらかがすでに他のバトルにマッチング済み
            db.execute("ROLLBACK")
            return None

        # バトル作成
        battle_id = create_battle(character_id, opponent_id)

        db.execute("COMMIT")
        return battle_id

    except sqlite3.IntegrityError:
        # UNIQUE制約違反（すでに別のバトルで使用中）
        db.execute("ROLLBACK")
        return None
    except Exception as e:
        db.execute("ROLLBACK")
        logger.error(f"Match attempt failed: {e}")
        return None
```

### 5.2 キュー離脱処理

**シナリオ**:
1. マッチング待機中にプレイヤーが離脱
2. 別のプレイヤーがその相手とマッチングしようとする

**対応**:
```python
async def handle_queue_leave_during_matching(character_id: int):
    """
    マッチング処理中のキュー離脱を処理する。
    """
    # トランザクション内でキュー削除とマッチング検証を同時実行
    # create_battle内でキューの存在確認を行うため、自動的に処理される
    pass  # 上記のatomic_match_attempt内で対応済み
```

### 5.3 接続切れ・タイムアウト対応

#### キュー参加後の接続切れ

```python
async def handle_disconnection(character_id: int):
    """
    クライアント接続切れ時の処理。

    Args:
        character_id: 切断されたキャラクターID
    """
    # キューから自動削除
    await leave_queue(character_id)

    logger.info(f"Character {character_id} removed from queue due to disconnection")
```

#### マッチング応答タイムアウト

```python
async def check_match_timeout(character_id: int):
    """
    マッチング成立後、クライアントの応答を待つ。

    タイムアウト時はバトルをキャンセル。
    """
    timeout = 30  # 30秒

    try:
        # クライアントの応答を待つ（将来実装）
        # await wait_for_battle_ready(character_id, timeout=timeout)
        pass
    except asyncio.TimeoutError:
        # タイムアウト時はバトルをキャンセル
        battle = get_active_battle_by_character(character_id)
        if battle:
            await cancel_battle(battle['id'], reason="Player timeout")
```

#### バトルキャンセル処理

```python
async def cancel_battle(battle_id: int, reason: str = "Unknown"):
    """
    バトルをキャンセルし、プレイヤーをキューに戻す。

    Args:
        battle_id: バトルID
        reason: キャンセル理由
    """
    try:
        db.execute("BEGIN TRANSACTION")

        # バトル情報取得
        battle = get_battle(battle_id)

        # バトルステータスを'cancelled'に更新
        db.execute(
            "UPDATE battles SET status = 'cancelled', ended_at = CURRENT_TIMESTAMP WHERE id = ?",
            (battle_id,)
        )

        # プレイヤーをキューに戻す（オプション）
        # 注: 自動では戻さず、プレイヤーが再度参加する必要がある

        db.execute("COMMIT")

        logger.warning(f"Battle {battle_id} cancelled: {reason}")

    except Exception as e:
        db.execute("ROLLBACK")
        logger.error(f"Failed to cancel battle {battle_id}: {e}")
```

---

## 6. データベース連携

### 6.1 使用テーブル

主に使用するテーブル:
- `queue`: マッチング待機キュー
- `battles`: バトル情報
- `characters`: キャラクター情報
- `stats`: レーティング情報

### 6.2 主要クエリ設計

#### マッチング検索（レーティング範囲指定）

```sql
-- 最適な相手を検索
SELECT
    q.character_id,
    q.rating,
    c.name,
    c.level,
    (julianday('now') - julianday(q.joined_at)) * 86400 as wait_seconds
FROM queue q
JOIN characters c ON q.character_id = c.id
WHERE q.character_id != ?
  AND q.rating BETWEEN ? AND ?
ORDER BY ABS(q.rating - ?), q.joined_at ASC
LIMIT 1;
```

#### キュー統計取得

```sql
-- キュー内の人数とレーティング分布
SELECT
    COUNT(*) as total_count,
    AVG(rating) as avg_rating,
    MIN(rating) as min_rating,
    MAX(rating) as max_rating,
    AVG((julianday('now') - julianday(joined_at)) * 86400) as avg_wait_seconds
FROM queue;
```

#### レーティング取得

```sql
-- キャラクターのレーティングを取得（デフォルト1000）
SELECT COALESCE(rating, 1000) as rating
FROM stats
WHERE character_id = ?;
```

### 6.3 インデックス活用

既存のインデックス:
- `idx_queue_rating`: レーティング検索の高速化
- `idx_queue_joined_at`: 待機時間順ソートの高速化

追加推奨インデックス（パフォーマンス向上時）:
```sql
-- 複合インデックス（レーティング範囲検索 + 待機時間ソート）
CREATE INDEX idx_queue_rating_joined ON queue(rating, joined_at);
```

---

## 7. パフォーマンス要件

### 7.1 処理時間目標

| 処理 | 目標時間 | 最大許容時間 |
|------|---------|-------------|
| キュー参加 | < 50ms | 200ms |
| マッチング検索 | < 30ms | 100ms |
| バトル作成 | < 100ms | 500ms |
| キュー離脱 | < 20ms | 100ms |

### 7.2 スケーラビリティ

**ローカル環境での制約**:
- 同時キュー参加者: 最大50キャラクター
- 同時進行バトル: 最大20バトル
- データベースファイルサイズ: 最大500MB

**将来のスケールアップ時の考慮事項**:
- PostgreSQL等のリレーショナルDBへの移行
- マッチングキューのRedis活用
- バックグラウンドワーカーによる非同期マッチング

### 7.3 キャッシュ戦略

レーティング情報のキャッシュ:

```python
from functools import lru_cache
from datetime import datetime, timedelta

class RatingCache:
    def __init__(self, ttl: int = 300):  # 5分間キャッシュ
        self.cache = {}
        self.ttl = ttl

    def get(self, character_id: int) -> Optional[int]:
        if character_id in self.cache:
            rating, timestamp = self.cache[character_id]
            if (datetime.now() - timestamp).total_seconds() < self.ttl:
                return rating
        return None

    def set(self, character_id: int, rating: int):
        self.cache[character_id] = (rating, datetime.now())

    def invalidate(self, character_id: int):
        if character_id in self.cache:
            del self.cache[character_id]

rating_cache = RatingCache()

def get_character_rating_cached(character_id: int) -> int:
    """レーティングをキャッシュから取得（キャッシュミス時はDBから取得）"""
    cached = rating_cache.get(character_id)
    if cached is not None:
        return cached

    rating = get_character_rating(character_id)
    rating_cache.set(character_id, rating)
    return rating
```

---

## 8. テスト戦略

### 8.1 ユニットテスト項目

```python
# test_matching_logic.py

class TestMatchingLogic(unittest.TestCase):

    def test_join_queue_success(self):
        """キューへの正常な参加"""
        character_id = create_test_character()
        result = join_queue(character_id)
        self.assertEqual(result['status'], 'waiting')

    def test_join_queue_duplicate(self):
        """重複参加のエラー処理"""
        character_id = create_test_character()
        join_queue(character_id)
        with self.assertRaises(ValidationError):
            join_queue(character_id)

    def test_immediate_match(self):
        """即座のマッチング成立"""
        char1 = create_test_character(rating=1000)
        char2 = create_test_character(rating=1050)

        join_queue(char1)
        result = join_queue(char2)

        self.assertEqual(result['status'], 'matched')
        self.assertIsNotNone(result['battle_id'])

    def test_rating_range_expansion(self):
        """待機時間によるレーティング範囲拡大"""
        self.assertEqual(get_rating_range(0), 100)
        self.assertEqual(get_rating_range(20), 200)
        self.assertEqual(get_rating_range(35), 400)
        self.assertIsNone(get_rating_range(50))

    def test_leave_queue_success(self):
        """キューからの正常な離脱"""
        character_id = create_test_character()
        join_queue(character_id)
        result = leave_queue(character_id)
        self.assertEqual(result['status'], 'left')

    def test_leave_queue_not_in_queue(self):
        """キューに参加していない状態での離脱エラー"""
        character_id = create_test_character()
        with self.assertRaises(ValidationError):
            leave_queue(character_id)

    def test_match_priority(self):
        """マッチング優先順位（レーティング差 > 待機時間）"""
        char1 = create_test_character(rating=1000)
        char2 = create_test_character(rating=1050)  # 差50
        char3 = create_test_character(rating=1090)  # 差90

        join_queue(char2)
        time.sleep(2)  # char2が先に待機
        join_queue(char3)

        result = join_queue(char1)

        # char2とマッチング（レーティング差が小さい）
        self.assertEqual(result['opponent_id'], char2)

    def test_concurrent_match_attempt(self):
        """同時マッチング競合の解決"""
        char1 = create_test_character(rating=1000)
        char2 = create_test_character(rating=1000)
        char3 = create_test_character(rating=1000)

        join_queue(char1)

        # char2とchar3が同時にchar1とマッチング試行
        result2 = atomic_match_attempt(char2, char1)
        result3 = atomic_match_attempt(char3, char1)

        # どちらか一方のみ成功
        self.assertTrue((result2 is not None) != (result3 is not None))

    def test_queue_cleanup(self):
        """古いキューエントリの削除"""
        character_id = create_test_character()

        # 11分前にキューに参加したと仮定
        db.execute(
            "INSERT INTO queue (character_id, rating, joined_at) VALUES (?, ?, datetime('now', '-11 minutes'))",
            (character_id, 1000)
        )
        db.commit()

        cleanup_expired_queue_entries()

        # キューから削除されていることを確認
        result = db.execute("SELECT * FROM queue WHERE character_id = ?", (character_id,)).fetchone()
        self.assertIsNone(result)
```

### 8.2 統合テスト項目

```python
# test_matching_integration.py

class TestMatchingIntegration(unittest.TestCase):

    async def test_full_matching_flow(self):
        """マッチングからバトル開始までの完全なフロー"""
        # キャラクター作成
        char1 = await create_character(account_id=1, name="Player1", ...)
        char2 = await create_character(account_id=2, name="Player2", ...)

        # キュー参加
        result1 = await join_queue(char1['character_id'])
        self.assertEqual(result1['status'], 'waiting')

        # 2人目の参加でマッチング成立
        result2 = await join_queue(char2['character_id'])
        self.assertEqual(result2['status'], 'matched')

        # バトルが作成されていることを確認
        battle = get_battle(result2['battle_id'])
        self.assertEqual(battle['status'], 'in_progress')
        self.assertIn(char1['character_id'], [battle['player1_id'], battle['player2_id']])
        self.assertIn(char2['character_id'], [battle['player1_id'], battle['player2_id']])

        # キューから両方削除されていることを確認
        queue_count = db.execute("SELECT COUNT(*) as count FROM queue").fetchone()['count']
        self.assertEqual(queue_count, 0)

    async def test_multiple_concurrent_matches(self):
        """複数の同時マッチング"""
        characters = [await create_character(account_id=i, ...) for i in range(10)]

        # 全員をキューに追加
        tasks = [join_queue(char['character_id']) for char in characters]
        results = await asyncio.gather(*tasks)

        # 5組のマッチングが成立していることを確認
        matched_count = sum(1 for r in results if r['status'] == 'matched')
        self.assertGreaterEqual(matched_count, 4)  # 最低4組

        # すべてのバトルが正常に作成されていることを確認
        for result in results:
            if result['status'] == 'matched':
                battle = get_battle(result['battle_id'])
                self.assertEqual(battle['status'], 'in_progress')
```

### 8.3 ストレステスト

```python
# test_matching_stress.py

class TestMatchingStress(unittest.TestCase):

    async def test_high_concurrent_queue_joins(self):
        """大量の同時キュー参加"""
        num_characters = 50
        characters = [await create_character(account_id=i, ...) for i in range(num_characters)]

        start_time = time.time()
        tasks = [join_queue(char['character_id']) for char in characters]
        results = await asyncio.gather(*tasks)
        end_time = time.time()

        # 全処理が10秒以内に完了
        self.assertLess(end_time - start_time, 10.0)

        # 約半数がマッチング成立
        matched_count = sum(1 for r in results if r['status'] == 'matched')
        self.assertGreaterEqual(matched_count, 20)

    async def test_rapid_join_leave_cycles(self):
        """頻繁なキュー参加・離脱"""
        character_id = create_test_character()

        for _ in range(100):
            await join_queue(character_id)
            await leave_queue(character_id)

        # データベースの整合性を確認
        queue_entry = db.execute("SELECT * FROM queue WHERE character_id = ?", (character_id,)).fetchone()
        self.assertIsNone(queue_entry)
```

---

## 9. モニタリング・ログ

### 9.1 ログ出力

```python
import logging

logger = logging.getLogger('llmbattle.matching')

# キュー参加
logger.info(f"Character {character_id} joined queue (rating={rating})")

# マッチング成立
logger.info(f"Match found: {char1_id} vs {char2_id} (battle_id={battle_id}, rating_diff={abs(r1-r2)})")

# マッチング失敗（待機）
logger.debug(f"No match found for {character_id} (wait_time={wait_time}s, rating_range={rating_range})")

# キュー離脱
logger.info(f"Character {character_id} left queue (wait_time={wait_time}s)")

# エラー
logger.error(f"Matching error: {error_message}", exc_info=True)
```

### 9.2 メトリクス収集

```python
class MatchingMetrics:
    def __init__(self):
        self.total_matches = 0
        self.total_wait_time = 0
        self.match_count_by_rating_range = {100: 0, 200: 0, 400: 0, None: 0}

    def record_match(self, wait_time: float, rating_range: Optional[int]):
        self.total_matches += 1
        self.total_wait_time += wait_time
        self.match_count_by_rating_range[rating_range] += 1

    def get_average_wait_time(self) -> float:
        return self.total_wait_time / self.total_matches if self.total_matches > 0 else 0

    def get_metrics(self) -> dict:
        return {
            "total_matches": self.total_matches,
            "average_wait_time": self.get_average_wait_time(),
            "match_distribution": self.match_count_by_rating_range
        }

metrics = MatchingMetrics()
```

### 9.3 デバッグ情報

```python
async def get_matching_debug_info() -> dict:
    """
    マッチングシステムのデバッグ情報を取得。
    """
    # キュー統計
    queue_stats = db.execute("""
        SELECT
            COUNT(*) as total_count,
            AVG(rating) as avg_rating,
            MIN(rating) as min_rating,
            MAX(rating) as max_rating,
            AVG((julianday('now') - julianday(joined_at)) * 86400) as avg_wait_seconds
        FROM queue
    """).fetchone()

    # 進行中のバトル数
    active_battles = db.execute("""
        SELECT COUNT(*) as count
        FROM battles
        WHERE status = 'in_progress'
    """).fetchone()['count']

    return {
        "queue_stats": dict(queue_stats),
        "active_battles": active_battles,
        "metrics": metrics.get_metrics()
    }
```

---

## 10. 将来の拡張

### 10.1 マッチング条件のカスタマイズ

プレイヤーがマッチング条件を指定できる機能:

```python
async def join_queue_with_preferences(
    character_id: int,
    preferences: dict = None
) -> dict:
    """
    マッチング設定付きでキューに参加。

    Args:
        character_id: キャラクターID
        preferences: マッチング設定
            - level_range: レベル差範囲
            - same_ability_only: 同じアビリティ所持者のみ
            - avoid_recent_opponents: 直近の対戦相手を避ける
    """
    # 将来実装
    pass
```

### 10.2 ランクマッチモード

ランク別のキュー:

```python
class RankTier(Enum):
    BRONZE = "bronze"      # 0-999
    SILVER = "silver"      # 1000-1499
    GOLD = "gold"          # 1500-1999
    PLATINUM = "platinum"  # 2000-2499
    DIAMOND = "diamond"    # 2500+

async def join_ranked_queue(character_id: int, tier: RankTier) -> dict:
    """ランク別キューに参加"""
    # 同じランク内でのみマッチング
    pass
```

### 10.3 グループマッチング

チーム戦のマッチング:

```python
async def join_team_queue(team_id: int) -> dict:
    """チームでキューに参加（2v2, 3v3など）"""
    # 複数キャラクターのグループマッチング
    pass
```

### 10.4 AI相手のマッチング

対戦相手がいない時のNPC対戦:

```python
async def match_with_ai(character_id: int) -> dict:
    """AI相手とのバトルを作成"""
    # 待機時間が長い場合、AI相手を提案
    pass
```

---

## 11. 関連ドキュメント

- [システムアーキテクチャ](./architecture.md)
- [データベース設計](./database.md)
- [MCPサーバー設計](./mcp-server.md)
- [バトルロジック設計](./battle-logic.md)

---

## 12. 設計チェックリスト

- [x] レーティングベースのマッチングアルゴリズム定義
- [x] 待機時間による条件緩和ロジック設計
- [x] キューデータ構造の設計
- [x] マッチング成立処理フローの設計
- [x] 同時マッチング競合の解決策
- [x] エッジケース（離脱、タイムアウト等）の対応
- [x] データベースクエリ設計
- [x] パフォーマンス要件定義
- [x] テスト戦略策定
- [x] ログ・モニタリング設計
- [x] 将来の拡張性考慮

---

**設計承認**: 待機中
**次のステップ**: Operatorによる実装開始
