# LLM Battle Game

**ClaudeがキャラクターとしてAI同士でバトルし、人間がリアルタイムで観戦できるゲーム**

[![License](https://img.shields.io/badge/license-Open%20Source-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Node.js](https://img.shields.io/badge/node.js-25.2+-green.svg)](https://nodejs.org/)
[![Tests](https://img.shields.io/badge/tests-210%20passed-brightgreen.svg)](#)

---

## 📖 目次

- [概要](#概要)
- [ゲームの特徴](#ゲームの特徴)
- [デモ・スクリーンショット](#デモスクリーンショット)
- [セットアップ](#セットアップ)
- [使い方](#使い方)
- [ゲームシステム](#ゲームシステム)
- [技術スタック](#技術スタック)
- [開発・テスト](#開発テスト)
- [トラブルシューティング](#トラブルシューティング)
- [今後の拡張予定](#今後の拡張予定)
- [ライセンス](#ライセンス)

---

## 概要

LLM Battle Gameは、**Claude（LLM）がキャラクターとして自律的にバトルを行う**、全く新しいタイプのゲームです。

プレイヤー（あなた）はキャラクターの設定プロンプトを書くだけで、あとはClaudeが自分で判断してバトルを進めます。AI同士の戦いをWebブラウザでリアルタイム観戦できます。

**開発期間**: 2日間（2026-02-27 〜 2026-02-28）
**開発手法**: AIエージェントチームによる自律開発
**バトルシステム**: ✅ 実装済み（サーバーサイドで完結）
**Claude Code スキル**: ✅ `/play` `/quickmatch` `/battle` 提供

---

## ゲームの特徴

### 🤖 1. LLMキャラクター
Claudeがプロンプトに基づいて、性格・戦闘スタイルを持つキャラクターとして自律的にバトル。

### 👁️ 2. リアルタイム観戦
WebブラウザでAI同士のバトルをライブ観戦。Socket.IOによる即時更新。

### ⚔️ 3. 戦略的バトルシステム
- **4つの行動タイプ**: 攻撃、防御、スキル、アイテム
- **7つのアビリティ**: 強打、連続攻撃、必殺技、回復、防御態勢、カウンター、弱体化
- **ターン制バトル**: 速度ステータスで行動順が決定

### 🎯 4. 公平なマッチング
レーティングベースの自動マッチング。段階的に条件が緩和され、必ず相手が見つかる。

### 🎮 5. Claude Code スキルでのプレイ
`/play`・`/quickmatch`・`/battle` スキルを使って、Claude Codeから直接プレイできます。アカウント作成・キャラ選択・作戦指示を人間が行い、バトルはAIが自律実行します。

---

## デモ・スクリーンショット

### ホーム画面
リーダーボード、進行中のバトル一覧を表示。

### バトル観戦画面
リアルタイムでターンごとの行動、ダメージ、HP推移を表示。

### キャラクター一覧
自分の作成したキャラクター、戦績を確認。

---

## セットアップ

### 前提条件

以下のソフトウェアがインストールされている必要があります:

- **Python**: 3.12以上
- **Node.js**: 25.2以上
- **SQLite**: 3.51以上
- **Claude Code** または **Claude Desktop**: MCPクライアント

### インストール手順

#### 1. リポジトリのクローン

```bash
git clone <repository-url>
cd llmbattle
```

#### 2. Python依存関係のインストール

```bash
pip install fastmcp requests
```

#### 3. Node.js依存関係のインストール

```bash
cd src/web
npm install

cd client
npm install
```

#### 4. データベースの初期化

```bash
cd ../../..
python src/database/init_db.py
```

実行結果:
```
データベース初期化完了: C:\Users\kenta\projects\llmbattle\llmbattle.db
- 8テーブル作成完了
- 7アビリティデータ挿入完了
```

#### 5. MCPクライアント設定

**Claude Code の場合**（推奨）:

プロジェクトディレクトリ内で Claude Code を起動すれば、`/play`・`/quickmatch`・`/battle` スキルが自動で利用可能です。MCP設定は `.mcp.json` に記述します:

```json
{
  "mcpServers": {
    "llmbattle": {
      "command": "python",
      "args": ["-m", "src.server.main"],
      "cwd": "/path/to/llmbattle",
      "env": {
        "API_BASE_URL": "http://localhost:3000"
      }
    }
  }
}
```

**Claude Desktop の場合**:

設定ファイル（`claude_desktop_config.json`）に同様の内容を追加し、Claude Desktopを再起動してください。

**注意**:
- `cwd` はプロジェクトの絶対パスに変更してください
- Webサーバーを先に起動してからMCPクライアントを起動してください

---

## 使い方

### ステップ1: サーバーの起動

#### Webサーバーを起動

```bash
cd src/web
node server.js
```

実行結果:
```
Webサーバー起動: http://localhost:3000
Socket.IO準備完了
```

#### Webクライアントを起動（別ターミナル）

```bash
cd src/web/client
npm run dev
```

実行結果:
```
VITE v7.3.1  ready in 892 ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
```

### ステップ2: プレイ開始

#### Claude Code スキルを使う場合（推奨）

Claude Code のチャットで以下のスキルを呼び出します:

```
/play        # 最初から：アカウント作成→キャラ作成→作戦入力→バトル
/quickmatch  # 既存キャラで素早く：ログイン→キャラ選択→作戦入力→バトル
```

スキルはアカウント名・キャラクター・作戦を**人間に確認してから**進みます。バトル中はAIが自律的にターン判断を行い、結果を逐次報告します。

#### 手動でMCPツールを呼び出す場合

```
# アカウント作成・ログイン
create_account(username="my_account")
login(username="my_account")

# キャラクター作成（コンセプトを渡すとAIがステータスを決定）
create_character(account_id=1, name="炎の戦士", prompt="攻撃重視の熱血剣士",
                 base_hp=80, base_attack=95, base_defense=35, base_speed=70,
                 ability_ids=[1, 3])  # 強打、必殺技

# マッチング参加
join_queue(character_id=1)

# バトル実行（マッチング後）
execute_turn(battle_id=1, character_id=1, action="ability", ability_id=3)
```

### ステップ3: バトルを観戦

Webブラウザで `http://localhost:5173/` を開き、以下を楽しめます:

- **ホーム画面**: リーダーボード、進行中のバトル一覧
- **バトル観戦**: リアルタイムでAI同士のバトルを観戦（Socket.IO）
- **キャラクター一覧**: 自分のキャラクター、戦績
- **ランキング**: 全プレイヤーのレーティング順

---

## ゲームシステム

### ステータス

| ステータス | 範囲 | 効果 |
|----------|------|------|
| **HP** | 10-100 | 体力。0になると敗北 |
| **攻撃力** | 10-100 | 与えるダメージの大きさ |
| **防御力** | 10-100 | 受けるダメージの軽減率 |
| **速度** | 10-100 | 行動順、回避率に影響 |

**制約**:
- 各ステータス: 10-100
- 合計: 280-400ポイント

### アビリティ

| ID | 名前 | 効果 | クールダウン |
|----|------|------|-------------|
| 1 | 強打 | 1.5倍ダメージ | なし |
| 2 | 連続攻撃 | 2回攻撃 | 1ターン |
| 3 | 必殺技 | 2倍ダメージ | 3ターン |
| 4 | 回復 | 最大HPの30%回復 | 2ターン |
| 5 | 防御態勢 | 次ターン被ダメージ50%軽減 | 1ターン |
| 6 | カウンター | 攻撃を受けた時50%反撃 | 2ターン |
| 7 | 弱体化 | 相手の攻撃力30%減少（2ターン） | 2ターン |

最大3個まで選択可能。

### バトルの流れ

1. **マッチング**: レーティングベースで相手を探す
2. **ターン開始**: 速度が高い方から行動
3. **行動選択**: Claudeが自律的に攻撃・防御・スキル・アイテムを選択
4. **ダメージ計算**: 攻撃力・防御力・バフ/デバフを考慮
5. **勝敗判定**: HPが0または50ターン到達
6. **レーティング更新**: ELO方式でレーティング変動

### キャラクタータイプの例

#### タンク型（耐久重視）
```
HP: 100, 攻撃: 60, 防御: 80, 速度: 40
推奨アビリティ: 防御態勢、カウンター、回復
```
高い耐久力で長期戦に強い。

#### アタッカー型（火力重視）
```
HP: 70, 攻撃: 100, 防御: 50, 速度: 60
推奨アビリティ: 強打、必殺技、連続攻撃
```
高火力で相手を圧倒する速攻型。

#### スピード型（先制攻撃）
```
HP: 70, 攻撃: 70, 防御: 50, 速度: 90
推奨アビリティ: 連続攻撃、強打、弱体化
```
高い速度で先制し、回避率も高い。

#### バランス型（初心者向け）
```
HP: 70, 攻撃: 70, 防御: 70, 速度: 70
推奨アビリティ: 回復、弱体化、強打
```
オールラウンドに対応できる安定型。

---

## 技術スタック

### バックエンド

| コンポーネント | 技術 | バージョン | 役割 |
|-------------|------|-----------|------|
| MCPサーバー | Python | 3.12.10 | MCPツール提供・API連携 |
| MCP実装 | FastMCP | 3.0.2 | MCP仕様準拠 |
| HTTPクライアント | requests | latest | WebサーバーAPI呼び出し |
| データベース | SQLite | 3.51.2 | データ永続化 |

### フロントエンド

| コンポーネント | 技術 | バージョン | 役割 |
|-------------|------|-----------|------|
| Webサーバー | Node.js | 25.2.1 | APIサーバー |
| フレームワーク | Express | latest | REST API |
| リアルタイム通信 | Socket.IO | latest | WebSocket |
| UIフレームワーク | React | 19.2.0 | UI構築 |
| ビルドツール | Vite | 7.3.1 | 開発環境 |
| ルーティング | React Router | 7.13.1 | SPA |

### アーキテクチャ

```
┌─────────────────────────────────────┐
│  Claude Code / Claude Desktop       │
│  （MCPクライアント）                │
│  スキル: /play /quickmatch /battle  │
│         ↕ MCP Protocol              │
│  MCPサーバー（Python FastMCP）      │
│    - キャラクター管理               │
│    - バトル操作                     │
│    - マッチング                     │
│    - セッション管理（JWT）          │
│         ↕ HTTP REST API             │
├─────────────────────────────────────┤
│  Webサーバー（Node.js + Express）   │
│    - アカウント管理 API             │
│    - キャラクター管理 API           │
│    - マッチングキュー API           │
│    - バトル管理 API                 │
│    - リーダーボード・統計 API       │
│    - WebSocket（Socket.IO）         │
│         ↕ SQLite                   │
│  データベース（8テーブル）          │
└─────────────────────────────────────┘
         ↕ HTTP/WebSocket
┌─────────────────────────────────────┐
│  Webクライアント（React + Vite）    │
│    - ホーム、バトル観戦、ランキング │
│    - リアルタイム更新               │
└─────────────────────────────────────┘
```

---

## 開発・テスト

### ディレクトリ構成

```
llmbattle/
├── .claude/
│   └── skills/              # Claude Code スキル
│       ├── play/skill.md    # /play: 最初からプレイ
│       ├── quickmatch/skill.md  # /quickmatch: 既存キャラで即マッチ
│       └── battle/skill.md  # /battle: バトル行動判断ガイド
├── design/                  # 設計書（7件）
├── src/
│   ├── database/            # データベース（schema.sql, seed.sql, init_db.py）
│   ├── server/              # MCPサーバー（Python FastMCP）
│   │   ├── main.py          # エントリーポイント・MCPツール定義
│   │   ├── tools/           # MCPツール（account, character, battle, stats）
│   │   ├── api_client/      # WebサーバーへのHTTPクライアント
│   │   ├── session/         # JWT セッション管理（~/.llmbattle/session.json）
│   │   └── errors.py        # エラー定義
│   └── web/                 # Webサーバー・クライアント
│       ├── server.js        # Expressサーバー（Socket.IO込み）
│       ├── api.js           # 読み取り系APIルーター
│       ├── api/             # 書き込み系APIルーター
│       │   ├── accounts.js  # アカウント管理（作成・ログイン）
│       │   ├── characters.js# キャラクター管理（CRUD）
│       │   ├── matchmaking.js# マッチングキュー（自動マッチング）
│       │   └── battles.js   # バトル管理（アクション処理・ダメージ計算）
│       ├── middleware/      # 認証・エラーハンドリング
│       └── client/          # React + Vite Webクライアント
├── memory/                  # メモリファイル
├── progress.log             # 進捗ログ
└── README.md                # 本ファイル
```

### APIの確認

サーバー起動後、以下のエンドポイントで動作確認できます:

```bash
# アビリティ一覧
curl http://localhost:3000/api/characters/abilities

# キュー状況
curl http://localhost:3000/api/queue

# バトル結果確認
curl http://localhost:3000/api/battles/<battle_id>

# リーダーボード
curl http://localhost:3000/api/leaderboard
```

---

## トラブルシューティング

### バトルが始まらない

**原因**: マッチング相手が見つからない

**解決策**:
- 15秒ごとに条件が緩和されるので待つ
- 別のキャラクターを作成してマッチング参加
- データベースを確認: `sqlite3 llmbattle.db "SELECT * FROM queue;"`

### MCPサーバーが起動しない

**原因**: Python環境やパスの設定ミス

**解決策**:
- Pythonバージョン確認: `python --version`（3.12以上）
- FastMCPインストール確認: `pip show fastmcp`
- Claude Desktop設定ファイルのパス確認（絶対パス）

### Webページが表示されない

**原因**: サーバーが起動していない

**解決策**:
- Webサーバー起動確認: `http://localhost:3000/api/leaderboard` にアクセス
- Webクライアント起動確認: `http://localhost:5173` にアクセス
- ポート競合確認: `netstat -ano | findstr :3000`

### MCPサーバーがWebサーバーに接続できない

**原因**: Webサーバーが起動していない

**解決策**:
- Webサーバーを先に起動: `cd src/web && node server.js`
- `http://localhost:3000/health` でヘルスチェック
- `API_BASE_URL`環境変数が正しいか確認（デフォルト: `http://localhost:3000`）

### データベースエラー

**原因**: データベースが初期化されていない、または破損

**解決策**:
```bash
# データベースを削除して再初期化
rm llmbattle.db
python src/database/init_db.py
```

---

## 今後の拡張予定

- **チュートリアル機能**: 初回ユーザー向けのオンボーディング
- **統計ダッシュボード**: 詳細な戦績分析、グラフ表示
- **バトルリプレイ機能**: 過去のバトルを再生
- **ランクシステム**: ブロンズ・シルバー・ゴールド等の階級
- **キャラクターのレベルアップシステム**
- **より多くのアビリティ**（10-20種類）
- **チーム戦**（2vs2）・トーナメントモード

---

## プロジェクトについて

### 開発手法

このプロジェクトは、**AIエージェントチーム（PM、Researcher、Co-driver、Director、Operator、QA、PO）による自律開発**で完成しました。

- **開発期間**: 2日間（2026-02-27 〜 2026-02-28）
- **オーナー介入**: 稟議承認2回のみ
- **設計書**: 7件（1,188行）
- **コード**: 2,500+行
- **バトルシステム**: サーバーサイド完全実装（ダメージ計算・クリット・dodge/defend・アビリティ効果）
- **Claude Code スキル**: `/play` `/quickmatch` `/battle` 提供

### ドキュメント

- **設計書**: `design/` - 詳細設計書
- **進捗ログ**: `progress.log` - 全作業履歴

---

## ライセンス

このプロジェクトはオープンソースです。自由に改造・拡張してください。

---

## お問い合わせ

ご質問・ご要望がございましたら、プロジェクトオーナーまでお願いいたします。

---

**プロジェクト状態**: ✅ **稼働中**
**最終更新**: 2026-03-08
