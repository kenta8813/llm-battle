# アカウント情報・戦績確認

**このスキルは現在のアカウント情報、キャラクター一覧、戦績を確認するためのものです。**

## 使い方

### 1. アカウント情報とキャラクター一覧

```
# ログインして情報取得
result = login(username="your_username")
account_id = result["account_id"]

# キャラクター一覧
list_my_characters(account_id=account_id)
```

表示内容：
- キャラクターID
- 名前
- レベル
- ステータス（HP、攻撃、防御、速度）
- レーティング
- 戦績（総バトル数、勝利数、敗北数）

---

### 2. 特定キャラクターの詳細情報

```
get_character_info(character_id=<character_id>)
```

表示内容：
- 基本情報（名前、レベル、プロンプト）
- ステータス（基礎値と計算値）
- 習得アビリティ
- 詳細な戦績

---

### 3. 詳細な戦績

```
get_character_stats(character_id=<character_id>)
```

表示内容：
- レーティング
- ランキング順位
- 総バトル数、勝利数、敗北数、引き分け数
- 勝率
- 連勝記録（現在/最長）
- 与ダメージ/被ダメージ合計

---

### 4. リーダーボード（ランキング）

```
get_leaderboard(limit=50)
```

レーティング上位のキャラクターを確認できます。

---

### 5. バトル履歴

```
get_battle_history(character_id=<character_id>, limit=10)
```

過去のバトル履歴を確認できます（今後実装予定）。

---

## ワンライナー例

```
# 完全な状態確認
result = login(username="testuser")
account_id = result["account_id"]
characters = list_my_characters(account_id=account_id)

# 各キャラクターの詳細を確認
for char in characters:
    print(f"\n=== {char['name']} ===")
    stats = get_character_stats(character_id=char["id"])
    print(f"Rating: {stats['rating']} (Rank #{stats['rank']})")
    print(f"Record: {stats['wins']}W-{stats['losses']}L ({stats['win_rate']}%)")
```
