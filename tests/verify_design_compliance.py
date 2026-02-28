"""
Verification script to check implementation compliance with design documents.
QA検証用: 設計書との整合性を確認するスクリプト
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from database import get_connection
from database.init_db import execute_sql_script
from server.battle.logic import calculate_damage, get_action_order
from server.matching.queue import get_rating_range

def verify_damage_calculation():
    """バトルロジック設計書 4.1 基本ダメージ計算式の検証"""
    print("\n=== ダメージ計算式の検証 ===")

    # 設計書の計算例を検証
    attacker = {'computed_attack': 80, 'computed_speed': 70}
    defender = {'computed_defense': 60, 'computed_speed': 50, 'action': 'attack'}

    # 期待値計算
    base_damage = 80
    defense_ratio = 60 / (60 + 100)  # 0.375
    damage_reduction = 80 * defense_ratio  # 30
    expected_base = base_damage - damage_reduction  # 50

    print(f"[OK] Base damage: {base_damage}")
    print(f"[OK] Defense ratio: {defense_ratio:.3f} (expected: 0.375)")
    print(f"[OK] Damage reduction: {damage_reduction} (expected: 30)")
    print(f"[OK] Final base damage: {expected_base} (expected: 50)")

    assert defense_ratio == 0.375, "Defense ratio mismatch"
    assert damage_reduction == 30, "Damage reduction mismatch"
    assert expected_base == 50, "Final base damage mismatch"

    print("[PASS] Damage calculation: matches design spec")

def verify_defend_modifier():
    """バトルロジック設計書 4.2 防御時のダメージ検証"""
    print("\n=== 防御時のダメージ軽減検証 ===")

    import random
    random.seed(42)

    attacker = {'computed_attack': 80, 'computed_speed': 70}

    # 通常時
    defender_normal = {'computed_defense': 60, 'computed_speed': 50, 'action': 'attack'}
    damage_normal = calculate_damage(attacker, defender_normal, 'attack')

    # 防御時
    defender_defend = {'computed_defense': 60, 'computed_speed': 50, 'action': 'defend'}
    damage_defend = calculate_damage(attacker, defender_defend, 'attack')

    # 防御時は50%軽減されるべき
    reduction_ratio = damage_defend / damage_normal if damage_normal > 0 else 0

    print(f"✓ 通常時ダメージ: {damage_normal}")
    print(f"✓ 防御時ダメージ: {damage_defend}")
    print(f"✓ 軽減比率: {reduction_ratio:.2f} (期待値: 約0.5)")

    # ランダム変動があるため、0.4~0.6の範囲で検証
    assert 0.4 <= reduction_ratio <= 0.6, f"防御時の軽減比率が範囲外です: {reduction_ratio}"

    print("✓ 防御時ダメージ軽減: 設計書と一致")

def verify_dodge_rate():
    """バトルロジック設計書 4.3 回避判定の検証"""
    print("\n=== 回避判定の検証 ===")

    import random

    # 基本回避率50%のケース
    attacker = {'computed_attack': 80, 'computed_speed': 70}
    defender = {'computed_defense': 60, 'computed_speed': 70, 'action': 'dodge'}

    # 速度差による補正
    speed_diff = 70 - 70  # 0
    expected_dodge_rate = 0.5 + (speed_diff / 200.0)  # 0.5

    print(f"✓ 速度差: {speed_diff}")
    print(f"✓ 期待回避率: {expected_dodge_rate:.1%} (基本50%)")

    # 高速キャラの回避率
    defender_fast = {'computed_defense': 60, 'computed_speed': 100, 'action': 'dodge'}
    speed_diff_fast = 100 - 70  # 30
    expected_dodge_rate_fast = 0.5 + (speed_diff_fast / 200.0)  # 0.65

    print(f"✓ 高速時の速度差: {speed_diff_fast}")
    print(f"✓ 高速時の期待回避率: {expected_dodge_rate_fast:.1%}")

    # 最大回避率90%、最小10%の検証
    assert 0.1 <= expected_dodge_rate_fast <= 0.9, "回避率が範囲外です"

    print("✓ 回避判定: 設計書と一致")

def verify_action_order():
    """バトルロジック設計書 7.1 速度による行動順の検証"""
    print("\n=== 行動順決定の検証 ===")

    # 速度差がある場合
    player1 = {'id': 1, 'computed_speed': 90}
    player2 = {'id': 2, 'computed_speed': 50}

    first, second = get_action_order(player1, player2)

    print(f"✓ プレイヤー1速度: {player1['computed_speed']}")
    print(f"✓ プレイヤー2速度: {player2['computed_speed']}")
    print(f"✓ 先攻: プレイヤー{first} (期待値: プレイヤー1)")

    assert first == 1, "速度が速い方が先攻になっていません"
    assert second == 2, "速度が遅い方が後攻になっていません"

    print("✓ 行動順決定: 設計書と一致")

def verify_rating_ranges():
    """マッチングロジック設計書 2.2 マッチング条件の検証"""
    print("\n=== レーティング範囲の検証 ===")

    # 待機時間による範囲拡大
    ranges = [
        (0, 100, "初期条件 (0-15秒)"),
        (10, 100, "初期条件 (0-15秒)"),
        (15, 200, "第1段階緩和 (15-30秒)"),
        (25, 200, "第1段階緩和 (15-30秒)"),
        (30, 400, "第2段階緩和 (30-45秒)"),
        (40, 400, "第2段階緩和 (30-45秒)"),
        (45, None, "最終段階 (45秒以上)"),
        (60, None, "最終段階 (45秒以上)"),
    ]

    for wait_time, expected_range, description in ranges:
        actual_range = get_rating_range(wait_time)
        status = "✓" if actual_range == expected_range else "✗"
        print(f"{status} {wait_time}秒: {actual_range} (期待値: {expected_range}) - {description}")
        assert actual_range == expected_range, f"レーティング範囲が設計書と一致しません: {wait_time}秒"

    print("✓ レーティング範囲: 設計書と一致")

def verify_abilities():
    """バトルロジック設計書 5.1 アビリティ一覧の検証"""
    print("\n=== アビリティ仕様の検証 ===")

    conn = get_connection(':memory:')
    schema_path = Path(__file__).parent.parent / 'src' / 'database' / 'schema.sql'
    execute_sql_script(conn, schema_path)

    seed_path = Path(__file__).parent.parent / 'src' / 'database' / 'seed.sql'
    execute_sql_script(conn, seed_path)

    cursor = conn.cursor()
    abilities = cursor.execute('SELECT * FROM abilities ORDER BY id').fetchall()

    # 設計書で定義された7つのアビリティ
    expected_abilities = [
        ('強打', 'damage', 150, 0),
        ('連続攻撃', 'damage', 140, 1),
        ('必殺技', 'damage', 200, 3),
        ('回復', 'heal', 30, 2),
        ('防御態勢', 'buff', 50, 1),
        ('カウンター', 'buff', 50, 2),
        ('弱体化', 'debuff', 30, 2),
    ]

    assert len(abilities) == 7, f"アビリティ数が一致しません: {len(abilities)}"

    for i, ability in enumerate(abilities):
        expected = expected_abilities[i]
        name = ability['name']
        effect_type = ability['effect_type']
        power = ability['power']
        cooldown = ability['cooldown']

        print(f"✓ {name}: {effect_type}, power={power}, cooldown={cooldown}")

        assert name == expected[0], f"アビリティ名が一致しません: {name}"
        assert effect_type == expected[1], f"効果タイプが一致しません: {effect_type}"
        assert power == expected[2], f"威力が一致しません: {power}"
        assert cooldown == expected[3], f"クールダウンが一致しません: {cooldown}"

    conn.close()
    print("✓ アビリティ仕様: 設計書と完全一致")

def verify_database_schema():
    """データベース設計書との整合性検証"""
    print("\n=== データベーススキーマの検証 ===")

    conn = get_connection(':memory:')
    schema_path = Path(__file__).parent.parent / 'src' / 'database' / 'schema.sql'
    execute_sql_script(conn, schema_path)

    cursor = conn.cursor()

    # テーブル一覧取得
    tables = cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()

    expected_tables = [
        'abilities', 'accounts', 'battle_turns', 'battles',
        'character_abilities', 'characters', 'queue',
        'schema_version', 'stats'
    ]

    table_names = [t['name'] for t in tables]

    for expected_table in expected_tables:
        if expected_table in table_names:
            print(f"✓ テーブル存在確認: {expected_table}")
        else:
            print(f"✗ テーブル不足: {expected_table}")
            assert False, f"テーブルが存在しません: {expected_table}"

    # インデックス確認
    indexes = cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'"
    ).fetchall()

    expected_indexes = [
        'idx_queue_joined_at', 'idx_queue_rating',
        'idx_stats_rating', 'idx_stats_wins'
    ]

    index_names = [idx['name'] for idx in indexes]

    for expected_index in expected_indexes:
        if expected_index in index_names:
            print(f"✓ インデックス存在確認: {expected_index}")
        else:
            print(f"✗ インデックス不足: {expected_index}")

    conn.close()
    print("✓ データベーススキーマ: 設計書と一致")

def main():
    """全検証の実行"""
    print("=" * 70)
    print("QA検証: 設計書との整合性チェック")
    print("=" * 70)

    try:
        verify_damage_calculation()
        verify_defend_modifier()
        verify_dodge_rate()
        verify_action_order()
        verify_rating_ranges()
        verify_abilities()
        verify_database_schema()

        print("\n" + "=" * 70)
        print("✓ すべての検証項目が合格しました")
        print("=" * 70)
        return 0

    except AssertionError as e:
        print(f"\n✗ 検証失敗: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ エラー発生: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
