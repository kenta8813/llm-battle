"""
データベース接続ヘルパー関数のテスト
"""

import pytest
import sqlite3
import os
import tempfile
from pathlib import Path
import sys

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database import get_connection, initialize_database


@pytest.fixture
def temp_db_path():
    """テスト用の一時データベースパスを作成"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / 'test_llmbattle.db'
        # データベースを初期化
        initialize_database(db_path=db_path, force=True)
        yield str(db_path)


class TestGetConnection:
    """get_connection関数のテスト"""

    def test_get_connection_default_path(self):
        """デフォルトパスでの接続をテスト"""
        conn = get_connection()
        assert conn is not None
        assert isinstance(conn, sqlite3.Connection)

        # 外部キー制約が有効化されているか確認
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys")
        assert cursor.fetchone()[0] == 1

        # Row factoryが設定されているか確認
        assert conn.row_factory == sqlite3.Row

        conn.close()

    def test_get_connection_with_path(self, temp_db_path):
        """指定されたパスでの接続をテスト"""
        conn = get_connection(db_path=temp_db_path)
        assert conn is not None
        assert isinstance(conn, sqlite3.Connection)

        # テーブルが存在することを確認
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        assert len(tables) > 0

        conn.close()

    def test_get_connection_with_env_var(self, temp_db_path, monkeypatch):
        """環境変数からパスを取得する場合のテスト"""
        # 環境変数を設定
        monkeypatch.setenv('DB_PATH', temp_db_path)

        conn = get_connection()
        assert conn is not None

        # 正しいデータベースに接続されているか確認
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM abilities")
        ability_count = cursor.fetchone()[0]
        assert ability_count == 7

        conn.close()

    def test_row_factory(self, temp_db_path):
        """Row factoryの動作をテスト"""
        conn = get_connection(db_path=temp_db_path)

        cursor = conn.cursor()
        cursor.execute("SELECT name, effect_type FROM abilities LIMIT 1")
        row = cursor.fetchone()

        # カラム名でアクセスできることを確認
        assert 'name' in row.keys()
        assert 'effect_type' in row.keys()

        # インデックスでもアクセスできることを確認
        assert row[0] is not None
        assert row[1] is not None

        conn.close()

    def test_multiple_connections(self, temp_db_path):
        """複数接続の動作をテスト"""
        conn1 = get_connection(db_path=temp_db_path)
        conn2 = get_connection(db_path=temp_db_path)

        assert conn1 is not conn2

        # 両方の接続が使用可能か確認
        cursor1 = conn1.cursor()
        cursor2 = conn2.cursor()

        cursor1.execute("SELECT COUNT(*) FROM abilities")
        count1 = cursor1.fetchone()[0]

        cursor2.execute("SELECT COUNT(*) FROM abilities")
        count2 = cursor2.fetchone()[0]

        assert count1 == count2 == 7

        conn1.close()
        conn2.close()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
