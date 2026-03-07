"""
LLMバトルゲーム MCPサーバー（API client version）

FastMCP 3.0.2を使用したMCPサーバーのエントリーポイント
APIサーバー経由でデータにアクセスします。
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

# APIクライアントとセッション管理のインポート
sys.path.insert(0, str(Path(__file__).parent.parent))
from server.api_client import ApiClient
from server.session import SessionManager

# ツールモジュールのインポート
from server.tools import account, character, battle, stats
from server.errors import GameError, ValidationError, AuthenticationError, BattleError

# MCPサーバーの初期化
mcp = FastMCP("LLMバトルゲーム")

# グローバルインスタンス
api_client = None
session_manager = None


def initialize_api_client():
    """APIクライアントとセッション管理を初期化"""
    global api_client, session_manager

    # Get API base URL from environment
    base_url = os.environ.get('API_BASE_URL', 'http://localhost:3000')

    # Initialize API client
    api_client = ApiClient(base_url=base_url)
    logger.info(f"APIクライアントを初期化しました: {base_url}")

    # Initialize session manager
    session_manager = SessionManager()

    # Load existing session if available
    session_data = session_manager.load_session()
    if session_data and 'token' in session_data:
        api_client.set_token(session_data['token'])
        logger.info(f"保存されたセッションをロードしました: account_id={session_data.get('account_id')}")

    # Set instances in tool modules
    account.set_api_client(api_client)
    account.set_session_manager(session_manager)
    character.set_api_client(api_client)
    battle.set_api_client(api_client)
    stats.set_api_client(api_client)

    return api_client, session_manager


# =====================
# アカウント管理ツール
# =====================

@mcp.tool()
async def create_account(username: str) -> dict:
    """
    新しいプレイヤーアカウントを作成します（API経由）

    Args:
        username: ユーザー名（1-50文字、一意）

    Returns:
        account_id: アカウントID
        session_id: セッションID
        token: JWT認証トークン
        message: 作成完了メッセージ
    """
    try:
        logger.info(f"Tool called: create_account(username={username})")
        result = account.create_account(username)
        logger.info(f"Account created: id={result['account_id']}, username={username}")
        return result
    except (ValidationError, AuthenticationError) as e:
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
    既存のアカウントにログインします（API経由）

    Args:
        username: ユーザー名

    Returns:
        account_id: アカウントID
        session_id: 新しいセッションID
        token: JWT認証トークン
        characters: 所有キャラクター一覧
    """
    try:
        logger.info(f"Tool called: login(username={username})")
        result = account.login(username)
        logger.info(f"Login successful: account_id={result['account_id']}")
        return result
    except (ValidationError, AuthenticationError) as e:
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
    base_hp: int,
    base_attack: int,
    base_defense: int,
    base_speed: int,
    ability_ids: list[int] = None
) -> dict:
    """
    新しいキャラクターを作成します。

    あなたはこのキャラクターとしてバトルに参加します。
    promptを読んで、キャラクターに合ったステータス配分とアビリティを判断してください。

    Args:
        account_id: アカウントID
        name: キャラクター名（1-50文字）
        prompt: キャラクター設定プロンプト（50-2000文字）
            - キャラクターの性格、戦闘スタイル、口調などを詳しく記述
        base_hp: 基礎HP（10-100）
        base_attack: 基礎攻撃力（10-100）
        base_defense: 基礎防御力（10-100）
        base_speed: 基礎速度（10-100）
        ability_ids: 習得アビリティID一覧（最大3個）

    ステータス配分ルール:
        - 合計: 280-400ポイント（推奨340）
        - 各ステータス: 10-100の範囲
        - promptに基づいて配分を決定してください
          例: 「素早い剣士」→ base_speed高め、base_hp低め
          例: 「重装騎士」→ base_hp, base_defense高め、base_speed低め

    アビリティ選択:
        - list_abilities()で利用可能なアビリティを確認できます
        - promptに合ったアビリティを最大3個選んでください

    Returns:
        character_id: キャラクターID
        computed_stats: 計算済みステータス（レベル1時点）
        abilities: 習得したアビリティ一覧
        message: 作成完了メッセージ
    """
    try:
        logger.info(f"Tool called: create_character(name={name}, account_id={account_id})")
        result = character.create_character(
            account_id, name, prompt,
            base_hp, base_attack, base_defense, base_speed,
            ability_ids
        )
        logger.info(f"Character created: id={result['character_id']}, name={name}")
        return result
    except ValidationError as e:
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
        result = character.get_character_info(character_id)
        logger.info(f"Character info retrieved: id={character_id}")
        return result
    except ValidationError as e:
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
        result = character.list_my_characters(account_id)
        logger.info(f"Characters retrieved: {len(result)} characters")
        return result
    except ValidationError as e:
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
        result = character.list_abilities()
        logger.info(f"Abilities retrieved: {len(result)} abilities")
        return result
    except ValidationError as e:
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
        result = battle.join_queue(character_id)
        logger.info(f"Queue join result: status={result.get('status', 'unknown')}")
        return result
    except (ValidationError, BattleError) as e:
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
        result = battle.leave_queue(character_id)
        logger.info(f"Left queue: character_id={character_id}")
        return result
    except ValidationError as e:
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
        result = battle.get_battle_status(battle_id)
        logger.info(f"Battle status retrieved: battle_id={battle_id}")
        return result
    except BattleError as e:
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
    バトルのターンで行動を実行します。

    両プレイヤーがそれぞれ行動を送信し、双方の送信後にサーバー側でターンが解決されます。
    相手がまだ行動を送信していない場合は status='waiting' を返します。

    Args:
        battle_id: バトルID
        character_id: あなたのキャラクターID
        action: 行動タイプ（'attack', 'defend', 'dodge', 'ability'）
        ability_id: アビリティ使用時のアビリティID（action='ability'の場合に必要）

    Returns:
        status='waiting': 相手の行動待ち中
        status='in_progress': ターン解決済み、バトル継続中（player1_hp, player2_hp等を含む）
        status='finished': バトル終了（winner_id, is_drawを含む）
    """
    try:
        logger.info(f"Tool called: execute_turn(battle_id={battle_id}, character_id={character_id}, action={action})")
        result = battle.execute_action(battle_id, character_id, action, ability_id)
        logger.info(f"execute_turn result: status={result.get('status')}")
        return result
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
        result = battle.get_battle_history(character_id, limit)
        logger.info(f"Battle history retrieved: {len(result)} battles")
        return result
    except ValidationError as e:
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
        result = stats.get_leaderboard(limit)
        logger.info(f"Leaderboard retrieved: {len(result)} entries")
        return result
    except ValidationError as e:
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
        result = stats.get_character_stats(character_id)
        logger.info(f"Character stats retrieved: character_id={character_id}")
        return result
    except ValidationError as e:
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
        logger.info("LLMバトルゲーム MCPサーバーを起動します（API client mode）")
        logger.info("=" * 60)

        # APIクライアント初期化
        initialize_api_client()
        logger.info("APIクライアント初期化完了")

        # サーバー起動
        logger.info("MCPサーバーを起動しました（STDIO接続待機中）")
        mcp.run()

    except KeyboardInterrupt:
        logger.info("サーバーを停止しています...")
    except Exception as e:
        logger.error(f"サーバー起動中にエラーが発生しました: {e}", exc_info=True)
        sys.exit(1)
