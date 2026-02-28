# LLM Battle Web Server

Node.js + Express Web サーバーで、バトル情報をREST APIで提供します。

## 構成

```
src/web/
├── server.js    # Expressサーバーのエントリポイント
├── db.js        # データベース接続モジュール
└── api.js       # REST APIエンドポイント
```

## セットアップ

### 依存関係のインストール

```bash
npm install
```

### サーバーの起動

```bash
# 本番モード
npm start

# 開発モード（自動リロード）
npm run dev
```

サーバーは `http://localhost:3000` で起動します。

## API エンドポイント

### レーダーボード

```bash
GET /api/leaderboard?limit=50
```

レーティング上位のキャラクター一覧を取得

### キャラクター詳細

```bash
GET /api/character/:id
```

指定したキャラクターの詳細情報、戦績、アビリティ、バトル履歴を取得

### バトル詳細

```bash
GET /api/battle/:id
```

指定したバトルの詳細情報とターンログを取得

### 全体統計

```bash
GET /api/stats
```

総バトル数、総キャラクター数、今日のバトル数などの統計情報を取得

### ヘルスチェック

```bash
GET /health
```

サーバーの稼働状態を確認

## テスト

### クイックテスト

```bash
node scripts/quick_test.js
```

### 包括的なテスト

```bash
node tests/test_web_api.js
```

## 設定

### 環境変数

| 変数名 | デフォルト値 | 説明 |
|--------|-------------|------|
| PORT | 3000 | サーバーのポート番号 |
| DB_PATH | ../database/llmbattle.db | データベースファイルのパス |

### 使用例

```bash
PORT=8080 npm start
```

## データベース

SQLiteデータベース (`src/database/llmbattle.db`) から以下のテーブルを読み取ります：

- `characters` - キャラクター情報
- `stats` - キャラクター戦績
- `abilities` - アビリティ定義
- `character_abilities` - キャラクター-アビリティ関連
- `battles` - バトル記録
- `battle_turns` - ターンログ
- `accounts` - プレイヤーアカウント
- `queue` - マッチングキュー

詳細は `design/database.md` を参照してください。

## エラーハンドリング

- 404: リソースが見つからない
- 500: サーバーエラー

すべてのエラーは JSON 形式で返されます：

```json
{
  "error": "Error message"
}
```

## セキュリティ

- CORS: すべてのオリジンからのリクエストを許可（開発環境）
- SQLインジェクション対策: パラメータ化されたクエリを使用
- 入力検証: IDは整数に変換して検証

## 今後の拡張

- WebSocket（Socket.IO）によるリアルタイム更新
- Webクライアント（React）の実装
- 認証・認可機能
- レート制限

## 関連ドキュメント

- [Web API Documentation](../../docs/web-api.md)
- [Database Schema](../../design/database.md)
- [Web Viewer Design](../../design/web-viewer.md)
