import { useState, useEffect, useCallback } from 'react';
import { getBattle, getBattleTurns } from '../api/client';

export function useBattleState(battleId) {
  const [battleState, setBattleState] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchBattle() {
      if (!battleId) {
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        setError(null);
        const battle = await getBattle(battleId);
        const turns = await getBattleTurns(battleId);
        setBattleState({ ...battle, turns: turns || [] });
      } catch (err) {
        console.error('Failed to fetch battle:', err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }

    fetchBattle();
  }, [battleId]);

  const updateBattle = useCallback((data) => {
    setBattleState(prev => {
      if (!prev) return data;
      return { ...prev, ...data };
    });
  }, []);

  const addTurn = useCallback((turnData) => {
    setBattleState(prev => {
      if (!prev) return prev;

      return {
        ...prev,
        current_turn: turnData.turn_number,
        turns: [...prev.turns, turnData],
        player1: {
          ...prev.player1,
          current_hp: turnData.player1_hp_after,
          current_action: turnData.player1_action
        },
        player2: {
          ...prev.player2,
          current_hp: turnData.player2_hp_after,
          current_action: turnData.player2_action
        }
      };
    });
  }, []);

  const endBattle = useCallback((resultData) => {
    setBattleState(prev => {
      if (!prev) return prev;

      return {
        ...prev,
        status: 'finished',
        winner_id: resultData.winner_id,
        winner_name: resultData.winner_name,
        ended_at: resultData.ended_at
      };
    });
  }, []);

  return {
    battleState,
    loading,
    error,
    updateBattle,
    addTurn,
    endBattle
  };
}
