# Project Memory - 2026-03-06（更新）

## 進行中プロジェクト

### LLMバトルゲーム開発
- 開始日：2026-02-27
- 現在のフェーズ：実装完了（追加開発待機中）
- 状態：MVPリリース可能状態
- 目標：LLM同士が戦うターン制バトルゲームをローカル環境で構築
- アサイン済み：PM, Researcher, Co-driver, PO, Director, Operator, QA
- 技術スタック：Python FastMCP + requests, SQLite, Node.js Express + JWT, React + Vite + Socket.IO

### 実際のアーキテクチャ（コード確認済み）
- MCPサーバー（Python）→ REST API経由 → Webサーバー（Node.js）→ SQLite
- MCPは直接DBアクセスしない（api_client/client.py がHTTPクライアント）
- JWT認証あり（middleware/auth.js）、セッションは ~/.llmbattle/session.json に保存

### 実装済み機能
- データベース（8テーブル）
- Webサーバー（REST API）：アカウント・キャラクター・マッチング・バトル・統計
- MCPサーバー：create_account, login, create_character, list_abilities, get_character_info, list_my_characters, join_queue, leave_queue, get_battle_status, get_battle_history, get_leaderboard, get_character_stats
- Webクライアント（React + Vite）：4ページ + 10コンポーネント

### 未実装・注意点
- execute_turn：NOT_IMPLEMENTEDを返す（バトル自動実行ロジック未実装）
- ステータス自動振り分け（allocator.py）：未実装（設計書のみ存在）
  - 代替：create_characterのdocstringで「呼び出し側Claudeが判断」方式に変更

### 設計成果物
- architecture.md, database.md, mcp-server.md, battle-logic.md, web-viewer.md, matching-logic.md, auto-status-allocation.md

## 完了プロジェクト
なし
