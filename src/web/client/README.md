# LLM Battle Game - Web Client

React + Vite + Socket.IOを使用したWebクライアント完全版

## 概要

LLMバトルゲームのリアルタイム観戦Webアプリケーション。
Socket.IOによるリアルタイム更新で、バトルの進行をライブで視聴できます。

## 技術スタック

- **React 18** - UIフレームワーク
- **Vite** - ビルドツール・開発サーバー
- **React Router** - ルーティング
- **Socket.IO Client** - WebSocket通信（リアルタイム更新）
- **CSS Variables** - スタイリング

## プロジェクト構造

```
src/
├── api/
│   └── client.js           # REST APIクライアント
├── components/
│   ├── Battle/            # バトル関連コンポーネント
│   │   ├── BattleField.jsx
│   │   ├── CharacterCard.jsx
│   │   ├── TurnIndicator.jsx
│   │   ├── ActionLog.jsx
│   │   └── BattleResult.jsx
│   ├── Character/         # キャラクター関連コンポーネント
│   │   └── CharacterItem.jsx
│   ├── Leaderboard/       # リーダーボード関連コンポーネント
│   │   └── LeaderboardTable.jsx
│   └── Common/            # 共通コンポーネント
│       ├── Header.jsx
│       ├── Footer.jsx
│       └── Loading.jsx
├── hooks/
│   ├── useWebSocket.js    # WebSocket接続管理
│   ├── useBattleState.js  # バトル状態管理
│   └── useApi.js          # API通信管理
├── pages/
│   ├── Home.jsx           # ホームページ
│   ├── BattleViewer.jsx   # バトル観戦ページ
│   ├── CharacterList.jsx  # キャラクター一覧
│   └── Leaderboard.jsx    # リーダーボード
├── App.jsx                # メインアプリ
├── main.jsx               # エントリーポイント
└── index.css              # グローバルスタイル
```

## 機能

### 実装済み機能

1. **ホームページ**
   - 進行中のバトル一覧（LIVE表示）
   - 最近のバトル一覧
   - リーダーボード・キャラクター一覧へのナビゲーション

2. **バトル観戦ページ**
   - リアルタイムバトル観戦
   - WebSocketによる自動更新
   - ターンインジケーター（進行状況表示）
   - バトルフィールド（キャラクターステータス表示）
   - HP バー（色が残量に応じて変化）
   - アクションログ（ターンごとの行動履歴）
   - バトル結果表示（勝者アナウンス）
   - 接続状態表示・自動再接続

3. **キャラクター一覧ページ**
   - 全キャラクター表示
   - キャラクターステータス閲覧

4. **リーダーボードページ**
   - ランキング表示
   - 自動更新（30秒間隔）
   - 上位3位の特別表示（金・銀・銅バッジ）

### デザイン特徴

- **ダークテーマ**: 目に優しい暗めの配色
- **レスポンシブデザイン**: モバイル・タブレット・デスクトップ対応
- **アニメーション**: フェードイン、スライド、パルスエフェクト
- **グラデーション**: プライマリカラーとセカンダリカラーのグラデーション

## セットアップ

### 1. 依存関係のインストール

```bash
cd src/web/client
npm install
```

### 2. 開発サーバーの起動

```bash
npm run dev
```

開発サーバーは `http://localhost:5173` で起動します。

### 3. 本番ビルド

```bash
npm run build
```

ビルド結果は `dist/` ディレクトリに出力されます。

## サーバー連携

このクライアントは以下のサーバーと連携します：

- **REST API**: `http://localhost:3000/api`
- **WebSocket**: `http://localhost:3000` (Socket.IO)

Vite の proxy 設定により、開発時は自動的にリクエストが転送されます。

## 環境変数

現在、環境変数は使用していません。
本番環境では、以下の変数を設定できます：

- `VITE_API_BASE_URL`: APIサーバーのURL
- `VITE_WS_URL`: WebSocketサーバーのURL

## API エンドポイント

クライアントが使用するAPIエンドポイント：

- `GET /api/battles/:id` - バトル詳細取得
- `GET /api/battles/:id/turns` - ターン履歴取得
- `GET /api/battles?status=finished&limit=10` - 最近のバトル取得
- `GET /api/battles?status=active&limit=5` - 進行中のバトル取得
- `GET /api/characters` - キャラクター一覧取得
- `GET /api/leaderboard` - リーダーボード取得

## WebSocket イベント

### クライアント → サーバー

- `subscribe_battle(battleId)` - バトル購読
- `unsubscribe_battle(battleId)` - バトル購読解除

### サーバー → クライアント

- `battle_started` - バトル開始通知
- `turn_executed` - ターン実行結果
- `battle_ended` - バトル終了通知

## トラブルシューティング

### WebSocket接続エラー

サーバーが起動していることを確認してください：

```bash
cd src/web
node server.js
```

### ポート競合

デフォルトポート（5173）が使用中の場合、`vite.config.js`で変更できます：

```javascript
export default defineConfig({
  server: {
    port: 別のポート番号
  }
})
```

## ライセンス

MIT License

## 作成者

LLM Battle Game Development Team
