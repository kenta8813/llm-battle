import { Link } from 'react-router-dom';
import { useState, useEffect } from 'react';
import { getRecentBattles, getActiveBattles } from '../api/client';
import Loading from '../components/Common/Loading';

function Home() {
  const [recentBattles, setRecentBattles] = useState([]);
  const [activeBattles, setActiveBattles] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchBattles() {
      try {
        setLoading(true);
        const [recent, active] = await Promise.all([
          getRecentBattles(10),
          getActiveBattles(5)
        ]);
        setRecentBattles(recent || []);
        setActiveBattles(active || []);
      } catch (error) {
        console.error('Failed to fetch battles:', error);
      } finally {
        setLoading(false);
      }
    }

    fetchBattles();
  }, []);

  if (loading) {
    return <Loading message="バトル情報を読み込み中..." />;
  }

  return (
    <div className="home">
      <section className="hero">
        <h1>LLM Battle Game</h1>
        <p>LLM同士が完全自律的に戦うバトルゲーム</p>
        <div className="cta-buttons">
          <Link to="/leaderboard" className="btn btn-primary">
            リーダーボード
          </Link>
          <Link to="/characters" className="btn btn-secondary">
            キャラクター一覧
          </Link>
        </div>
      </section>

      {activeBattles.length > 0 && (
        <section className="active-battles">
          <h2>進行中のバトル</h2>
          <div className="battle-list">
            {activeBattles.map(battle => (
              <Link
                key={battle.id}
                to={`/battle/${battle.id}`}
                className="battle-card active"
              >
                <div className="battle-status">LIVE</div>
                <div className="players">
                  <span>{battle.player1_name}</span>
                  <span className="vs">vs</span>
                  <span>{battle.player2_name}</span>
                </div>
                <div className="turn-info">
                  ターン {battle.current_turn || 0}
                </div>
              </Link>
            ))}
          </div>
        </section>
      )}

      <section className="recent-battles">
        <h2>最近のバトル</h2>
        <div className="battle-list">
          {recentBattles.length === 0 ? (
            <p className="no-battles">まだバトルが行われていません</p>
          ) : (
            recentBattles.map(battle => (
              <Link
                key={battle.id}
                to={`/battle/${battle.id}`}
                className="battle-card"
              >
                <div className="players">
                  <span>{battle.player1_name}</span>
                  <span className="vs">vs</span>
                  <span>{battle.player2_name}</span>
                </div>
                <div className="result">
                  {battle.status === 'finished'
                    ? `勝者: ${battle.winner_name}`
                    : '進行中'}
                </div>
              </Link>
            ))
          )}
        </div>
      </section>
    </div>
  );
}

export default Home;
