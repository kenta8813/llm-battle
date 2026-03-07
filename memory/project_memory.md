# Project Memory - 2026-03-08（更新）

## 進行中プロジェクト

### LLMバトルゲーム開発
- 開始日：2026-02-27
- 現在のフェーズ：オンライン対戦動作確認済み・稼働中
- 状態：フル機能稼働中（サブエージェントによる自律バトル確認済み）
- 目標：LLM同士が戦うターン制バトルゲームをローカル環境で構築
- 技術スタック：Python FastMCP + requests, SQLite, Node.js Express + JWT, React + Vite + Socket.IO

### 実際のアーキテクチャ（コード確認済み）
- MCPサーバー（Python）→ REST API経由 → Webサーバー（Node.js）→ SQLite
- MCPは直接DBアクセスしない（api_client/client.py がHTTPクライアント）
- JWT認証あり（middleware/auth.js）、セッションは ~/.llmbattle/session.json に保存
- バトルロジックはWebサーバーサイド（battles.js）で完結（Approach B）

### 実装済み機能
- データベース（8テーブル、battlesテーブルにHP列追加済み）
- Webサーバー（REST API）：アカウント・キャラクター・マッチング・バトル・統計
  - POST /api/battles/:id/action（バトルアクション、サーバーサイドダメージ計算）
  - GET /api/characters/:id/battles（バトル履歴）
  - 自動マッチング（matchmaking.js がHP初期値をセットしてバトル生成）
- MCPサーバー：create_account, login, create_character, list_abilities, get_character_info, list_my_characters, join_queue, leave_queue, execute_turn, get_battle_status, get_battle_history, get_leaderboard, get_character_stats
- Webクライアント（React + Vite）：4ページ + 10コンポーネント
- Claude Code スキル：.claude/skills/play/, quickmatch/, battle/

### 注意点
- ステータス自動振り分け（allocator.py）：未実装（設計書のみ存在）
  - 代替：create_characterのdocstringで「呼び出し側Claudeが判断」方式

### 設計成果物
- architecture.md, database.md, mcp-server.md, battle-logic.md, web-viewer.md, matching-logic.md, auto-status-allocation.md

## 完了プロジェクト
なし
