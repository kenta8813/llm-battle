function CharacterCard({ character, side, isActive }) {
  if (!character) {
    return null;
  }

  const hpPercentage = (character.current_hp / character.max_hp) * 100;
  const getHpColor = (percentage) => {
    if (percentage > 70) return 'var(--color-hp-high)';
    if (percentage > 30) return 'var(--color-hp-medium)';
    return 'var(--color-hp-low)';
  };

  return (
    <div className={`character-card ${side} ${isActive ? 'active' : ''}`}>
      <div className="character-name">{character.name}</div>

      <div className="hp-bar">
        <div
          className="hp-bar-fill"
          style={{
            width: `${Math.max(0, hpPercentage)}%`,
            backgroundColor: getHpColor(hpPercentage)
          }}
        />
        <div className="hp-text">
          HP: {Math.max(0, character.current_hp)} / {character.max_hp}
        </div>
      </div>

      <div className="stats">
        <div className="stat">
          <span className="stat-label">攻撃</span>
          <span className="stat-value">{character.attack || 0}</span>
        </div>
        <div className="stat">
          <span className="stat-label">防御</span>
          <span className="stat-value">{character.defense || 0}</span>
        </div>
        <div className="stat">
          <span className="stat-label">速度</span>
          <span className="stat-value">{character.speed || 0}</span>
        </div>
      </div>

      {character.current_action && (
        <div className="current-action">
          {character.current_action}
        </div>
      )}
    </div>
  );
}

export default CharacterCard;
