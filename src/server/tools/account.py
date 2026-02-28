"""
アカウント管理ツール
"""

import re
import uuid
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Any, List

from ..errors import ValidationError, AuthenticationError, DatabaseError


def validate_username(username: str) -> None:
    """
    ユーザー名のバリデーション

    Args:
        username: 検証するユーザー名

    Raises:
        ValidationError: バリデーションエラー
    """
    if not username:
        raise ValidationError("ユーザー名を入力してください")

    if len(username) < 1 or len(username) > 50:
        raise ValidationError("ユーザー名は1-50文字で入力してください")

    # 英数字とアンダースコアのみ許可
    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        raise ValidationError("ユーザー名は英数字とアンダースコア(_)のみ使用できます")


def create_account(conn: sqlite3.Connection, username: str) -> Dict[str, Any]:
    """
    新しいプレイヤーアカウントを作成します。

    Args:
        conn: データベース接続
        username: ユーザー名（1-50文字、一意）

    Returns:
        account_id: アカウントID
        session_id: セッションID
        message: 作成完了メッセージ

    Raises:
        ValidationError: バリデーションエラー
        DatabaseError: データベースエラー
    """
    try:
        # バリデーション
        validate_username(username)

        # 重複チェック
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM accounts WHERE username = ?", (username,))
        if cursor.fetchone() is not None:
            raise ValidationError(f"ユーザー名 '{username}' は既に使用されています")

        # セッションIDを生成
        session_id = str(uuid.uuid4())

        # アカウント作成
        cursor.execute(
            """
            INSERT INTO accounts (username, session_id, created_at, last_login)
            VALUES (?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            (username, session_id)
        )
        account_id = cursor.lastrowid
        conn.commit()

        return {
            "account_id": account_id,
            "session_id": session_id,
            "message": f"アカウント '{username}' が作成されました"
        }

    except ValidationError:
        raise
    except sqlite3.IntegrityError as e:
        raise ValidationError(f"ユーザー名 '{username}' は既に使用されています")
    except sqlite3.Error as e:
        raise DatabaseError(f"データベースエラー: {e}")


def login(conn: sqlite3.Connection, username: str) -> Dict[str, Any]:
    """
    既存のアカウントにログインします。

    Args:
        conn: データベース接続
        username: ユーザー名

    Returns:
        account_id: アカウントID
        session_id: 新しいセッションID
        characters: 所有キャラクター一覧

    Raises:
        AuthenticationError: 認証エラー
        DatabaseError: データベースエラー
    """
    try:
        # バリデーション
        validate_username(username)

        # アカウント検索
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM accounts WHERE username = ?", (username,))
        row = cursor.fetchone()

        if row is None:
            raise AuthenticationError(f"ユーザー名 '{username}' は存在しません")

        account_id = row[0]

        # 新しいセッションIDを生成
        session_id = str(uuid.uuid4())

        # セッションIDと最終ログイン時刻を更新
        cursor.execute(
            """
            UPDATE accounts
            SET session_id = ?, last_login = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (session_id, account_id)
        )

        # 所有キャラクター一覧を取得
        cursor.execute(
            """
            SELECT id, name, level, computed_hp, computed_attack, computed_defense, computed_speed
            FROM characters
            WHERE account_id = ?
            ORDER BY created_at DESC
            """,
            (account_id,)
        )

        characters = []
        for row in cursor.fetchall():
            characters.append({
                "id": row[0],
                "name": row[1],
                "level": row[2],
                "hp": row[3],
                "attack": row[4],
                "defense": row[5],
                "speed": row[6]
            })

        conn.commit()

        return {
            "account_id": account_id,
            "session_id": session_id,
            "characters": characters,
            "message": f"ようこそ、{username}さん！"
        }

    except (ValidationError, AuthenticationError):
        raise
    except sqlite3.Error as e:
        raise DatabaseError(f"データベースエラー: {e}")
