"""
キャラクター管理ツール
"""

import sqlite3
import logging
from typing import Dict, Any, List, Optional

from ..errors import ValidationError, DatabaseError

logger = logging.getLogger(__name__)


def validate_character_name(name: str) -> None:
    """
    キャラクター名のバリデーション

    Args:
        name: 検証するキャラクター名

    Raises:
        ValidationError: バリデーションエラー
    """
    if not name:
        raise ValidationError("キャラクター名を入力してください")

    if len(name) < 1 or len(name) > 50:
        raise ValidationError("キャラクター名は1-50文字で入力してください")


def validate_prompt(prompt: str) -> None:
    """
    キャラクター設定プロンプトのバリデーション

    Args:
        prompt: 検証するプロンプト

    Raises:
        ValidationError: バリデーションエラー
    """
    if not prompt:
        raise ValidationError("キャラクター設定プロンプトを入力してください")

    if len(prompt) < 50:
        raise ValidationError("キャラクター設定プロンプトは50文字以上で入力してください")

    if len(prompt) > 2000:
        raise ValidationError("キャラクター設定プロンプトは2000文字以内で入力してください")


def validate_base_stats(base_hp: int, base_attack: int, base_defense: int, base_speed: int) -> None:
    """
    基礎ステータスのバリデーション

    Args:
        base_hp: 基礎HP
        base_attack: 基礎攻撃力
        base_defense: 基礎防御力
        base_speed: 基礎速度

    Raises:
        ValidationError: バリデーションエラー
    """
    # ステータス合計値チェック（個別値チェックより先に実行）
    total = base_hp + base_attack + base_defense + base_speed
    if not (280 <= total <= 400):
        raise ValidationError(
            f"ステータスの合計値は280-400の範囲で指定してください（現在: {total}）"
        )

    # 各ステータスの範囲チェック
    if not (10 <= base_hp <= 100):
        raise ValidationError("基礎HPは10-100の範囲で指定してください")
    if not (10 <= base_attack <= 100):
        raise ValidationError("基礎攻撃力は10-100の範囲で指定してください")
    if not (10 <= base_defense <= 100):
        raise ValidationError("基礎防御力は10-100の範囲で指定してください")
    if not (10 <= base_speed <= 100):
        raise ValidationError("基礎速度は10-100の範囲で指定してください")


def validate_ability_ids(conn: sqlite3.Connection, ability_ids: List[int]) -> None:
    """
    アビリティIDリストのバリデーション

    Args:
        conn: データベース接続
        ability_ids: アビリティIDリスト

    Raises:
        ValidationError: バリデーションエラー
    """
    if len(ability_ids) > 3:
        raise ValidationError("アビリティは最大3個まで選択できます")

    # アビリティIDの重複チェック
    if len(ability_ids) != len(set(ability_ids)):
        raise ValidationError("同じアビリティを複数選択することはできません")

    # アビリティが存在するかチェック
    if ability_ids:
        cursor = conn.cursor()
        placeholders = ','.join('?' * len(ability_ids))
        cursor.execute(
            f"SELECT id FROM abilities WHERE id IN ({placeholders})",
            ability_ids
        )
        existing_ids = {row[0] for row in cursor.fetchall()}

        for ability_id in ability_ids:
            if ability_id not in existing_ids:
                raise ValidationError(f"アビリティID {ability_id} は存在しません")


def compute_stats(base_hp: int, base_attack: int, base_defense: int, base_speed: int, level: int = 1) -> Dict[str, int]:
    """
    ステータス計算

    Args:
        base_hp: 基礎HP
        base_attack: 基礎攻撃力
        base_defense: 基礎防御力
        base_speed: 基礎速度
        level: レベル（デフォルト: 1）

    Returns:
        計算済みステータス
    """
    multiplier = 1 + (level - 1) * 0.1

    return {
        "hp": int(base_hp * multiplier),
        "attack": int(base_attack * multiplier),
        "defense": int(base_defense * multiplier),
        "speed": int(base_speed * multiplier)
    }


async def create_character(
    conn: sqlite3.Connection,
    account_id: int,
    name: str,
    prompt: str,
    base_hp: Optional[int] = None,
    base_attack: Optional[int] = None,
    base_defense: Optional[int] = None,
    base_speed: Optional[int] = None,
    ability_ids: Optional[List[int]] = None,
    auto_allocate: bool = False,
    total_points: int = 340,
    auto_select_abilities: bool = False
) -> Dict[str, Any]:
    """
    新しいキャラクターを作成します。

    あなたはこのキャラクターとしてバトルに参加します。
    promptには、キャラクターの性格、戦闘スタイル、口調などを詳しく記述してください。

    Args:
        conn: データベース接続
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
        abilities: アビリティ一覧
        allocated_stats: 自動振り分けされた基礎ステータス（auto_allocate=Trueの場合）
        auto_allocation_reasoning: 自動振り分けの理由（auto_allocate=Trueの場合）
        character_archetype: キャラクタータイプ（auto_allocate=Trueの場合）
        message: 作成完了メッセージ

    Raises:
        ValidationError: バリデーションエラー
        DatabaseError: データベースエラー
    """
    try:
        if ability_ids is None:
            ability_ids = []

        # 基本バリデーション
        validate_character_name(name)
        validate_prompt(prompt)

        # ステータス決定
        allocation_info = None
        if auto_allocate:
            # 自動振り分けモード
            logger.info(f"ステータス自動振り分け開始: total_points={total_points}")

            from ..llm.allocator import allocate_stats_with_retry

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

            # 利用可能なアビリティを取得
            available_abilities = list_abilities(conn)

            from ..llm.allocator import auto_select_abilities as select_abilities_func

            ability_ids = await select_abilities_func(prompt, allocated_stats, available_abilities)

        validate_ability_ids(conn, ability_ids)

        # ステータス計算
        level = 1
        computed_stats = compute_stats(base_hp, base_attack, base_defense, base_speed, level)

        # トランザクション開始
        cursor = conn.cursor()

        # キャラクター作成
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

        # アビリティの設定
        abilities = []
        if ability_ids:
            for ability_id in ability_ids:
                cursor.execute(
                    """
                    INSERT INTO character_abilities (character_id, ability_id)
                    VALUES (?, ?)
                    """,
                    (character_id, ability_id)
                )

            # アビリティ情報を取得
            placeholders = ','.join('?' * len(ability_ids))
            cursor.execute(
                f"""
                SELECT id, name, description, effect_type, power
                FROM abilities
                WHERE id IN ({placeholders})
                """,
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


def get_character_info(conn: sqlite3.Connection, character_id: int) -> Dict[str, Any]:
    """
    指定したキャラクターの詳細情報を取得します。

    Args:
        conn: データベース接続
        character_id: キャラクターID

    Returns:
        キャラクターの全情報（名前、ステータス、アビリティ、戦績など）

    Raises:
        ValidationError: キャラクターが存在しない場合
        DatabaseError: データベースエラー
    """
    try:
        cursor = conn.cursor()

        # キャラクター基本情報を取得
        cursor.execute(
            """
            SELECT
                c.id, c.account_id, c.name, c.prompt, c.level,
                c.base_hp, c.base_attack, c.base_defense, c.base_speed,
                c.computed_hp, c.computed_attack, c.computed_defense, c.computed_speed,
                c.created_at, c.updated_at,
                a.username
            FROM characters c
            JOIN accounts a ON c.account_id = a.id
            WHERE c.id = ?
            """,
            (character_id,)
        )

        row = cursor.fetchone()
        if row is None:
            raise ValidationError(f"キャラクターID {character_id} は存在しません")

        character = {
            "id": row[0],
            "account_id": row[1],
            "owner_username": row[15],
            "name": row[2],
            "prompt": row[3],
            "level": row[4],
            "base_stats": {
                "hp": row[5],
                "attack": row[6],
                "defense": row[7],
                "speed": row[8]
            },
            "computed_stats": {
                "hp": row[9],
                "attack": row[10],
                "defense": row[11],
                "speed": row[12]
            },
            "created_at": row[13],
            "updated_at": row[14]
        }

        # アビリティ情報を取得
        cursor.execute(
            """
            SELECT a.id, a.name, a.description, a.effect_type, a.power
            FROM abilities a
            JOIN character_abilities ca ON a.id = ca.ability_id
            WHERE ca.character_id = ?
            """,
            (character_id,)
        )

        abilities = []
        for row in cursor.fetchall():
            abilities.append({
                "id": row[0],
                "name": row[1],
                "description": row[2],
                "effect_type": row[3],
                "power": row[4]
            })

        character["abilities"] = abilities

        # 戦績情報を取得
        cursor.execute(
            """
            SELECT
                total_battles, wins, losses, draws,
                total_damage_dealt, total_damage_received,
                longest_win_streak, current_win_streak, rating
            FROM stats
            WHERE character_id = ?
            """,
            (character_id,)
        )

        row = cursor.fetchone()
        if row:
            character["stats"] = {
                "total_battles": row[0],
                "wins": row[1],
                "losses": row[2],
                "draws": row[3],
                "total_damage_dealt": row[4],
                "total_damage_received": row[5],
                "longest_win_streak": row[6],
                "current_win_streak": row[7],
                "rating": row[8]
            }
        else:
            character["stats"] = {
                "total_battles": 0,
                "wins": 0,
                "losses": 0,
                "draws": 0,
                "total_damage_dealt": 0,
                "total_damage_received": 0,
                "longest_win_streak": 0,
                "current_win_streak": 0,
                "rating": 1000
            }

        return character

    except ValidationError:
        raise
    except sqlite3.Error as e:
        raise DatabaseError(f"データベースエラー: {e}")


def list_my_characters(conn: sqlite3.Connection, account_id: int) -> List[Dict[str, Any]]:
    """
    あなたが作成したキャラクター一覧を取得します。

    Args:
        conn: データベース接続
        account_id: アカウントID

    Returns:
        キャラクター一覧

    Raises:
        DatabaseError: データベースエラー
    """
    try:
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT
                c.id, c.name, c.level,
                c.computed_hp, c.computed_attack, c.computed_defense, c.computed_speed,
                s.rating, s.total_battles, s.wins, s.losses
            FROM characters c
            LEFT JOIN stats s ON c.id = s.character_id
            WHERE c.account_id = ?
            ORDER BY c.created_at DESC
            """,
            (account_id,)
        )

        characters = []
        for row in cursor.fetchall():
            characters.append({
                "id": row[0],
                "name": row[1],
                "level": row[2],
                "stats": {
                    "hp": row[3],
                    "attack": row[4],
                    "defense": row[5],
                    "speed": row[6]
                },
                "rating": row[7] if row[7] is not None else 1000,
                "battles": {
                    "total": row[8] if row[8] is not None else 0,
                    "wins": row[9] if row[9] is not None else 0,
                    "losses": row[10] if row[10] is not None else 0
                }
            })

        return characters

    except sqlite3.Error as e:
        raise DatabaseError(f"データベースエラー: {e}")


def list_abilities(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    """
    キャラクター作成時に選択できるアビリティの一覧を取得します。

    Args:
        conn: データベース接続

    Returns:
        アビリティ一覧（名前、説明、効果、威力など）

    Raises:
        DatabaseError: データベースエラー
    """
    try:
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id, name, description, effect_type, power, cost, cooldown
            FROM abilities
            ORDER BY id
            """
        )

        abilities = []
        for row in cursor.fetchall():
            abilities.append({
                "id": row[0],
                "name": row[1],
                "description": row[2],
                "effect_type": row[3],
                "power": row[4],
                "cost": row[5],
                "cooldown": row[6]
            })

        return abilities

    except sqlite3.Error as e:
        raise DatabaseError(f"データベースエラー: {e}")
