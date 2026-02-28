"""
アカウント管理ツールのテスト
"""

import pytest
import sqlite3
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from database import get_connection, initialize_database
from server.tools import account
from server.errors import ValidationError, AuthenticationError, DatabaseError


@pytest.fixture
def db_conn():
    """テスト用データベース接続"""
    # インメモリデータベースを使用
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    # スキーマと初期データを投入
    schema_path = Path(__file__).parent.parent / 'src' / 'database' / 'schema.sql'
    seed_path = Path(__file__).parent.parent / 'src' / 'database' / 'seed.sql'

    with open(schema_path, 'r', encoding='utf-8') as f:
        conn.executescript(f.read())

    with open(seed_path, 'r', encoding='utf-8') as f:
        conn.executescript(f.read())

    yield conn
    conn.close()


class TestCreateAccount:
    """create_accountツールのテスト"""

    def test_create_account_success(self, db_conn):
        """正常なアカウント作成"""
        result = account.create_account(db_conn, "test_user")

        assert "account_id" in result
        assert "session_id" in result
        assert "message" in result
        assert result["account_id"] > 0
        assert len(result["session_id"]) > 0
        assert "test_user" in result["message"]

        # データベースに保存されていることを確認
        cursor = db_conn.cursor()
        cursor.execute("SELECT username FROM accounts WHERE id = ?", (result["account_id"],))
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == "test_user"

    def test_create_account_duplicate(self, db_conn):
        """重複アカウント作成のエラー"""
        account.create_account(db_conn, "test_user")

        # 同じユーザー名で再度作成しようとする
        with pytest.raises(ValidationError) as exc_info:
            account.create_account(db_conn, "test_user")

        assert "既に使用されています" in str(exc_info.value)

    def test_create_account_empty_username(self, db_conn):
        """空のユーザー名でエラー"""
        with pytest.raises(ValidationError) as exc_info:
            account.create_account(db_conn, "")

        assert "ユーザー名を入力してください" in str(exc_info.value)

    def test_create_account_too_long_username(self, db_conn):
        """長すぎるユーザー名でエラー"""
        long_username = "a" * 51  # 51文字

        with pytest.raises(ValidationError) as exc_info:
            account.create_account(db_conn, long_username)

        assert "1-50文字" in str(exc_info.value)

    def test_create_account_invalid_characters(self, db_conn):
        """無効な文字を含むユーザー名でエラー"""
        invalid_usernames = [
            "user name",  # スペース
            "user@name",  # @記号
            "user-name",  # ハイフン
            "ユーザー",    # 日本語
        ]

        for invalid_username in invalid_usernames:
            with pytest.raises(ValidationError) as exc_info:
                account.create_account(db_conn, invalid_username)

            assert "英数字とアンダースコア" in str(exc_info.value)

    def test_create_account_valid_characters(self, db_conn):
        """有効な文字のみのユーザー名で成功"""
        valid_usernames = [
            "user123",
            "test_user",
            "USER_NAME_123",
            "a",
            "a" * 50,
        ]

        for i, valid_username in enumerate(valid_usernames):
            result = account.create_account(db_conn, valid_username)
            assert result["account_id"] > 0


class TestLogin:
    """loginツールのテスト"""

    def test_login_success(self, db_conn):
        """正常なログイン"""
        # アカウント作成
        create_result = account.create_account(db_conn, "test_user")
        account_id = create_result["account_id"]
        original_session_id = create_result["session_id"]

        # ログイン
        login_result = account.login(db_conn, "test_user")

        assert "account_id" in login_result
        assert "session_id" in login_result
        assert "characters" in login_result
        assert "message" in login_result

        assert login_result["account_id"] == account_id
        assert login_result["session_id"] != original_session_id  # 新しいセッションIDが発行される
        assert isinstance(login_result["characters"], list)
        assert "test_user" in login_result["message"]

    def test_login_nonexistent_account(self, db_conn):
        """存在しないアカウントへのログイン"""
        with pytest.raises(AuthenticationError) as exc_info:
            account.login(db_conn, "nonexistent_user")

        assert "存在しません" in str(exc_info.value)

    def test_login_with_characters(self, db_conn):
        """キャラクター所有アカウントのログイン"""
        from server.tools import character

        # アカウント作成
        create_result = account.create_account(db_conn, "test_user")
        account_id = create_result["account_id"]

        # キャラクター作成
        character.create_character(
            db_conn, account_id,
            name="テストキャラ",
            prompt="これはテスト用のキャラクターです。" + "a" * 50,
            base_hp=80,
            base_attack=70,
            base_defense=60,
            base_speed=90,
            ability_ids=[]
        )

        # ログイン
        login_result = account.login(db_conn, "test_user")

        assert len(login_result["characters"]) == 1
        assert login_result["characters"][0]["name"] == "テストキャラ"
        assert login_result["characters"][0]["level"] == 1

    def test_login_empty_username(self, db_conn):
        """空のユーザー名でログインエラー"""
        with pytest.raises(ValidationError) as exc_info:
            account.login(db_conn, "")

        assert "ユーザー名を入力してください" in str(exc_info.value)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
