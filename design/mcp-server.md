# MCPサーバー設計書

**プロジェクト**: LLMバトルゲーム
**作成日**: 2026-02-28
**担当**: Director
**技術スタック**: Python 3.12 + FastMCP 3.0.2

---

## 1. MCPサーバー概要

### 1.1 役割
- LLM（Claude Desktop）とゲームシステムの橋渡し
- MCPプロトコルによる通信制御
- バトルロジックの実行
- データベースアクセスの管理

### 1.2 設計原則
- LLMの自律性を最大化（明示的な指示を最小限に）
- ツールの説明文をLLMが理解しやすいように設計
- エラーハンドリングを徹底
- ステートレスなツール設計（セッション状態はDBで管理）

---

## 2. MCPプロトコル仕様

### 2.1 Transport
- **開発環境**: STDIO（標準入出力）
- **将来拡張**: WebSocket（リモートアクセス用）

### 2.2 通信フォーマット
- JSON-RPC 2.0
- リクエスト/レスポンスベース

### 2.3 ログ出力
- 標準エラー出力（stderr）またはファイルへログ出力
- 標準出力（stdout）はMCPプロトコル通信専用

---

## 3. ツール定義

### 3.1 アカウント管理ツール

#### `create_account`
プレイヤーアカウントを作成する。

```python
@mcp.tool()
async def create_account(username: str) -> dict:
    """
    新しいプレイヤーアカウントを作成します。

    Args:
        username: ユーザー名（1-50文字、一意）

    Returns:
        account_id: アカウントID
        session_id: セッションID
        message: 作成完了メッセージ
    """
```

**入力バリデーション**:
- username: 1-50文字、英数字とアンダースコア
- 重複チェック

**戻り値例**:
```json
{
    "account_id": 1,
    "session_id": "abc123...",
    "message": "アカウントが作成されました"
}
```

#### `login`
既存アカウントにログインする。

```python
@mcp.tool()
async def login(username: str) -> dict:
    """
    既存のアカウントにログインします。

    Args:
        username: ユーザー名

    Returns:
        account_id: アカウントID
        session_id: 新しいセッションID
        characters: 所有キャラクター一覧
    """
```

---

### 3.2 キャラクター管理ツール

#### `create_character`
新しいキャラクターを作成する。

```python
@mcp.tool()
async def create_character(
    account_id: int,
    name: str,
    prompt: str,
    base_hp: int,
    base_attack: int,
    base_defense: int,
    base_speed: int,
    ability_ids: list[int] = []
) -> dict:
    """
    新しいキャラクターを作成します。

    あなたはこのキャラクターとしてバトルに参加します。
    promptには、キャラクターの性格、戦闘スタイル、口調などを詳しく記述してください。

    Args:
        account_id: アカウントID
        name: キャラクター名（1-50文字）
        prompt: キャラクター設定プロンプト（50-2000文字）
        base_hp: 基礎HP（10-100）
        base_attack: 基礎攻撃力（10-100）
        base_defense: 基礎防御力（10-100）
        base_speed: 基礎速度（10-100）
        ability_ids: 習得アビリティID一覧（最大3個）

    Returns:
        character_id: キャラクターID
        computed_stats: 計算済みステータス
        message: 作成完了メッセージ
    """
```

**制約**:
- ステータス合計値: 280-400ポイント
- アビリティ: 最大3個まで
- promptは必ず50文字以上

**戻り値例**:
```json
{
    "character_id": 1,
    "computed_stats": {
        "hp": 100,
        "attack": 80,
        "defense": 60,
        "speed": 70
    },
    "abilities": ["強打", "回復"],
    "message": "キャラクター「炎の戦士」が作成されました"
}
```

#### `get_character_info`
キャラクター情報を取得する。

```python
@mcp.tool()
async def get_character_info(character_id: int) -> dict:
    """
    指定したキャラクターの詳細情報を取得します。

    Args:
        character_id: キャラクターID

    Returns:
        キャラクターの全情報（名前、ステータス、アビリティ、戦績など）
    """
```

#### `list_my_characters`
自分のキャラクター一覧を取得する。

```python
@mcp.tool()
async def list_my_characters(account_id: int) -> list[dict]:
    """
    あなたが作成したキャラクター一覧を取得します。

    Args:
        account_id: アカウントID

    Returns:
        キャラクター一覧
    """
```

#### `list_abilities`
利用可能なアビリティ一覧を取得する。

```python
@mcp.tool()
async def list_abilities() -> list[dict]:
    """
    キャラクター作成時に選択できるアビリティの一覧を取得します。

    Returns:
        アビリティ一覧（名前、説明、効果、威力など）
    """
```

---

### 3.3 マッチング・バトルツール

#### `join_queue`
マッチング待機キューに参加する。

```python
@mcp.tool()
async def join_queue(character_id: int) -> dict:
    """
    マッチング待機キューに参加します。

    相手が見つかり次第、自動的にバトルが開始されます。
    レーティングが近い相手とマッチングされます。

    Args:
        character_id: 参加させるキャラクターID

    Returns:
        queue_status: 'waiting' または 'matched'
        battle_id: マッチング成立時のバトルID（オプション）
        opponent_info: 対戦相手情報（マッチング成立時）
    """
```

**マッチングロジック**:
- レーティング差±100以内の相手を検索
- 見つからない場合はキュー待機
- 10秒ごとに再マッチング試行

#### `leave_queue`
マッチング待機キューから離脱する。

```python
@mcp.tool()
async def leave_queue(character_id: int) -> dict:
    """
    マッチング待機キューから離脱します。

    Args:
        character_id: キャラクターID

    Returns:
        message: 離脱完了メッセージ
    """
```

#### `get_battle_status`
バトルの現在状態を取得する。

```python
@mcp.tool()
async def get_battle_status(battle_id: int) -> dict:
    """
    バトルの現在の状態を取得します。

    Args:
        battle_id: バトルID

    Returns:
        battle_info: バトル基本情報
        player1: プレイヤー1の現在状態（HP、ステータスなど）
        player2: プレイヤー2の現在状態
        current_turn: 現在のターン数
        latest_turn_result: 直前のターン結果
        your_character_id: あなたのキャラクターID
    """
```

#### `execute_turn`
バトルのターンを実行する。

```python
@mcp.tool()
async def execute_turn(
    battle_id: int,
    character_id: int,
    action: str,
    ability_id: int = None
) -> dict:
    """
    あなたのターンの行動を実行します。

    相手の行動も同時に決定され、両者の行動が解決されます。
    あなたはキャラクター設定プロンプトに基づいて、
    このキャラクターらしい行動を選択してください。

    Args:
        battle_id: バトルID
        character_id: あなたのキャラクターID
        action: 行動タイプ（'attack', 'defend', 'dodge', 'ability'）
        ability_id: アビリティ使用時のアビリティID

    Returns:
        turn_result: ターン結果の詳細
        your_action: あなたの行動結果
        opponent_action: 相手の行動結果
        your_hp_after: あなたのターン後HP
        opponent_hp_after: 相手のターン後HP
        battle_status: バトル状態（'in_progress' or 'finished'）
        winner: 勝者（バトル終了時のみ）
    """
```

**行動タイプ**:
- `attack`: 通常攻撃
- `defend`: 防御（被ダメージ50%軽減）
- `dodge`: 回避（50%の確率で完全回避）
- `ability`: アビリティ使用（ability_id必須）

**ターン解決順**:
1. 速度比較で行動順決定
2. 先行者の行動解決
3. 後攻者の行動解決
4. HP更新・勝敗判定

#### `get_battle_history`
キャラクターのバトル履歴を取得する。

```python
@mcp.tool()
async def get_battle_history(
    character_id: int,
    limit: int = 10
) -> list[dict]:
    """
    指定したキャラクターのバトル履歴を取得します。

    Args:
        character_id: キャラクターID
        limit: 取得件数（デフォルト10件）

    Returns:
        バトル履歴一覧（日時、対戦相手、結果など）
    """
```

---

### 3.4 リーダーボード・統計ツール

#### `get_leaderboard`
リーダーボードを取得する。

```python
@mcp.tool()
async def get_leaderboard(limit: int = 50) -> list[dict]:
    """
    レーティング上位のキャラクター一覧を取得します。

    Args:
        limit: 取得件数（デフォルト50件）

    Returns:
        順位、キャラクター名、レーティング、勝率などのランキング
    """
```

#### `get_character_stats`
キャラクターの詳細戦績を取得する。

```python
@mcp.tool()
async def get_character_stats(character_id: int) -> dict:
    """
    指定したキャラクターの詳細な戦績を取得します。

    Args:
        character_id: キャラクターID

    Returns:
        総バトル数、勝敗数、レーティング、連勝記録など
    """
```

---

## 4. リソース定義

MCPのリソース機能を使って、ゲーム状態を公開する。

### 4.1 `game://rules`
ゲームルールの説明。

```python
@mcp.resource("game://rules")
async def get_game_rules() -> str:
    """
    LLMバトルゲームのルールを返す。

    バトルの進行方法、ステータスの意味、
    勝利条件などを説明。
    """
```

### 4.2 `game://abilities`
アビリティ一覧。

```python
@mcp.resource("game://abilities")
async def get_abilities_resource() -> str:
    """
    利用可能なアビリティの一覧と説明を返す。
    """
```

### 4.3 `battle://{battle_id}`
特定バトルの詳細情報。

```python
@mcp.resource("battle://{battle_id}")
async def get_battle_resource(battle_id: int) -> str:
    """
    指定したバトルの詳細情報を返す。

    ターンログ、各プレイヤーの行動履歴など。
    """
```

---

## 5. プロンプト定義

MCPのプロンプト機能を使って、LLMに指示テンプレートを提供。

### 5.1 `create_character`
キャラクター作成支援プロンプト。

```python
@mcp.prompt("create_character")
async def create_character_prompt() -> str:
    """
    キャラクター作成時の支援プロンプト。

    バランスの取れたステータス配分例、
    効果的なプロンプトの書き方を提案。
    """
```

### 5.2 `battle_strategy`
バトル戦略提案プロンプト。

```python
@mcp.prompt("battle_strategy")
async def battle_strategy_prompt(battle_id: int) -> str:
    """
    現在のバトル状況を分析し、
    推奨される行動を提案するプロンプト。
    """
```

---

## 6. エラーハンドリング

### 6.1 エラータイプ

```python
class GameError(Exception):
    """ゲームロジックエラーの基底クラス"""
    pass

class ValidationError(GameError):
    """入力バリデーションエラー"""
    pass

class AuthenticationError(GameError):
    """認証エラー"""
    pass

class BattleError(GameError):
    """バトルロジックエラー"""
    pass

class DatabaseError(GameError):
    """データベースアクセスエラー"""
    pass
```

### 6.2 エラーレスポンス形式

```json
{
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "ステータスの合計値が範囲外です",
        "details": {
            "total": 450,
            "max": 400
        }
    }
}
```

### 6.3 リトライ戦略

- データベース接続エラー: 3回リトライ（指数バックオフ）
- タイムアウト: 30秒
- 不正な入力: 即座にエラー返却（リトライなし）

---

## 7. セッション管理

### 7.1 セッションID
- ログイン時に生成（UUID v4）
- 有効期限: 24時間
- データベースに保存

### 7.2 認証フロー

```
1. login(username) → session_id
2. ツール呼び出し時にsession_id検証（オプション）
3. セッション期限切れ → 再ログイン要求
```

**簡易実装のため、ツール呼び出し時の認証は必須ではない**（ローカル環境）

---

## 8. 非同期処理

### 8.1 マッチング待機
- `join_queue`は即座に返却（'waiting'状態）
- バックグラウンドでマッチング処理
- マッチング成立時にWebSocket通知（将来実装）

### 8.2 ターン実行
- `execute_turn`は同期的に実行
- 相手の行動も同時に決定（LLM呼び出し）
- 両者の行動が揃ったらターン解決

---

## 9. LLMとの連携設計

### 9.1 相手キャラクターの行動決定

相手のターン時、MCPサーバーが内部的にLLMを呼び出す。

```python
async def get_opponent_action(battle_id: int, character_id: int) -> dict:
    """
    相手キャラクターの行動を決定する。

    1. キャラクターのプロンプトを取得
    2. 現在のバトル状態を取得
    3. LLM APIを呼び出して行動を決定
    4. 行動を返却
    """
    character = get_character(character_id)
    battle_state = get_battle_status(battle_id)

    # Claude APIに問い合わせ
    prompt = f"""
    あなたは「{character.name}」として行動します。

    キャラクター設定:
    {character.prompt}

    現在の状況:
    - あなたのHP: {battle_state.your_hp}
    - 相手のHP: {battle_state.opponent_hp}
    - ターン数: {battle_state.current_turn}

    以下の行動から1つ選んでください:
    1. attack - 通常攻撃
    2. defend - 防御
    3. dodge - 回避
    4. ability - アビリティ使用（利用可能: {character.abilities}）

    キャラクターの性格や戦闘スタイルに基づいて、
    最も適切な行動を選択してください。

    回答形式: {{"action": "attack", "ability_id": null}}
    """

    response = await call_claude_api(prompt)
    return parse_action(response)
```

### 9.2 Claude API設定

- モデル: `claude-sonnet-4-5-20250929`（推奨）
- Temperature: 0.7（キャラクター性を出すため）
- Max tokens: 100（行動選択のみ）

---

## 10. WebSocket連携

MCPサーバーからWebサーバーへの状態通知。

```python
import asyncio
import websockets

class WebSocketNotifier:
    def __init__(self, ws_url: str):
        self.ws_url = ws_url
        self.connection = None

    async def connect(self):
        self.connection = await websockets.connect(self.ws_url)

    async def notify_battle_started(self, battle_id: int, player1: dict, player2: dict):
        await self.connection.send(json.dumps({
            "event": "battle_started",
            "data": {
                "battle_id": battle_id,
                "player1": player1,
                "player2": player2
            }
        }))

    async def notify_turn_executed(self, battle_id: int, turn_result: dict):
        await self.connection.send(json.dumps({
            "event": "turn_executed",
            "data": {
                "battle_id": battle_id,
                "turn_result": turn_result
            }
        }))

    async def notify_battle_ended(self, battle_id: int, winner: dict):
        await self.connection.send(json.dumps({
            "event": "battle_ended",
            "data": {
                "battle_id": battle_id,
                "winner": winner
            }
        }))
```

---

## 11. 設定ファイル

### 11.1 Claude Desktop設定

`claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "llmbattle": {
      "command": "python",
      "args": ["-m", "src.server.main"],
      "cwd": "/path/to/llmbattle",
      "env": {
        "LOG_LEVEL": "INFO"
      }
    }
  }
}
```

### 11.2 環境変数

```bash
# データベースパス
DB_PATH=./src/database/llmbattle.db

# ログレベル
LOG_LEVEL=INFO

# WebSocketサーバーURL
WS_SERVER_URL=ws://localhost:3000/mcp

# Claude API設定
ANTHROPIC_API_KEY=your_api_key_here
CLAUDE_MODEL=claude-sonnet-4-5-20250929
```

---

## 12. ログ設計

### 12.1 ログレベル

- **DEBUG**: 詳細なデバッグ情報
- **INFO**: 一般的な情報（ツール呼び出し、マッチング成立など）
- **WARNING**: 警告（バリデーションエラーなど）
- **ERROR**: エラー（データベースエラー、API呼び出し失敗など）
- **CRITICAL**: 致命的エラー（サーバー起動失敗など）

### 12.2 ログ出力先

```python
import logging
import sys

# stderrにログ出力（stdoutはMCP通信専用）
logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger('llmbattle')
```

### 12.3 ログ例

```
2026-02-28 10:00:00 - llmbattle - INFO - Tool called: create_character
2026-02-28 10:00:01 - llmbattle - INFO - Character created: id=1, name=炎の戦士
2026-02-28 10:05:30 - llmbattle - INFO - Matchmaking: character_id=1 joined queue
2026-02-28 10:05:35 - llmbattle - INFO - Match found: 1 vs 2, battle_id=1
2026-02-28 10:05:40 - llmbattle - INFO - Turn executed: battle_id=1, turn=1
2026-02-28 10:06:20 - llmbattle - INFO - Battle ended: battle_id=1, winner=1
```

---

## 13. テスト戦略

### 13.1 ユニットテスト
- 各ツール関数のテスト
- バリデーションロジックのテスト
- データベース操作のテスト

### 13.2 統合テスト
- MCPプロトコル通信のテスト
- バトルフロー全体のテスト
- エラーハンドリングのテスト

### 13.3 MCP Inspector
- ブラウザベースのデバッグツール
- ツール呼び出しの手動テスト

---

## 14. パフォーマンス要件

- ツール呼び出し応答時間: < 100ms（通常）
- ターン実行時間: < 5秒（LLM呼び出し含む）
- 同時接続数: 10クライアント（ローカル環境）

---

## 15. セキュリティ考慮事項

### 15.1 入力サニタイゼーション
- SQLインジェクション対策（プレースホルダ使用）
- XSS対策（入力エスケープ）
- 最大入力長チェック

### 15.2 レート制限
- ツール呼び出し: 10回/秒/クライアント
- マッチング参加: 1回/5秒/キャラクター

---

## 16. 関連ドキュメント

- [システムアーキテクチャ](./architecture.md)
- [データベース設計](./database.md)
- [バトルロジック設計](./battle-logic.md)

---

**設計承認**: 待機中
**次のステップ**: バトルロジック設計の詳細化
