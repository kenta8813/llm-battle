import { useState, useEffect } from 'react';
import { getLeaderboard } from '../api/client';
import LeaderboardTable from '../components/Leaderboard/LeaderboardTable';
import Loading from '../components/Common/Loading';

function Leaderboard() {
  const [leaderboard, setLeaderboard] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchLeaderboard() {
      try {
        setLoading(true);
        setError(null);
        const data = await getLeaderboard(50);
        setLeaderboard(data || []);
      } catch (err) {
        console.error('Failed to fetch leaderboard:', err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }

    fetchLeaderboard();

    // 30秒ごとに更新
    const interval = setInterval(fetchLeaderboard, 30000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return <Loading message="リーダーボードを読み込み中..." />;
  }

  if (error) {
    return (
      <div className="error-page">
        <h2>エラーが発生しました</h2>
        <p>{error}</p>
        <button onClick={() => window.location.reload()}>再読み込み</button>
      </div>
    );
  }

  return (
    <div className="leaderboard-page">
      <div className="page-header">
        <h1>リーダーボード</h1>
        <p className="update-info">30秒ごとに自動更新されます</p>
      </div>

      <LeaderboardTable data={leaderboard} />
    </div>
  );
}

export default Leaderboard;
