/**
 * API レスポンス構造の確認スクリプト
 */

const BASE_URL = 'http://localhost:3000/api';

async function checkLeaderboard() {
  console.log('=== Checking /api/leaderboard ===');
  const response = await fetch(`${BASE_URL}/leaderboard?limit=1`);
  const data = await response.json();
  console.log(JSON.stringify(data[0], null, 2));
  console.log();
}

async function checkCharacter() {
  console.log('=== Checking /api/character/:id ===');
  // Get first character from leaderboard
  const leaderboard = await fetch(`${BASE_URL}/leaderboard?limit=1`);
  const chars = await leaderboard.json();
  if (chars.length > 0) {
    const response = await fetch(`${BASE_URL}/character/${chars[0].id}`);
    const data = await response.json();
    console.log('Keys:', Object.keys(data));
    console.log('Character keys:', Object.keys(data.character));
    console.log('Stats keys:', Object.keys(data.stats));
    console.log();
  }
}

async function checkBattle() {
  console.log('=== Checking /api/battle/:id ===');
  // Get first character
  const leaderboard = await fetch(`${BASE_URL}/leaderboard?limit=1`);
  const chars = await leaderboard.json();
  if (chars.length > 0) {
    const charResp = await fetch(`${BASE_URL}/character/${chars[0].id}`);
    const charData = await charResp.json();
    if (charData.battleHistory && charData.battleHistory.length > 0) {
      const response = await fetch(`${BASE_URL}/battle/${charData.battleHistory[0].id}`);
      const data = await response.json();
      console.log('Keys:', Object.keys(data));
      console.log('Battle keys:', Object.keys(data.battle));
      console.log();
    }
  }
}

async function checkStats() {
  console.log('=== Checking /api/stats ===');
  const response = await fetch(`${BASE_URL}/stats`);
  const data = await response.json();
  console.log(JSON.stringify(data, null, 2));
  console.log();
}

async function main() {
  await checkLeaderboard();
  await checkCharacter();
  await checkBattle();
  await checkStats();
  process.exit(0);
}

main().catch(console.error);
