"""
LLMバトルゲーム MCPサーバー

FastMCP 3.0.2を使用したMCPサーバーのエントリーポイント
"""

import os
import sys
import logging
from pathlib import Path
from typing import Dict, Any, List

from fastmcp import FastMCP

# ログ設定（stderrに出力、stdoutはMCP通信専用）
logging.basicConfig(
    stream=sys.stderr,
    level=os.environ.get('LOG_LEVEL', 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('llmbattle')

# データベースモジュールのインポート
sys.path.insert(0, str(Path(__file__).parent.parent))
from database import get_connection

# ツールモジュールのインポート
from server.tools import account, character, battle, stats
from server.errors import GameError, ValidationError, AuthenticationError, BattleError, DatabaseError

# MCPサーバーの初期化
mcp = FastMCP("LLMバトルゲーム")

# データベース接続（グローバル変数として保持）
db_conn = None


def get_db_connection():
    """データベース接続を取得"""
    global db_conn
    if db_conn is None:
        db_path = os.environ.get('DB_PATH')
        db_conn = get_connection(db_path)
        logger.info(f"データベース接続を確立しました: {db_path or 'デフォルトパス'}")
    return db_conn


# =====================
# アカウント管理ツール
# =====================

@mcp.tool()
async def create_account(username: str) -> dict:
    """
    新しいプレイヤーアカウントを作成します。

    Args:
        username: ユーザー名（1-50文字、一意）

    Returns:
        account_id: アカウントID
        session_id: セッションID
        message: 作成完了メッセージ
    """
    try:
        logger.info(f"Tool called: create_account(username={username})")
        conn = get_db_connection()
        result = account.create_account(conn, username)
        logger.info(f"Account created: id={result['account_id']}, username={username}")
        return result
    except (ValidationError, AuthenticationError, DatabaseError) as e:
        logger.error(f"Error in create_account: {e}")
        return {
            "error": {
                "code": type(e).__name__.upper(),
                "message": str(e)
            }
        }
    except Exception as e:
        logger.error(f"Unexpected error in create_account: {e}", exc_info=True)
        return {
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "予期しないエラーが発生しました"
            }
        }


@mcp.tool()
async def login(username: str) -> dict:
    """
    既存のアカウントにログインします。

    Args:
        username: ユーザー名

    Returns:
        account_id: アカウントID
        session_id: 新しいセッションID
        characters: 所有キャラクター一覧
    """
    try:
        logger.info(f"Tool called: login(username={username})")
        conn = get_db_connection()
        result = account.login(conn, username)
        logger.info(f"Login successful: account_id={result['account_id']}")
        return result
    except (ValidationError, AuthenticationError, DatabaseError) as e:
        logger.error(f"Error in login: {e}")
        return {
            "error": {
                "code": type(e).__name__.upper(),
                "message": str(e)
            }
        }
    except Exception as e:
        logger.error(f"Unexpected error in login: {e}", exc_info=True)
        return {
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "予期しないエラーが発生しました"
            }
        }


# ========================
# キャラクター管理ツール
# ========================

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
        abilities: アビリティ一覧
        allocated_stats: 自動振り分けされた基礎ステータス（auto_allocate=Trueの場合）
        auto_allocation_reasoning: 自動振り分けの理由（auto_allocate=Trueの場合）
        character_archetype: キャラクタータイプ（auto_allocate=Trueの場合）
        message: 作成完了メッセージ
    """
    try:
        logger.info(f"Tool called: create_character(name={name}, account_id={account_id}, auto_allocate={auto_allocate})")
        conn = get_db_connection()
        result = await character.create_character(
            conn, account_id, name, prompt,
            base_hp, base_attack, base_defense, base_speed,
            ability_ids, auto_allocate, total_points, auto_select_abilities
        )
        logger.info(f"Character created: id={result['character_id']}, name={name}")
        return result
    except (ValidationError, DatabaseError) as e:
        logger.error(f"Error in create_character: {e}")
        return {
            "error": {
                "code": type(e).__name__.upper(),
                "message": str(e)
            }
        }
    except Exception as e:
        logger.error(f"Unexpected error in create_character: {e}", exc_info=True)
        return {
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "予期しないエラーが発生しました"
            }
        }


@mcp.tool()
async def get_character_info(character_id: int) -> dict:
    """
    指定したキャラクターの詳細情報を取得します。

    Args:
        character_id: キャラクターID

    Returns:
        キャラクターの全情報（名前、ステータス、アビリティ、戦績など）
    """
    try:
        logger.info(f"Tool called: get_character_info(character_id={character_id})")
        conn = get_db_connection()
        result = character.get_character_info(conn, character_id)
        logger.info(f"Character info retrieved: id={character_id}")
        return result
    except (ValidationError, DatabaseError) as e:
        logger.error(f"Error in get_character_info: {e}")
        return {
            "error": {
                "code": type(e).__name__.upper(),
                "message": str(e)
            }
        }
    except Exception as e:
        logger.error(f"Unexpected error in get_character_info: {e}", exc_info=True)
        return {
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "予期しないエラーが発生しました"
            }
        }


@mcp.tool()
async def list_my_characters(account_id: int) -> list[dict]:
    """
    あなたが作成したキャラクター一覧を取得します。

    Args:
        account_id: アカウントID

    Returns:
        キャラクター一覧
    """
    try:
        logger.info(f"Tool called: list_my_characters(account_id={account_id})")
        conn = get_db_connection()
        result = character.list_my_characters(conn, account_id)
        logger.info(f"Characters retrieved: {len(result)} characters")
        return result
    except DatabaseError as e:
        logger.error(f"Error in list_my_characters: {e}")
        return {
            "error": {
                "code": type(e).__name__.upper(),
                "message": str(e)
            }
        }
    except Exception as e:
        logger.error(f"Unexpected error in list_my_characters: {e}", exc_info=True)
        return {
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "予期しないエラーが発生しました"
            }
        }


@mcp.tool()
async def list_abilities() -> list[dict]:
    """
    キャラクター作成時に選択できるアビリティの一覧を取得します。

    Returns:
        アビリティ一覧（名前、説明、効果、威力など）
    """
    try:
        logger.info(f"Tool called: list_abilities()")
        conn = get_db_connection()
        result = character.list_abilities(conn)
        logger.info(f"Abilities retrieved: {len(result)} abilities")
        return result
    except DatabaseError as e:
        logger.error(f"Error in list_abilities: {e}")
        return {
            "error": {
                "code": type(e).__name__.upper(),
                "message": str(e)
            }
        }
    except Exception as e:
        logger.error(f"Unexpected error in list_abilities: {e}", exc_info=True)
        return {
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "予期しないエラーが発生しました"
            }
        }


# ========================
# マッチング・バトルツール
# ========================

@mcp.tool()
async def join_queue(character_id: int) -> dict:
    """
    マッチング待機キューに参加します。

    相手が見つかり次第、自動的にバトルが開始されます。
    レーティングが近い相手とマッチングされます。

    Args:
        character_id: 参加させるキャラクターID

    Returns:
        queue_status: 'waiting' または 'matched'
        battle_id: マッチング成立時のバトルID（オプション）
        opponent_info: 対戦相手情報（マッチング成立時）
    """
    try:
        logger.info(f"Tool called: join_queue(character_id={character_id})")
        conn = get_db_connection()
        result = battle.join_queue(conn, character_id)
        logger.info(f"Queue join result: status={result['status']}")
        return result
    except (ValidationError, BattleError, DatabaseError) as e:
        logger.error(f"Error in join_queue: {e}")
        return {
            "error": {
                "code": type(e).__name__.upper(),
                "message": str(e)
            }
        }
    except Exception as e:
        logger.error(f"Unexpected error in join_queue: {e}", exc_info=True)
        return {
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "予期しないエラーが発生しました"
            }
        }


@mcp.tool()
async def leave_queue(character_id: int) -> dict:
    """
    マッチング待機キューから離脱します。

    Args:
        character_id: キャラクターID

    Returns:
        message: 離脱完了メッセージ
    """
    try:
        logger.info(f"Tool called: leave_queue(character_id={character_id})")
        conn = get_db_connection()
        result = battle.leave_queue(conn, character_id)
        logger.info(f"Left queue: character_id={character_id}")
        return result
    except (ValidationError, DatabaseError) as e:
        logger.error(f"Error in leave_queue: {e}")
        return {
            "error": {
                "code": type(e).__name__.upper(),
                "message": str(e)
            }
        }
    except Exception as e:
        logger.error(f"Unexpected error in leave_queue: {e}", exc_info=True)
        return {
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "予期しないエラーが発生しました"
            }
        }


@mcp.tool()
async def get_battle_status(battle_id: int) -> dict:
    """
    バトルの現在の状態を取得します。

    Args:
        battle_id: バトルID

    Returns:
        battle_info: バトル基本情報
        player1: プレイヤー1の現在状態（HP、ステータスなど）
        player2: プレイヤー2の現在状態
        current_turn: 現在のターン数
        latest_turn_result: 直前のターン結果
    """
    try:
        logger.info(f"Tool called: get_battle_status(battle_id={battle_id})")
        conn = get_db_connection()
        result = battle.get_battle_status(conn, battle_id)
        logger.info(f"Battle status retrieved: battle_id={battle_id}, turn={result['current_turn']}")
        return result
    except (BattleError, DatabaseError) as e:
        logger.error(f"Error in get_battle_status: {e}")
        return {
            "error": {
                "code": type(e).__name__.upper(),
                "message": str(e)
            }
        }
    except Exception as e:
        logger.error(f"Unexpected error in get_battle_status: {e}", exc_info=True)
        return {
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "予期しないエラーが発生しました"
            }
        }


@mcp.tool()
async def execute_turn(
    battle_id: int,
    character_id: int,
    action: str,
    ability_id: int = None
) -> dict:
    """
    あなたのターンの行動を実行します。

    相手の行動も同時に決定され、両者の行動が解決されます。
    あなたはキャラクター設定プロンプトに基づいて、
    このキャラクターらしい行動を選択してください。

    Args:
        battle_id: バトルID
        character_id: あなたのキャラクターID
        action: 行動タイプ（'attack', 'defend', 'dodge', 'ability'）
        ability_id: アビリティ使用時のアビリティID

    Returns:
        turn_result: ターン結果の詳細
        your_action: あなたの行動結果
        opponent_action: 相手の行動結果
        your_hp_after: あなたのターン後HP
        opponent_hp_after: 相手のターン後HP
        battle_status: バトル状態（'in_progress' or 'finished'）
        winner: 勝者（バトル終了時のみ）
    """
    try:
        logger.info(f"Tool called: execute_turn(battle_id={battle_id}, character_id={character_id}, action={action})")
        conn = get_db_connection()
        result = battle.execute_turn(conn, battle_id, character_id, action, ability_id)
        logger.info(f"Turn executed: battle_id={battle_id}, status={result['battle_status']}")
        return result
    except (ValidationError, BattleError, DatabaseError) as e:
        logger.error(f"Error in execute_turn: {e}")
        return {
            "error": {
                "code": type(e).__name__.upper(),
                "message": str(e)
            }
        }
    except Exception as e:
        logger.error(f"Unexpected error in execute_turn: {e}", exc_info=True)
        return {
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "予期しないエラーが発生しました"
            }
        }


@mcp.tool()
async def get_battle_history(
    character_id: int,
    limit: int = 10
) -> list[dict]:
    """
    指定したキャラクターのバトル履歴を取得します。

    Args:
        character_id: キャラクターID
        limit: 取得件数（デフォルト10件）

    Returns:
        バトル履歴一覧（日時、対戦相手、結果など）
    """
    try:
        logger.info(f"Tool called: get_battle_history(character_id={character_id}, limit={limit})")
        conn = get_db_connection()
        result = battle.get_battle_history(conn, character_id, limit)
        logger.info(f"Battle history retrieved: {len(result)} battles")
        return result
    except DatabaseError as e:
        logger.error(f"Error in get_battle_history: {e}")
        return {
            "error": {
                "code": type(e).__name__.upper(),
                "message": str(e)
            }
        }
    except Exception as e:
        logger.error(f"Unexpected error in get_battle_history: {e}", exc_info=True)
        return {
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "予期しないエラーが発生しました"
            }
        }


# ============================
# リーダーボード・統計ツール
# ============================

@mcp.tool()
async def get_leaderboard(limit: int = 50) -> list[dict]:
    """
    レーティング上位のキャラクター一覧を取得します。

    Args:
        limit: 取得件数（デフォルト50件）

    Returns:
        順位、キャラクター名、レーティング、勝率などのランキング
    """
    try:
        logger.info(f"Tool called: get_leaderboard(limit={limit})")
        conn = get_db_connection()
        result = stats.get_leaderboard(conn, limit)
        logger.info(f"Leaderboard retrieved: {len(result)} entries")
        return result
    except DatabaseError as e:
        logger.error(f"Error in get_leaderboard: {e}")
        return {
            "error": {
                "code": type(e).__name__.upper(),
                "message": str(e)
            }
        }
    except Exception as e:
        logger.error(f"Unexpected error in get_leaderboard: {e}", exc_info=True)
        return {
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "予期しないエラーが発生しました"
            }
        }


@mcp.tool()
async def get_character_stats(character_id: int) -> dict:
    """
    指定したキャラクターの詳細な戦績を取得します。

    Args:
        character_id: キャラクターID

    Returns:
        総バトル数、勝敗数、レーティング、連勝記録など
    """
    try:
        logger.info(f"Tool called: get_character_stats(character_id={character_id})")
        conn = get_db_connection()
        result = stats.get_character_stats(conn, character_id)
        logger.info(f"Character stats retrieved: character_id={character_id}, rating={result['rating']}")
        return result
    except (ValidationError, DatabaseError) as e:
        logger.error(f"Error in get_character_stats: {e}")
        return {
            "error": {
                "code": type(e).__name__.upper(),
                "message": str(e)
            }
        }
    except Exception as e:
        logger.error(f"Unexpected error in get_character_stats: {e}", exc_info=True)
        return {
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "予期しないエラーが発生しました"
            }
        }


# =====================
# メインエントリポイント
# =====================

if __name__ == "__main__":
    try:
        logger.info("=" * 60)
        logger.info("LLMバトルゲーム MCPサーバーを起動します")
        logger.info("=" * 60)

        # データベース接続確認
        conn = get_db_connection()
        logger.info("データベース接続確認完了")

        # サーバー起動
        logger.info("MCPサーバーを起動しました（STDIO接続待機中）")
        mcp.run()

    except KeyboardInterrupt:
        logger.info("サーバーを停止しています...")
    except Exception as e:
        logger.error(f"サーバー起動中にエラーが発生しました: {e}", exc_info=True)
        sys.exit(1)
    finally:
        if db_conn:
            db_conn.close()
            logger.info("データベース接続を閉じました")
