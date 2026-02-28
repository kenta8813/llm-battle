function TurnIndicator({ currentTurn, maxTurns }) {
  const progress = (currentTurn / maxTurns) * 100;

  return (
    <div className="turn-indicator">
      <h2 className="turn-title">
        ターン {currentTurn || 0} / {maxTurns || 100}
      </h2>
      <div className="turn-progress">
        <div
          className="turn-progress-fill"
          style={{ width: `${progress}%` }}
        />
      </div>
    </div>
  );
}

export default TurnIndicator;
