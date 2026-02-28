const API_BASE = 'http://localhost:3000/api';

async function fetchAPI(endpoint) {
  try {
    const response = await fetch(`${API_BASE}${endpoint}`);
    if (!response.ok) {
      throw new Error(`API error: ${response.statusText}`);
    }
    return response.json();
  } catch (error) {
    console.error('API fetch error:', error);
    throw error;
  }
}

export async function getBattle(battleId) {
  return fetchAPI(`/battles/${battleId}`);
}

export async function getBattleTurns(battleId) {
  return fetchAPI(`/battles/${battleId}/turns`);
}

export async function getRecentBattles(limit = 10) {
  return fetchAPI(`/battles?status=finished&limit=${limit}`);
}

export async function getActiveBattles(limit = 10) {
  return fetchAPI(`/battles?status=active&limit=${limit}`);
}

export async function getCharacter(characterId) {
  return fetchAPI(`/characters/${characterId}`);
}

export async function getCharacters(limit = 50, offset = 0) {
  return fetchAPI(`/characters?limit=${limit}&offset=${offset}`);
}

export async function getLeaderboard(limit = 50) {
  return fetchAPI(`/leaderboard?limit=${limit}`);
}

export async function getCharacterStats(characterId) {
  return fetchAPI(`/characters/${characterId}/stats`);
}
