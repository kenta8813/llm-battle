import { useEffect, useState, useCallback } from 'react';
import { io } from 'socket.io-client';

export function useWebSocket({ battleId, onBattleStarted, onTurnExecuted, onBattleEnded }) {
  const [socket, setSocket] = useState(null);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    const WS_URL = import.meta.env.VITE_WS_URL || 'http://localhost:3000';
    const newSocket = io(WS_URL, {
      reconnection: true,
      reconnectionDelay: 1000,
      reconnectionAttempts: 5,
      transports: ['websocket', 'polling']
    });

    newSocket.on('connect', () => {
      console.log('WebSocket connected:', newSocket.id);
      setConnected(true);

      if (battleId) {
        newSocket.emit('subscribe_battle', battleId);
        console.log('Subscribed to battle:', battleId);
      }
    });

    newSocket.on('disconnect', () => {
      console.log('WebSocket disconnected');
      setConnected(false);
    });

    newSocket.on('connect_error', (error) => {
      console.error('WebSocket connection error:', error);
      setConnected(false);
    });

    // Battle event listeners
    if (onBattleStarted) {
      newSocket.on('battle_started', onBattleStarted);
    }

    if (onTurnExecuted) {
      newSocket.on('turn_executed', onTurnExecuted);
    }

    if (onBattleEnded) {
      newSocket.on('battle_ended', onBattleEnded);
    }

    setSocket(newSocket);

    return () => {
      if (battleId) {
        newSocket.emit('unsubscribe_battle', battleId);
      }
      newSocket.close();
    };
  }, [battleId, onBattleStarted, onTurnExecuted, onBattleEnded]);

  return { socket, connected };
}
