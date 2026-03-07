# PM Memory - 2026-03-08（更新）

## 現在の状態
- 進行中プロジェクト：LLMバトルゲーム開発
- 現在のフェーズ：オンライン対戦フル機能稼働中
- 次にやること：オーナーの次の要求待ち

## 承認済みリソース
- エージェント：co-driver.md, marketer.md, merchandiser.md, pm.md, po.md, researcher.md, director.md, operator.md, qa.md
- MCP：なし
- ソフトウェア：
  - Node.js v25.2.1（インストール済み）
  - Python 3.12.10（インストール済み）
  - SQLite 3.51.2（インストール済み）
  - FastMCP 3.0.2（インストール済み）
  - requests（インストール済み）
- Claude Codeツール：Bash(*) 全許可（.claude/settings.json）/ wget（拒否）

## 未解決事項
- ステータス自動振り分け（allocator.py）が未実装（設計書 auto-status-allocation.md のみ存在）

## これまでの主要な判断
- フレームワークの初期構築完了
- LLMバトルゲーム開発プロジェクト開始
- 技術スタック選定（Python FastMCP + requests, SQLite, Node.js Express + JWT, React + Vite）
- MCPサーバーをAPI経由アクセス方式に変更（直接SQLiteアクセスから変更）
- execute_turn 実装：Approach B（バトルロジックをWebサーバーサイドに移動）
- マッチング時のHP初期値バグ修正（matchmaking.js）
- バトル履歴エンドポイント追加（GET /api/characters/:id/battles）
- Claude Code スキル作成：/play, /quickmatch, /battle（.claude/skills/配下）
- サブエージェント用に Bash(*) 許可（settings.json）
