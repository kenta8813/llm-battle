"""
ステータス自動振り分けモジュール

Claude APIを使用してキャラクタープロンプトからステータスを自動振り分けする機能を提供します。
"""

import os
import re
import json
import asyncio
import logging
import time
from typing import Dict, List, Optional
from json import JSONDecodeError

from ..errors import ValidationError

logger = logging.getLogger(__name__)

# レート制限用（簡易版：メモリ上のカウンタ）
_rate_limit_counter = {}
_rate_limit_window_start = time.time()
MAX_REQUESTS_PER_MINUTE = 50


def check_rate_limit() -> None:
    """
    APIレート制限をチェック（簡易版）

    Raises:
        ValidationError: レート制限を超えた場合
    """
    global _rate_limit_counter, _rate_limit_window_start

    current_time = time.time()

    # 1分経過したらカウンタをリセット
    if current_time - _rate_limit_window_start >= 60:
        _rate_limit_counter = {}
        _rate_limit_window_start = current_time

    # カウンタを増加
    count = _rate_limit_counter.get('global', 0)

    if count >= MAX_REQUESTS_PER_MINUTE:
        raise ValidationError(
            f"APIレート制限に達しました。1分あたり最大{MAX_REQUESTS_PER_MINUTE}回まで。"
        )

    _rate_limit_counter['global'] = count + 1


def sanitize_prompt(prompt: str) -> str:
    """
    プロンプトインジェクション攻撃を防ぐためのサニタイズ

    Args:
        prompt: サニタイズするプロンプト

    Returns:
        サニタイズされたプロンプト

    Raises:
        ValidationError: 不正なプロンプトが検出された場合
    """
    # 長さ制限
    if len(prompt) > 2000:
        prompt = prompt[:2000]

    # 危険なパターンをチェック
    dangerous_patterns = [
        r"```.*?system.*?```",
        r"<\|system\|>",
        r"IGNORE PREVIOUS INSTRUCTIONS"
    ]

    for pattern in dangerous_patterns:
        if re.search(pattern, prompt, re.IGNORECASE | re.DOTALL):
            raise ValidationError("不正なプロンプトが検出されました")

    return prompt


async def call_claude_api(
    system: str,
    user: str,
    model: str = "claude-sonnet-4-5-20250929",
    temperature: float = 0.3,
    max_tokens: int = 500
) -> str:
    """
    Claude APIを呼び出すヘルパー関数

    Args:
        system: システムプロンプト
        user: ユーザープロンプト
        model: 使用するモデル
        temperature: 温度パラメータ
        max_tokens: 最大トークン数

    Returns:
        APIレスポンステキスト

    Raises:
        Exception: API呼び出し失敗時
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")

    if not api_key:
        logger.warning("ANTHROPIC_API_KEY が設定されていません。デフォルト配分を使用します。")
        raise Exception("ANTHROPIC_API_KEY が設定されていません")

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)

        # タイムアウト30秒を設定
        message = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=[{"role": "user", "content": user}],
            timeout=30.0
        )

        response_text = message.content[0].text
        return response_text

    except ImportError:
        logger.error("anthropic パッケージがインストールされていません。pip install anthropic を実行してください。")
        raise Exception("anthropic パッケージがインストールされていません")
    except Exception as e:
        logger.error(f"Claude API呼び出しエラー: {e}")
        raise


def parse_json_response(response: str) -> dict:
    """
    JSON形式のレスポンスを解析

    Args:
        response: JSONレスポンステキスト

    Returns:
        解析されたデータ

    Raises:
        JSONDecodeError: JSON解析エラー
    """
    # JSONブロックを抽出（```json ... ``` の形式に対応）
    json_match = re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL)
    if json_match:
        json_str = json_match.group(1)
    else:
        # 直接JSONが返ってきた場合
        json_str = response.strip()

    return json.loads(json_str)


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
    final_total = stats["base_hp"] + stats["base_attack"] + stats["base_defense"] + stats["base_speed"]
    if not (280 <= final_total <= 400):
        raise ValidationError(
            f"ステータス合計値は280-400の範囲で指定してください（現在: {final_total}）"
        )


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

    Raises:
        ValidationError: バリデーションエラー
        Exception: API呼び出しエラー
    """
    # プロンプトをサニタイズ
    sanitized_prompt = sanitize_prompt(prompt)

    # レート制限チェック
    check_rate_limit()

    system_prompt = f"""
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
{{
  "base_hp": 数値,
  "base_attack": 数値,
  "base_defense": 数値,
  "base_speed": 数値,
  "reasoning": "なぜこの配分にしたかの簡潔な説明（100文字程度）",
  "character_archetype": "キャラクタータイプ（タンク型/アタッカー型/スピード型/テクニック型/特殊型）"
}}
```
"""

    user_prompt = f"""
以下のキャラクター設定プロンプトを読んで、最適なステータス配分を決定してください。

## キャラクター設定プロンプト
```
{sanitized_prompt}
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
        temperature=0.3,
        max_tokens=500
    )

    # JSON解析
    stats = parse_json_response(response)

    # バリデーション
    validate_allocated_stats(stats, total_points)

    return stats


async def allocate_stats_with_retry(
    prompt: str,
    total_points: int,
    max_retries: int = 3
) -> dict:
    """
    リトライ機能付きステータス振り分け

    Claude APIの応答が不正な場合、最大3回まで再試行

    Args:
        prompt: キャラクター設定プロンプト
        total_points: 合計ポイント数
        max_retries: 最大リトライ回数

    Returns:
        振り分けられたステータス
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

        except Exception as e:
            # API呼び出しエラー（APIキー未設定など）はリトライせずにデフォルト値を返す
            logger.error(f"API呼び出しエラー: {e}")
            return get_default_allocation(total_points)

    # ここには到達しないはず
    return get_default_allocation(total_points)


def format_abilities_for_prompt(abilities: List[dict]) -> str:
    """
    アビリティリストをプロンプト用にフォーマット

    Args:
        abilities: アビリティリスト

    Returns:
        フォーマットされたアビリティ情報
    """
    formatted = []
    for ability in abilities:
        formatted.append(
            f"- ID {ability['id']}: {ability['name']} "
            f"({ability['effect_type']}) - {ability['description']}"
        )
    return "\n".join(formatted)


async def auto_select_abilities(
    prompt: str,
    allocated_stats: dict,
    available_abilities: List[dict],
    max_abilities: int = 3
) -> List[int]:
    """
    キャラクター設定とステータスに基づいてアビリティを自動選択

    Args:
        prompt: キャラクター設定プロンプト
        allocated_stats: 振り分けられたステータス
        available_abilities: 利用可能なアビリティのリスト
        max_abilities: 最大選択数（デフォルト3）

    Returns:
        選択されたアビリティIDのリスト
    """
    # プロンプトをサニタイズ
    sanitized_prompt = sanitize_prompt(prompt)

    # レート制限チェック
    check_rate_limit()

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
{sanitized_prompt}
```

## 振り分けられたステータス
- HP: {allocated_stats["base_hp"]}
- 攻撃力: {allocated_stats["base_attack"]}
- 防御力: {allocated_stats["base_defense"]}
- 速度: {allocated_stats["base_speed"]}
- タイプ: {allocated_stats.get("character_archetype", "不明")}

## 利用可能なアビリティ
{format_abilities_for_prompt(available_abilities)}

最大3個まで選択してください。
"""

    try:
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

    except Exception as e:
        logger.error(f"アビリティ自動選択エラー: {e}")
        # エラー時は空のリストを返す
        return []
