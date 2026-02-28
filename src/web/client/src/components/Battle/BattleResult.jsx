function BattleResult({ winner, player1, player2 }) {
  if (!winner) return null;

  const winnerName = winner.name || winner;

  return (
    <div className="battle-result">
      <div className="result-overlay">
        <div className="result-card">
          <h2 className="result-title">バトル終了</h2>
          <div className="winner-announcement">
            <p className="winner-label">勝者</p>
            <p className="winner-name">{winnerName}</p>
          </div>
          <div className="final-stats">
            <div className="player-final-stat">
              <h4>{player1?.name}</h4>
              <p>最終HP: {player1?.current_hp || 0}</p>
            </div>
            <div className="player-final-stat">
              <h4>{player2?.name}</h4>
              <p>最終HP: {player2?.current_hp || 0}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default BattleResult;
