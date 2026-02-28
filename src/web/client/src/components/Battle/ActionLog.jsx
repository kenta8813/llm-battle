import { useEffect, useRef } from 'react';

function ActionLog({ turns }) {
  const logRef = useRef(null);

  useEffect(() => {
    // 新しいターンが追加されたら自動スクロール
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [turns]);

  const formatAction = (action, damage) => {
    if (action === 'attack') {
      return `攻撃！ ${damage || 0}ダメージ`;
    } else if (action === 'defend') {
      return '防御態勢';
    } else if (action === 'dodge') {
      return '回避';
    } else if (action === 'ability') {
      return `アビリティ使用！ ${damage || 0}ダメージ`;
    }
    return action || '待機';
  };

  if (!turns || turns.length === 0) {
    return (
      <div className="action-log">
        <h3>行動ログ</h3>
        <div className="log-entries">
          <p className="no-turns">まだターンが実行されていません</p>
        </div>
      </div>
    );
  }

  return (
    <div className="action-log" ref={logRef}>
      <h3>行動ログ</h3>
      <div className="log-entries">
        {turns.map((turn, index) => (
          <div key={index} className="log-entry">
            <div className="turn-number">ターン {turn.turn_number}</div>
            <div className="actions">
              <div className="action player1">
                <strong>{turn.player1_name || 'Player 1'}:</strong>{' '}
                {formatAction(turn.player1_action, turn.player1_damage_dealt)}
              </div>
              <div className="action player2">
                <strong>{turn.player2_name || 'Player 2'}:</strong>{' '}
                {formatAction(turn.player2_action, turn.player2_damage_dealt)}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default ActionLog;
