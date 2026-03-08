# Project Memory - 2026-03-08（最終更新）

## 進行中プロジェクト

### LLMバトルゲーム開発
- 開始日：2026-02-27
- 現在のフェーズ：リモートMCP統合完了・稼働中
- 状態：フル機能稼働中（2 LLM間のリモートMCPバトル確認済み）
- コンセプト：自分のLLMをMCPサーバーに接続するだけで世界中のLLMと自律対戦できるオンラインゲーム

### 実際のアーキテクチャ（確定）
- **統合サーバー**: Node.js が MCP + REST API + WebSocket + 静的ファイルを一手に担う
- **Python MCPサーバーは廃止**（旧: src/server/ は残存するが使わない）
- MCP endpoint: POST /mcp（Streamable HTTP、Stateless）
- 認証: x-api-key ヘッダー（MCP）/ JWT Bearer（REST API）
- バトルロジック: battles.js サーバーサイドで完結（同時行動制、pendingActions Map）
- Socket.IO: io.js シングルトンで循環依存を回避

### 実装済み機能
- MCP Layer: src/web/mcp/index.js（7ツール：get_my_status, list_abilities, create_character, join_queue, check_queue, get_battle_state, take_action）
- REST API: accounts, characters, battles, matchmaking, leaderboard
- DB: SQLite 9テーブル（api_key列マイグレーション自動実行）
- Webクライアント（React + Vite）：観戦・リーダーボード
- next_step パターン: 全MCPツールレスポンスにLLM誘導テキストを含む

### 技術スタック
- Node.js + Express + Socket.IO
- @modelcontextprotocol/sdk + zod（MCP）
- SQLite（WALモード）
- React + Vite（観戦UI）

### 設計成果物
- architecture.md（更新済み）, database.md, battle-logic.md, web-viewer.md, matching-logic.md

## 完了プロジェクト
なし
