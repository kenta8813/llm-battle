function LeaderboardTable({ data }) {
  if (!data || data.length === 0) {
    return (
      <div className="leaderboard-empty">
        <p>リーダーボードにデータがありません</p>
      </div>
    );
  }

  return (
    <div className="leaderboard-table-container">
      <table className="leaderboard-table">
        <thead>
          <tr>
            <th>順位</th>
            <th>キャラクター名</th>
            <th>レーティング</th>
            <th>バトル数</th>
            <th>勝利数</th>
            <th>勝率</th>
            <th>連勝</th>
          </tr>
        </thead>
        <tbody>
          {data.map((entry, index) => {
            const winRate = entry.total_battles > 0
              ? ((entry.wins / entry.total_battles) * 100).toFixed(1)
              : 0;

            return (
              <tr key={entry.character_id || index}>
                <td className="rank">
                  <span className={`rank-badge rank-${Math.min(index + 1, 3)}`}>
                    {index + 1}
                  </span>
                </td>
                <td className="name">{entry.name}</td>
                <td className="rating">{entry.rating || 1000}</td>
                <td className="battles">{entry.total_battles || 0}</td>
                <td className="wins">{entry.wins || 0}</td>
                <td className="win-rate">{winRate}%</td>
                <td className="streak">{entry.current_win_streak || 0}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export default LeaderboardTable;
