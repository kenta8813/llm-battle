# Web API Documentation

**Base URL**: `http://localhost:3000/api`

## Endpoints

### 1. GET /api/leaderboard

レーティング上位のキャラクター一覧を取得

#### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| limit | integer | 50 | 取得件数 (1-1000) |

#### Response

```json
[
  {
    "id": 3,
    "name": "風の剣士",
    "level": 6,
    "computed_hp": 135,
    "computed_attack": 127,
    "computed_defense": 82,
    "computed_speed": 142,
    "rating": 1100,
    "total_battles": 2,
    "wins": 2,
    "losses": 0,
    "draws": 0,
    "win_rate": 100.0,
    "current_win_streak": 2,
    "longest_win_streak": 2,
    "total_damage_dealt": 420,
    "total_damage_received": 250
  }
]
```

#### Example

```bash
curl http://localhost:3000/api/leaderboard?limit=10
```

---

### 2. GET /api/character/:id

指定したキャラクターの詳細情報を取得

#### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| id | integer | キャラクターID |

#### Response

```json
{
  "character": {
    "id": 1,
    "account_id": 1,
    "name": "炎の戦士",
    "prompt": "あなたは熱き魂を持つ戦士です...",
    "level": 5,
    "base_hp": 100,
    "base_attack": 80,
    "base_defense": 60,
    "base_speed": 70,
    "computed_hp": 140,
    "computed_attack": 112,
    "computed_defense": 84,
    "computed_speed": 98,
    "owner_username": "player1"
  },
  "stats": {
    "character_id": 1,
    "total_battles": 3,
    "wins": 2,
    "losses": 1,
    "draws": 0,
    "total_damage_dealt": 450,
    "total_damage_received": 320,
    "longest_win_streak": 2,
    "current_win_streak": 2,
    "rating": 1050
  },
  "abilities": [
    {
      "id": 1,
      "name": "強打",
      "description": "通常攻撃の1.5倍のダメージを与える",
      "effect_type": "damage",
      "power": 150,
      "cost": 0,
      "cooldown": 0
    }
  ],
  "battleHistory": [
    {
      "id": 5,
      "player1_id": 4,
      "player2_id": 1,
      "winner_id": 1,
      "status": "finished",
      "started_at": "2026-02-27 03:34:36",
      "ended_at": "2026-02-27 04:09:36",
      "player1_name": "大地の盾",
      "player2_name": "炎の戦士",
      "result": "win"
    }
  ]
}
```

#### Example

```bash
curl http://localhost:3000/api/character/1
```

#### Error Response (404)

```json
{
  "error": "Character not found"
}
```

---

### 3. GET /api/battle/:id

指定したバトルの詳細情報を取得

#### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| id | integer | バトルID |

#### Response

```json
{
  "battle": {
    "id": 1,
    "player1_id": 1,
    "player2_id": 2,
    "winner_id": 1,
    "max_turns": 50,
    "current_turn": 15,
    "status": "finished",
    "started_at": "2026-02-18 03:34:36",
    "ended_at": "2026-02-18 04:04:36",
    "player1_name": "炎の戦士",
    "player1_max_hp": 140,
    "player1_attack": 112,
    "player1_defense": 84,
    "player1_speed": 98,
    "player2_name": "氷の魔法使い",
    "player2_max_hp": 112,
    "player2_attack": 126,
    "player2_defense": 70,
    "player2_speed": 119,
    "winner_name": "炎の戦士"
  },
  "turns": [
    {
      "id": 1,
      "battle_id": 1,
      "turn_number": 1,
      "player1_action": "attack",
      "player1_ability_id": null,
      "player1_target": null,
      "player1_damage_dealt": 20,
      "player1_damage_received": 15,
      "player1_hp_after": 125,
      "player2_action": "attack",
      "player2_ability_id": null,
      "player2_target": null,
      "player2_damage_dealt": 15,
      "player2_damage_received": 20,
      "player2_hp_after": 92,
      "turn_result": "{\"summary\": \"両者が攻撃\"}",
      "player1_ability_name": null,
      "player2_ability_name": null
    }
  ]
}
```

#### Example

```bash
curl http://localhost:3000/api/battle/1
```

#### Error Response (404)

```json
{
  "error": "Battle not found"
}
```

---

### 4. GET /api/stats

全体統計を取得

#### Response

```json
{
  "totalBattles": 5,
  "totalCharacters": 5,
  "todayBattles": 0,
  "activeBattles": 0,
  "playersInQueue": 0,
  "topRating": 1100,
  "avgRating": 1013
}
```

#### Example

```bash
curl http://localhost:3000/api/stats
```

---

## Health Check

### GET /health

サーバーのヘルスチェック

#### Response

```json
{
  "status": "ok",
  "timestamp": "2026-02-28T03:37:37.641Z"
}
```

#### Example

```bash
curl http://localhost:3000/health
```

---

## Error Handling

すべてのエラーは以下の形式で返されます：

```json
{
  "error": "Error message"
}
```

### HTTP Status Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 404 | Resource not found |
| 500 | Internal server error |

---

## Testing

### Quick Test

```bash
node scripts/quick_test.js
```

### Comprehensive Test

```bash
node tests/test_web_api.js
```

### Manual Testing

```bash
# Health check
curl http://localhost:3000/health

# Get leaderboard
curl http://localhost:3000/api/leaderboard

# Get character details
curl http://localhost:3000/api/character/1

# Get battle details
curl http://localhost:3000/api/battle/1

# Get global stats
curl http://localhost:3000/api/stats
```

---

## Database Schema Reference

The API reads from the following tables:

- `characters` - Character information
- `stats` - Character statistics and ratings
- `abilities` - Ability definitions
- `character_abilities` - Character-ability relationships
- `battles` - Battle records
- `battle_turns` - Turn-by-turn battle logs
- `accounts` - Player accounts
- `queue` - Matchmaking queue

See `design/database.md` for full schema documentation.
