# バトルロジック設計書

**プロジェクト**: LLMバトルゲーム
**作成日**: 2026-02-28
**担当**: Director

---

## 1. バトルシステム概要

### 1.1 基本コンセプト
- ターン制コマンドバトル
- LLMが完全自律的に行動を決定
- 「言ったもん勝ち」要素とゲームバランスの両立

### 1.2 勝利条件
1. 相手のHPを0以下にする
2. 最大ターン到達時、残りHPが多い方が勝利
3. 同HP時は引き分け

### 1.3 バトル進行
```
初期化 → ターン1 → ターン2 → ... → 勝敗判定 → 終了
```

---

## 2. ステータス設計

### 2.1 基本ステータス

#### HP（Hit Points）
- **役割**: 耐久力
- **範囲**: 基礎値 10-100
- **計算式**: `computed_hp = base_hp * (1 + (level - 1) * 0.1)`
- **バトル中**: 減少のみ（回復アビリティ除く）

#### 攻撃力（Attack）
- **役割**: 与ダメージの基準値
- **範囲**: 基礎値 10-100
- **計算式**: `computed_attack = base_attack * (1 + (level - 1) * 0.1)`
- **影響**: ダメージ計算に使用

#### 防御力（Defense）
- **役割**: 被ダメージ軽減
- **範囲**: 基礎値 10-100
- **計算式**: `computed_defense = base_defense * (1 + (level - 1) * 0.1)`
- **影響**: ダメージ軽減率に使用

#### 速度（Speed）
- **役割**: 行動順決定、回避率
- **範囲**: 基礎値 10-100
- **計算式**: `computed_speed = base_speed * (1 + (level - 1) * 0.1)`
- **影響**: 先攻後攻、回避成功率

### 2.2 ステータス合計制約
- 基礎ステータス合計: 280-400ポイント
- バランス型推奨: 各ステータス70ポイント（合計280）
- 特化型許可: 一点集中も可能（例: HP100, 攻撃100, 防御50, 速度50）

---

## 3. 行動システム

### 3.1 行動タイプ

#### 1. 通常攻撃（Attack）
- **説明**: 基本的な攻撃
- **ダメージ計算**: 後述のダメージ計算式
- **追加効果**: なし
- **消費**: なし

#### 2. 防御（Defend）
- **説明**: 次に受けるダメージを軽減
- **効果**: 被ダメージ 50%軽減
- **持続**: このターンのみ
- **反撃**: なし

#### 3. 回避（Dodge）
- **説明**: 攻撃を避ける試み
- **成功率**: `50% + (自分の速度 - 相手の速度) / 10`（最小10%、最大90%）
- **成功時**: ダメージ無効化
- **失敗時**: 通常通りダメージを受ける
- **反撃**: なし

#### 4. アビリティ（Ability）
- **説明**: 特殊技の使用
- **効果**: アビリティごとに異なる
- **クールダウン**: アビリティによる
- **制約**: クールダウン中は使用不可

### 3.2 行動決定フロー

```
[ターン開始]
    ↓
[プレイヤー1の行動決定]
    - LLMがキャラクター設定に基づいて行動選択
    - バトル状況（HP、ターン数など）を考慮
    ↓
[プレイヤー2の行動決定]
    - 同様にLLMが決定
    ↓
[行動順決定]
    - 速度ステータス比較
    - 速度が同じ場合はランダム
    ↓
[先攻者の行動解決]
    ↓
[後攻者の行動解決]
    - 先攻で倒された場合は行動不可
    ↓
[ターン終了処理]
    - HP更新
    - 状態異常更新（将来実装）
    - クールダウン減少
    ↓
[勝敗判定]
    - HP 0以下 → 勝敗確定
    - 最大ターン到達 → HP比較
    ↓
[次のターンまたは終了]
```

---

## 4. ダメージ計算

### 4.1 基本ダメージ計算式

```python
base_damage = attacker.attack * 1.0  # 基本倍率

# 防御力による軽減
defense_ratio = defender.defense / (defender.defense + 100)
damage_reduction = base_damage * defense_ratio

# 最終ダメージ
final_damage = base_damage - damage_reduction

# ランダム変動（±10%）
random_factor = random.uniform(0.9, 1.1)
final_damage = int(final_damage * random_factor)

# 最低保証ダメージ
final_damage = max(final_damage, 1)
```

#### 計算例
- 攻撃者攻撃力: 80
- 防御者防御力: 60

```
base_damage = 80
defense_ratio = 60 / (60 + 100) = 0.375
damage_reduction = 80 * 0.375 = 30
final_damage = 80 - 30 = 50
random_factor = 1.05（例）
final_damage = 50 * 1.05 = 52.5 → 52
```

### 4.2 防御時のダメージ

```python
if defender.action == 'defend':
    final_damage = final_damage * 0.5  # 50%軽減
```

### 4.3 回避判定

```python
dodge_base_rate = 0.5  # 基本50%
speed_diff = defender.speed - attacker.speed
dodge_rate = dodge_base_rate + (speed_diff / 200.0)

# 範囲制限
dodge_rate = max(0.1, min(0.9, dodge_rate))

# 判定
if random.random() < dodge_rate:
    final_damage = 0  # 完全回避
```

### 4.4 クリティカルヒット（オプション）

```python
critical_rate = 0.1  # 10%の確率

if random.random() < critical_rate:
    final_damage = final_damage * 1.5  # 1.5倍
```

---

## 5. アビリティシステム

### 5.1 アビリティ一覧

#### 攻撃系

##### 強打（Power Strike）
- **効果タイプ**: damage
- **威力**: 150（通常攻撃の1.5倍相当）
- **計算**: `damage = attacker.attack * 1.5`（防御計算は通常通り）
- **クールダウン**: なし
- **説明**: 強力な一撃を放つ

##### 連続攻撃（Double Strike）
- **効果タイプ**: damage
- **威力**: 140（各70%×2回）
- **計算**: 通常攻撃を2回実行（各70%のダメージ）
- **クールダウン**: 1ターン
- **説明**: 素早い2連撃

##### 必殺技（Ultimate）
- **効果タイプ**: damage
- **威力**: 200（通常攻撃の2倍）
- **計算**: `damage = attacker.attack * 2.0`
- **クールダウン**: 3ターン
- **説明**: 最大火力の一撃

#### 補助系

##### 回復（Heal）
- **効果タイプ**: heal
- **威力**: 30（最大HPの30%）
- **計算**: `heal_amount = character.max_hp * 0.3`
- **クールダウン**: 2ターン
- **説明**: 自身のHPを回復

##### 防御態勢（Guard Stance）
- **効果タイプ**: buff
- **威力**: 50（50%軽減）
- **効果**: 次のターンの被ダメージを50%軽減
- **持続**: 1ターン
- **クールダウン**: 1ターン
- **説明**: 防御力を一時的に強化

##### カウンター（Counter）
- **効果タイプ**: buff
- **威力**: 50（反撃ダメージ50%）
- **効果**: 攻撃を受けた時、相手に攻撃力の50%のダメージを与える
- **持続**: 1ターン
- **クールダウン**: 2ターン
- **説明**: 反撃態勢を取る

#### デバフ系

##### 弱体化（Weaken）
- **効果タイプ**: debuff
- **威力**: 30（30%減少）
- **効果**: 相手の攻撃力を1ターン30%減少
- **持続**: 1ターン
- **クールダウン**: 2ターン
- **説明**: 相手を弱体化させる

### 5.2 クールダウン管理

```python
# アビリティ使用時
ability_cooldowns[ability_id] = ability.cooldown

# 各ターン終了時
for ability_id in ability_cooldowns:
    if ability_cooldowns[ability_id] > 0:
        ability_cooldowns[ability_id] -= 1

# 使用可否チェック
def can_use_ability(ability_id):
    return ability_cooldowns.get(ability_id, 0) == 0
```

---

## 6. 状態異常システム（将来実装）

### 6.1 実装予定の状態異常

#### 毒（Poison）
- **効果**: 毎ターン最大HPの5%ダメージ
- **持続**: 3ターン
- **スタック**: 不可

#### 火傷（Burn）
- **効果**: 毎ターン固定ダメージ + 攻撃力10%減少
- **持続**: 2ターン
- **スタック**: 不可

#### スタン（Stun）
- **効果**: 1ターン行動不能
- **持続**: 1ターン
- **スタック**: 不可

---

## 7. 行動優先順位

### 7.1 速度による行動順

```python
def determine_turn_order(player1, player2):
    if player1.speed > player2.speed:
        return (player1, player2)
    elif player2.speed > player1.speed:
        return (player2, player1)
    else:
        # 速度が同じ場合はランダム
        if random.random() < 0.5:
            return (player1, player2)
        else:
            return (player2, player1)
```

### 7.2 同時行動の解決

基本的に速度順で解決するが、以下の場合は同時判定:

#### 相打ち
- 先攻の攻撃で後攻が倒される
- 後攻の反撃効果（カウンター）で先攻も倒される
- → 引き分け

---

## 8. ターン処理詳細

### 8.1 ターン開始時

```python
def start_turn(battle_id, turn_number):
    battle = get_battle(battle_id)

    # クールダウン減少
    decrease_cooldowns(battle.player1)
    decrease_cooldowns(battle.player2)

    # バフ/デバフ持続ターン減少
    decrease_buff_durations(battle.player1)
    decrease_buff_durations(battle.player2)

    # 状態異常ダメージ適用（将来実装）
    apply_status_damage(battle.player1)
    apply_status_damage(battle.player2)

    return battle
```

### 8.2 行動解決

```python
def resolve_action(attacker, defender, action, ability_id=None):
    result = {
        'attacker_id': attacker.id,
        'defender_id': defender.id,
        'action': action,
        'damage_dealt': 0,
        'damage_received': 0,
        'effects': []
    }

    if action == 'attack':
        damage = calculate_damage(attacker, defender)
        defender.current_hp -= damage
        result['damage_dealt'] = damage

        # カウンター判定
        if defender.has_buff('counter'):
            counter_damage = int(attacker.attack * 0.5)
            attacker.current_hp -= counter_damage
            result['damage_received'] = counter_damage
            result['effects'].append('counter')

    elif action == 'defend':
        attacker.add_buff('defend', duration=1)
        result['effects'].append('defend_ready')

    elif action == 'dodge':
        attacker.add_buff('dodge', duration=1)
        result['effects'].append('dodge_ready')

    elif action == 'ability':
        ability = get_ability(ability_id)
        execute_ability(attacker, defender, ability, result)

    return result
```

### 8.3 ターン終了時

```python
def end_turn(battle_id):
    battle = get_battle(battle_id)

    # HP上下限チェック
    battle.player1.current_hp = max(0, min(battle.player1.max_hp, battle.player1.current_hp))
    battle.player2.current_hp = max(0, min(battle.player2.max_hp, battle.player2.current_hp))

    # 勝敗判定
    winner = check_winner(battle)

    if winner or battle.current_turn >= battle.max_turns:
        end_battle(battle, winner)

    return battle
```

---

## 9. 勝敗判定

### 9.1 判定ロジック

```python
def check_winner(battle):
    player1 = battle.player1
    player2 = battle.player2

    # HP 0以下判定
    if player1.current_hp <= 0 and player2.current_hp <= 0:
        return None  # 引き分け

    if player1.current_hp <= 0:
        return player2.id

    if player2.current_hp <= 0:
        return player1.id

    # 最大ターン到達判定
    if battle.current_turn >= battle.max_turns:
        if player1.current_hp > player2.current_hp:
            return player1.id
        elif player2.current_hp > player1.current_hp:
            return player2.id
        else:
            return None  # 引き分け

    return None  # 継続中
```

### 9.2 レーティング更新

```python
def update_ratings(winner_id, loser_id):
    winner = get_character(winner_id)
    loser = get_character(loser_id)

    winner_rating = get_rating(winner_id)
    loser_rating = get_rating(loser_id)

    # レーティング差に応じた変動量
    rating_diff = loser_rating - winner_rating
    bonus = rating_diff / 20

    # 基本変動量
    winner_change = 25 + bonus
    loser_change = -25 - bonus

    # 更新
    update_rating(winner_id, winner_rating + winner_change)
    update_rating(loser_id, loser_rating + loser_change)
```

---

## 10. バランス調整

### 10.1 ステータスバランス

| 特化型 | HP | 攻撃 | 防御 | 速度 | 特徴 |
|-------|---|-----|-----|-----|------|
| タンク型 | 100 | 60 | 80 | 40 | 高耐久・低速 |
| アタッカー型 | 70 | 100 | 50 | 60 | 高火力・低耐久 |
| スピード型 | 70 | 70 | 50 | 90 | 先攻・回避率高 |
| バランス型 | 70 | 70 | 70 | 70 | オールラウンド |

### 10.2 アビリティバランス

- 強力なアビリティほど長いクールダウン
- 攻撃アビリティは最大2倍まで
- 回復は最大HPの30%まで
- デバフは最大50%減少まで

### 10.3 「言ったもん勝ち」要素の実装

LLMがキャラクター設定に基づいて行動を選択する際、以下を考慮:

```python
def get_llm_action_prompt(character, battle_state):
    return f"""
    あなたは「{character.name}」として戦っています。

    キャラクター設定:
    {character.prompt}

    現在の状況:
    - あなたのHP: {battle_state.your_hp} / {character.max_hp}
    - 相手のHP: {battle_state.opponent_hp}
    - ターン数: {battle_state.current_turn}
    - 使用可能なアビリティ: {battle_state.available_abilities}

    あなたのキャラクター設定に基づいて、
    最もそのキャラクターらしい行動を選択してください。

    - 勇敢なキャラクターなら積極的に攻撃
    - 慎重なキャラクターなら防御や回避を選択
    - 戦略的なキャラクターなら状況に応じて最適解を選択

    選択肢:
    1. attack - 通常攻撃
    2. defend - 防御（次の被ダメージ50%軽減）
    3. dodge - 回避（成功率{battle_state.dodge_rate}%）
    4. ability - アビリティ使用
       {format_abilities(battle_state.available_abilities)}

    回答形式: {{"action": "attack", "ability_id": null, "reason": "キャラクターらしい理由"}}
    """
```

**「言ったもん勝ち」の実現**:
- プロンプトに「俺は最強」と書いたキャラクターは、実際に積極的な行動を取る傾向
- ただしゲームルールの制約内で動作（無限ダメージなどは不可）
- LLMの判断により、キャラクター性が戦闘に反映される

---

## 11. エッジケース処理

### 11.1 同時KO
- 両者のHPが同時に0以下 → 引き分け
- 戦績に「draws」としてカウント

### 11.2 最大ターン到達
- 50ターン到達時点で勝敗判定
- 残りHP多い方が勝利
- 同HPなら引き分け

### 11.3 切断・エラー
- LLM応答タイムアウト（30秒）→ ランダム行動（attack）
- データベースエラー → バトル中断、ロールバック
- プレイヤー離脱 → 不戦敗処理

---

## 12. パフォーマンス最適化

### 12.1 計算キャッシュ
- ステータス計算結果はキャラクター作成時に保存
- バトル中は再計算不要

### 12.2 並列処理
- 両プレイヤーの行動決定を並列実行
- LLM API呼び出しを非同期化

---

## 13. デバッグ・テスト

### 13.1 バトルシミュレーション

```python
def simulate_battle(character1_id, character2_id, max_turns=50):
    """
    バトルをシミュレーションし、結果を返す。

    テスト用途で、実際のLLM呼び出しなしで動作。
    """
    battle = create_battle(character1_id, character2_id)

    for turn in range(1, max_turns + 1):
        # ランダム行動
        action1 = random_action(character1_id)
        action2 = random_action(character2_id)

        execute_turn(battle.id, action1, action2)

        winner = check_winner(battle)
        if winner:
            break

    return get_battle_result(battle.id)
```

### 13.2 バランステスト

```python
def test_balance():
    """
    各ステータス特化型のキャラクターでバトルを100回実行し、
    勝率を測定してバランスを検証。
    """
    tank = create_test_character(hp=100, attack=60, defense=80, speed=40)
    attacker = create_test_character(hp=70, attack=100, defense=50, speed=60)
    speedster = create_test_character(hp=70, attack=70, defense=50, speed=90)
    balanced = create_test_character(hp=70, attack=70, defense=70, speed=70)

    results = {}
    for char1 in [tank, attacker, speedster, balanced]:
        for char2 in [tank, attacker, speedster, balanced]:
            if char1.id != char2.id:
                wins = 0
                for _ in range(100):
                    result = simulate_battle(char1.id, char2.id)
                    if result.winner_id == char1.id:
                        wins += 1
                results[f"{char1.name} vs {char2.name}"] = wins / 100

    return results
```

---

## 14. 将来の拡張

### 14.1 チーム戦
- 2vs2、3vs3のバトル形式
- ターゲット選択の追加
- 連携アビリティ

### 14.2 装備システム
- 武器・防具の概念
- ステータスボーナス
- 特殊効果付与

### 14.3 スキルツリー
- レベルアップによるアビリティ習得
- 成長パスの選択
- カスタマイズ性の向上

### 14.4 バトルモード追加
- ランクマッチ
- トーナメント
- サバイバルモード（連戦）

---

## 15. 関連ドキュメント

- [システムアーキテクチャ](./architecture.md)
- [データベース設計](./database.md)
- [MCPサーバー設計](./mcp-server.md)

---

**設計承認**: 待機中
**次のステップ**: Webビュアー設計の詳細化
