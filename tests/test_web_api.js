/**
 * Web API Test Suite
 *
 * Tests for the Web API endpoints
 * Run with: node tests/test_web_api.js
 *
 * Prerequisites:
 * - Web server must be running on http://localhost:3000
 * - Database must be initialized with test data
 */

const BASE_URL = 'http://localhost:3000/api';

// Simple test framework
class TestRunner {
  constructor() {
    this.passed = 0;
    this.failed = 0;
    this.tests = [];
  }

  async test(name, fn) {
    this.tests.push({ name, fn });
  }

  async run() {
    console.log('===================================');
    console.log('Web API Test Suite');
    console.log('===================================\n');

    for (const { name, fn } of this.tests) {
      try {
        await fn();
        this.passed++;
        console.log(`✓ ${name}`);
      } catch (error) {
        this.failed++;
        console.error(`✗ ${name}`);
        console.error(`  Error: ${error.message}`);
      }
    }

    console.log('\n===================================');
    console.log(`Total: ${this.tests.length} | Passed: ${this.passed} | Failed: ${this.failed}`);
    console.log('===================================');

    process.exit(this.failed > 0 ? 1 : 0);
  }
}

// Assertion helpers
function assert(condition, message) {
  if (!condition) {
    throw new Error(message || 'Assertion failed');
  }
}

function assertEqual(actual, expected, message) {
  if (actual !== expected) {
    throw new Error(message || `Expected ${expected}, got ${actual}`);
  }
}

function assertType(value, type, message) {
  if (typeof value !== type) {
    throw new Error(message || `Expected type ${type}, got ${typeof value}`);
  }
}

function assertArray(value, message) {
  if (!Array.isArray(value)) {
    throw new Error(message || 'Expected an array');
  }
}

// HTTP client
async function fetchAPI(endpoint) {
  const response = await fetch(`${BASE_URL}${endpoint}`);
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }
  return response.json();
}

// Test suite
const runner = new TestRunner();

// Test 1: Health check
runner.test('Server health check', async () => {
  const response = await fetch('http://localhost:3000/health');
  const data = await response.json();
  assertEqual(data.status, 'ok', 'Health check should return ok status');
});

// Test 2: Get leaderboard
runner.test('GET /api/leaderboard - success', async () => {
  const data = await fetchAPI('/leaderboard');
  assertArray(data, 'Leaderboard should return an array');

  if (data.length > 0) {
    const first = data[0];
    assert(first.id, 'Character should have id');
    assert(first.name, 'Character should have name');
    assertType(first.rating, 'number', 'Rating should be a number');
    assertType(first.total_battles, 'number', 'Total battles should be a number');
  }
});

// Test 3: Get leaderboard with limit
runner.test('GET /api/leaderboard?limit=10 - success', async () => {
  const data = await fetchAPI('/leaderboard?limit=10');
  assertArray(data, 'Leaderboard should return an array');
  assert(data.length <= 10, 'Leaderboard should respect limit parameter');
});

// Test 4: Get character details (valid ID) - 複数形URL
runner.test('GET /api/characters/:id - success', async () => {
  // First get a character ID from leaderboard
  const leaderboard = await fetchAPI('/leaderboard?limit=1');

  if (leaderboard.length > 0) {
    const characterId = leaderboard[0].id;
    const data = await fetchAPI(`/characters/${characterId}`);

    assert(data.character, 'Response should have character field');
    assert(data.stats, 'Response should have stats field');
    assertArray(data.abilities, 'Response should have abilities array');
    assertArray(data.battleHistory, 'Response should have battleHistory array');

    assertEqual(data.character.id, characterId, 'Character ID should match');
  }
});

// Test 4b: Get character details (valid ID) - 後方互換性テスト（単数形URL）
runner.test('GET /api/character/:id - backward compatibility', async () => {
  // First get a character ID from leaderboard
  const leaderboard = await fetchAPI('/leaderboard?limit=1');

  if (leaderboard.length > 0) {
    const characterId = leaderboard[0].id;
    const data = await fetchAPI(`/character/${characterId}`);

    assert(data.character, 'Response should have character field');
    assert(data.stats, 'Response should have stats field');
    assertArray(data.abilities, 'Response should have abilities array');
    assertArray(data.battleHistory, 'Response should have battleHistory array');

    assertEqual(data.character.id, characterId, 'Character ID should match');
  }
});

// Test 5: Get character details (invalid ID)
runner.test('GET /api/characters/:id - not found', async () => {
  try {
    await fetchAPI('/characters/999999');
    throw new Error('Should have thrown 404 error');
  } catch (error) {
    assert(error.message.includes('404'), 'Should return 404 for non-existent character');
  }
});

// Test 6: Get battle details (if battles exist) - 複数形URL
runner.test('GET /api/battles/:id - success', async () => {
  // First get a character with battle history
  const leaderboard = await fetchAPI('/leaderboard?limit=1');

  if (leaderboard.length > 0) {
    const characterId = leaderboard[0].id;
    const characterData = await fetchAPI(`/characters/${characterId}`);

    if (characterData.battleHistory.length > 0) {
      const battleId = characterData.battleHistory[0].id;
      const data = await fetchAPI(`/battles/${battleId}`);

      assert(data.battle, 'Response should have battle field');
      assertArray(data.turns, 'Response should have turns array');

      assertEqual(data.battle.id, battleId, 'Battle ID should match');
      assert(data.battle.player1_name, 'Battle should have player1_name');
      assert(data.battle.player2_name, 'Battle should have player2_name');
    }
  }
});

// Test 6b: Get battle details - 後方互換性テスト（単数形URL）
runner.test('GET /api/battle/:id - backward compatibility', async () => {
  // First get a character with battle history
  const leaderboard = await fetchAPI('/leaderboard?limit=1');

  if (leaderboard.length > 0) {
    const characterId = leaderboard[0].id;
    const characterData = await fetchAPI(`/characters/${characterId}`);

    if (characterData.battleHistory.length > 0) {
      const battleId = characterData.battleHistory[0].id;
      const data = await fetchAPI(`/battle/${battleId}`);

      assert(data.battle, 'Response should have battle field');
      assertArray(data.turns, 'Response should have turns array');

      assertEqual(data.battle.id, battleId, 'Battle ID should match');
      assert(data.battle.player1_name, 'Battle should have player1_name');
      assert(data.battle.player2_name, 'Battle should have player2_name');
    }
  }
});

// Test 7: Get battle details (invalid ID)
runner.test('GET /api/battles/:id - not found', async () => {
  try {
    await fetchAPI('/battles/999999');
    throw new Error('Should have thrown 404 error');
  } catch (error) {
    assert(error.message.includes('404'), 'Should return 404 for non-existent battle');
  }
});

// Test 8: Get global stats
runner.test('GET /api/stats - success', async () => {
  const data = await fetchAPI('/stats');

  assertType(data.totalBattles, 'number', 'totalBattles should be a number');
  assertType(data.totalCharacters, 'number', 'totalCharacters should be a number');
  assertType(data.todayBattles, 'number', 'todayBattles should be a number');
  assertType(data.activeBattles, 'number', 'activeBattles should be a number');
  assertType(data.playersInQueue, 'number', 'playersInQueue should be a number');
  assertType(data.topRating, 'number', 'topRating should be a number');
  assertType(data.avgRating, 'number', 'avgRating should be a number');

  assert(data.totalBattles >= 0, 'Total battles should be non-negative');
  assert(data.totalCharacters >= 0, 'Total characters should be non-negative');
});

// Test 9: Invalid endpoint
runner.test('GET /api/invalid - not found', async () => {
  try {
    await fetchAPI('/invalid');
    throw new Error('Should have thrown 404 error');
  } catch (error) {
    assert(error.message.includes('404'), 'Should return 404 for invalid endpoint');
  }
});

// Test 10: Data consistency
runner.test('Data consistency check', async () => {
  const stats = await fetchAPI('/stats');
  const leaderboard = await fetchAPI('/leaderboard?limit=1000');

  // Leaderboard should not have more characters than total characters
  assert(
    leaderboard.length <= stats.totalCharacters,
    'Leaderboard count should not exceed total characters'
  );

  // All leaderboard entries should have valid stats
  for (const character of leaderboard) {
    assert(character.total_battles > 0, 'Characters on leaderboard should have battles');
    assert(character.rating >= 0, 'Rating should be non-negative');
    assert(character.wins + character.losses + character.draws === character.total_battles,
      'Win/loss/draw should sum to total battles');
  }
});

// Test 11: Get battles list
runner.test('GET /api/battles - success', async () => {
  const data = await fetchAPI('/battles');
  assertArray(data, 'Battles should return an array');

  if (data.length > 0) {
    const first = data[0];
    assert(first.id, 'Battle should have id');
    assert(first.player1_name, 'Battle should have player1_name');
    assert(first.player2_name, 'Battle should have player2_name');
    assert(first.status, 'Battle should have status');
  }
});

// Test 12: Get battles list with status filter
runner.test('GET /api/battles?status=finished - filtering', async () => {
  const data = await fetchAPI('/battles?status=finished');
  assertArray(data, 'Battles should return an array');

  for (const battle of data) {
    assertEqual(battle.status, 'finished', 'All battles should have status=finished');
  }
});

// Test 13: Get battle turns
runner.test('GET /api/battles/:id/turns - success', async () => {
  const battles = await fetchAPI('/battles?status=finished&limit=1');

  if (battles.length > 0) {
    const battleId = battles[0].id;
    const data = await fetchAPI(`/battles/${battleId}/turns`);

    assertArray(data, 'Turns should return an array');

    if (data.length > 0) {
      const first = data[0];
      assertType(first.turn_number, 'number', 'Turn should have turn_number');
      assert(first.player1_action, 'Turn should have player1_action');
      assert(first.player2_action, 'Turn should have player2_action');
    }
  }
});

// Test 14: Get battle turns (invalid ID)
runner.test('GET /api/battles/:id/turns - not found', async () => {
  try {
    await fetchAPI('/battles/999999/turns');
    throw new Error('Should have thrown 404 error');
  } catch (error) {
    assert(error.message.includes('404'), 'Should return 404 for non-existent battle');
  }
});

// Test 15: Get characters list
runner.test('GET /api/characters - success', async () => {
  const data = await fetchAPI('/characters');
  assertArray(data, 'Characters should return an array');

  if (data.length > 0) {
    const first = data[0];
    assert(first.id, 'Character should have id');
    assert(first.name, 'Character should have name');
    assertType(first.level, 'number', 'Character should have level');
  }
});

// Test 16: Get characters list with limit
runner.test('GET /api/characters?limit=5 - limit parameter', async () => {
  const data = await fetchAPI('/characters?limit=5');
  assertArray(data, 'Characters should return an array');
  assert(data.length <= 5, 'Characters should respect limit parameter');
});

// Test 17: Get character stats
runner.test('GET /api/characters/:id/stats - success', async () => {
  const characters = await fetchAPI('/characters?limit=1');

  if (characters.length > 0) {
    const characterId = characters[0].id;
    const data = await fetchAPI(`/characters/${characterId}/stats`);

    assertEqual(data.character_id, characterId, 'Character ID should match');
    assertType(data.rating, 'number', 'Stats should have rating');
    assertType(data.total_battles, 'number', 'Stats should have total_battles');
    assertType(data.wins, 'number', 'Stats should have wins');
    assertType(data.losses, 'number', 'Stats should have losses');
  }
});

// Test 18: Get character stats (invalid ID)
runner.test('GET /api/characters/:id/stats - not found', async () => {
  try {
    await fetchAPI('/characters/999999/stats');
    throw new Error('Should have thrown 404 error');
  } catch (error) {
    assert(error.message.includes('404'), 'Should return 404 for non-existent character');
  }
});

// Run all tests
runner.run();
