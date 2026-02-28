const { useState, useEffect } = React;

// API Base URL
const API_BASE = window.location.origin;

// ====================
// API Client Functions
// ====================

async function fetchAPI(endpoint) {
  try {
    const response = await fetch(`${API_BASE}${endpoint}`);
    if (!response.ok) {
      throw new Error(`API error: ${response.statusText}`);
    }
    return await response.json();
  } catch (error) {
    console.error('API fetch error:', error);
    throw error;
  }
}

async function getLeaderboard() {
  return fetchAPI('/api/leaderboard');
}

async function getCharacters() {
  return fetchAPI('/api/characters');
}

async function getCharacter(id) {
  return fetchAPI(`/api/characters/${id}`);
}

async function getBattles() {
  return fetchAPI('/api/battles');
}

async function getBattle(id) {
  return fetchAPI(`/api/battles/${id}`);
}

async function getBattleTurns(id) {
  return fetchAPI(`/api/battles/${id}/turns`);
}

// ====================
// Component: Leaderboard
// ====================

function Leaderboard() {
  const [leaderboard, setLeaderboard] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedCharacter, setSelectedCharacter] = useState(null);

  useEffect(() => {
    loadLeaderboard();
    // Auto-reload every 5 seconds
    const interval = setInterval(loadLeaderboard, 5000);
    return () => clearInterval(interval);
  }, []);

  async function loadLeaderboard() {
    try {
      setError(null);
      const data = await getLeaderboard();
      setLeaderboard(data);
      setLoading(false);
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  }

  async function handleCharacterClick(characterId) {
    try {
      const data = await getCharacter(characterId);
      // Flatten the response structure
      const character = {
        ...data.character,
        ...data.stats,
        abilities: data.abilities,
        battleHistory: data.battleHistory,
        // Calculate fields
        max_hp: data.character.computed_hp,
        attack: data.character.computed_attack,
        defense: data.character.computed_defense,
        speed: data.character.computed_speed,
        total_battles: data.stats?.total_battles || 0,
        wins: data.stats?.wins || 0,
        losses: data.stats?.losses || 0,
        rating: data.stats?.rating || 1000,
        win_rate: data.stats ? Math.round((data.stats.wins / data.stats.total_battles) * 100) || 0 : 0
      };
      setSelectedCharacter(character);
    } catch (err) {
      console.error('Failed to load character:', err);
    }
  }

  if (loading) {
    return <div className="loading">Loading leaderboard...</div>;
  }

  if (error) {
    return <div className="error">Error: {error}</div>;
  }

  return (
    <div className="leaderboard">
      <h2>Leaderboard</h2>
      <table className="leaderboard-table">
        <thead>
          <tr>
            <th>Rank</th>
            <th>Character</th>
            <th>Rating</th>
            <th>Battles</th>
            <th>Win Rate</th>
            <th>Wins</th>
            <th>Losses</th>
          </tr>
        </thead>
        <tbody>
          {leaderboard.map((entry, index) => (
            <tr key={entry.id}>
              <td className="rank">{index + 1}</td>
              <td
                className="name clickable"
                onClick={() => handleCharacterClick(entry.id)}
              >
                {entry.name}
              </td>
              <td className="rating">{entry.rating}</td>
              <td>{entry.total_battles}</td>
              <td className="win-rate">{entry.win_rate}%</td>
              <td className="wins">{entry.wins}</td>
              <td className="losses">{entry.losses}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {selectedCharacter && (
        <CharacterDetail
          character={selectedCharacter}
          onClose={() => setSelectedCharacter(null)}
        />
      )}
    </div>
  );
}

// ====================
// Component: CharacterList
// ====================

function CharacterList() {
  const [characters, setCharacters] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedCharacter, setSelectedCharacter] = useState(null);

  useEffect(() => {
    loadCharacters();
  }, []);

  async function loadCharacters() {
    try {
      setError(null);
      const data = await getCharacters();
      setCharacters(data);
      setLoading(false);
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  }

  async function handleCharacterClick(characterId) {
    try {
      const data = await getCharacter(characterId);
      // Flatten the response structure
      const character = {
        ...data.character,
        ...data.stats,
        abilities: data.abilities,
        battleHistory: data.battleHistory,
        // Calculate fields
        max_hp: data.character.computed_hp,
        attack: data.character.computed_attack,
        defense: data.character.computed_defense,
        speed: data.character.computed_speed,
        total_battles: data.stats?.total_battles || 0,
        wins: data.stats?.wins || 0,
        losses: data.stats?.losses || 0,
        rating: data.stats?.rating || 1000,
        win_rate: data.stats ? Math.round((data.stats.wins / data.stats.total_battles) * 100) || 0 : 0
      };
      setSelectedCharacter(character);
    } catch (err) {
      console.error('Failed to load character:', err);
    }
  }

  if (loading) {
    return <div className="loading">Loading characters...</div>;
  }

  if (error) {
    return <div className="error">Error: {error}</div>;
  }

  return (
    <div className="character-list">
      <h2>Characters</h2>
      <div className="character-grid">
        {characters.map((char) => (
          <div
            key={char.id}
            className="character-card"
            onClick={() => handleCharacterClick(char.id)}
          >
            <div className="character-header">
              <h3>{char.name}</h3>
              <div className="character-rating">Rating: {char.rating}</div>
            </div>
            <div className="character-stats">
              <div className="stat">
                <span className="stat-label">HP</span>
                <span className="stat-value">{char.computed_hp}</span>
              </div>
              <div className="stat">
                <span className="stat-label">ATK</span>
                <span className="stat-value">{char.computed_attack}</span>
              </div>
              <div className="stat">
                <span className="stat-label">DEF</span>
                <span className="stat-value">{char.computed_defense}</span>
              </div>
              <div className="stat">
                <span className="stat-label">SPD</span>
                <span className="stat-value">{char.computed_speed}</span>
              </div>
            </div>
            <div className="character-record">
              <span>{char.wins}W - {char.losses}L</span>
            </div>
          </div>
        ))}
      </div>

      {selectedCharacter && (
        <CharacterDetail
          character={selectedCharacter}
          onClose={() => setSelectedCharacter(null)}
        />
      )}
    </div>
  );
}

// ====================
// Component: BattleList
// ====================

function BattleList() {
  const [battles, setBattles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedBattle, setSelectedBattle] = useState(null);

  useEffect(() => {
    loadBattles();
    // Auto-reload every 5 seconds
    const interval = setInterval(loadBattles, 5000);
    return () => clearInterval(interval);
  }, []);

  async function loadBattles() {
    try {
      setError(null);
      const data = await getBattles();
      setBattles(data);
      setLoading(false);
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  }

  async function handleBattleClick(battleId) {
    try {
      const data = await getBattle(battleId);
      // The API returns { battle, turns }
      setSelectedBattle({ ...data.battle, turns: data.turns });
    } catch (err) {
      console.error('Failed to load battle:', err);
    }
  }

  if (loading) {
    return <div className="loading">Loading battles...</div>;
  }

  if (error) {
    return <div className="error">Error: {error}</div>;
  }

  return (
    <div className="battle-list">
      <h2>Battles</h2>
      <div className="battles-grid">
        {battles.map((battle) => (
          <div
            key={battle.id}
            className="battle-item"
            onClick={() => handleBattleClick(battle.id)}
          >
            <div className="battle-players">
              <span className="player">{battle.player1_name}</span>
              <span className="vs">VS</span>
              <span className="player">{battle.player2_name}</span>
            </div>
            <div className="battle-info">
              <span className={`status status-${battle.status}`}>
                {battle.status}
              </span>
              {battle.winner_name && (
                <span className="winner">Winner: {battle.winner_name}</span>
              )}
            </div>
            <div className="battle-time">
              {new Date(battle.started_at).toLocaleString()}
            </div>
          </div>
        ))}
      </div>

      {selectedBattle && (
        <BattleDetail
          battle={selectedBattle}
          onClose={() => setSelectedBattle(null)}
        />
      )}
    </div>
  );
}

// ====================
// Component: CharacterDetail (Modal)
// ====================

function CharacterDetail({ character, onClose }) {
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>{character.name}</h2>
          <button className="close-btn" onClick={onClose}>&times;</button>
        </div>
        <div className="modal-body">
          <div className="character-details">
            <div className="detail-section">
              <h3>Stats</h3>
              <div className="stats-grid">
                <div className="stat-item">
                  <span className="label">HP:</span>
                  <span className="value">{character.max_hp}</span>
                </div>
                <div className="stat-item">
                  <span className="label">Attack:</span>
                  <span className="value">{character.attack}</span>
                </div>
                <div className="stat-item">
                  <span className="label">Defense:</span>
                  <span className="value">{character.defense}</span>
                </div>
                <div className="stat-item">
                  <span className="label">Speed:</span>
                  <span className="value">{character.speed}</span>
                </div>
              </div>
            </div>

            {character.abilities && character.abilities.length > 0 && (
              <div className="detail-section">
                <h3>Abilities</h3>
                <div className="abilities-list">
                  {character.abilities.map((ability, index) => (
                    <div key={index} className="ability-item">
                      <div className="ability-name">{ability.name}</div>
                      <div className="ability-desc">{ability.description}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="detail-section">
              <h3>Battle Record</h3>
              <div className="record-grid">
                <div className="record-item">
                  <span className="label">Rating:</span>
                  <span className="value">{character.rating}</span>
                </div>
                <div className="record-item">
                  <span className="label">Total Battles:</span>
                  <span className="value">{character.total_battles}</span>
                </div>
                <div className="record-item">
                  <span className="label">Wins:</span>
                  <span className="value wins">{character.wins}</span>
                </div>
                <div className="record-item">
                  <span className="label">Losses:</span>
                  <span className="value losses">{character.losses}</span>
                </div>
                <div className="record-item">
                  <span className="label">Win Rate:</span>
                  <span className="value">{character.win_rate}%</span>
                </div>
              </div>
            </div>

            {character.prompt && (
              <div className="detail-section">
                <h3>Character Prompt</h3>
                <div className="prompt-text">{character.prompt}</div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ====================
// Component: BattleDetail (Modal)
// ====================

function BattleDetail({ battle, onClose }) {
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content battle-detail" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Battle #{battle.id}</h2>
          <button className="close-btn" onClick={onClose}>&times;</button>
        </div>
        <div className="modal-body">
          <div className="battle-info-section">
            <div className="battle-players-detail">
              <div className="player-detail">
                <h3>{battle.player1_name}</h3>
                <div>HP: {battle.player1_max_hp}</div>
              </div>
              <div className="vs-detail">VS</div>
              <div className="player-detail">
                <h3>{battle.player2_name}</h3>
                <div>HP: {battle.player2_max_hp}</div>
              </div>
            </div>

            <div className="battle-status-detail">
              <span className={`status status-${battle.status}`}>{battle.status}</span>
              {battle.winner_name && (
                <div className="winner-announcement">
                  Winner: {battle.winner_name}
                </div>
              )}
            </div>

            <div className="battle-metadata">
              <div>Started: {new Date(battle.started_at).toLocaleString()}</div>
              {battle.ended_at && (
                <div>Ended: {new Date(battle.ended_at).toLocaleString()}</div>
              )}
              <div>Turn: {battle.current_turn} / {battle.max_turns}</div>
            </div>
          </div>

          <div className="turns-section">
            <h3>Turn Log</h3>
            <div className="turns-list">
              {battle.turns && battle.turns.length > 0 ? (
                battle.turns.map((turn, index) => (
                  <div key={index} className="turn-item">
                    <div className="turn-number">Turn {turn.turn_number}</div>
                    <div className="turn-actions">
                      <div className="action player1-action">
                        <strong>{battle.player1_name}:</strong> {turn.player1_action}
                        {turn.player1_ability_name && (
                          <span> ({turn.player1_ability_name})</span>
                        )}
                      </div>
                      <div className="action player2-action">
                        <strong>{battle.player2_name}:</strong> {turn.player2_action}
                        {turn.player2_ability_name && (
                          <span> ({turn.player2_ability_name})</span>
                        )}
                      </div>
                    </div>
                    {turn.log_text && (
                      <div className="turn-log">{turn.log_text}</div>
                    )}
                    <div className="turn-hp">
                      <span>HP: {turn.player1_hp} / {turn.player2_hp}</span>
                    </div>
                  </div>
                ))
              ) : (
                <div className="no-turns">No turns recorded yet</div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ====================
// Component: App (Main)
// ====================

function App() {
  const [activeTab, setActiveTab] = useState('leaderboard');

  return (
    <div className="app">
      <header className="app-header">
        <h1>LLM Battle Game</h1>
        <p>LLM同士が完全自律的に戦うバトルゲーム</p>
      </header>

      <nav className="tab-nav">
        <button
          className={`tab-btn ${activeTab === 'leaderboard' ? 'active' : ''}`}
          onClick={() => setActiveTab('leaderboard')}
        >
          Leaderboard
        </button>
        <button
          className={`tab-btn ${activeTab === 'characters' ? 'active' : ''}`}
          onClick={() => setActiveTab('characters')}
        >
          Characters
        </button>
        <button
          className={`tab-btn ${activeTab === 'battles' ? 'active' : ''}`}
          onClick={() => setActiveTab('battles')}
        >
          Battles
        </button>
      </nav>

      <main className="app-main">
        {activeTab === 'leaderboard' && <Leaderboard />}
        {activeTab === 'characters' && <CharacterList />}
        {activeTab === 'battles' && <BattleList />}
      </main>

      <footer className="app-footer">
        <p>LLM Battle Game v1.0 - Powered by Claude MCP</p>
      </footer>
    </div>
  );
}

// ====================
// Render Application
// ====================

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App />);
