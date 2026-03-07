# 意思決定ログ

## 2026-02-27 メモリ機能パッチ適用
- 既存環境にメモリ永続化機能を追加
- memory/配下に3つのメモリファイルを設置

## 2026-02-27 LLMバトルゲーム開発プロジェクト開始
- プロジェクトタイプ：ゲーム開発
- 技術スタック選定：Python FastMCP（MCPサーバー）、SQLite（DB）、React + Node.js（Webビュアー）
- アサイン決定：PO, Director, Operator, QA
- Marketer/Merchandiserはアサインしない（ローカルMVP優先）
- 稟議 #1 を作成・オーナーへ上申

## 2026-02-27 稟議 #1 承認・リソース構築完了
- エージェントファイル作成：director.md, operator.md, qa.md
- Claude Code設定更新：bash許可追加（npm, pip, python, node, sqlite3）
- プロジェクト構造初期化：src/, design/, tests/, docs/, README.md, .gitignore
- 環境確認結果：Node.js インストール済み / Python・SQLite 未インストール
- 判断：Python・SQLiteは手動インストールが必要（稟議 #2 作成予定）

## 2026-02-27 稟議 #2 承認
- Python 3.8以上とSQLiteの手動インストールを依頼
- オーナー承認済み
- 次のステップ：オーナーによる手動インストール待ち

## 2026-02-27 フェーズ0完了 - 開発環境構築完了
- Python 3.12.10 インストール完了
- SQLite 3.51.2 インストール完了
- FastMCP 3.0.2 インストール完了
- フェーズ1（設計）への移行準備完了

## 2026-02-27 フェーズ1完了 - システム設計完了
- Directorによる5つの設計書作成完了
- システムアーキテクチャ設計：4層構成（MCPサーバー、Webサーバー、Webクライアント、DB）
- データベース設計：7テーブル（accounts, characters, abilities等）
- MCPサーバー設計：13ツール（アカウント管理、キャラクター管理、バトル操作等）
- バトルロジック設計：4行動タイプ、7アビリティ、ダメージ計算式
- Webビュアー設計：4ページ、15コンポーネント、リアルタイム更新
- フェーズ2（実装）への移行準備完了

## 2026-02-28 マッチングロジック詳細設計完了
- オーナーからマッチングロジックの詳細設計要求
- Directorが「matching-logic.md」を新規作成
- マッチングアルゴリズム：レーティング±100から段階的に緩和、15秒ごとに条件変更
- キュー管理システム：queueテーブル活用、トランザクション制御で同時競合解決
- マッチング成立処理：アトミックなペアリング、バトル初期化フロー
- エッジケース対応：同時競合、離脱、タイムアウト、接続切れ
- QA検証完了：設計書が品質基準を満たし合格判定
- 既存5つの設計書との整合性確認完了

## 2026-03-06 実装状態の実コード確認・ドキュメント修正
- Co-driver: 実際のコードを確認し、ドキュメントとの乖離を発見・修正
- 確認された実際の実装状態：
  - MCPサーバーは直接SQLiteではなくREST API経由でアクセス（api_client/client.py）
  - Webサーバーに書き込み系APIルーター追加（api/accounts.js, api/characters.js, api/battles.js, api/matchmaking.js）
  - JWT認証追加（middleware/auth.js）
  - セッション管理追加（session/manager.py → ~/.llmbattle/session.json）
  - execute_turnはNOT_IMPLEMENTEDを返す（未実装）
  - ステータス自動振り分け（allocator.py）は未実装（設計書のみ存在）
    ※ progress.logの「フェーズ3完了」という記録は実装前の状態への誤記の可能性大
  - create_characterのdocstringで「呼び出し側Claudeが判断」方式に変更済み
- 修正したドキュメント：README.md（アーキテクチャ図、依存パッケージ、使い方）
- 更新したメモリ：pm_memory.md, project_memory.md, decisions.md

