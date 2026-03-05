"""
アカウント管理ツール（API経由）
"""

from typing import Dict, Any
from ..api_client import ApiClient
from ..session import SessionManager
from ..errors import ValidationError, AuthenticationError


# グローバルインスタンス（main.pyで初期化される）
_api_client: ApiClient = None
_session_manager: SessionManager = None


def set_api_client(client: ApiClient):
    """Set API client instance"""
    global _api_client
    _api_client = client


def set_session_manager(manager: SessionManager):
    """Set session manager instance"""
    global _session_manager
    _session_manager = manager


def create_account(username: str) -> Dict[str, Any]:
    """
    新しいプレイヤーアカウントを作成します（API経由）

    Args:
        username: ユーザー名（1-50文字、一意）

    Returns:
        account_id: アカウントID
        session_id: セッションID
        token: JWT認証トークン
        message: 作成完了メッセージ

    Raises:
        ValidationError: バリデーションエラー
        AuthenticationError: 認証エラー
    """
    if not _api_client:
        raise RuntimeError("API client not initialized")

    # Call API
    result = _api_client.create_account(username)

    # Save token to session
    if 'token' in result and _session_manager:
        _session_manager.save_session(
            account_id=result['account_id'],
            session_id=result['session_id'],
            token=result['token'],
            username=username
        )
        _api_client.set_token(result['token'])

    return result


def login(username: str) -> Dict[str, Any]:
    """
    既存のアカウントにログインします（API経由）

    Args:
        username: ユーザー名

    Returns:
        account_id: アカウントID
        session_id: 新しいセッションID
        token: JWT認証トークン
        characters: 所有キャラクター一覧
        message: ログインメッセージ

    Raises:
        AuthenticationError: 認証エラー
    """
    if not _api_client:
        raise RuntimeError("API client not initialized")

    # Call API
    result = _api_client.login(username)

    # Save token to session
    if 'token' in result and _session_manager:
        _session_manager.save_session(
            account_id=result['account_id'],
            session_id=result['session_id'],
            token=result['token'],
            username=username
        )
        _api_client.set_token(result['token'])

    return result
