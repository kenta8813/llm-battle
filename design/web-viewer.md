# Webビュアー設計書

**プロジェクト**: LLMバトルゲーム
**作成日**: 2026-02-28
**担当**: Director
**技術スタック**: React 18 + Vite + Socket.IO Client / Node.js + Express + Socket.IO

---

## 1. Webビュアー概要

### 1.1 目的
- バトルの視覚的な観戦
- キャラクター情報の閲覧
- リーダーボードの表示
- バトル履歴の確認

### 1.2 設計原則
- シンプルで直感的なUI
- リアルタイム更新
- レスポンシブデザイン（PC優先）
- アニメーション効果で臨場感

---

## 2. システム構成

### 2.1 全体構成

```
┌─────────────────────────────────────────┐
│         Webサーバー (Node.js)             │
│                                         │
│  ┌────────────┐    ┌────────────┐     │
│  │ Express    │    │ Socket.IO  │     │
│  │ (REST API) │    │ (WebSocket)│     │
│  └────────────┘    └────────────┘     │
│         │                 │            │
└─────────┼─────────────────┼────────────┘
          │                 │
          │ HTTP            │ WebSocket
          │                 │
┌─────────▼─────────────────▼────────────┐
│       Webクライアント (React)            │
│                                         │
│  ┌─────────────────────────────────┐  │
│  │         App Router               │  │
│  │  /           - Home (Landing)    │  │
│  │  /battle/:id - Battle Viewer     │  │
│  │  /characters - Character List    │  │
│  │  /leaderboard - Leaderboard      │  │
│  └─────────────────────────────────┘  │
│                                         │
└─────────────────────────────────────────┘
```

### 2.2 ディレクトリ構造

```
src/web/
├── server/                 # Webサーバー（Node.js）
│   ├── index.js            # エントリポイント
│   ├── api/
│   │   ├── battles.js      # バトルAPI
│   │   ├── characters.js   # キャラクターAPI
│   │   └── leaderboard.js  # リーダーボードAPI
│   ├── socket/
│   │   ├── handler.js      # WebSocketハンドラ
│   │   └── events.js       # イベント定義
│   └── middleware/
│       ├── cors.js         # CORS設定
│       └── error.js        # エラーハンドリング
│
└── client/                 # Webクライアント（React）
    ├── src/
    │   ├── main.jsx        # エントリポイント
    │   ├── App.jsx         # ルートコンポーネント
    │   ├── pages/
    │   │   ├── Home.jsx
    │   │   ├── BattleViewer.jsx
    │   │   ├── CharacterList.jsx
    │   │   └── Leaderboard.jsx
    │   ├── components/
    │   │   ├── Battle/
    │   │   │   ├── BattleField.jsx
    │   │   │   ├── CharacterCard.jsx
    │   │   │   ├── TurnIndicator.jsx
    │   │   │   ├── ActionLog.jsx
    │   │   │   └── BattleResult.jsx
    │   │   ├── Character/
    │   │   │   ├── CharacterItem.jsx
    │   │   │   └── CharacterDetails.jsx
    │   │   ├── Leaderboard/
    │   │   │   └── LeaderboardTable.jsx
    │   │   └── Common/
    │   │       ├── Header.jsx
    │   │       ├── Footer.jsx
    │   │       └── Loading.jsx
    │   ├── hooks/
    │   │   ├── useWebSocket.js
    │   │   ├── useBattleState.js
    │   │   └── useApi.js
    │   ├── api/
    │   │   └── client.js
    │   └── styles/
    │       ├── index.css
    │       └── components/
    ├── public/
    │   ├── index.html
    │   └── assets/
    └── vite.config.js
```

---

## 3. Webサーバー設計（Node.js + Express）

### 3.1 サーバーエントリポイント

```javascript
// src/web/server/index.js
import express from 'express';
import { createServer } from 'http';
import { Server } from 'socket.io';
import cors from 'cors';
import battleRouter from './api/battles.js';
import characterRouter from './api/characters.js';
import leaderboardRouter from './api/leaderboard.js';
import { handleSocketConnection } from './socket/handler.js';

const app = express();
const httpServer = createServer(app);
const io = new Server(httpServer, {
  cors: {
    origin: 'http://localhost:5173',
    methods: ['GET', 'POST']
  }
});

// ミドルウェア
app.use(cors());
app.use(express.json());

// REST APIルート
app.use('/api/battles', battleRouter);
app.use('/api/characters', characterRouter);
app.use('/api/leaderboard', leaderboardRouter);

// WebSocket接続
io.on('connection', (socket) => handleSocketConnection(socket, io));

// サーバー起動
const PORT = process.env.PORT || 3000;
httpServer.listen(PORT, () => {
  console.log(`Server running on http://localhost:${PORT}`);
});
```

### 3.2 REST API設計

#### バトルAPI

```javascript
// GET /api/battles/:id - バトル詳細取得
router.get('/:id', async (req, res) => {
  try {
    const battleId = req.params.id;
    const battle = await getBattleFromDB(battleId);

    if (!battle) {
      return res.status(404).json({ error: 'Battle not found' });
    }

    res.json(battle);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// GET /api/battles - バトル一覧取得
router.get('/', async (req, res) => {
  try {
    const { status, limit = 20, offset = 0 } = req.query;
    const battles = await getBattlesFromDB({ status, limit, offset });
    res.json(battles);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// GET /api/battles/:id/turns - ターン履歴取得
router.get('/:id/turns', async (req, res) => {
  try {
    const battleId = req.params.id;
    const turns = await getBattleTurnsFromDB(battleId);
    res.json(turns);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});
```

#### キャラクターAPI

```javascript
// GET /api/characters/:id - キャラクター詳細取得
router.get('/:id', async (req, res) => {
  try {
    const characterId = req.params.id;
    const character = await getCharacterFromDB(characterId);
    res.json(character);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// GET /api/characters - キャラクター一覧取得
router.get('/', async (req, res) => {
  try {
    const { limit = 50, offset = 0 } = req.query;
    const characters = await getCharactersFromDB({ limit, offset });
    res.json(characters);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// GET /api/characters/:id/stats - 戦績取得
router.get('/:id/stats', async (req, res) => {
  try {
    const characterId = req.params.id;
    const stats = await getCharacterStatsFromDB(characterId);
    res.json(stats);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});
```

#### リーダーボードAPI

```javascript
// GET /api/leaderboard - リーダーボード取得
router.get('/', async (req, res) => {
  try {
    const { limit = 50 } = req.query;
    const leaderboard = await getLeaderboardFromDB(limit);
    res.json(leaderboard);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});
```

### 3.3 WebSocketイベント設計

#### サーバー → クライアント

```javascript
// socket/events.js
export const EVENTS = {
  // バトル関連
  BATTLE_STARTED: 'battle_started',
  TURN_EXECUTED: 'turn_executed',
  BATTLE_ENDED: 'battle_ended',

  // リーダーボード更新
  LEADERBOARD_UPDATED: 'leaderboard_updated',

  // エラー
  ERROR: 'error'
};

// socket/handler.js
export function handleSocketConnection(socket, io) {
  console.log(`Client connected: ${socket.id}`);

  // バトル購読
  socket.on('subscribe_battle', (battleId) => {
    socket.join(`battle_${battleId}`);
    console.log(`Socket ${socket.id} subscribed to battle ${battleId}`);
  });

  // バトル購読解除
  socket.on('unsubscribe_battle', (battleId) => {
    socket.leave(`battle_${battleId}`);
    console.log(`Socket ${socket.id} unsubscribed from battle ${battleId}`);
  });

  // 切断処理
  socket.on('disconnect', () => {
    console.log(`Client disconnected: ${socket.id}`);
  });
}

// バトル開始時の通知（MCPサーバーから呼ばれる）
export function notifyBattleStarted(io, battleId, battleData) {
  io.to(`battle_${battleId}`).emit(EVENTS.BATTLE_STARTED, battleData);
}

// ターン実行時の通知
export function notifyTurnExecuted(io, battleId, turnData) {
  io.to(`battle_${battleId}`).emit(EVENTS.TURN_EXECUTED, turnData);
}

// バトル終了時の通知
export function notifyBattleEnded(io, battleId, resultData) {
  io.to(`battle_${battleId}`).emit(EVENTS.BATTLE_ENDED, resultData);
}
```

---

## 4. Webクライアント設計（React + Vite）

### 4.1 ルーティング

```jsx
// App.jsx
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Home from './pages/Home';
import BattleViewer from './pages/BattleViewer';
import CharacterList from './pages/CharacterList';
import Leaderboard from './pages/Leaderboard';
import Header from './components/Common/Header';
import Footer from './components/Common/Footer';

function App() {
  return (
    <BrowserRouter>
      <div className="app">
        <Header />
        <main>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/battle/:id" element={<BattleViewer />} />
            <Route path="/characters" element={<CharacterList />} />
            <Route path="/leaderboard" element={<Leaderboard />} />
          </Routes>
        </main>
        <Footer />
      </div>
    </BrowserRouter>
  );
}

export default App;
```

### 4.2 ページコンポーネント

#### Home（ランディングページ）

```jsx
// pages/Home.jsx
import { Link } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { getRecentBattles } from '../api/client';

function Home() {
  const [recentBattles, setRecentBattles] = useState([]);

  useEffect(() => {
    async function fetchBattles() {
      const battles = await getRecentBattles();
      setRecentBattles(battles);
    }
    fetchBattles();
  }, []);

  return (
    <div className="home">
      <section className="hero">
        <h1>LLM Battle Game</h1>
        <p>LLM同士が完全自律的に戦うバトルゲーム</p>
        <div className="cta-buttons">
          <Link to="/leaderboard" className="btn btn-primary">
            リーダーボード
          </Link>
          <Link to="/characters" className="btn btn-secondary">
            キャラクター一覧
          </Link>
        </div>
      </section>

      <section className="recent-battles">
        <h2>最近のバトル</h2>
        <div className="battle-list">
          {recentBattles.map(battle => (
            <Link
              key={battle.id}
              to={`/battle/${battle.id}`}
              className="battle-card"
            >
              <div className="players">
                <span>{battle.player1_name}</span>
                <span>vs</span>
                <span>{battle.player2_name}</span>
              </div>
              <div className="result">
                {battle.status === 'finished'
                  ? `勝者: ${battle.winner_name}`
                  : '進行中'}
              </div>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}

export default Home;
```

#### BattleViewer（バトル観戦ページ）

```jsx
// pages/BattleViewer.jsx
import { useParams } from 'react-router-dom';
import { useState, useEffect } from 'react';
import BattleField from '../components/Battle/BattleField';
import TurnIndicator from '../components/Battle/TurnIndicator';
import ActionLog from '../components/Battle/ActionLog';
import BattleResult from '../components/Battle/BattleResult';
import { useBattleState } from '../hooks/useBattleState';
import { useWebSocket } from '../hooks/useWebSocket';

function BattleViewer() {
  const { id } = useParams();
  const { battleState, updateBattle, addTurn, endBattle } = useBattleState(id);
  const { connected } = useWebSocket({
    battleId: id,
    onBattleStarted: updateBattle,
    onTurnExecuted: addTurn,
    onBattleEnded: endBattle
  });

  if (!battleState) {
    return <div className="loading">バトル情報を読み込み中...</div>;
  }

  return (
    <div className="battle-viewer">
      <TurnIndicator
        currentTurn={battleState.current_turn}
        maxTurns={battleState.max_turns}
      />

      <BattleField
        player1={battleState.player1}
        player2={battleState.player2}
      />

      <ActionLog turns={battleState.turns} />

      {battleState.status === 'finished' && (
        <BattleResult
          winner={battleState.winner}
          player1={battleState.player1}
          player2={battleState.player2}
        />
      )}

      {!connected && (
        <div className="connection-warning">
          接続が切断されました。再接続中...
        </div>
      )}
    </div>
  );
}

export default BattleViewer;
```

#### Leaderboard（リーダーボードページ）

```jsx
// pages/Leaderboard.jsx
import { useState, useEffect } from 'react';
import { getLeaderboard } from '../api/client';
import LeaderboardTable from '../components/Leaderboard/LeaderboardTable';

function Leaderboard() {
  const [leaderboard, setLeaderboard] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchLeaderboard() {
      setLoading(true);
      const data = await getLeaderboard();
      setLeaderboard(data);
      setLoading(false);
    }
    fetchLeaderboard();

    // 30秒ごとに更新
    const interval = setInterval(fetchLeaderboard, 30000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return <div className="loading">読み込み中...</div>;
  }

  return (
    <div className="leaderboard-page">
      <h1>リーダーボード</h1>
      <LeaderboardTable data={leaderboard} />
    </div>
  );
}

export default Leaderboard;
```

### 4.3 主要コンポーネント

#### BattleField（バトルフィールド表示）

```jsx
// components/Battle/BattleField.jsx
import CharacterCard from './CharacterCard';

function BattleField({ player1, player2 }) {
  return (
    <div className="battle-field">
      <CharacterCard
        character={player1}
        side="left"
        isActive={player1.is_active}
      />

      <div className="vs-indicator">VS</div>

      <CharacterCard
        character={player2}
        side="right"
        isActive={player2.is_active}
      />
    </div>
  );
}

export default BattleField;
```

#### CharacterCard（キャラクターカード）

```jsx
// components/Battle/CharacterCard.jsx
function CharacterCard({ character, side, isActive }) {
  const hpPercentage = (character.current_hp / character.max_hp) * 100;

  return (
    <div className={`character-card ${side} ${isActive ? 'active' : ''}`}>
      <div className="character-name">{character.name}</div>

      <div className="hp-bar">
        <div className="hp-bar-fill" style={{ width: `${hpPercentage}%` }} />
        <div className="hp-text">
          {character.current_hp} / {character.max_hp}
        </div>
      </div>

      <div className="stats">
        <div className="stat">
          <span className="stat-label">攻撃</span>
          <span className="stat-value">{character.attack}</span>
        </div>
        <div className="stat">
          <span className="stat-label">防御</span>
          <span className="stat-value">{character.defense}</span>
        </div>
        <div className="stat">
          <span className="stat-label">速度</span>
          <span className="stat-value">{character.speed}</span>
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
```

#### ActionLog（行動ログ）

```jsx
// components/Battle/ActionLog.jsx
import { useEffect, useRef } from 'react';

function ActionLog({ turns }) {
  const logRef = useRef(null);

  useEffect(() => {
    // 新しいターンが追加されたら自動スクロール
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [turns]);

  return (
    <div className="action-log" ref={logRef}>
      <h3>行動ログ</h3>
      <div className="log-entries">
        {turns.map((turn, index) => (
          <div key={index} className="log-entry">
            <div className="turn-number">ターン {turn.turn_number}</div>
            <div className="actions">
              <div className="action player1">
                {formatAction(turn.player1_action, turn.player1_damage_dealt)}
              </div>
              <div className="action player2">
                {formatAction(turn.player2_action, turn.player2_damage_dealt)}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function formatAction(action, damage) {
  if (action === 'attack') {
    return `攻撃！ ${damage}ダメージ`;
  } else if (action === 'defend') {
    return '防御態勢';
  } else if (action === 'dodge') {
    return '回避';
  } else if (action === 'ability') {
    return `アビリティ使用！ ${damage}ダメージ`;
  }
  return action;
}

export default ActionLog;
```

#### LeaderboardTable（リーダーボードテーブル）

```jsx
// components/Leaderboard/LeaderboardTable.jsx
function LeaderboardTable({ data }) {
  return (
    <table className="leaderboard-table">
      <thead>
        <tr>
          <th>順位</th>
          <th>キャラクター名</th>
          <th>レーティング</th>
          <th>バトル数</th>
          <th>勝率</th>
          <th>連勝</th>
        </tr>
      </thead>
      <tbody>
        {data.map((entry, index) => (
          <tr key={entry.character_id}>
            <td className="rank">{index + 1}</td>
            <td className="name">{entry.name}</td>
            <td className="rating">{entry.rating}</td>
            <td className="battles">{entry.total_battles}</td>
            <td className="win-rate">{entry.win_rate}%</td>
            <td className="streak">{entry.current_win_streak}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default LeaderboardTable;
```

### 4.4 カスタムフック

#### useWebSocket

```javascript
// hooks/useWebSocket.js
import { useEffect, useState } from 'react';
import { io } from 'socket.io-client';

export function useWebSocket({ battleId, onBattleStarted, onTurnExecuted, onBattleEnded }) {
  const [socket, setSocket] = useState(null);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    const newSocket = io('http://localhost:3000', {
      reconnection: true,
      reconnectionDelay: 1000,
      reconnectionAttempts: 5
    });

    newSocket.on('connect', () => {
      console.log('WebSocket connected');
      setConnected(true);

      if (battleId) {
        newSocket.emit('subscribe_battle', battleId);
      }
    });

    newSocket.on('disconnect', () => {
      console.log('WebSocket disconnected');
      setConnected(false);
    });

    newSocket.on('battle_started', onBattleStarted);
    newSocket.on('turn_executed', onTurnExecuted);
    newSocket.on('battle_ended', onBattleEnded);

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
```

#### useBattleState

```javascript
// hooks/useBattleState.js
import { useState, useEffect } from 'react';
import { getBattle, getBattleTurns } from '../api/client';

export function useBattleState(battleId) {
  const [battleState, setBattleState] = useState(null);

  useEffect(() => {
    async function fetchBattle() {
      const battle = await getBattle(battleId);
      const turns = await getBattleTurns(battleId);
      setBattleState({ ...battle, turns });
    }
    fetchBattle();
  }, [battleId]);

  const updateBattle = (data) => {
    setBattleState(prev => ({ ...prev, ...data }));
  };

  const addTurn = (turnData) => {
    setBattleState(prev => ({
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
    }));
  };

  const endBattle = (resultData) => {
    setBattleState(prev => ({
      ...prev,
      status: 'finished',
      winner: resultData.winner
    }));
  };

  return { battleState, updateBattle, addTurn, endBattle };
}
```

### 4.5 APIクライアント

```javascript
// api/client.js
const API_BASE = 'http://localhost:3000/api';

async function fetchAPI(endpoint) {
  const response = await fetch(`${API_BASE}${endpoint}`);
  if (!response.ok) {
    throw new Error(`API error: ${response.statusText}`);
  }
  return response.json();
}

export async function getBattle(battleId) {
  return fetchAPI(`/battles/${battleId}`);
}

export async function getBattleTurns(battleId) {
  return fetchAPI(`/battles/${battleId}/turns`);
}

export async function getRecentBattles() {
  return fetchAPI('/battles?status=finished&limit=10');
}

export async function getCharacter(characterId) {
  return fetchAPI(`/characters/${characterId}`);
}

export async function getCharacters() {
  return fetchAPI('/characters');
}

export async function getLeaderboard() {
  return fetchAPI('/leaderboard');
}

export async function getCharacterStats(characterId) {
  return fetchAPI(`/characters/${characterId}/stats`);
}
```

---

## 5. スタイリング設計

### 5.1 デザインシステム

#### カラーパレット

```css
:root {
  /* Primary colors */
  --color-primary: #3b82f6;
  --color-primary-dark: #2563eb;
  --color-primary-light: #60a5fa;

  /* Secondary colors */
  --color-secondary: #8b5cf6;
  --color-secondary-dark: #7c3aed;
  --color-secondary-light: #a78bfa;

  /* Status colors */
  --color-success: #10b981;
  --color-warning: #f59e0b;
  --color-error: #ef4444;
  --color-info: #3b82f6;

  /* HP bar colors */
  --color-hp-high: #10b981;
  --color-hp-medium: #f59e0b;
  --color-hp-low: #ef4444;

  /* Neutral colors */
  --color-bg: #0f172a;
  --color-bg-secondary: #1e293b;
  --color-bg-tertiary: #334155;
  --color-text: #f1f5f9;
  --color-text-secondary: #cbd5e1;
  --color-border: #475569;
}
```

#### タイポグラフィ

```css
/* Font families */
--font-primary: 'Inter', system-ui, sans-serif;
--font-mono: 'Fira Code', monospace;

/* Font sizes */
--text-xs: 0.75rem;
--text-sm: 0.875rem;
--text-base: 1rem;
--text-lg: 1.125rem;
--text-xl: 1.25rem;
--text-2xl: 1.5rem;
--text-3xl: 1.875rem;
--text-4xl: 2.25rem;
```

### 5.2 主要スタイル

#### BattleField

```css
.battle-field {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 2rem;
  background: var(--color-bg-secondary);
  border-radius: 1rem;
  margin: 2rem 0;
}

.character-card {
  width: 300px;
  padding: 1.5rem;
  background: var(--color-bg-tertiary);
  border-radius: 0.5rem;
  border: 2px solid var(--color-border);
  transition: all 0.3s ease;
}

.character-card.active {
  border-color: var(--color-primary);
  box-shadow: 0 0 20px rgba(59, 130, 246, 0.5);
  transform: scale(1.05);
}

.hp-bar {
  position: relative;
  width: 100%;
  height: 30px;
  background: var(--color-bg);
  border-radius: 0.25rem;
  overflow: hidden;
  margin: 1rem 0;
}

.hp-bar-fill {
  height: 100%;
  background: linear-gradient(90deg,
    var(--color-hp-low) 0%,
    var(--color-hp-medium) 50%,
    var(--color-hp-high) 100%);
  transition: width 0.5s ease;
}

.hp-text {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  color: var(--color-text);
  font-weight: bold;
}

.vs-indicator {
  font-size: var(--text-4xl);
  font-weight: bold;
  color: var(--color-primary);
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.7; transform: scale(1.1); }
}
```

#### ActionLog

```css
.action-log {
  max-height: 400px;
  overflow-y: auto;
  padding: 1rem;
  background: var(--color-bg-secondary);
  border-radius: 0.5rem;
}

.log-entry {
  padding: 0.75rem;
  margin: 0.5rem 0;
  background: var(--color-bg-tertiary);
  border-left: 3px solid var(--color-primary);
  border-radius: 0.25rem;
  animation: slideIn 0.3s ease;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateX(-20px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}
```

---

## 6. アニメーション効果

### 6.1 ダメージエフェクト

```jsx
function DamageEffect({ damage, position }) {
  return (
    <div
      className="damage-effect"
      style={{
        left: position.x,
        top: position.y
      }}
    >
      -{damage}
    </div>
  );
}
```

```css
.damage-effect {
  position: absolute;
  font-size: 2rem;
  font-weight: bold;
  color: var(--color-error);
  animation: damageFloat 1s ease-out forwards;
  pointer-events: none;
}

@keyframes damageFloat {
  0% {
    opacity: 1;
    transform: translateY(0);
  }
  100% {
    opacity: 0;
    transform: translateY(-50px);
  }
}
```

### 6.2 ターンインジケーター

```css
.turn-indicator {
  text-align: center;
  padding: 1rem;
  background: var(--color-bg-secondary);
  border-radius: 0.5rem;
  margin: 1rem 0;
}

.turn-progress {
  width: 100%;
  height: 10px;
  background: var(--color-bg);
  border-radius: 5px;
  overflow: hidden;
  margin: 0.5rem 0;
}

.turn-progress-fill {
  height: 100%;
  background: linear-gradient(90deg,
    var(--color-primary),
    var(--color-secondary));
  transition: width 0.5s ease;
}
```

---

## 7. レスポンシブデザイン

### 7.1 ブレークポイント

```css
/* Mobile: < 640px */
/* Tablet: 640px - 1024px */
/* Desktop: > 1024px */

@media (max-width: 1024px) {
  .battle-field {
    flex-direction: column;
    gap: 1rem;
  }

  .character-card {
    width: 100%;
    max-width: 400px;
  }

  .vs-indicator {
    transform: rotate(90deg);
  }
}

@media (max-width: 640px) {
  .battle-viewer {
    padding: 0.5rem;
  }

  .character-card {
    padding: 1rem;
  }

  .action-log {
    max-height: 300px;
  }
}
```

---

## 8. パフォーマンス最適化

### 8.1 コード分割

```javascript
// main.jsx
import { lazy, Suspense } from 'react';

const BattleViewer = lazy(() => import('./pages/BattleViewer'));
const Leaderboard = lazy(() => import('./pages/Leaderboard'));

function App() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <Routes>
        <Route path="/battle/:id" element={<BattleViewer />} />
        <Route path="/leaderboard" element={<Leaderboard />} />
      </Routes>
    </Suspense>
  );
}
```

### 8.2 メモ化

```jsx
import { memo } from 'react';

const CharacterCard = memo(function CharacterCard({ character, side }) {
  // レンダリング処理
}, (prevProps, nextProps) => {
  // 変更がない場合は再レンダリングしない
  return prevProps.character.current_hp === nextProps.character.current_hp
    && prevProps.character.current_action === nextProps.character.current_action;
});
```

---

## 9. エラーハンドリング

### 9.1 エラーバウンダリ

```jsx
class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    console.error('Error caught by boundary:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="error-page">
          <h1>エラーが発生しました</h1>
          <p>ページをリロードしてください</p>
        </div>
      );
    }

    return this.props.children;
  }
}
```

### 9.2 接続エラー処理

```jsx
function ConnectionStatus({ connected }) {
  if (!connected) {
    return (
      <div className="connection-error">
        <p>サーバーとの接続が切断されました</p>
        <button onClick={() => window.location.reload()}>
          再接続
        </button>
      </div>
    );
  }
  return null;
}
```

---

## 10. セキュリティ

### 10.1 XSS対策
- Reactのデフォルト動作でエスケープされる
- `dangerouslySetInnerHTML`は使用しない

### 10.2 CORS設定
- WebサーバーでCORS許可設定
- 本番環境では適切なオリジンのみ許可

---

## 11. デプロイ

### 11.1 ビルド

```bash
# クライアントビルド
cd src/web/client
npm run build

# ビルド結果は dist/ に出力される
```

### 11.2 本番環境設定

```javascript
// vite.config.js
import { defineConfig } from 'vite';

export default defineConfig({
  build: {
    outDir: 'dist',
    sourcemap: false,
    minify: 'terser'
  },
  server: {
    proxy: {
      '/api': 'http://localhost:3000',
      '/socket.io': {
        target: 'http://localhost:3000',
        ws: true
      }
    }
  }
});
```

---

## 12. テスト

### 12.1 コンポーネントテスト

```javascript
// __tests__/CharacterCard.test.jsx
import { render, screen } from '@testing-library/react';
import CharacterCard from '../components/Battle/CharacterCard';

test('renders character name', () => {
  const character = {
    name: 'Test Character',
    current_hp: 100,
    max_hp: 100,
    attack: 80,
    defense: 60,
    speed: 70
  };

  render(<CharacterCard character={character} side="left" />);
  expect(screen.getByText('Test Character')).toBeInTheDocument();
});
```

---

## 13. 関連ドキュメント

- [システムアーキテクチャ](./architecture.md)
- [MCPサーバー設計](./mcp-server.md)
- [バトルロジック設計](./battle-logic.md)

---

**設計承認**: 待機中
**次のステップ**: 実装フェーズへ移行（Operatorへ引き継ぎ）
