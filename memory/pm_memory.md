# PM Memory - 2026-03-06（更新）

## 現在の状態
- 進行中プロジェクト：LLMバトルゲーム開発
- 現在のフェーズ：実装完了・追加開発待機中
- 次にやること：オーナーの次の要求待ち（execute_turn実装、allocator.py実装など候補あり）

## 承認済みリソース
- エージェント：co-driver.md, marketer.md, merchandiser.md, pm.md, po.md, researcher.md, director.md, operator.md, qa.md
- MCP：なし
- ソフトウェア：
  - Node.js v25.2.1（インストール済み）
  - Python 3.12.10（インストール済み）
  - SQLite 3.51.2（インストール済み）
  - pip 25.0.1（インストール済み）
  - FastMCP 3.0.2（インストール済み）
  - requests（インストール済み）
- Claude Codeツール：find, ls, cat, mkdir, touch, npm, pip, python, node, sqlite3（許可）/ curl, wget（拒否）

## 未解決事項
- execute_turn が未実装（バトル実行ロジックは battle/logic.py に存在するが未接続）
- ステータス自動振り分け（allocator.py）が未実装（設計書 auto-status-allocation.md のみ存在）

## これまでの主要な判断
- フレームワークの初期構築完了
- LLMバトルゲーム開発プロジェクト開始
- 技術スタック選定（Python FastMCP + requests, SQLite, Node.js Express + JWT, React + Vite）
- PO・Director・Operator・QAのアサイン決定
- 稟議 #1・#2 承認完了
- MCPサーバーをAPI経由アクセス方式に変更（直接SQLiteアクセスから変更）
- Webサーバーに書き込み系APIと認証を追加
