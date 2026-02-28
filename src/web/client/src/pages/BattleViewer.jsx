import { useParams } from 'react-router-dom';
import { useCallback } from 'react';
import BattleField from '../components/Battle/BattleField';
import TurnIndicator from '../components/Battle/TurnIndicator';
import ActionLog from '../components/Battle/ActionLog';
import BattleResult from '../components/Battle/BattleResult';
import Loading from '../components/Common/Loading';
import { useBattleState } from '../hooks/useBattleState';
import { useWebSocket } from '../hooks/useWebSocket';

function BattleViewer() {
  const { id } = useParams();
  const { battleState, loading, error, updateBattle, addTurn, endBattle } = useBattleState(id);

  const handleBattleStarted = useCallback((data) => {
    console.log('Battle started:', data);
    updateBattle(data);
  }, [updateBattle]);

  const handleTurnExecuted = useCallback((data) => {
    console.log('Turn executed:', data);
    addTurn(data);
  }, [addTurn]);

  const handleBattleEnded = useCallback((data) => {
    console.log('Battle ended:', data);
    endBattle(data);
  }, [endBattle]);

  const { connected } = useWebSocket({
    battleId: id,
    onBattleStarted: handleBattleStarted,
    onTurnExecuted: handleTurnExecuted,
    onBattleEnded: handleBattleEnded
  });

  if (loading) {
    return <Loading message="バトル情報を読み込み中..." />;
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

  if (!battleState) {
    return (
      <div className="error-page">
        <h2>バトルが見つかりません</h2>
        <p>指定されたバトルは存在しません。</p>
      </div>
    );
  }

  return (
    <div className="battle-viewer">
      <div className="battle-header">
        <h1>バトル観戦</h1>
        {!connected && (
          <div className="connection-warning">
            接続が切断されました。再接続中...
          </div>
        )}
      </div>

      <TurnIndicator
        currentTurn={battleState.current_turn}
        maxTurns={battleState.max_turns || 100}
      />

      <BattleField
        player1={battleState.player1}
        player2={battleState.player2}
      />

      <ActionLog turns={battleState.turns || []} />

      {battleState.status === 'finished' && (
        <BattleResult
          winner={battleState.winner_name || battleState.winner}
          player1={battleState.player1}
          player2={battleState.player2}
        />
      )}
    </div>
  );
}

export default BattleViewer;
