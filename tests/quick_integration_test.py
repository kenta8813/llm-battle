"""
簡易統合テスト - 主要な機能の動作確認
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


def main():
    print("=" * 70)
    print("LLMバトルゲーム 簡易統合テスト")
    print("=" * 70)
    print()

    # テスト用データベースを作成
    tmpdir = tempfile.mkdtemp()
    db_path = Path(tmpdir) / 'test_llmbattle.db'
    print(f"テスト用データベース: {db_path}\n")

    # データベースを初期化
    success = initialize_database(db_path=db_path, force=True)
    if not success:
        print("❌ データベースの初期化に失敗しました")
        return False

    print("✓ データベース初期化成功\n")

    # テスト実行
    conn = get_connection(db_path=str(db_path))

    try:
        # 1. アカウント作成
        print("1. アカウント作成...")
        acc1 = account.create_account(conn, "player1")
        acc2 = account.create_account(conn, "player2")
        print(f"   - player1: account_id={acc1['account_id']}")
        print(f"   - player2: account_id={acc2['account_id']}")
        print("   ✓ 成功\n")

        # 2. アビリティ一覧取得
        print("2. アビリティ一覧取得...")
        abilities = character.list_abilities(conn)
        print(f"   - {len(abilities)}個のアビリティが存在")
        print("   ✓ 成功\n")

        # 3. キャラクター作成
        print("3. キャラクター作成...")
        char1 = character.create_character(
            conn,
            acc1["account_id"],
            name="勇者",
            prompt="正義の勇者です。" + "a" * 60,
            base_hp=90,
            base_attack=80,
            base_defense=70,
            base_speed=60,
            ability_ids=[abilities[0]["id"]]
        )
        print(f"   - 勇者: character_id={char1['character_id']}")

        char2 = character.create_character(
            conn,
            acc2["account_id"],
            name="魔王",
            prompt="闇の魔王です。" + "b" * 60,
            base_hp=100,
            base_attack=90,
            base_defense=60,
            base_speed=50,
            ability_ids=[abilities[1]["id"]]
        )
        print(f"   - 魔王: character_id={char2['character_id']}")
        print("   ✓ 成功\n")

        # 4. マッチング
        print("4. マッチング...")
        result1 = battle.join_queue(conn, char1["character_id"])
        print(f"   - player1 join queue: status={result1['status']}")

        result2 = battle.join_queue(conn, char2["character_id"])
        print(f"   - player2 join queue: status={result2['status']}")

        if result2["status"] == "matched":
            battle_id = result2["battle_id"]
            print(f"   - マッチング成立! battle_id={battle_id}")
            print("   ✓ 成功\n")
        else:
            print("   ❌ マッチングに失敗しました")
            return False

        # 5. バトル実行
        print("5. バトル実行...")
        for turn in range(20):
            status = battle.get_battle_status(conn, battle_id)
            print(f"   - ターン{turn + 1}: P1 HP={status['player1']['hp']}, P2 HP={status['player2']['hp']}")

            if status["status"] == "finished":
                print("   - バトル終了!")
                break

            battle.execute_turn(conn, battle_id, char1["character_id"], "attack")

        print("   ✓ 成功\n")

        # 6. 戦績確認
        print("6. 戦績確認...")
        stats1 = stats.get_character_stats(conn, char1["character_id"])
        stats2 = stats.get_character_stats(conn, char2["character_id"])

        print(f"   - 勇者: 戦績={stats1['wins']}勝{stats1['losses']}敗{stats1['draws']}分")
        print(f"   - 魔王: 戦績={stats2['wins']}勝{stats2['losses']}敗{stats2['draws']}分")
        print("   ✓ 成功\n")

        # 7. リーダーボード
        print("7. リーダーボード...")
        leaderboard = stats.get_leaderboard(conn, limit=10)
        print(f"   - {len(leaderboard)}キャラクターがランクイン")
        for i, char in enumerate(leaderboard[:3], 1):
            print(f"   {i}位: {char['name']} (Rating: {char['rating']})")
        print("   ✓ 成功\n")

        print("=" * 70)
        print("✓ すべてのテストが成功しました!")
        print("=" * 70)

        conn.close()
        return True

    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        conn.close()
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
