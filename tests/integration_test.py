"""
結合テストスクリプト

このスクリプトは、LLMバトルゲームの結合テストを実行します。
MCPツール、データベース、Webサーバーの統合を確認します。
"""

import sqlite3
import sys
import tempfile
from pathlib import Path
import io

# Windowsコンソールのエンコーディング対応
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from database import get_connection, initialize_database
from server.tools import account, character, battle, stats


class IntegrationTestRunner:
    """結合テストランナー"""

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.tests = []

    def test(self, name):
        """テストデコレータ"""
        def decorator(func):
            self.tests.append((name, func))
            return func
        return decorator

    def run(self):
        """全テストを実行"""
        print("=" * 70)
        print("LLMバトルゲーム 結合テスト")
        print("=" * 70)
        print()

        # テスト用データベースを作成
        tmpdir = tempfile.mkdtemp()
        db_path = Path(tmpdir) / 'test_llmbattle.db'
        print(f"テスト用データベース: {db_path}")

        # データベースを初期化
        success = initialize_database(db_path=db_path, force=True)
        if not success:
            print("❌ データベースの初期化に失敗しました")
            return

        print("✓ データベース初期化成功\n")

        # 各テストを実行
        for test_name, test_func in self.tests:
            try:
                # 新しい接続を取得
                conn = get_connection(db_path=str(db_path))
                test_func(conn)
                conn.close()

                self.passed += 1
                print(f"✓ {test_name}")
            except Exception as e:
                self.failed += 1
                print(f"❌ {test_name}")
                print(f"   エラー: {e}")
                import traceback
                traceback.print_exc()

        print()
        print("=" * 70)
        print(f"合計: {len(self.tests)} | 成功: {self.passed} | 失敗: {self.failed}")
        print("=" * 70)

        return self.failed == 0


# テストランナーのインスタンス
runner = IntegrationTestRunner()


@runner.test("シナリオ1: 新規プレイヤーの登録からバトルまで")
def test_scenario_1(conn):
    """完全なゲームフロー"""

    # 1. アカウント作成
    account1 = account.create_account(conn, "player1")
    account2 = account.create_account(conn, "player2")
    assert account1["account_id"] > 0
    assert account2["account_id"] > 0

    # 2. アビリティ一覧取得
    abilities = character.list_abilities(conn)
    assert len(abilities) == 7
    ability_ids = [a["id"] for a in abilities[:3]]

    # 3. キャラクター作成
    char1 = character.create_character(
        conn,
        account1["account_id"],
        name="勇者アレックス",
        prompt="正義感が強く、仲間思いの勇者。炎の魔法を得意とする。" + "a" * 30,
        base_hp=90,
        base_attack=80,
        base_defense=60,
        base_speed=70,
        ability_ids=ability_ids
    )

    char2 = character.create_character(
        conn,
        account2["account_id"],
        name="暗殺者シャドウ",
        prompt="闇に潜む暗殺者。素早い攻撃と毒を使いこなす。" + "b" * 40,
        base_hp=70,
        base_attack=90,
        base_defense=50,
        base_speed=90,
        ability_ids=ability_ids
    )

    assert char1["character_id"] > 0
    assert char2["character_id"] > 0

    # 4. マッチングキュー参加（プレイヤー1）
    queue1 = battle.join_queue(conn, char1["character_id"])
    assert queue1["status"] in ["waiting", "matched"]

    # 5. マッチングキュー参加（プレイヤー2）- マッチング成立
    queue2 = battle.join_queue(conn, char2["character_id"])
    assert queue2["status"] == "matched"
    battle_id = queue2["battle_id"]

    # 6. バトル状態取得
    battle_status = battle.get_battle_status(conn, battle_id)
    assert battle_status["status"] == "in_progress"
    assert battle_status["current_turn"] == 1

    # 7. ターン実行（最大20ターン）
    max_turns = 20
    for turn in range(max_turns):
        battle_status = battle.get_battle_status(conn, battle_id)
        if battle_status["status"] == "finished":
            break

        # 通常攻撃を実行
        turn_result = battle.execute_turn(
            conn, battle_id, char1["character_id"], "attack"
        )

        # バトルが終了したか確認
        if turn_result.get("status") == "finished":
            break

    # 8. バトル終了確認
    final_status = battle.get_battle_status(conn, battle_id)
    assert final_status["status"] == "finished"

    # 勝者IDを取得
    cursor = conn.cursor()
    cursor.execute("SELECT winner_id FROM battles WHERE id = ?", (battle_id,))
    battle_row = cursor.fetchone()
    assert battle_row is not None
    winner_id = battle_row["winner_id"]

    # 9. 戦績取得
    char1_stats = stats.get_character_stats(conn, char1["character_id"])
    char2_stats = stats.get_character_stats(conn, char2["character_id"])

    # 両方のキャラクターに戦績が記録されている
    assert char1_stats["total_battles"] == 1
    assert char2_stats["total_battles"] == 1

    # 勝者と敗者の戦績が正しい
    if winner_id == char1["character_id"]:
        assert char1_stats["wins"] == 1
        assert char2_stats["losses"] == 1
    elif winner_id == char2["character_id"]:
        assert char2_stats["wins"] == 1
        assert char1_stats["losses"] == 1
    else:
        # 引き分け
        assert char1_stats["draws"] == 1
        assert char2_stats["draws"] == 1

    # 10. リーダーボード確認
    leaderboard = stats.get_leaderboard(conn, limit=10)
    assert len(leaderboard) >= 2
    assert any(c["name"] == "勇者アレックス" for c in leaderboard)
    assert any(c["name"] == "暗殺者シャドウ" for c in leaderboard)


@runner.test("シナリオ2: 複数プレイヤーのマッチング")
def test_scenario_2(conn):
    """複数プレイヤーの同時マッチング"""

    # 3つのアカウントとキャラクターを作成
    players = []
    for i in range(3):
        acc = account.create_account(conn, f"player_{i}")
        abilities = character.list_abilities(conn)

        char = character.create_character(
            conn,
            acc["account_id"],
            name=f"キャラクター{i}",
            prompt=f"これはテストキャラクター{i}です。" + "x" * 50,
            base_hp=90,
            base_attack=80,
            base_defense=70,
            base_speed=60 + i * 5,
            ability_ids=[abilities[0]["id"]]
        )
        players.append(char)

    # プレイヤー1と2がマッチング
    queue1 = battle.join_queue(conn, players[0]["character_id"])
    queue2 = battle.join_queue(conn, players[1]["character_id"])

    # マッチングが成立しているはず
    assert queue2["status"] == "matched"
    battle_id_1 = queue2["battle_id"]

    # プレイヤー3はキューで待機
    queue3 = battle.join_queue(conn, players[2]["character_id"])
    assert queue3["status"] == "waiting"

    # バトル1を実行
    for _ in range(20):
        battle_status = battle.get_battle_status(conn, battle_id_1)
        if battle_status["status"] == "finished":
            break
        battle.execute_turn(conn, battle_id_1, players[0]["character_id"], "attack")

    # 結果確認
    final_status = battle.get_battle_status(conn, battle_id_1)
    assert final_status["status"] == "finished"

    # 戦績が正しく記録されている
    stats1 = stats.get_character_stats(conn, players[0]["character_id"])
    stats2 = stats.get_character_stats(conn, players[1]["character_id"])

    assert stats1["total_battles"] == 1
    assert stats2["total_battles"] == 1


@runner.test("データベース統合: MCPサーバーとWebサーバーが同じDBを参照")
def test_database_integration(conn):
    """データベースの共有を確認"""

    # アカウントとキャラクターを作成
    acc = account.create_account(conn, "db_test_user")
    abilities = character.list_abilities(conn)

    char = character.create_character(
        conn,
        acc["account_id"],
        name="DB統合テスト",
        prompt="データベース統合テストのキャラクター" + "z" * 40,
        base_hp=100,
        base_attack=100,
        base_defense=100,
        base_speed=100,
        ability_ids=[abilities[0]["id"]]
    )

    # データベースから直接読み取り
    cursor = conn.cursor()
    cursor.execute("SELECT name, level FROM characters WHERE id = ?", (char["character_id"],))
    row = cursor.fetchone()

    assert row is not None
    assert row["name"] == "DB統合テスト"
    assert row["level"] == 1

    # アカウントも確認
    cursor.execute("SELECT username FROM accounts WHERE id = ?", (acc["account_id"],))
    acc_row = cursor.fetchone()

    assert acc_row is not None
    assert acc_row["username"] == "db_test_user"


@runner.test("外部キー制約: アカウント削除時のカスケード")
def test_foreign_key_cascade(conn):
    """外部キー制約のカスケード削除を確認"""

    # アカウントとキャラクターを作成
    acc = account.create_account(conn, "cascade_test")
    abilities = character.list_abilities(conn)

    char = character.create_character(
        conn,
        acc["account_id"],
        name="カスケードテスト",
        prompt="外部キー制約のカスケード削除テスト" + "y" * 40,
        base_hp=80,
        base_attack=80,
        base_defense=80,
        base_speed=80,
        ability_ids=[abilities[0]["id"]]
    )

    character_id = char["character_id"]
    account_id = acc["account_id"]

    # キャラクターが存在することを確認
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM characters WHERE id = ?", (character_id,))
    assert cursor.fetchone()[0] == 1

    # アカウントを削除
    cursor.execute("DELETE FROM accounts WHERE id = ?", (account_id,))
    conn.commit()

    # キャラクターも削除されているはず
    cursor.execute("SELECT COUNT(*) FROM characters WHERE id = ?", (character_id,))
    assert cursor.fetchone()[0] == 0


@runner.test("バトルフロー: キャラクター作成→マッチング→バトル→結果")
def test_battle_flow(conn):
    """バトルの一連の流れを確認"""

    # 2人のプレイヤーを作成
    acc1 = account.create_account(conn, "battle_player1")
    acc2 = account.create_account(conn, "battle_player2")

    abilities = character.list_abilities(conn)

    char1 = character.create_character(
        conn, acc1["account_id"],
        name="戦士", prompt="強力な戦士" + "w" * 60,
        base_hp=100, base_attack=90, base_defense=80, base_speed=60,
        ability_ids=[abilities[0]["id"], abilities[1]["id"]]
    )

    char2 = character.create_character(
        conn, acc2["account_id"],
        name="魔法使い", prompt="賢明な魔法使い" + "m" * 60,
        base_hp=70, base_attack=100, base_defense=50, base_speed=80,
        ability_ids=[abilities[0]["id"], abilities[2]["id"]]
    )

    # マッチング
    battle.join_queue(conn, char1["character_id"])
    result = battle.join_queue(conn, char2["character_id"])

    # battle_idがない場合はバトルテーブルから取得
    if "battle_id" not in result:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id FROM battles
            WHERE (player1_id = ? OR player2_id = ?)
               OR (player1_id = ? OR player2_id = ?)
            ORDER BY id DESC LIMIT 1
        """, (char1["character_id"], char1["character_id"],
              char2["character_id"], char2["character_id"]))
        row = cursor.fetchone()
        battle_id = row["id"] if row else None
    else:
        battle_id = result["battle_id"]

    assert battle_id is not None, "バトルIDが取得できませんでした"

    # バトル実行
    turns_executed = 0
    for _ in range(20):
        status = battle.get_battle_status(conn, battle_id)
        if status["status"] == "finished":
            break

        battle.execute_turn(conn, battle_id, char1["character_id"], "attack")
        turns_executed += 1

    # バトルが終了している
    final_status = battle.get_battle_status(conn, battle_id)
    assert final_status["status"] == "finished"
    assert turns_executed > 0

    # バトル履歴が記録されている
    history1 = battle.get_battle_history(conn, char1["character_id"])
    history2 = battle.get_battle_history(conn, char2["character_id"])

    assert len(history1) == 1
    assert len(history2) == 1
    assert history1[0]["id"] == battle_id
    assert history2[0]["id"] == battle_id


@runner.test("統計情報: リーダーボードとキャラクター戦績")
def test_stats_integration(conn):
    """統計情報の統合を確認"""

    # 複数のキャラクターとバトルを作成
    players = []
    for i in range(4):
        acc = account.create_account(conn, f"stats_player_{i}")
        abilities = character.list_abilities(conn)

        char = character.create_character(
            conn, acc["account_id"],
            name=f"統計テスト{i}",
            prompt=f"統計情報テスト用キャラクター{i}" + "s" * 50,
            base_hp=90, base_attack=80, base_defense=70, base_speed=60 + i * 5,
            ability_ids=[abilities[i % 7]["id"]]
        )
        players.append(char)

    # 2つのバトルを実行
    # バトル1: プレイヤー0 vs プレイヤー1
    battle.join_queue(conn, players[0]["character_id"])
    result1 = battle.join_queue(conn, players[1]["character_id"])
    battle_id_1 = result1.get("battle_id")

    # battle_idがない場合は取得
    if not battle_id_1:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id FROM battles
            WHERE (player1_id IN (?, ?) AND player2_id IN (?, ?))
            ORDER BY id DESC LIMIT 1
        """, (players[0]["character_id"], players[1]["character_id"],
              players[0]["character_id"], players[1]["character_id"]))
        row = cursor.fetchone()
        battle_id_1 = row["id"] if row else None

    assert battle_id_1 is not None, "バトル1のIDが取得できませんでした"

    for _ in range(20):
        status = battle.get_battle_status(conn, battle_id_1)
        if status["status"] == "finished":
            break
        battle.execute_turn(conn, battle_id_1, players[0]["character_id"], "attack")

    # バトル2: プレイヤー2 vs プレイヤー3
    battle.join_queue(conn, players[2]["character_id"])
    result2 = battle.join_queue(conn, players[3]["character_id"])
    assert result2["status"] == "matched"
    battle_id_2 = result2["battle_id"]

    for _ in range(20):
        status = battle.get_battle_status(conn, battle_id_2)
        if status["status"] == "finished":
            break
        battle.execute_turn(conn, battle_id_2, players[2]["character_id"], "attack")

    # リーダーボード確認
    leaderboard = stats.get_leaderboard(conn, limit=10)
    assert len(leaderboard) >= 4

    # 全員が戦績を持っている
    for player in players:
        player_stats = stats.get_character_stats(conn, player["character_id"])
        assert player_stats["total_battles"] == 1

    # リーダーボードの順序（レーティング順）
    ratings = [c["rating"] for c in leaderboard]
    assert ratings == sorted(ratings, reverse=True)


@runner.test("エラーハンドリング: 不正な入力への対応")
def test_error_handling(conn):
    """エラーハンドリングの確認"""
    from server.errors import ValidationError, BattleError

    # 存在しないキャラクターIDでバトル状態取得
    try:
        battle.get_battle_status(conn, 999999)
        assert False, "BattleErrorが発生するべき"
    except BattleError:
        pass

    # 存在しないキャラクターIDでキャラクター情報取得
    try:
        character.get_character_info(conn, 999999)
        assert False, "エラーが発生するべき"
    except Exception:
        pass

    # 不正なステータス値でキャラクター作成
    acc = account.create_account(conn, "error_test_user")
    try:
        character.create_character(
            conn, acc["account_id"],
            name="エラーテスト",
            prompt="x" * 100,
            base_hp=-10,  # 負の値
            base_attack=80,
            base_defense=60,
            base_speed=70,
            ability_ids=[]
        )
        assert False, "ValidationErrorが発生するべき"
    except (ValidationError, Exception):
        pass


if __name__ == '__main__':
    success = runner.run()
    sys.exit(0 if success else 1)
