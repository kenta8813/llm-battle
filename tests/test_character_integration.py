"""
キャラクター作成機能の統合テスト（自動振り分け対応）
"""

import pytest
import sqlite3
import sys
from pathlib import Path
from unittest.mock import patch, AsyncMock

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from database import get_connection, initialize_database
from server.tools import account, character
from server.errors import ValidationError, DatabaseError


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


@pytest.fixture
def test_account(db_conn):
    """テスト用アカウント"""
    result = account.create_account(db_conn, "test_user")
    return result["account_id"]


class TestCreateCharacterAutoAllocate:
    """キャラクター作成の統合テスト（自動振り分け）"""

    @pytest.mark.asyncio
    async def test_create_character_auto_allocate(self, db_conn, test_account):
        """キャラクター作成（自動振り分けモード）"""
        # Claude APIをモック化
        mock_response = """```json
{
  "base_hp": 70,
  "base_attack": 95,
  "base_defense": 85,
  "base_speed": 90,
  "reasoning": "熱血漢で攻撃一辺倒のキャラクターのため、攻撃力と速度を高めに設定しました。",
  "character_archetype": "アタッカー型"
}
```"""

        with patch('server.llm.allocator.call_claude_api', new_callable=AsyncMock) as mock_api:
            mock_api.return_value = mock_response

            # キャラクター作成（自動振り分け）
            result = await character.create_character(
                conn=db_conn,
                account_id=test_account,
                name="炎の戦士",
                prompt="熱血漢で攻撃一辺倒。防御は二の次で、とにかく攻めまくる戦闘スタイル。常に前線で戦い、仲間を引っ張っていくリーダータイプです。",
                auto_allocate=True,
                total_points=340,
                auto_select_abilities=False
            )

            # 結果検証
            assert result["character_id"] > 0
            assert "allocated_stats" in result
            assert "auto_allocation_reasoning" in result
            assert "character_archetype" in result

            stats = result["allocated_stats"]
            total = stats["base_hp"] + stats["base_attack"] + stats["base_defense"] + stats["base_speed"]
            assert 338 <= total <= 342  # 自動調整を考慮

            # データベース確認
            cursor = db_conn.cursor()
            cursor.execute(
                "SELECT base_hp, base_attack, base_defense, base_speed FROM characters WHERE id = ?",
                (result["character_id"],)
            )
            row = cursor.fetchone()
            assert row is not None
            assert row[0] == stats["base_hp"]
            assert row[1] == stats["base_attack"]

    @pytest.mark.asyncio
    async def test_create_character_auto_allocate_with_abilities(self, db_conn, test_account):
        """キャラクター作成（自動振り分け + アビリティ自動選択）"""
        # Claude APIをモック化（ステータス）
        mock_stats_response = """```json
{
  "base_hp": 85,
  "base_attack": 85,
  "base_defense": 85,
  "base_speed": 85,
  "reasoning": "バランス型のキャラクターです。",
  "character_archetype": "テクニック型"
}
```"""

        # Claude APIをモック化（アビリティ）
        mock_abilities_response = """```json
{
  "ability_ids": [1, 2],
  "reasoning": "攻撃と防御のバランスを考慮"
}
```"""

        with patch('server.llm.allocator.call_claude_api', new_callable=AsyncMock) as mock_api:
            # 1回目はステータス、2回目はアビリティ
            mock_api.side_effect = [mock_stats_response, mock_abilities_response]

            result = await character.create_character(
                conn=db_conn,
                account_id=test_account,
                name="万能戦士",
                prompt="バランスの取れた戦い方をする万能タイプの戦士です。あらゆる状況に対応できます。攻撃・防御・速度のバランスを重視した戦闘スタイルを持ちます。",
                auto_allocate=True,
                total_points=340,
                auto_select_abilities=True
            )

            # 結果検証
            assert result["character_id"] > 0
            assert "allocated_stats" in result
            assert "character_archetype" in result
            assert len(result["abilities"]) > 0  # アビリティが選択されている

    @pytest.mark.asyncio
    async def test_create_character_auto_allocate_api_failure(self, db_conn, test_account):
        """キャラクター作成（API失敗時のデフォルト配分）"""
        with patch('server.llm.allocator.call_claude_api', new_callable=AsyncMock) as mock_api:
            # API呼び出しエラー
            mock_api.side_effect = Exception("API呼び出し失敗")

            result = await character.create_character(
                conn=db_conn,
                account_id=test_account,
                name="テストキャラ",
                prompt="API失敗時のテストキャラクターです。" + "a" * 50,
                auto_allocate=True,
                total_points=340,
                auto_select_abilities=False
            )

            # デフォルト配分が使われる
            assert result["character_id"] > 0
            assert result["character_archetype"] == "バランス型"
            assert "デフォルト" in result["auto_allocation_reasoning"]

            stats = result["allocated_stats"]
            total = stats["base_hp"] + stats["base_attack"] + stats["base_defense"] + stats["base_speed"]
            assert total == 340


class TestCreateCharacterManualMode:
    """キャラクター作成の統合テスト（手動モード）"""

    @pytest.mark.asyncio
    async def test_create_character_manual_mode(self, db_conn, test_account):
        """キャラクター作成（手動モード - 後方互換性）"""
        # キャラクター作成（手動）
        result = await character.create_character(
            conn=db_conn,
            account_id=test_account,
            name="鋼の守護者",
            prompt="仲間を守る盾となる守護者です。どんな攻撃も受け止め、仲間を守り抜きます。高い耐久力と防御力を持ち、チームの要として戦います。",
            base_hp=90,
            base_attack=60,
            base_defense=85,
            base_speed=45,
            auto_allocate=False
        )

        # 自動振り分け情報が含まれていないことを確認
        assert "allocated_stats" not in result
        assert "auto_allocation_reasoning" not in result
        assert "character_archetype" not in result

        # ステータスが指定通りであることを確認
        assert result["character_id"] > 0
        assert result["computed_stats"]["hp"] == 90
        assert result["computed_stats"]["attack"] == 60

    @pytest.mark.asyncio
    async def test_create_character_manual_mode_missing_stats(self, db_conn, test_account):
        """キャラクター作成（手動モードでステータス未指定エラー）"""
        with pytest.raises(ValidationError) as exc_info:
            await character.create_character(
                conn=db_conn,
                account_id=test_account,
                name="テストキャラ",
                prompt="テスト用のキャラクターです。" + "a" * 50,
                auto_allocate=False
                # ステータスを指定していない
            )

        assert "base_hp" in str(exc_info.value) or "指定してください" in str(exc_info.value)


class TestCreateCharacterEdgeCases:
    """エッジケースのテスト"""

    @pytest.mark.asyncio
    async def test_create_character_total_points_boundary(self, db_conn, test_account):
        """合計ポイントの境界値テスト"""
        mock_response = """```json
{
  "base_hp": 70,
  "base_attack": 70,
  "base_defense": 70,
  "base_speed": 70,
  "reasoning": "バランス型の配分です。",
  "character_archetype": "バランス型"
}
```"""

        with patch('server.llm.allocator.call_claude_api', new_callable=AsyncMock) as mock_api:
            mock_api.return_value = mock_response

            # 最小値（280）
            result = await character.create_character(
                conn=db_conn,
                account_id=test_account,
                name="最小ポイント",
                prompt="最小ポイントのテストキャラクターです。" + "a" * 50,
                auto_allocate=True,
                total_points=280
            )
            assert result["character_id"] > 0

            # 最大値（400）
            result = await character.create_character(
                conn=db_conn,
                account_id=test_account,
                name="最大ポイント",
                prompt="最大ポイントのテストキャラクターです。" + "a" * 50,
                auto_allocate=True,
                total_points=400
            )
            assert result["character_id"] > 0

    @pytest.mark.asyncio
    async def test_create_character_with_existing_abilities(self, db_conn, test_account):
        """手動でアビリティを指定した自動振り分け"""
        mock_response = """```json
{
  "base_hp": 85,
  "base_attack": 85,
  "base_defense": 85,
  "base_speed": 85,
  "reasoning": "バランス型の配分です。",
  "character_archetype": "バランス型"
}
```"""

        with patch('server.llm.allocator.call_claude_api', new_callable=AsyncMock) as mock_api:
            mock_api.return_value = mock_response

            result = await character.create_character(
                conn=db_conn,
                account_id=test_account,
                name="手動アビリティ",
                prompt="手動でアビリティを指定したテストキャラクターです。" + "a" * 50,
                auto_allocate=True,
                total_points=340,
                ability_ids=[1, 2],  # 手動でアビリティ指定
                auto_select_abilities=False
            )

            assert result["character_id"] > 0
            assert len(result["abilities"]) == 2
            assert result["abilities"][0]["id"] == 1
            assert result["abilities"][1]["id"] == 2


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
