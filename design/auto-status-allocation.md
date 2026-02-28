# ステータス自動振り分け機能 設計書

**プロジェクト**: LLMバトルゲーム
**作成日**: 2026-02-28
**担当**: Director
**要求**: プロンプトを元にAIがステータスを自動振り分け

---

## 1. 機能概要

### 1.1 目的
キャラクター作成時、ユーザーが入力したプロンプト（キャラクター設定）を解析し、Claude APIを使用してキャラクターの性格・特性に合った基礎ステータス（HP、攻撃力、防御力、速度）を自動で振り分ける。

### 1.2 設計原則
- **シンプル性**: ユーザーはプロンプトを書くだけでキャラクターが完成
- **整合性**: プロンプトの内容とステータスが論理的に一致
- **バランス**: ゲームバランスを保ちつつ、キャラクターの個性を反映
- **後方互換性**: 手動でのステータス指定も引き続きサポート

---

## 2. システム設計

### 2.1 アーキテクチャ

```
[ユーザー入力]
  ↓
  name: "炎の戦士"
  prompt: "熱血漢で攻撃一辺倒。防御は捨てて..."
  auto_allocate: true (新規パラメータ)
  total_points: 340 (オプション、デフォルト: 340)
  ↓
[MCPツール: create_character]
  ↓
[ステータス振り分けロジック]
  ├─ 手動モード: base_hp, base_attack等が指定済み
  │   → 既存のバリデーションを実行
  │
  └─ 自動モード: auto_allocate = true
      ↓
      [Claude API呼び出し]
        - プロンプトを解析
        - キャラクター性格・戦闘スタイルを推定
        - ステータス配分を決定
      ↓
      [ステータス生成]
        - HP, 攻撃, 防御, 速度を算出
        - 制約チェック（各10-100、合計280-400）
        - 必要に応じて調整
      ↓
      [アビリティ自動選択]（オプション）
        - キャラクター性格に合ったアビリティを推奨
        - ユーザーが手動選択も可能
  ↓
[キャラクター作成]
  ↓
[完成]
```

---

## 3. MCPツール統合

### 3.1 create_character ツールの拡張

#### 変更前
```python
@mcp.tool()
async def create_character(
    account_id: int,
    name: str,
    prompt: str,
    base_hp: int,
    base_attack: int,
    base_defense: int,
    base_speed: int,
    ability_ids: list[int] = []
) -> dict:
```

#### 変更後
```python
@mcp.tool()
async def create_character(
    account_id: int,
    name: str,
    prompt: str,
    base_hp: int = None,
    base_attack: int = None,
    base_defense: int = None,
    base_speed: int = None,
    ability_ids: list[int] = None,
    auto_allocate: bool = False,
    total_points: int = 340,
    auto_select_abilities: bool = False
) -> dict:
    """
    新しいキャラクターを作成します。

    あなたはこのキャラクターとしてバトルに参加します。
    promptには、キャラクターの性格、戦闘スタイル、口調などを詳しく記述してください。

    Args:
        account_id: アカウントID
        name: キャラクター名（1-50文字）
        prompt: キャラクター設定プロンプト（50-2000文字）
        base_hp: 基礎HP（10-100）※auto_allocate=Falseの場合は必須
        base_attack: 基礎攻撃力（10-100）※auto_allocate=Falseの場合は必須
        base_defense: 基礎防御力（10-100）※auto_allocate=Falseの場合は必須
        base_speed: 基礎速度（10-100）※auto_allocate=Falseの場合は必須
        ability_ids: 習得アビリティID一覧（最大3個）
        auto_allocate: Trueの場合、プロンプトから自動でステータスを振り分け
        total_points: 自動振り分け時の合計ポイント（280-400、デフォルト340）
        auto_select_abilities: Trueの場合、アビリティも自動選択

    Returns:
        character_id: キャラクターID
        computed_stats: 計算済みステータス
        allocated_stats: 自動振り分けされた基礎ステータス（auto_allocate=Trueの場合）
        abilities: アビリティ一覧
        auto_allocation_reasoning: 自動振り分けの理由（auto_allocate=Trueの場合）
        message: 作成完了メッセージ
    """
```

### 3.2 パラメータ詳細

#### auto_allocate（bool）
- **デフォルト**: False
- **説明**: Trueの場合、base_hp等を無視してプロンプトから自動振り分け
- **動作**: Claude APIを呼び出してステータスを決定

#### total_points（int）
- **デフォルト**: 340
- **範囲**: 280-400
- **説明**: 自動振り分け時のステータス合計値
- **推奨値**:
  - 280: バランス型（各70）
  - 320: やや強め
  - 340: 標準的な特化型
  - 360: 強力な特化型
  - 400: 最大値（極端な特化）

#### auto_select_abilities（bool）
- **デフォルト**: False
- **説明**: Trueの場合、アビリティも自動選択（最大3個）
- **動作**: プロンプトとステータスに基づいて適切なアビリティを推奨

---

## 4. ステータス自動振り分けロジック

### 4.1 Claude APIプロンプト設計

```python
async def allocate_stats_with_llm(prompt: str, total_points: int) -> dict:
    """
    Claude APIを使用してステータスを自動振り分け

    Args:
        prompt: キャラクター設定プロンプト
        total_points: 合計ポイント数

    Returns:
        {
            "base_hp": int,
            "base_attack": int,
            "base_defense": int,
            "base_speed": int,
            "reasoning": str,
            "character_archetype": str
        }
    """

    system_prompt = """
あなたはゲームキャラクターのステータス設計アシスタントです。
ユーザーが入力したキャラクター設定プロンプトを解析し、
そのキャラクターの性格・戦闘スタイルに最も適したステータス配分を決定してください。

## ステータスの意味
- **HP**: 耐久力、タフネス、生命力
- **攻撃力（Attack）**: 与えるダメージの大きさ
- **防御力（Defense）**: 受けるダメージの軽減率
- **速度（Speed）**: 行動順、回避率に影響

## 制約条件
- 各ステータス: 10〜100の範囲
- 合計値: {total_points}ポイント（厳密に守る）
- 最低保証: 各ステータスは最低10以上

## キャラクタータイプの例
### タンク型（耐久重視）
- HP: 高（80-100）
- 攻撃力: 中-低（50-70）
- 防御力: 高（70-90）
- 速度: 低（30-50）
- 適性: 守護者、騎士、盾役

### アタッカー型（火力重視）
- HP: 中-低（60-80）
- 攻撃力: 高（80-100）
- 防御力: 低-中（40-60）
- 速度: 中（50-70）
- 適性: 戦士、バーサーカー、破壊者

### スピード型（速度重視）
- HP: 中-低（60-80）
- 攻撃力: 中（60-80）
- 防御力: 低（40-60）
- 速度: 高（80-100）
- 適性: 忍者、盗賊、アサシン

### テクニック型（バランス重視）
- HP: 中（65-75）
- 攻撃力: 中（65-75）
- 防御力: 中（65-75）
- 速度: 中（65-75）
- 適性: 剣士、魔法使い、万能型

### 特殊型（極端な配分）
- 一点特化や二点特化など、独自の配分
- 例: HP100, 攻撃100, 防御70, 速度30（合計300の場合）

## 回答形式
必ず以下のJSON形式で回答してください。他の文章は含めないこと。

```json
{
  "base_hp": 数値,
  "base_attack": 数値,
  "base_defense": 数値,
  "base_speed": 数値,
  "reasoning": "なぜこの配分にしたかの簡潔な説明（100文字程度）",
  "character_archetype": "キャラクタータイプ（タンク型/アタッカー型/スピード型/テクニック型/特殊型）"
}
```
"""

    user_prompt = f"""
以下のキャラクター設定プロンプトを読んで、最適なステータス配分を決定してください。

## キャラクター設定プロンプト
```
{prompt}
```

## 制約
- 合計ポイント: {total_points}
- 各ステータス: 10〜100

キャラクターの性格、戦闘スタイル、特性を考慮して、このキャラクターらしいステータス配分を提案してください。
"""

    # Claude API呼び出し
    response = await call_claude_api(
        system=system_prompt,
        user=user_prompt,
        model="claude-sonnet-4-5-20250929",
        temperature=0.3,  # 一貫性を重視
        max_tokens=500
    )

    # JSON解析
    stats = parse_json_response(response)

    # バリデーション
    validate_allocated_stats(stats, total_points)

    return stats
```

### 4.2 バリデーション・調整ロジック

```python
def validate_allocated_stats(stats: dict, expected_total: int) -> None:
    """
    自動振り分けされたステータスを検証し、必要に応じて調整

    Args:
        stats: 振り分けられたステータス
        expected_total: 期待される合計値

    Raises:
        ValidationError: バリデーション失敗時
    """
    base_hp = stats["base_hp"]
    base_attack = stats["base_attack"]
    base_defense = stats["base_defense"]
    base_speed = stats["base_speed"]

    # 各ステータスの範囲チェック
    for stat_name, value in [
        ("HP", base_hp),
        ("攻撃力", base_attack),
        ("防御力", base_defense),
        ("速度", base_speed)
    ]:
        if not (10 <= value <= 100):
            raise ValidationError(
                f"自動振り分けエラー: {stat_name}が範囲外です（{value}）。"
                f"10〜100の範囲で設定してください。"
            )

    # 合計値チェック
    total = base_hp + base_attack + base_defense + base_speed

    if total != expected_total:
        # 許容範囲（±2ポイント）なら自動調整
        diff = expected_total - total

        if abs(diff) <= 2:
            # 速度を調整（最も調整の影響が少ないため）
            stats["base_speed"] += diff

            # 調整後の再チェック
            if not (10 <= stats["base_speed"] <= 100):
                raise ValidationError(
                    f"自動振り分けエラー: 合計値調整に失敗しました。"
                    f"期待値: {expected_total}, 実際: {total}"
                )
        else:
            raise ValidationError(
                f"自動振り分けエラー: 合計値が期待値と大きく異なります。"
                f"期待値: {expected_total}, 実際: {total}"
            )

    # 280-400の範囲内であることを確認
    if not (280 <= total <= 400):
        raise ValidationError(
            f"ステータス合計値は280-400の範囲で指定してください（現在: {total}）"
        )
```

### 4.3 リトライ機能

```python
async def allocate_stats_with_retry(
    prompt: str,
    total_points: int,
    max_retries: int = 3
) -> dict:
    """
    リトライ機能付きステータス振り分け

    Claude APIの応答が不正な場合、最大3回まで再試行
    """
    for attempt in range(max_retries):
        try:
            stats = await allocate_stats_with_llm(prompt, total_points)
            validate_allocated_stats(stats, total_points)
            return stats

        except (ValidationError, JSONDecodeError) as e:
            logger.warning(
                f"ステータス振り分け失敗（試行{attempt + 1}/{max_retries}）: {e}"
            )

            if attempt == max_retries - 1:
                # 最終手段: デフォルト値を使用
                logger.error("ステータス自動振り分けに失敗。デフォルト値を使用します。")
                return get_default_allocation(total_points)

            # 少し待ってから再試行
            await asyncio.sleep(1)

    # ここには到達しないはず
    return get_default_allocation(total_points)


def get_default_allocation(total_points: int) -> dict:
    """
    デフォルトのステータス配分（バランス型）

    Args:
        total_points: 合計ポイント

    Returns:
        均等配分されたステータス
    """
    base_value = total_points // 4
    remainder = total_points % 4

    return {
        "base_hp": base_value + (1 if remainder > 0 else 0),
        "base_attack": base_value + (1 if remainder > 1 else 0),
        "base_defense": base_value + (1 if remainder > 2 else 0),
        "base_speed": base_value,
        "reasoning": "API呼び出しに失敗したため、デフォルトのバランス型配分を使用しました。",
        "character_archetype": "バランス型"
    }
```

---

## 5. アビリティ自動選択

### 5.1 アビリティ推奨ロジック

```python
async def auto_select_abilities(
    prompt: str,
    allocated_stats: dict,
    max_abilities: int = 3
) -> list[int]:
    """
    キャラクター設定とステータスに基づいてアビリティを自動選択

    Args:
        prompt: キャラクター設定プロンプト
        allocated_stats: 振り分けられたステータス
        max_abilities: 最大選択数（デフォルト3）

    Returns:
        選択されたアビリティIDのリスト
    """

    # 利用可能なアビリティを取得
    available_abilities = get_all_abilities()

    system_prompt = """
あなたはゲームキャラクターのアビリティ選択アシスタントです。
キャラクター設定プロンプトと振り分けられたステータスを基に、
最も適したアビリティを選択してください。

## アビリティ選択の原則
1. キャラクターの戦闘スタイルに合ったアビリティを選ぶ
2. ステータス配分と相性の良いアビリティを選ぶ
3. 最大3個まで選択可能
4. バランスを考慮（攻撃・防御・補助のバランス）

## ステータスとの相性
- 高HP・高防御 → 防御系アビリティ、カウンター系
- 高攻撃 → 攻撃系アビリティ、必殺技
- 高速度 → 連続攻撃、回避系
- バランス型 → 回復、弱体化などの補助系

## 回答形式
選択したアビリティのIDを配列で返してください。

```json
{
  "ability_ids": [1, 3, 4],
  "reasoning": "選択理由の簡潔な説明"
}
```
"""

    user_prompt = f"""
以下のキャラクター設定とステータスに基づいて、最適なアビリティを選択してください。

## キャラクター設定プロンプト
```
{prompt}
```

## 振り分けられたステータス
- HP: {allocated_stats["base_hp"]}
- 攻撃力: {allocated_stats["base_attack"]}
- 防御力: {allocated_stats["base_defense"]}
- 速度: {allocated_stats["base_speed"]}
- タイプ: {allocated_stats["character_archetype"]}

## 利用可能なアビリティ
{format_abilities_for_prompt(available_abilities)}

最大3個まで選択してください。
"""

    response = await call_claude_api(
        system=system_prompt,
        user=user_prompt,
        model="claude-sonnet-4-5-20250929",
        temperature=0.3,
        max_tokens=300
    )

    result = parse_json_response(response)
    ability_ids = result["ability_ids"]

    # バリデーション
    if len(ability_ids) > max_abilities:
        ability_ids = ability_ids[:max_abilities]

    return ability_ids


def format_abilities_for_prompt(abilities: list[dict]) -> str:
    """
    アビリティリストをプロンプト用にフォーマット
    """
    formatted = []
    for ability in abilities:
        formatted.append(
            f"- ID {ability['id']}: {ability['name']} "
            f"({ability['effect_type']}) - {ability['description']}"
        )
    return "\n".join(formatted)
```

---

## 6. 実装フロー

### 6.1 create_character関数の処理フロー

```python
async def create_character(
    conn: sqlite3.Connection,
    account_id: int,
    name: str,
    prompt: str,
    base_hp: int = None,
    base_attack: int = None,
    base_defense: int = None,
    base_speed: int = None,
    ability_ids: list[int] = None,
    auto_allocate: bool = False,
    total_points: int = 340,
    auto_select_abilities: bool = False
) -> dict:
    """
    キャラクター作成（自動振り分け対応版）
    """
    try:
        # 基本バリデーション
        validate_character_name(name)
        validate_prompt(prompt)

        # ステータス決定
        if auto_allocate:
            # 自動振り分けモード
            logger.info(f"ステータス自動振り分け開始: total_points={total_points}")

            allocated = await allocate_stats_with_retry(prompt, total_points)

            base_hp = allocated["base_hp"]
            base_attack = allocated["base_attack"]
            base_defense = allocated["base_defense"]
            base_speed = allocated["base_speed"]

            allocation_info = {
                "reasoning": allocated["reasoning"],
                "character_archetype": allocated["character_archetype"]
            }
        else:
            # 手動モード
            if any(stat is None for stat in [base_hp, base_attack, base_defense, base_speed]):
                raise ValidationError(
                    "auto_allocate=Falseの場合、base_hp, base_attack, base_defense, "
                    "base_speedを全て指定してください。"
                )

            validate_base_stats(base_hp, base_attack, base_defense, base_speed)
            allocation_info = None

        # アビリティ決定
        if auto_select_abilities:
            logger.info("アビリティ自動選択開始")

            allocated_stats = {
                "base_hp": base_hp,
                "base_attack": base_attack,
                "base_defense": base_defense,
                "base_speed": base_speed,
                "character_archetype": allocation_info.get("character_archetype", "不明")
                    if allocation_info else "不明"
            }

            ability_ids = await auto_select_abilities(prompt, allocated_stats)
        else:
            if ability_ids is None:
                ability_ids = []

        validate_ability_ids(conn, ability_ids)

        # ステータス計算
        level = 1
        computed_stats = compute_stats(base_hp, base_attack, base_defense, base_speed, level)

        # データベースに保存（既存のロジック）
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO characters (
                account_id, name, prompt, level,
                base_hp, base_attack, base_defense, base_speed,
                computed_hp, computed_attack, computed_defense, computed_speed,
                created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            (
                account_id, name, prompt, level,
                base_hp, base_attack, base_defense, base_speed,
                computed_stats["hp"], computed_stats["attack"],
                computed_stats["defense"], computed_stats["speed"]
            )
        )
        character_id = cursor.lastrowid

        # 戦績初期化
        cursor.execute(
            "INSERT INTO stats (character_id) VALUES (?)",
            (character_id,)
        )

        # アビリティ設定（既存のロジック）
        abilities = []
        if ability_ids:
            for ability_id in ability_ids:
                cursor.execute(
                    "INSERT INTO character_abilities (character_id, ability_id) VALUES (?, ?)",
                    (character_id, ability_id)
                )

            placeholders = ','.join('?' * len(ability_ids))
            cursor.execute(
                f"SELECT id, name, description, effect_type, power FROM abilities WHERE id IN ({placeholders})",
                ability_ids
            )

            for row in cursor.fetchall():
                abilities.append({
                    "id": row[0],
                    "name": row[1],
                    "description": row[2],
                    "effect_type": row[3],
                    "power": row[4]
                })

        conn.commit()

        # レスポンス構築
        response = {
            "character_id": character_id,
            "computed_stats": computed_stats,
            "abilities": abilities,
            "message": f"キャラクター「{name}」が作成されました"
        }

        # 自動振り分けの場合は追加情報を返す
        if auto_allocate and allocation_info:
            response["allocated_stats"] = {
                "base_hp": base_hp,
                "base_attack": base_attack,
                "base_defense": base_defense,
                "base_speed": base_speed
            }
            response["auto_allocation_reasoning"] = allocation_info["reasoning"]
            response["character_archetype"] = allocation_info["character_archetype"]

        return response

    except ValidationError:
        raise
    except sqlite3.Error as e:
        conn.rollback()
        raise DatabaseError(f"データベースエラー: {e}")
```

---

## 7. エラーハンドリング

### 7.1 エラーシナリオと対処

| エラーシナリオ | 対処方法 |
|-------------|---------|
| Claude API呼び出し失敗 | 3回リトライ、失敗時はデフォルト配分（バランス型） |
| JSON解析エラー | リトライ、最終的にデフォルト配分 |
| ステータス範囲外（10未満 or 100超） | エラーメッセージを返してリトライ |
| 合計値が期待値と異なる | ±2ポイントなら自動調整、それ以上ならリトライ |
| プロンプト解釈失敗 | デフォルト配分を使用し、ユーザーに通知 |
| アビリティ選択失敗 | アビリティなしでキャラクター作成、後から追加可能 |

### 7.2 ユーザーへのフィードバック

```python
# 自動振り分け成功時
{
    "message": "キャラクター「炎の戦士」が作成されました",
    "auto_allocation_reasoning": "熱血漢で攻撃重視のキャラクター性から、高攻撃・低防御のアタッカー型として設計しました。",
    "character_archetype": "アタッカー型",
    "allocated_stats": {
        "base_hp": 70,
        "base_attack": 95,
        "base_defense": 50,
        "base_speed": 65
    }
}

# デフォルト配分使用時
{
    "message": "キャラクター「炎の戦士」が作成されました（ステータスは標準配分を使用）",
    "auto_allocation_reasoning": "プロンプト解析に時間がかかったため、バランス型の標準配分を使用しました。後でステータスを調整できます。",
    "character_archetype": "バランス型",
    "allocated_stats": {
        "base_hp": 85,
        "base_attack": 85,
        "base_defense": 85,
        "base_speed": 85
    }
}
```

---

## 8. テスト戦略

### 8.1 ユニットテスト

```python
# test_auto_allocation.py

import pytest
from unittest.mock import patch, AsyncMock

@pytest.mark.asyncio
async def test_allocate_stats_basic():
    """基本的なステータス振り分けテスト"""
    prompt = "勇敢な戦士。攻撃力が高く、防御は苦手。"
    total_points = 340

    result = await allocate_stats_with_llm(prompt, total_points)

    assert 10 <= result["base_hp"] <= 100
    assert 10 <= result["base_attack"] <= 100
    assert 10 <= result["base_defense"] <= 100
    assert 10 <= result["base_speed"] <= 100

    total = (result["base_hp"] + result["base_attack"] +
             result["base_defense"] + result["base_speed"])
    assert total == total_points

    # 攻撃力が他より高いことを期待
    assert result["base_attack"] >= result["base_defense"]


@pytest.mark.asyncio
async def test_allocate_stats_tank_type():
    """タンク型キャラクターのテスト"""
    prompt = "鋼鉄の守護者。誰よりも硬く、仲間を守る盾となる。"
    total_points = 340

    result = await allocate_stats_with_llm(prompt, total_points)

    # HPと防御が高いことを期待
    assert result["base_hp"] >= 70
    assert result["base_defense"] >= 70


@pytest.mark.asyncio
async def test_allocate_stats_validation_error():
    """バリデーションエラーのテスト"""
    stats = {
        "base_hp": 150,  # 範囲外
        "base_attack": 50,
        "base_defense": 50,
        "base_speed": 50
    }

    with pytest.raises(ValidationError):
        validate_allocated_stats(stats, 300)


@pytest.mark.asyncio
async def test_allocate_stats_with_retry():
    """リトライ機能のテスト"""
    prompt = "テストキャラクター"
    total_points = 340

    # Claude APIをモック化し、1回目は失敗、2回目は成功
    with patch('server.tools.character.allocate_stats_with_llm') as mock:
        mock.side_effect = [
            ValidationError("合計値が不正"),
            {
                "base_hp": 85,
                "base_attack": 85,
                "base_defense": 85,
                "base_speed": 85,
                "reasoning": "テスト",
                "character_archetype": "バランス型"
            }
        ]

        result = await allocate_stats_with_retry(prompt, total_points, max_retries=3)

        assert result["base_hp"] == 85
        assert mock.call_count == 2  # 2回呼ばれた


@pytest.mark.asyncio
async def test_default_allocation():
    """デフォルト配分のテスト"""
    result = get_default_allocation(340)

    total = (result["base_hp"] + result["base_attack"] +
             result["base_defense"] + result["base_speed"])
    assert total == 340

    # 各ステータスがほぼ均等であることを確認
    values = [result["base_hp"], result["base_attack"],
              result["base_defense"], result["base_speed"]]
    assert max(values) - min(values) <= 1


@pytest.mark.asyncio
async def test_auto_select_abilities():
    """アビリティ自動選択のテスト"""
    prompt = "素早い暗殺者"
    allocated_stats = {
        "base_hp": 60,
        "base_attack": 90,
        "base_defense": 50,
        "base_speed": 100,
        "character_archetype": "スピード型"
    }

    ability_ids = await auto_select_abilities(prompt, allocated_stats)

    assert len(ability_ids) <= 3
    assert all(isinstance(id, int) for id in ability_ids)
```

### 8.2 統合テスト

```python
@pytest.mark.asyncio
async def test_create_character_auto_allocate(test_db):
    """キャラクター作成の統合テスト（自動振り分け）"""
    conn = test_db

    # アカウント作成
    cursor = conn.cursor()
    cursor.execute("INSERT INTO accounts (username) VALUES (?)", ("test_user",))
    account_id = cursor.lastrowid
    conn.commit()

    # キャラクター作成（自動振り分け）
    result = await create_character(
        conn=conn,
        account_id=account_id,
        name="炎の戦士",
        prompt="熱血漢で攻撃一辺倒。防御は二の次で、とにかく攻めまくる戦闘スタイル。",
        auto_allocate=True,
        total_points=340,
        auto_select_abilities=True
    )

    # 結果検証
    assert result["character_id"] > 0
    assert "allocated_stats" in result
    assert "auto_allocation_reasoning" in result
    assert "character_archetype" in result

    stats = result["allocated_stats"]
    total = stats["base_hp"] + stats["base_attack"] + stats["base_defense"] + stats["base_speed"]
    assert total == 340

    # データベース確認
    cursor.execute("SELECT base_hp, base_attack, base_defense, base_speed FROM characters WHERE id = ?",
                   (result["character_id"],))
    row = cursor.fetchone()
    assert row is not None
    assert row[0] == stats["base_hp"]
    assert row[1] == stats["base_attack"]


@pytest.mark.asyncio
async def test_create_character_manual_mode(test_db):
    """キャラクター作成の統合テスト（手動モード）"""
    conn = test_db

    cursor = conn.cursor()
    cursor.execute("INSERT INTO accounts (username) VALUES (?)", ("test_user2",))
    account_id = cursor.lastrowid
    conn.commit()

    # キャラクター作成（手動）
    result = await create_character(
        conn=conn,
        account_id=account_id,
        name="鋼の守護者",
        prompt="仲間を守る盾",
        base_hp=90,
        base_attack=60,
        base_defense=85,
        base_speed=45,
        auto_allocate=False
    )

    # 自動振り分け情報が含まれていないことを確認
    assert "allocated_stats" not in result
    assert "auto_allocation_reasoning" not in result
```

### 8.3 実プロンプトテスト

様々なプロンプトでの振り分け結果を検証:

| プロンプト例 | 期待されるタイプ | 期待される特徴 |
|------------|---------------|--------------|
| "勇敢な騎士。仲間を守る盾となる。" | タンク型 | HP高、防御高、速度低 |
| "俺は最強。全てを破壊する。" | アタッカー型 | 攻撃力極大、防御低 |
| "影に潜む暗殺者。誰よりも速く。" | スピード型 | 速度極大、HP低 |
| "賢者。バランスの取れた戦い方。" | テクニック型 | 全ステータス均等 |
| "不死身の化け物。倒れない。" | タンク型 | HP極大、攻撃中 |

---

## 9. パフォーマンス最適化

### 9.1 キャッシュ戦略

```python
from functools import lru_cache
import hashlib

# プロンプトのハッシュをキーとしてキャッシュ
@lru_cache(maxsize=100)
def get_cached_allocation(prompt_hash: str, total_points: int) -> dict:
    """
    同じプロンプトの場合、キャッシュから取得
    （開発・テスト用、本番では無効化推奨）
    """
    pass


def hash_prompt(prompt: str) -> str:
    """プロンプトのハッシュ値を計算"""
    return hashlib.sha256(prompt.encode()).hexdigest()
```

### 9.2 並列処理

```python
async def create_character_fast(
    conn: sqlite3.Connection,
    account_id: int,
    name: str,
    prompt: str,
    auto_allocate: bool = True,
    total_points: int = 340,
    auto_select_abilities: bool = True
) -> dict:
    """
    ステータス振り分けとアビリティ選択を並列実行
    """

    if auto_allocate:
        # ステータス振り分けとアビリティ選択を並列実行
        stats_task = allocate_stats_with_retry(prompt, total_points)

        if auto_select_abilities:
            # 仮のステータスを使ってアビリティ選択を先に開始
            # （実際のステータスは後で差し替え）
            abilities_task = auto_select_abilities(
                prompt,
                get_default_allocation(total_points)
            )

            stats, ability_ids = await asyncio.gather(stats_task, abilities_task)
        else:
            stats = await stats_task
            ability_ids = []

        # 以降は通常フロー
        # ...
```

---

## 10. 後方互換性

### 10.1 既存のツール呼び出し

既存のクライアントが手動でステータスを指定する場合、従来通り動作します:

```python
# 従来の呼び出し方（引き続きサポート）
create_character(
    account_id=1,
    name="戦士",
    prompt="勇敢な戦士",
    base_hp=80,
    base_attack=90,
    base_defense=60,
    base_speed=70
)
```

### 10.2 新しい呼び出し方

自動振り分けを利用する場合:

```python
# 新しい呼び出し方（自動振り分け）
create_character(
    account_id=1,
    name="戦士",
    prompt="勇敢な戦士。攻撃力が高く、前線で戦う。",
    auto_allocate=True,
    total_points=340  # オプション
)

# アビリティも自動選択
create_character(
    account_id=1,
    name="戦士",
    prompt="勇敢な戦士。攻撃力が高く、前線で戦う。",
    auto_allocate=True,
    auto_select_abilities=True
)
```

---

## 11. 将来の拡張

### 11.1 ステータス調整機能

キャラクター作成後、一定の条件下でステータスを再配分できる機能:

```python
@mcp.tool()
async def reallocate_stats(
    character_id: int,
    new_total_points: int = None
) -> dict:
    """
    既存キャラクターのステータスを再配分

    制約:
    - レベル1かつバトル未参加のキャラクターのみ
    - 1キャラクターにつき1回まで
    """
```

### 11.2 プリセット配分

よくある配分パターンをプリセットとして提供:

```python
PRESET_ALLOCATIONS = {
    "tank": {"hp": 100, "attack": 60, "defense": 80, "speed": 40},
    "attacker": {"hp": 70, "attack": 100, "defense": 50, "speed": 60},
    "speedster": {"hp": 70, "attack": 70, "defense": 50, "speed": 90},
    "balanced": {"hp": 70, "attack": 70, "defense": 70, "speed": 70}
}
```

### 11.3 ユーザーフィードバック学習

ユーザーが自動振り分け結果を修正した場合、そのパターンを学習:

```python
async def learn_from_user_adjustment(
    original_allocation: dict,
    user_adjustment: dict,
    prompt: str
) -> None:
    """
    ユーザーの調整を学習し、将来の振り分けに反映
    （機械学習的アプローチ、将来実装）
    """
```

---

## 12. セキュリティ考慮事項

### 12.1 プロンプトインジェクション対策

```python
def sanitize_prompt(prompt: str) -> str:
    """
    プロンプトインジェクション攻撃を防ぐためのサニタイズ

    - 極端に長いプロンプトを制限
    - 特殊な制御文字を除去
    - システムプロンプト汚染を防ぐ
    """
    # 長さ制限
    if len(prompt) > 2000:
        prompt = prompt[:2000]

    # 特殊文字除去（改行は許可）
    # APIインジェクション文字列のパターンマッチング
    dangerous_patterns = [
        r"```.*?system.*?```",
        r"<\|system\|>",
        r"IGNORE PREVIOUS INSTRUCTIONS"
    ]

    for pattern in dangerous_patterns:
        if re.search(pattern, prompt, re.IGNORECASE | re.DOTALL):
            raise ValidationError("不正なプロンプトが検出されました")

    return prompt
```

### 12.2 レート制限

```python
# ユーザーごとの自動振り分け回数制限
MAX_AUTO_ALLOCATIONS_PER_DAY = 50

async def check_rate_limit(account_id: int) -> None:
    """
    1日あたりの自動振り分け回数をチェック
    """
    today_count = get_auto_allocation_count_today(account_id)

    if today_count >= MAX_AUTO_ALLOCATIONS_PER_DAY:
        raise ValidationError(
            f"1日あたりの自動振り分け回数の上限（{MAX_AUTO_ALLOCATIONS_PER_DAY}回）に達しました"
        )
```

---

## 13. ログ・デバッグ

### 13.1 ログ出力

```python
logger.info(f"ステータス自動振り分け開始: prompt={prompt[:50]}..., total_points={total_points}")
logger.info(f"振り分け結果: HP={stats['base_hp']}, ATK={stats['base_attack']}, DEF={stats['base_defense']}, SPD={stats['base_speed']}")
logger.info(f"タイプ: {stats['character_archetype']}, 理由: {stats['reasoning']}")
```

### 13.2 デバッグモード

```python
DEBUG_MODE = os.getenv("DEBUG_AUTO_ALLOCATION", "false").lower() == "true"

if DEBUG_MODE:
    # Claude APIの詳細なリクエスト/レスポンスをログ出力
    logger.debug(f"Claude API Request: {api_request}")
    logger.debug(f"Claude API Response: {api_response}")
```

---

## 14. 設計承認チェックリスト

- [x] 既存の仕様との整合性確認
- [x] 後方互換性の確保
- [x] エラーハンドリングの網羅性
- [x] テスト戦略の策定
- [x] パフォーマンス最適化の検討
- [x] セキュリティ考慮事項の洗い出し
- [x] ユーザーエクスペリエンスの向上
- [x] 実装可能性の確認

---

## 15. 関連ドキュメント

- [システムアーキテクチャ](./architecture.md)
- [データベース設計](./database.md)
- [MCPサーバー設計](./mcp-server.md)
- [バトルロジック設計](./battle-logic.md)

---

## 16. 次のステップ

1. **実装フェーズ**:
   - `src/server/tools/character.py` の拡張
   - `src/server/llm/` ディレクトリに `allocator.py` を作成
   - Claude API呼び出しロジックの実装

2. **テスト**:
   - ユニットテストの作成
   - 統合テストの実行
   - 実プロンプトでの動作確認

3. **ドキュメント更新**:
   - `mcp-server.md` のツール定義を更新
   - ユーザーガイドの作成

---

**設計承認**: 待機中
**設計者**: Director
**レビュー**: PM, PO
