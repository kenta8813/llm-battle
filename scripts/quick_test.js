/**
 * Quick API test using Node.js fetch
 * Run with: node scripts/quick_test.js
 */

const BASE_URL = 'http://localhost:3000';

async function testEndpoint(name, path) {
  try {
    const response = await fetch(`${BASE_URL}${path}`);
    const data = await response.json();
    console.log(`✓ ${name}`);
    console.log(`  Status: ${response.status}`);
    console.log(`  Data preview:`, JSON.stringify(data).substring(0, 200));
    console.log('');
    return true;
  } catch (error) {
    console.log(`✗ ${name}`);
    console.log(`  Error: ${error.message}`);
    console.log('');
    return false;
  }
}

async function runTests() {
  console.log('===================================');
  console.log('Quick API Test');
  console.log('===================================\n');

  let passed = 0;
  let failed = 0;

  // Test 1: Health check
  if (await testEndpoint('Health Check', '/health')) passed++; else failed++;

  // Test 2: Leaderboard
  if (await testEndpoint('Leaderboard', '/api/leaderboard')) passed++; else failed++;

  // Test 3: Leaderboard with limit
  if (await testEndpoint('Leaderboard (limit=3)', '/api/leaderboard?limit=3')) passed++; else failed++;

  // Test 4: Global stats
  if (await testEndpoint('Global Stats', '/api/stats')) passed++; else failed++;

  // Test 5: Character details
  if (await testEndpoint('Character Details (ID=1)', '/api/character/1')) passed++; else failed++;

  // Test 6: Battle details
  if (await testEndpoint('Battle Details (ID=1)', '/api/battle/1')) passed++; else failed++;

  // Test 7: Invalid character
  try {
    const response = await fetch(`${BASE_URL}/api/character/99999`);
    if (response.status === 404) {
      console.log('✓ Error handling (404 for invalid character)');
      passed++;
    } else {
      console.log('✗ Error handling failed (expected 404)');
      failed++;
    }
  } catch (error) {
    console.log('✗ Error handling test failed');
    failed++;
  }
  console.log('');

  console.log('===================================');
  console.log(`Results: ${passed} passed, ${failed} failed`);
  console.log('===================================');

  process.exit(failed > 0 ? 1 : 0);
}

runTests();
