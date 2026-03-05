"""
キャラクター管理ツール（API経由）
LLM呼び出しはローカルで実行し、結果をAPIに送信
"""

import logging
from typing import Dict, Any, List, Optional

from ..api_client import ApiClient
from ..errors import ValidationError

logger = logging.getLogger(__name__)


# グローバルインスタンス（main.pyで初期化される）
_api_client: ApiClient = None


def set_api_client(client: ApiClient):
    """Set API client instance"""
    global _api_client
    _api_client = client


# Validation functions removed - API handles validation
# We keep only local LLM logic


def create_character(
    account_id: int,
    name: str,
    prompt: str,
    base_hp: int,
    base_attack: int,
    base_defense: int,
    base_speed: int,
    ability_ids: Optional[List[int]] = None
) -> Dict[str, Any]:
    """
    新しいキャラクターを作成します（API経由）

    ステータスとアビリティは呼び出し側（Claude Desktop）が判断して指定します。
    プロンプトを読んで、キャラクターに合ったステータス配分とアビリティを選んでください。

    Args:
        account_id: アカウントID
        name: キャラクター名（1-50文字）
        prompt: キャラクター設定プロンプト（50-2000文字）
        base_hp: 基礎HP（10-100）
        base_attack: 基礎攻撃力（10-100）
        base_defense: 基礎防御力（10-100）
        base_speed: 基礎速度（10-100）
        ability_ids: 習得アビリティID一覧（最大3個）

    ステータス配分ルール:
        - 合計: 280-400ポイント（推奨340）
        - 各ステータス: 10-100の範囲

    Returns:
        character_id: キャラクターID
        computed_stats: 計算済みステータス（レベル1時点）
        abilities: 習得したアビリティ一覧
        message: 作成完了メッセージ

    Raises:
        ValidationError: バリデーションエラー
    """
    if not _api_client:
        raise RuntimeError("API client not initialized")

    if ability_ids is None:
        ability_ids = []

    # APIにキャラクター作成を依頼
    result = _api_client.create_character(
        account_id=account_id,
        name=name,
        prompt=prompt,
        base_hp=base_hp,
        base_attack=base_attack,
        base_defense=base_defense,
        base_speed=base_speed,
        ability_ids=ability_ids
    )

    return result


def get_character_info(character_id: int) -> Dict[str, Any]:
    """
    指定したキャラクターの詳細情報を取得します（API経由）

    Args:
        character_id: キャラクターID

    Returns:
        キャラクターの全情報（名前、ステータス、アビリティ、戦績など）

    Raises:
        ValidationError: キャラクターが存在しない場合
    """
    if not _api_client:
        raise RuntimeError("API client not initialized")

    return _api_client.get_character(character_id)


def list_my_characters(account_id: int) -> List[Dict[str, Any]]:
    """
    あなたが作成したキャラクター一覧を取得します（API経由）

    Args:
        account_id: アカウントID

    Returns:
        キャラクター一覧
    """
    if not _api_client:
        raise RuntimeError("API client not initialized")

    result = _api_client.list_characters(account_id)
    return result.get('characters', [])


def list_abilities() -> List[Dict[str, Any]]:
    """
    キャラクター作成時に選択できるアビリティの一覧を取得します（API経由）

    Returns:
        アビリティ一覧（名前、説明、効果、威力など）
    """
    if not _api_client:
        raise RuntimeError("API client not initialized")

    result = _api_client.list_abilities()
    return result.get('abilities', [])
