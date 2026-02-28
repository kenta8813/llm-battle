"""
データベース初期化のテストスクリプト

データベースの初期化、スキーマ、初期データ、外部キー制約をテストします。
"""

import pytest
import sqlite3
import tempfile
import os
from pathlib import Path
import sys

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database.init_db import (
    initialize_database,
    get_database_path,
    check_database_exists,
    verify_tables,
    verify_initial_data
)


@pytest.fixture
def temp_db_path():
    """テスト用の一時データベースパスを作成"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / 'test_llmbattle.db'
        yield db_path
        # テスト後のクリーンアップは自動的に行われる


@pytest.fixture
def initialized_db(temp_db_path):
    """初期化済みのテストデータベース"""
    success = initialize_database(db_path=temp_db_path, force=True)
    assert success, "データベースの初期化に失敗しました"
    yield temp_db_path


class TestDatabaseInitialization:
    """データベース初期化のテスト"""

    def test_database_file_creation(self, temp_db_path):
        """データベースファイルが正しく作成されるかテスト"""
        # データベースを初期化
        success = initialize_database(db_path=temp_db_path, force=True)
        assert success, "データベース初期化が失敗しました"

        # ファイルが存在することを確認
        assert temp_db_path.exists(), "データベースファイルが作成されていません"
        assert temp_db_path.is_file(), "データベースパスがファイルではありません"

    def test_database_already_exists(self, initialized_db):
        """既存のデータベースに対する初期化をテスト"""
        # 既存のデータベースに対して再度初期化
        success = initialize_database(db_path=initialized_db, force=False)
        assert success, "既存データベースへの初期化が失敗しました"

    def test_database_force_recreate(self, initialized_db):
        """データベースの強制再作成をテスト"""
        # 強制再作成
        success = initialize_database(db_path=initialized_db, force=True)
        assert success, "データベースの強制再作成が失敗しました"


class TestTableCreation:
    """テーブル作成のテスト"""

    def test_all_tables_created(self, initialized_db):
        """すべてのテーブルが作成されているかテスト"""
        conn = sqlite3.connect(str(initialized_db))
        try:
            success, tables = verify_tables(conn)
            assert success, "テーブルの検証に失敗しました"

            # 期待されるテーブル
            expected_tables = [
                'abilities',
                'accounts',
                'battle_turns',
                'battles',
                'character_abilities',
                'characters',
                'queue',
                'schema_version',
                'stats'
            ]

            for table in expected_tables:
                assert table in tables, f"テーブル '{table}' が作成されていません"

        finally:
            conn.close()

    def test_accounts_table_structure(self, initialized_db):
        """accountsテーブルの構造をテスト"""
        conn = sqlite3.connect(str(initialized_db))
        try:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(accounts)")
            columns = {row[1]: row[2] for row in cursor.fetchall()}

            # 期待されるカラム
            assert 'id' in columns
            assert 'username' in columns
            assert 'session_id' in columns
            assert 'created_at' in columns
            assert 'last_login' in columns

        finally:
            conn.close()

    def test_characters_table_structure(self, initialized_db):
        """charactersテーブルの構造をテスト"""
        conn = sqlite3.connect(str(initialized_db))
        try:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(characters)")
            columns = {row[1]: row[2] for row in cursor.fetchall()}

            # 基礎ステータス
            assert 'base_hp' in columns
            assert 'base_attack' in columns
            assert 'base_defense' in columns
            assert 'base_speed' in columns

            # 計算済みステータス
            assert 'computed_hp' in columns
            assert 'computed_attack' in columns
            assert 'computed_defense' in columns
            assert 'computed_speed' in columns

        finally:
            conn.close()

    def test_abilities_table_structure(self, initialized_db):
        """abilitiesテーブルの構造をテスト"""
        conn = sqlite3.connect(str(initialized_db))
        try:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(abilities)")
            columns = {row[1]: row[2] for row in cursor.fetchall()}

            assert 'name' in columns
            assert 'description' in columns
            assert 'effect_type' in columns
            assert 'power' in columns
            assert 'cooldown' in columns

        finally:
            conn.close()

    def test_battles_table_structure(self, initialized_db):
        """battlesテーブルの構造をテスト"""
        conn = sqlite3.connect(str(initialized_db))
        try:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(battles)")
            columns = {row[1]: row[2] for row in cursor.fetchall()}

            assert 'player1_id' in columns
            assert 'player2_id' in columns
            assert 'winner_id' in columns
            assert 'status' in columns
            assert 'max_turns' in columns
            assert 'current_turn' in columns

        finally:
            conn.close()


class TestInitialData:
    """初期データ投入のテスト"""

    def test_abilities_initial_data(self, initialized_db):
        """アビリティの初期データをテスト"""
        conn = sqlite3.connect(str(initialized_db))
        try:
            success, ability_count = verify_initial_data(conn)
            assert success, "初期データの検証に失敗しました"
            assert ability_count == 7, f"アビリティの数が不正です: {ability_count}"

        finally:
            conn.close()

    def test_abilities_content(self, initialized_db):
        """アビリティの内容をテスト"""
        conn = sqlite3.connect(str(initialized_db))
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT name, effect_type, power FROM abilities ORDER BY name")
            abilities = cursor.fetchall()

            # アビリティ名のリスト
            ability_names = [ability[0] for ability in abilities]

            expected_names = ['カウンター', '回復', '弱体化', '強打', '必殺技', '防御態勢', '連続攻撃']
            for name in expected_names:
                assert name in ability_names, f"アビリティ '{name}' が存在しません"

            # 各アビリティのクールダウンをチェック
            cursor.execute("SELECT name, cooldown FROM abilities ORDER BY name")
            cooldowns = {row[0]: row[1] for row in cursor.fetchall()}

            expected_cooldowns = {
                '強打': 0,
                '連続攻撃': 1,
                '必殺技': 3,
                '回復': 2,
                '防御態勢': 1,
                'カウンター': 2,
                '弱体化': 2
            }

            for ability_name, expected_cd in expected_cooldowns.items():
                assert cooldowns[ability_name] == expected_cd, \
                    f"{ability_name}のクールダウンが不正です: 期待={expected_cd}, 実際={cooldowns[ability_name]}"

        finally:
            conn.close()

    def test_schema_version(self, initialized_db):
        """スキーマバージョンテーブルをテスト"""
        conn = sqlite3.connect(str(initialized_db))
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT version, description FROM schema_version")
            row = cursor.fetchone()

            assert row is not None, "スキーマバージョンが記録されていません"
            assert row[0] == 1, f"スキーマバージョンが不正です: {row[0]}"

        finally:
            conn.close()


class TestForeignKeyConstraints:
    """外部キー制約のテスト"""

    def test_foreign_keys_enabled(self, initialized_db):
        """外部キー制約が有効化できるかテスト"""
        conn = sqlite3.connect(str(initialized_db))
        try:
            # 外部キー制約を有効化
            conn.execute("PRAGMA foreign_keys = ON")

            cursor = conn.cursor()
            cursor.execute("PRAGMA foreign_keys")
            foreign_keys = cursor.fetchone()[0]
            assert foreign_keys == 1, "外部キー制約が有効化されていません"

        finally:
            conn.close()

    def test_cascade_delete_account(self, initialized_db):
        """アカウント削除時のカスケード削除をテスト"""
        conn = sqlite3.connect(str(initialized_db))
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            cursor = conn.cursor()

            # テストアカウントを作成
            cursor.execute(
                "INSERT INTO accounts (username) VALUES (?)",
                ('test_user',)
            )
            account_id = cursor.lastrowid

            # テストキャラクターを作成
            cursor.execute(
                """INSERT INTO characters
                (account_id, name, prompt, base_hp, base_attack, base_defense, base_speed,
                 computed_hp, computed_attack, computed_defense, computed_speed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (account_id, 'test_char', 'test prompt', 100, 80, 60, 70, 100, 80, 60, 70)
            )
            character_id = cursor.lastrowid

            # キャラクターが存在することを確認
            cursor.execute("SELECT COUNT(*) FROM characters WHERE id = ?", (character_id,))
            assert cursor.fetchone()[0] == 1

            # アカウントを削除
            cursor.execute("DELETE FROM accounts WHERE id = ?", (account_id,))
            conn.commit()

            # キャラクターも削除されていることを確認
            cursor.execute("SELECT COUNT(*) FROM characters WHERE id = ?", (character_id,))
            assert cursor.fetchone()[0] == 0, "カスケード削除が機能していません"

        finally:
            conn.close()

    def test_foreign_key_violation(self, initialized_db):
        """外部キー制約違反をテスト"""
        conn = sqlite3.connect(str(initialized_db))
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            cursor = conn.cursor()

            # 存在しないaccount_idでキャラクターを作成しようとする
            with pytest.raises(sqlite3.IntegrityError):
                cursor.execute(
                    """INSERT INTO characters
                    (account_id, name, prompt, base_hp, base_attack, base_defense, base_speed,
                     computed_hp, computed_attack, computed_defense, computed_speed)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (99999, 'test_char', 'test prompt', 100, 80, 60, 70, 100, 80, 60, 70)
                )
                conn.commit()

        finally:
            conn.close()


class TestCheckConstraints:
    """CHECK制約のテスト"""

    def test_positive_stats_constraint(self, initialized_db):
        """ステータス値の正の整数制約をテスト"""
        conn = sqlite3.connect(str(initialized_db))
        try:
            cursor = conn.cursor()

            # テストアカウントを作成
            cursor.execute("INSERT INTO accounts (username) VALUES (?)", ('test_user',))
            account_id = cursor.lastrowid

            # 負のステータスでキャラクターを作成しようとする
            with pytest.raises(sqlite3.IntegrityError):
                cursor.execute(
                    """INSERT INTO characters
                    (account_id, name, prompt, base_hp, base_attack, base_defense, base_speed,
                     computed_hp, computed_attack, computed_defense, computed_speed)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (account_id, 'test_char', 'test prompt', -10, 80, 60, 70, -10, 80, 60, 70)
                )
                conn.commit()

        finally:
            conn.close()

    def test_battle_status_constraint(self, initialized_db):
        """バトルステータスのENUM制約をテスト"""
        conn = sqlite3.connect(str(initialized_db))
        try:
            cursor = conn.cursor()

            # テストデータを作成
            cursor.execute("INSERT INTO accounts (username) VALUES (?)", ('user1',))
            account_id1 = cursor.lastrowid

            cursor.execute("INSERT INTO accounts (username) VALUES (?)", ('user2',))
            account_id2 = cursor.lastrowid

            cursor.execute(
                """INSERT INTO characters
                (account_id, name, prompt, base_hp, base_attack, base_defense, base_speed,
                 computed_hp, computed_attack, computed_defense, computed_speed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (account_id1, 'char1', 'prompt1', 100, 80, 60, 70, 100, 80, 60, 70)
            )
            char_id1 = cursor.lastrowid

            cursor.execute(
                """INSERT INTO characters
                (account_id, name, prompt, base_hp, base_attack, base_defense, base_speed,
                 computed_hp, computed_attack, computed_defense, computed_speed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (account_id2, 'char2', 'prompt2', 100, 80, 60, 70, 100, 80, 60, 70)
            )
            char_id2 = cursor.lastrowid

            # 不正なステータスでバトルを作成しようとする
            with pytest.raises(sqlite3.IntegrityError):
                cursor.execute(
                    """INSERT INTO battles (player1_id, player2_id, status)
                    VALUES (?, ?, ?)""",
                    (char_id1, char_id2, 'invalid_status')
                )
                conn.commit()

        finally:
            conn.close()


class TestIndexes:
    """インデックスのテスト"""

    def test_indexes_created(self, initialized_db):
        """インデックスが作成されているかテスト"""
        conn = sqlite3.connect(str(initialized_db))
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'"
            )
            indexes = [row[0] for row in cursor.fetchall()]

            # 期待されるインデックス
            expected_indexes = [
                'idx_accounts_username',
                'idx_accounts_session_id',
                'idx_characters_account_id',
                'idx_characters_level',
                'idx_abilities_effect_type',
                'idx_char_abilities_character',
                'idx_char_abilities_ability',
                'idx_battles_player1',
                'idx_battles_player2',
                'idx_battles_status',
                'idx_battles_started_at',
                'idx_battle_turns_battle',
                'idx_stats_rating',
                'idx_stats_wins',
                'idx_queue_rating',
                'idx_queue_joined_at'
            ]

            for index in expected_indexes:
                assert index in indexes, f"インデックス '{index}' が作成されていません"

        finally:
            conn.close()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
