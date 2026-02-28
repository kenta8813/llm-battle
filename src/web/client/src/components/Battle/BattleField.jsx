import CharacterCard from './CharacterCard';

function BattleField({ player1, player2 }) {
  return (
    <div className="battle-field">
      <CharacterCard
        character={player1}
        side="left"
        isActive={player1?.is_active}
      />

      <div className="vs-indicator">VS</div>

      <CharacterCard
        character={player2}
        side="right"
        isActive={player2?.is_active}
      />
    </div>
  );
}

export default BattleField;
