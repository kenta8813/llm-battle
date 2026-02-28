# システムアーキテクチャ設計書

**プロジェクト**: LLMバトルゲーム
**作成日**: 2026-02-28
**担当**: Director

---

## 1. システム概要

LLM同士が完全自律的に戦うターン制バトルゲーム。プレイヤーはキャラクター設定プロンプトを作成し、LLMがそのキャラクターとして戦闘を行う。

### 設計原則
- ローカル環境で完結（外部クラウド不要）
- シンプルで拡張可能
- LLMの自律性を最大化
- 「言ったもん勝ち」要素の考慮

---

## 2. 全体アーキテクチャ

```
┌─────────────────────────────────────────────────────────┐
│                    Claude Desktop                        │
│              (プレイヤー1のLLMクライアント)                │
└───────────────────────┬─────────────────────────────────┘
                        │ MCP Protocol (STDIO)
                        │
┌───────────────────────▼─────────────────────────────────┐
│                                                          │
│                   MCP Server (Python)                    │
│                                                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │   Auth      │  │   Battle    │  │  Database   │    │
│  │   Module    │  │   Logic     │  │   Access    │    │
│  └─────────────┘  └─────────────┘  └─────────────┘    │
│                                                          │
└───────────────────────┬─────────────────────────────────┘
                        │
                        │ ├─ SQLite (データ永続化)
                        │ └─ WebSocket (状態通知)
                        │
┌───────────────────────▼─────────────────────────────────┐
│                 Web Server (Node.js)                     │
│                Express + Socket.IO                       │
│                                                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │   REST      │  │  WebSocket  │  │   Static    │    │
│  │   API       │  │   Handler   │  │   Files     │    │
│  └─────────────┘  └─────────────┘  └─────────────┘    │
│                                                          │
└───────────────────────┬─────────────────────────────────┘
                        │ HTTP/WebSocket
                        │
┌───────────────────────▼─────────────────────────────────┐
│              Web Client (React + Vite)                   │
│                                                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │   Battle    │  │  Character  │  │Leaderboard  │    │
│  │   Viewer    │  │   Manager   │  │   Viewer    │    │
│  └─────────────┘  └─────────────┘  └─────────────┘    │
│                                                          │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                     SQLite Database                      │
│                                                          │
│  accounts │ characters │ battles │ stats │ queue       │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## 3. コンポーネント構成

### 3.1 MCPサーバー（Python FastMCP）

**責務**:
- LLMクライアントとの通信（MCPプロトコル）
- 認証・セッション管理
- バトルロジックの実行
- データベースアクセス
- Webサーバーへの状態通知

**主要モジュール**:

```
src/server/
├── main.py                 # MCPサーバーエントリポイント
├── auth/
│   ├── __init__.py
│   ├── account.py          # アカウント管理
│   └── session.py          # セッション管理
├── battle/
│   ├── __init__.py
│   ├── engine.py           # バトルエンジン
│   ├── turn.py             # ターン進行
│   ├── calculator.py       # ダメージ計算
│   └── judge.py            # 勝敗判定
├── character/
│   ├── __init__.py
│   ├── character.py        # キャラクター管理
│   └── stats.py            # ステータス計算
├── database/
│   ├── __init__.py
│   ├── connection.py       # DB接続
│   ├── accounts.py         # アカウントDB
│   ├── characters.py       # キャラクターDB
│   ├── battles.py          # バトルDB
│   └── queue.py            # マッチングキューDB
├── matchmaking/
│   ├── __init__.py
│   └── matcher.py          # マッチングロジック
└── tools/
    ├── __init__.py
    ├── account_tools.py    # アカウント操作ツール
    ├── character_tools.py  # キャラクター操作ツール
    └── battle_tools.py     # バトル操作ツール
```

**技術スタック**:
- Python 3.12
- FastMCP 3.0.2
- sqlite3（標準ライブラリ）

### 3.2 Webサーバー（Node.js + Express）

**責務**:
- REST API提供
- WebSocketによるリアルタイム通信
- 静的ファイル配信
- クライアント状態管理

**主要モジュール**:

```
src/web/server/
├── index.js                # サーバーエントリポイント
├── api/
│   ├── battles.js          # バトル情報API
│   ├── characters.js       # キャラクター情報API
│   └── leaderboard.js      # リーダーボードAPI
├── socket/
│   ├── handler.js          # WebSocketハンドラ
│   └── events.js           # イベント定義
└── middleware/
    ├── cors.js             # CORS設定
    └── error.js            # エラーハンドリング
```

**技術スタック**:
- Node.js v25.2.1
- Express.js
- Socket.IO

### 3.3 Webクライアント（React + Vite）

**責務**:
- バトルの可視化
- キャラクター管理画面
- リーダーボード表示
- リアルタイム更新受信

**主要コンポーネント**:

```
src/web/client/
├── src/
│   ├── App.jsx             # アプリケーションルート
│   ├── main.jsx            # エントリポイント
│   ├── components/
│   │   ├── Battle/
│   │   │   ├── BattleViewer.jsx
│   │   │   ├── BattleField.jsx
│   │   │   ├── CharacterCard.jsx
│   │   │   ├── TurnIndicator.jsx
│   │   │   └── ActionLog.jsx
│   │   ├── Character/
│   │   │   ├── CharacterList.jsx
│   │   │   └── CharacterDetails.jsx
│   │   └── Leaderboard/
│   │       └── LeaderboardTable.jsx
│   ├── hooks/
│   │   ├── useWebSocket.js
│   │   └── useBattleState.js
│   └── api/
│       └── client.js       # APIクライアント
└── public/
    └── assets/             # 画像・アイコン等
```

**技術スタック**:
- React 18
- Vite
- Socket.IO Client

### 3.4 データベース（SQLite）

**責務**:
- すべてのゲームデータの永続化
- トランザクション管理
- 履歴データ保存

**データベースファイル**:
```
src/database/
└── llmbattle.db            # 単一DBファイル
```

---

## 4. データフロー

### 4.1 アカウント作成フロー

```
[Claude Desktop]
    → MCP: create_account(username)
    → DB: INSERT accounts
    ← MCP: account_id
[Claude Desktop]
```

### 4.2 キャラクター作成フロー

```
[Claude Desktop]
    → MCP: create_character(name, prompt, base_stats)
    → DB: INSERT characters
    → Calc: ステータス計算
    → DB: UPDATE characters (computed_stats)
    ← MCP: character_id
[Claude Desktop]
```

### 4.3 マッチング〜バトルフロー

```
[Claude Desktop]
    → MCP: join_queue(character_id)
    → DB: INSERT queue
    → Matcher: マッチング処理
    → DB: マッチング成立時にバトルレコード作成
    ← MCP: battle_id, opponent_info

[バトル開始]
    → MCPサーバー: バトルセッション作成
    → WebSocket: battle_started イベント送信
    → Web Client: バトル画面表示

[各ターン]
    → MCP: execute_turn(battle_id)
    → LLM1: アクション決定（攻撃/防御/回避/アビリティ）
    → LLM2: アクション決定
    → Battle Engine: アクション解決
    → DB: UPDATE battles (battle_log)
    → WebSocket: turn_executed イベント送信
    → Web Client: アクション結果表示

[勝敗判定]
    → Battle Engine: HP 0以下 or 最大ターン到達
    → DB: UPDATE battles (winner_id, ended_at)
    → DB: UPDATE stats (勝敗記録)
    → WebSocket: battle_ended イベント送信
    → Web Client: 結果表示
    ← MCP: battle_result
[Claude Desktop]
```

### 4.4 リーダーボード更新フロー

```
[定期的/バトル終了時]
    → Web Client: GET /api/leaderboard
    → Web Server: DB読み取り
    → Web Server: レスポンス返却
    ← Web Client: リーダーボード表示更新
```

---

## 5. 通信プロトコル

### 5.1 MCPプロトコル（Claude ↔ MCP Server）

**Transport**: STDIO（標準入出力）
**形式**: JSON-RPC 2.0

**主要ツール**:
- `create_account(username)` - アカウント作成
- `create_character(name, prompt, hp, attack, defense, abilities)` - キャラクター作成
- `join_queue(character_id)` - マッチング参加
- `get_battle_status(battle_id)` - バトル状態取得
- `execute_turn(battle_id, action, target)` - ターン実行
- `get_character_info(character_id)` - キャラクター情報取得
- `get_battle_history(character_id)` - バトル履歴取得

### 5.2 WebSocket（MCP Server ↔ Web Server ↔ Web Client）

**プロトコル**: Socket.IO
**イベント**:

**サーバー → クライアント**:
- `battle_started` - バトル開始通知
- `turn_executed` - ターン実行結果
- `battle_ended` - バトル終了通知
- `leaderboard_updated` - リーダーボード更新

**クライアント → サーバー**:
- `subscribe_battle(battle_id)` - バトル購読
- `unsubscribe_battle(battle_id)` - バトル購読解除

### 5.3 REST API（Web Server ↔ Web Client）

**Base URL**: `http://localhost:3000/api`

**エンドポイント**:
- `GET /battles/:id` - バトル詳細取得
- `GET /battles` - バトル一覧取得
- `GET /characters/:id` - キャラクター詳細取得
- `GET /leaderboard` - リーダーボード取得
- `GET /stats/:character_id` - 戦績取得

---

## 6. セキュリティ設計

### 6.1 認証

**ローカル環境のため簡易認証**:
- アカウント名のみで識別
- セッションIDによる一時的な認証
- 本番環境では後からOAuth 2.1に拡張可能

### 6.2 データ整合性

- SQLiteトランザクションによる整合性保証
- 外部キー制約の有効化
- バトル中の同時書き込み制御（ロック）

### 6.3 入力バリデーション

- キャラクター名: 1-50文字
- プロンプト: 1-2000文字
- ステータス値: 正の整数、合計値上限設定
- アビリティ: 事前定義リストから選択

---

## 7. パフォーマンス設計

### 7.1 データベース最適化

- 頻繁にクエリするカラムにインデックス作成
- バトルログはJSON形式で単一カラムに格納
- 定期的なVACUUM実行

### 7.2 WebSocket最適化

- バトル参加者のみにイベント送信（ルーム機能）
- イベントペイロードの最小化
- 自動再接続機能の実装

### 7.3 キャッシュ戦略

- キャラクター情報のメモリキャッシュ
- リーダーボードの定期更新（5秒間隔）

---

## 8. エラーハンドリング

### 8.1 MCP Server

- LLMタイムアウト: 30秒でターンスキップ
- DB接続エラー: リトライ3回
- バトルロジックエラー: ログ記録、バトル中断

### 8.2 Web Server

- WebSocket切断: 自動再接続
- API エラー: 適切なHTTPステータスコード返却
- 不正なリクエスト: バリデーションエラー返却

### 8.3 Web Client

- 接続エラー: ユーザーへの通知表示
- データ取得失敗: リトライボタン表示
- タイムアウト: ローディング表示とキャンセル機能

---

## 9. デプロイ構成

### 9.1 開発環境

```
localhost:
  - MCPサーバー: STDIO (Claude Desktopから起動)
  - Webサーバー: http://localhost:3000
  - Webクライアント: http://localhost:5173 (Vite dev server)
  - データベース: ./src/database/llmbattle.db
```

### 9.2 本番環境（将来拡張）

```
server:
  - MCPサーバー: WebSocket (wss://...)
  - Webサーバー: https://... (Nginx reverse proxy)
  - Webクライアント: 静的ファイル配信
  - データベース: PostgreSQL (スケール時)
```

---

## 10. 拡張性

### 10.1 近い将来の拡張

- キャラクターレベルアップシステム
- アビリティのカスタマイズ
- ランクマッチモード
- 観戦モード

### 10.2 長期的な拡張

- マルチプレイヤートーナメント
- キャラクターのビジュアル表示
- リプレイ機能
- AIによる戦略分析

---

## 11. 技術的負債の管理

### 11.1 既知の制約

- SQLiteは並行書き込みに弱い → 将来PostgreSQLへ移行
- MCPプロトコルはまだ発展途上 → 定期的な仕様確認

### 11.2 リファクタリング計画

- フェーズ7（統合テスト後）にコードレビュー実施
- 重複コードの削減
- テストカバレッジの向上

---

## 12. 関連ドキュメント

- [データベース設計](./database.md)
- [MCPサーバー設計](./mcp-server.md)
- [バトルロジック設計](./battle-logic.md)
- [Webビュアー設計](./web-viewer.md)

---

**設計承認**: 待機中
**次のステップ**: データベース設計の詳細化
