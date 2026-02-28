import { Link } from 'react-router-dom';

function CharacterItem({ character }) {
  return (
    <div className="character-item">
      <div className="character-item-header">
        <h3 className="character-item-name">{character.name}</h3>
      </div>
      <div className="character-item-stats">
        <div className="stat-item">
          <span className="stat-label">HP</span>
          <span className="stat-value">{character.max_hp}</span>
        </div>
        <div className="stat-item">
          <span className="stat-label">攻撃</span>
          <span className="stat-value">{character.attack}</span>
        </div>
        <div className="stat-item">
          <span className="stat-label">防御</span>
          <span className="stat-value">{character.defense}</span>
        </div>
        <div className="stat-item">
          <span className="stat-label">速度</span>
          <span className="stat-value">{character.speed}</span>
        </div>
      </div>
      <div className="character-item-footer">
        <p className="character-owner">Owner: {character.owner_name || 'Unknown'}</p>
      </div>
    </div>
  );
}

export default CharacterItem;
