"""
キャラクター管理ツールのテスト
"""

import pytest
import sqlite3
import sys
from pathlib import Path

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


class TestCreateCharacter:
    """create_characterツールのテスト"""

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_create_character_success(self, db_conn, test_account):
        """正常なキャラクター作成"""
        result = await character.create_character(
            db_conn,
            account_id=test_account,
            name="炎の戦士",
            prompt="あなたは熱き魂を持つ戦士です。常に正面から戦い、卑怯な手段は決して使いません。正々堂々と戦うことを信条としています。",
            base_hp=100,
            base_attack=80,
            base_defense=60,
            base_speed=60,
            ability_ids=[1, 2]  # 強打、防御態勢
        )

        assert "character_id" in result
        assert "computed_stats" in result
        assert "abilities" in result
        assert "message" in result

        assert result["character_id"] > 0
        assert result["computed_stats"]["hp"] == 100
        assert result["computed_stats"]["attack"] == 80
        assert result["computed_stats"]["defense"] == 60
        assert result["computed_stats"]["speed"] == 60
        assert len(result["abilities"]) == 2
        assert "炎の戦士" in result["message"]

        # データベースに保存されていることを確認
        cursor = db_conn.cursor()
        cursor.execute("SELECT name FROM characters WHERE id = ?", (result["character_id"],))
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == "炎の戦士"

        # 戦績が初期化されていることを確認
        cursor.execute("SELECT rating FROM stats WHERE character_id = ?", (result["character_id"],))
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == 1000  # 初期レーティング

    @pytest.mark.asyncio


    async def test_create_character_no_abilities(self, db_conn, test_account):
        """アビリティなしでキャラクター作成"""
        result = await character.create_character(
            db_conn,
            account_id=test_account,
            name="剣士",
            prompt="普通の剣士です。特別な技は持っていませんが、基本に忠実な戦いをします。常に冷静に状況を判断して行動します。",
            base_hp=70,
            base_attack=70,
            base_defense=70,
            base_speed=70,
            ability_ids=[]
        )

        assert len(result["abilities"]) == 0

    @pytest.mark.asyncio


    async def test_create_character_max_abilities(self, db_conn, test_account):
        """最大数のアビリティでキャラクター作成"""
        result = await character.create_character(
            db_conn,
            account_id=test_account,
            name="魔法使い",
            prompt="多彩な魔法を操る魔法使いです。状況に応じて様々な魔法を使い分けます。戦略的な思考を重視して戦います。",
            base_hp=70,
            base_attack=70,
            base_defense=70,
            base_speed=70,
            ability_ids=[1, 2, 3]  # 強打、防御態勢、回復
        )

        assert len(result["abilities"]) == 3

    @pytest.mark.asyncio


    async def test_create_character_too_many_abilities(self, db_conn, test_account):
        """アビリティが4個以上でエラー"""
        with pytest.raises(ValidationError) as exc_info:
            await character.create_character(
                db_conn,
                account_id=test_account,
                name="魔法使い",
                prompt="多彩な魔法を操る魔法使いです。状況に応じて様々な魔法を使い分けます。戦略的な思考を重視して戦います。",
                base_hp=70,
                base_attack=70,
                base_defense=70,
                base_speed=70,
                ability_ids=[1, 2, 3, 4]
            )

        assert "最大3個" in str(exc_info.value)

    @pytest.mark.asyncio


    async def test_create_character_duplicate_abilities(self, db_conn, test_account):
        """重複するアビリティでエラー"""
        with pytest.raises(ValidationError) as exc_info:
            await character.create_character(
                db_conn,
                account_id=test_account,
                name="戦士",
                prompt="戦士です。" + "a" * 50,
                base_hp=70,
                base_attack=70,
                base_defense=70,
                base_speed=70,
                ability_ids=[1, 1, 2]
            )

        assert "同じアビリティ" in str(exc_info.value)

    @pytest.mark.asyncio


    async def test_create_character_invalid_ability_id(self, db_conn, test_account):
        """存在しないアビリティIDでエラー"""
        with pytest.raises(ValidationError) as exc_info:
            await character.create_character(
                db_conn,
                account_id=test_account,
                name="戦士",
                prompt="戦士です。" + "a" * 50,
                base_hp=70,
                base_attack=70,
                base_defense=70,
                base_speed=70,
                ability_ids=[999]
            )

        assert "存在しません" in str(exc_info.value)

    @pytest.mark.asyncio


    async def test_create_character_empty_name(self, db_conn, test_account):
        """空のキャラクター名でエラー"""
        with pytest.raises(ValidationError) as exc_info:
            await character.create_character(
                db_conn,
                account_id=test_account,
                name="",
                prompt="テスト用のキャラクターです。" + "a" * 50,
                base_hp=70,
                base_attack=70,
                base_defense=70,
                base_speed=70
            )

        assert "キャラクター名を入力してください" in str(exc_info.value)

    @pytest.mark.asyncio


    async def test_create_character_too_long_name(self, db_conn, test_account):
        """長すぎるキャラクター名でエラー"""
        with pytest.raises(ValidationError) as exc_info:
            await character.create_character(
                db_conn,
                account_id=test_account,
                name="a" * 51,
                prompt="テスト用のキャラクターです。" + "a" * 50,
                base_hp=70,
                base_attack=70,
                base_defense=70,
                base_speed=70
            )

        assert "1-50文字" in str(exc_info.value)

    @pytest.mark.asyncio


    async def test_create_character_prompt_too_short(self, db_conn, test_account):
        """短すぎるプロンプトでエラー"""
        with pytest.raises(ValidationError) as exc_info:
            await character.create_character(
                db_conn,
                account_id=test_account,
                name="戦士",
                prompt="短い",
                base_hp=70,
                base_attack=70,
                base_defense=70,
                base_speed=70
            )

        assert "50文字以上" in str(exc_info.value)

    @pytest.mark.asyncio


    async def test_create_character_prompt_too_long(self, db_conn, test_account):
        """長すぎるプロンプトでエラー"""
        with pytest.raises(ValidationError) as exc_info:
            await character.create_character(
                db_conn,
                account_id=test_account,
                name="戦士",
                prompt="a" * 2001,
                base_hp=70,
                base_attack=70,
                base_defense=70,
                base_speed=70
            )

        assert "2000文字以内" in str(exc_info.value)

    @pytest.mark.asyncio


    async def test_create_character_stats_too_low(self, db_conn, test_account):
        """ステータス合計値が低すぎる場合のエラー"""
        with pytest.raises(ValidationError) as exc_info:
            await character.create_character(
                db_conn,
                account_id=test_account,
                name="弱キャラ",
                prompt="とても弱いキャラクターです。" + "a" * 50,
                base_hp=60,
                base_attack=60,
                base_defense=60,
                base_speed=60  # 合計240 < 280
            )

        assert "280-400" in str(exc_info.value)

    @pytest.mark.asyncio


    async def test_create_character_stats_too_high(self, db_conn, test_account):
        """ステータス合計値が高すぎる場合のエラー"""
        with pytest.raises(ValidationError) as exc_info:
            await character.create_character(
                db_conn,
                account_id=test_account,
                name="強キャラ",
                prompt="とても強いキャラクターです。" + "a" * 50,
                base_hp=100,
                base_attack=100,
                base_defense=100,
                base_speed=101  # 合計401 > 400
            )

        assert "280-400" in str(exc_info.value)

    @pytest.mark.asyncio


    async def test_create_character_stats_min_boundary(self, db_conn, test_account):
        """ステータス合計値の下限ぎりぎりで成功"""
        result = await character.create_character(
            db_conn,
            account_id=test_account,
            name="バランス型",
            prompt="バランスの取れたキャラクターです。" + "a" * 50,
            base_hp=70,
            base_attack=70,
            base_defense=70,
            base_speed=70  # 合計280
        )

        assert result["character_id"] > 0

    @pytest.mark.asyncio


    async def test_create_character_stats_max_boundary(self, db_conn, test_account):
        """ステータス合計値の上限ぎりぎりで成功"""
        result = await character.create_character(
            db_conn,
            account_id=test_account,
            name="パワー型",
            prompt="圧倒的なパワーを持つキャラクターです。" + "a" * 50,
            base_hp=100,
            base_attack=100,
            base_defense=100,
            base_speed=100  # 合計400
        )

        assert result["character_id"] > 0

    @pytest.mark.asyncio


    async def test_create_character_individual_stat_out_of_range(self, db_conn, test_account):
        """個別ステータスが範囲外でエラー"""
        # HPが範囲外（ステータス合計は280-400の範囲内に調整）
        with pytest.raises(ValidationError) as exc_info:
            await character.create_character(
                db_conn,
                account_id=test_account,
                name="テスト",
                prompt="テストキャラです。" + "a" * 50,
                base_hp=5,  # 10未満
                base_attack=95,
                base_defense=95,
                base_speed=95  # 合計290
            )
        assert "基礎HP" in str(exc_info.value)

        # 攻撃力が範囲外（ステータス合計は280-400の範囲内に調整）
        with pytest.raises(ValidationError) as exc_info:
            await character.create_character(
                db_conn,
                account_id=test_account,
                name="テスト",
                prompt="テストキャラです。" + "a" * 50,
                base_hp=96,
                base_attack=101,  # 100超過
                base_defense=96,
                base_speed=97  # 合計390
            )
        assert "基礎攻撃力" in str(exc_info.value)


class TestGetCharacterInfo:
    """get_character_infoツールのテスト"""

    @pytest.mark.asyncio


    async def test_get_character_info_success(self, db_conn, test_account):
        """正常なキャラクター情報取得"""
        # キャラクター作成
        create_result = await character.create_character(
            db_conn,
            account_id=test_account,
            name="テストキャラ",
            prompt="テスト用のキャラクターです。" + "a" * 50,
            base_hp=80,
            base_attack=70,
            base_defense=60,
            base_speed=90,
            ability_ids=[1, 2]
        )
        character_id = create_result["character_id"]

        # 情報取得
        result = character.get_character_info(db_conn, character_id)

        assert result["id"] == character_id
        assert result["name"] == "テストキャラ"
        assert result["level"] == 1
        assert result["base_stats"]["hp"] == 80
        assert result["computed_stats"]["hp"] == 80
        assert len(result["abilities"]) == 2
        assert "stats" in result
        assert result["stats"]["rating"] == 1000

    @pytest.mark.asyncio


    async def test_get_character_info_nonexistent(self, db_conn):
        """存在しないキャラクターIDでエラー"""
        with pytest.raises(ValidationError) as exc_info:
            character.get_character_info(db_conn, 999)

        assert "存在しません" in str(exc_info.value)


class TestListMyCharacters:
    """list_my_charactersツールのテスト"""

    @pytest.mark.asyncio


    async def test_list_my_characters_empty(self, db_conn, test_account):
        """キャラクターなしの場合"""
        result = character.list_my_characters(db_conn, test_account)
        assert isinstance(result, list)
        assert len(result) == 0

    @pytest.mark.asyncio


    async def test_list_my_characters_multiple(self, db_conn, test_account):
        """複数キャラクターの一覧取得"""
        # キャラクター作成
        await character.create_character(
            db_conn, test_account, "キャラ1",
            "キャラクター1です。" + "a" * 50,
            70, 70, 70, 70, []
        )
        await character.create_character(
            db_conn, test_account, "キャラ2",
            "キャラクター2です。" + "a" * 50,
            80, 60, 70, 70, []
        )

        # 一覧取得
        result = character.list_my_characters(db_conn, test_account)

        assert len(result) == 2
        # キャラクターが2つ存在することを確認
        names = [char["name"] for char in result]
        assert "キャラ1" in names
        assert "キャラ2" in names


class TestListAbilities:
    """list_abilitiesツールのテスト"""

    @pytest.mark.asyncio


    async def test_list_abilities_success(self, db_conn):
        """正常なアビリティ一覧取得"""
        result = character.list_abilities(db_conn)

        assert isinstance(result, list)
        assert len(result) == 7  # 初期データのアビリティ数

        # 各アビリティの情報が含まれているか確認
        ability = result[0]
        assert "id" in ability
        assert "name" in ability
        assert "description" in ability
        assert "effect_type" in ability
        assert "power" in ability
        assert "cost" in ability
        assert "cooldown" in ability


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
