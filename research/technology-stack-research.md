# LLM同士が戦うターン制バトルゲーム - 技術スタック調査レポート

調査日: 2026-02-27
調査者: Researcher

---

## 1. MCPサーバーの実装

### 推奨技術

#### オプションA: **TypeScript/Node.js**
- **理由**:
  - 公式のTypeScript SDKが充実（`@modelcontextprotocol/sdk`）
  - 2026年Q1にv2 SDKの安定版リリース予定
  - 多数のチュートリアルとコミュニティサポート
  - Claudeとの統合が最も簡単
  - JSON-RPCベースのプロトコル実装が容易

- **実装難易度**: **中**
  - 基本的なサーバーは10分以内に作成可能
  - Claudeとの連携設定が必要
  - WebSocketやSTDIO transportの理解が必要

- **必要なソフトウェア**:
  - Node.js (v18以上推奨) - bashでインストール可能
  - npm または yarn - Node.jsに同梱
  - TypeScript - `npm install -g typescript` でインストール可能

#### オプションB: **Python FastMCP**
- **理由**:
  - 最も簡単なMCP実装（FastMCP 2.0）
  - 公式Python SDKに統合済み
  - デコレータベースで直感的（`@mcp.tool`）
  - 型ヒントとdocstringから自動スキーマ生成
  - 全MCP サーバーの70%がFastMCPを使用

- **実装難易度**: **低**
  - 最もシンプルな実装方法
  - Pythonの基礎知識があれば十分
  - `pip install fastmcp` で即開始可能

- **必要なソフトウェア**:
  - Python 3.8以上 - bashでインストール可能
  - pip - Pythonに同梱
  - FastMCP - `pip install fastmcp[websockets]` でインストール可能

### MCPプロトコルの概要
- JSON-RPC 2.0ベースの通信プロトコル
- 3つのコア機能:
  1. **Tools**: LLMが呼び出せる関数
  2. **Resources**: アプリケーション側のデータソース
  3. **Prompts**: 構造化されたテンプレート
- Transport: STDIO（ローカル開発）またはSSE/WebSocket（Web展開）

### 実装のベストプラクティス
- STDIO サーバーでは標準出力を使わない（JSON-RPCメッセージが破損）
- ロギングはstderrまたはファイルに出力
- 各MCPサーバーは単一の明確な目的を持つべき
- OAuth 2.1を使用した認証（2025年以降の標準）
- MCP Inspectorでデバッグ（`http://localhost:<port>/mcp`）

---

## 2. バトルビュアー（Webインターフェース）

### 推奨技術

#### **React + Vite + WebSocket**
- **理由**:
  - Viteによる高速な開発環境
  - WebSocketによる双方向リアルタイム通信
  - メッセージレイテンシを最大70%削減
  - ターン制バトルに最適な状態管理
  - 豊富なチュートリアルとサンプル

- **実装難易度**: **中**
  - React Hooksの理解が必要
  - WebSocket接続管理の実装
  - 再接続ロジックとエラーハンドリング

- **必要なソフトウェア**:
  - Node.js (v18以上) - bashでインストール可能
  - Vite - `npm create vite@latest` でプロジェクト作成
  - 推奨ライブラリ:
    - `socket.io-client` - WebSocket管理
    - `react-use-websocket` - React Hooks統合

#### バックエンド: **Express.js + Socket.IO**
- **理由**:
  - Node.jsの定番Webフレームワーク
  - Socket.IOによる簡単なWebSocket実装
  - Go + Gorilla WebSocketなら10,000同時接続以上対応可能
  - RESTful APIとWebSocketの統合が容易

- **実装難易度**: **低〜中**
  - Express.jsの基本的な理解
  - Socket.IOのイベント駆動プログラミング

- **必要なソフトウェア**:
  - Node.js - bashでインストール可能
  - Express.js - `npm install express` でインストール可能
  - Socket.IO - `npm install socket.io` でインストール可能

### リアルタイム更新の実装方法
1. **WebSocket接続確立**
   - クライアント→サーバー: 初期接続
   - サーバー→クライアント: 接続承認

2. **バトル状態の同期**
   - ターン開始時にLLMが行動を決定
   - MCPサーバー経由でバトルロジック実行
   - WebSocket経由で全クライアントに結果配信

3. **再接続処理**
   - 接続断時の自動再接続
   - 状態復元のためのスナップショット取得

### UIコンポーネント設計
- バトルフィールド表示
- ターン進行インジケーター
- HP/ステータス表示
- アクションログ
- キャラクター表示

---

## 3. データ保存

### 推奨技術

#### **SQLite**
- **理由**:
  - ローカル環境に最適（サーバー不要）
  - 単一ファイルで管理が簡単
  - 600KiB未満の小さいフットプリント
  - ファイルシステムより高速な場合が多い
  - ネットワークレイテンシなし
  - モバイル・ゲームでの実績豊富

- **実装難易度**: **低**
  - SQL基礎知識があれば十分
  - ORMライブラリで更に簡単に
  - 設定・メンテナンス不要

- **制限事項**:
  - 高並行書き込みには不向き（ローカルゲームでは問題なし）
  - 1TB以上のデータには不向き（バトルゲームでは問題なし）
  - 単一ファイルのため、大規模化時にボトルネック

- **必要なソフトウェア**:
  - SQLite - bashでインストール可能
  - Node.js用: `better-sqlite3` - `npm install better-sqlite3`
  - Python用: `sqlite3` - 標準ライブラリに含まれる

### データベース設計

#### テーブル構造（案）
```sql
-- アカウント
CREATE TABLE accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- キャラクター
CREATE TABLE characters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    level INTEGER DEFAULT 1,
    hp INTEGER NOT NULL,
    attack INTEGER NOT NULL,
    defense INTEGER NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES accounts(id)
);

-- バトル履歴
CREATE TABLE battles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player1_id INTEGER NOT NULL,
    player2_id INTEGER NOT NULL,
    winner_id INTEGER,
    battle_data TEXT, -- JSON形式でバトルの詳細を保存
    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    ended_at DATETIME,
    FOREIGN KEY (player1_id) REFERENCES characters(id),
    FOREIGN KEY (player2_id) REFERENCES characters(id),
    FOREIGN KEY (winner_id) REFERENCES characters(id)
);

-- 戦績
CREATE TABLE stats (
    character_id INTEGER PRIMARY KEY,
    total_battles INTEGER DEFAULT 0,
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    draws INTEGER DEFAULT 0,
    FOREIGN KEY (character_id) REFERENCES characters(id)
);
```

### 代替案

#### **Redis** (オプション)
- **用途**: キャッシュ・リアルタイム状態管理
- **理由**:
  - ターンベースゲームの状態管理に最適
  - 強い一貫性と明確なターン順序
  - 再接続時の状態復元が容易
- **実装難易度**: **中**
- **必要性**: SQLiteだけでも十分だが、複雑な状態管理が必要な場合に検討

---

## 4. マッチングシステム

### 推奨技術

#### **シンプルなキューベースマッチング**
- **理由**:
  - ローカル環境に最適
  - 実装がシンプル
  - レーティング（MMR）ベースのマッチング可能
  - Redisキューまたはメモリ内キューで実装

- **実装難易度**: **低〜中**
  - 基本的なキュー操作の理解
  - マッチング条件の設定

- **実装アプローチ**:
  1. プレイヤーがマッチング待機キューに参加
  2. サーバーが定期的にキューをチェック
  3. 条件に合うプレイヤーをペアリング
  4. バトルセッション作成
  5. 両プレイヤーに通知

### マッチングアルゴリズム（案）
```javascript
// シンプルなMMRベースマッチング
function findMatch(waitingPlayers, newPlayer) {
  const MMR_RANGE = 100; // レーティング差の許容範囲

  for (let player of waitingPlayers) {
    const mmrDiff = Math.abs(player.mmr - newPlayer.mmr);
    if (mmrDiff <= MMR_RANGE) {
      return player; // マッチング成立
    }
  }

  // マッチング相手が見つからない場合はキューに追加
  waitingPlayers.push(newPlayer);
  return null;
}
```

### 高度なオプション

#### **Open Match**（必要に応じて）
- Kubernetes上で動作する分散マッチングシステム
- 複雑なマッチング条件に対応
- **実装難易度**: **高**
- **必要性**: 初期実装では不要

---

## 5. 必要なソフトウェア・ツール

### bashでインストールできるもの

#### 必須
1. **Node.js** (v18以上)
   ```bash
   # Windows (Chocolatey経由)
   choco install nodejs

   # または公式インストーラーをダウンロード
   ```

2. **Python** (3.8以上)
   ```bash
   # Windows (Chocolatey経由)
   choco install python
   ```

3. **SQLite**
   ```bash
   # Windows (Chocolatey経由)
   choco install sqlite
   ```

4. **Git** (バージョン管理)
   ```bash
   # Windows (Chocolatey経由)
   choco install git
   ```

#### 推奨
5. **TypeScript**
   ```bash
   npm install -g typescript
   ```

6. **プロジェクト依存パッケージ**
   ```bash
   # MCPサーバー（TypeScript）
   npm install @modelcontextprotocol/sdk

   # MCPサーバー（Python）
   pip install fastmcp[websockets]

   # Webサーバー
   npm install express socket.io

   # フロントエンド
   npm create vite@latest
   npm install socket.io-client

   # データベース
   npm install better-sqlite3  # Node.js用
   # Python用はsqlite3が標準ライブラリに含まれる
   ```

### 手動でインストールが必要なもの

1. **Claude Desktop** (MCPサーバーのテスト用)
   - 公式サイトからダウンロード
   - MCPサーバーを`claude_desktop_config.json`に登録

2. **テキストエディタ/IDE**
   - Visual Studio Code（推奨）
   - Claude Code統合が利用可能

3. **Chocolatey** (Windowsパッケージマネージャー)
   - PowerShellから公式スクリプトを実行
   - 他のソフトウェアのインストールを簡略化

---

## 6. システムアーキテクチャの推奨構成

### 全体構成図（概念）
```
┌─────────────────────┐
│  Claude Desktop     │
│  (LLMクライアント)   │
└──────────┬──────────┘
           │ MCP Protocol (STDIO)
           │
┌──────────▼──────────┐
│  MCP Server         │
│  (バトルロジック)    │
│  - TypeScript/Python│
│  - SQLite接続       │
└──────────┬──────────┘
           │
           │ WebSocket
           │
┌──────────▼──────────┐
│  Web Server         │
│  (Express + Socket) │
└──────────┬──────────┘
           │
           │ WebSocket
           │
┌──────────▼──────────┐
│  Web Client         │
│  (React + Vite)     │
│  - バトルビュアー    │
└─────────────────────┘

┌─────────────────────┐
│  SQLite DB          │
│  - accounts.db      │
│  - battles.db       │
└─────────────────────┘
```

### 推奨開発フロー
1. **フェーズ1**: SQLiteデータベース設計・実装
2. **フェーズ2**: 基本的なMCPサーバー実装（Python FastMCP推奨）
3. **フェーズ3**: バトルロジックの実装
4. **フェーズ4**: Express.js Webサーバー + Socket.IO実装
5. **フェーズ5**: React フロントエンド実装
6. **フェーズ6**: マッチングシステム実装
7. **フェーズ7**: 統合テスト・デバッグ

---

## 7. 実装難易度まとめ

| コンポーネント | 技術スタック | 実装難易度 | 開発時間目安 |
|--------------|-------------|-----------|------------|
| データベース | SQLite | **低** | 1-2日 |
| MCPサーバー | Python FastMCP | **低** | 2-3日 |
| バトルロジック | Python/TypeScript | **中** | 3-5日 |
| Webサーバー | Express + Socket.IO | **中** | 2-3日 |
| フロントエンド | React + Vite | **中** | 3-5日 |
| マッチング | メモリキュー | **低** | 1-2日 |

**合計開発期間**: 約2-3週間（1人）

---

## 8. リスクと注意事項

### 技術的リスク
1. **MCP Protocol学習曲線**
   - 軽減策: Python FastMCPを使用（最も簡単）
   - 公式ドキュメントとチュートリアルが充実

2. **WebSocketの接続管理**
   - 軽減策: Socket.IOを使用（自動再接続機能あり）
   - エラーハンドリングとタイムアウト処理を実装

3. **LLMのレスポンス時間**
   - 軽減策: タイムアウト設定とローディング表示
   - 非同期処理で他プレイヤーを待たせない

### 運用リスク
1. **SQLiteの同時書き込み制限**
   - 影響: ローカル環境では問題なし
   - 将来の拡張: 必要に応じてPostgreSQLに移行可能

2. **Claude APIの使用料金**
   - 影響: API呼び出し回数に応じて課金
   - 軽減策: 開発時はテストモード、本番はレート制限

---

## 9. 参考資料

### MCPサーバー実装
- [Build an MCP server - Model Context Protocol](https://modelcontextprotocol.io/docs/develop/build-server)
- [How to Build an MCP Server (Step-by-Step Guide) 2026](https://www.leanware.co/insights/how-to-build-mcp-server)
- [Build Your First MCP Server with TypeScript](https://noqta.tn/en/tutorials/build-mcp-server-typescript-2026)
- [Building an MCP Server and Client with FastMCP 2.0](https://www.datacamp.com/tutorial/building-mcp-server-client-fastmcp)
- [FastMCP Documentation](https://gofastmcp.com/getting-started/quickstart)

### Claude MCP Protocol
- [Introducing the Model Context Protocol](https://www.anthropic.com/news/model-context-protocol)
- [MCP Protocol Specification](https://www.claudemcp.com/specification)
- [Connect Claude Code to tools via MCP](https://code.claude.com/docs/en/mcp)

### WebSocket & リアルタイム通信
- [How to Use WebSockets in React for Real-Time Applications](https://oneuptime.com/blog/post/2026-01-15-websockets-react-real-time-applications/view)
- [The complete guide to WebSockets with React](https://ably.com/blog/websockets-react-tutorial)
- [Building A Real-Time App with React, Node and WebSockets](https://www.telerik.com/blogs/building-real-time-app-react-node-websockets)

### データベース
- [Appropriate Uses For SQLite](https://sqlite.org/whentouse.html)
- [SQLite vs MySQL vs PostgreSQL](https://www.digitalocean.com/community/tutorials/sqlite-vs-mysql-vs-postgresql-a-comparison-of-relational-database-management-systems)

### ゲーム状態管理
- [The Turn-Based Game Architecture](https://outscal.com/blog/turn-based-game-architecture)
- [How to Implement Game State Management with Redis](https://oneuptime.com/blog/post/2026-01-21-redis-game-state-management/view)
- [boardgame.io - State Management for Turn-Based Games](https://github.com/boardgameio/boardgame.io)

### マッチングシステム
- [Design a Simple Real-Time Matchmaking Service](https://yashh21.medium.com/designing-a-simple-real-time-matchmaking-service-architecture-implementation-96e10f095ce1)
- [Open Match Documentation](https://open-match.dev/site/docs/guides/matchmaker/)

### Express.js & Node.js
- [Express "Hello World" example](https://expressjs.com/en/starter/hello-world.html)
- [Express/Node introduction - MDN](https://developer.mozilla.org/en-US/docs/Learn_web_development/Extensions/Server-side/Express_Nodejs/Introduction)
- [How To Get Started with Node.js and Express](https://www.digitalocean.com/community/tutorials/nodejs-express-basics)

---

## 10. 結論と推奨事項

### 最も推奨する技術スタック

1. **MCPサーバー**: Python FastMCP
   - 最も簡単で学習曲線が低い
   - 公式SDK統合済み
   - 開発速度が速い

2. **データベース**: SQLite
   - ローカル環境に最適
   - 設定不要で即利用可能
   - ゲームデータには十分な性能

3. **Webサーバー**: Express.js + Socket.IO
   - Node.jsエコシステムの定番
   - WebSocket統合が簡単
   - 豊富なチュートリアル

4. **フロントエンド**: React + Vite + Socket.IO-Client
   - 最新の開発環境
   - リアルタイム通信に最適
   - コンポーネントベースで保守性が高い

5. **マッチング**: シンプルなメモリキュー
   - ローカル環境では十分
   - 複雑性を最小化
   - 必要に応じて拡張可能

### 開発開始に必要な最初のステップ
1. Node.js と Python のインストール
2. SQLiteのインストール
3. プロジェクトディレクトリの作成
4. データベーススキーマの設計
5. FastMCP サーバーの基本実装

このアプローチにより、ローカル環境で完全に動作する「LLM同士が戦うターン制バトルゲーム」を実装できます。

---

**調査完了日**: 2026-02-27
**次のステップ**: PMへの稟議書作成（リソース承認申請）
