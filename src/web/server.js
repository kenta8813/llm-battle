import express from 'express';
import cors from 'cors';
import path from 'path';
import { fileURLToPath } from 'url';
import { createServer } from 'http';
import { Server } from 'socket.io';
import dotenv from 'dotenv';
import apiRouter from './api.js';
import accountsRouter from './api/accounts.js';
import charactersRouter from './api/characters.js';
import matchmakingRouter from './api/matchmaking.js';
import battlesRouter from './api/battles.js';
import { errorHandler, notFoundHandler } from './middleware/error_handler.js';
import { handleMcpRequest } from './mcp/index.js';
import { run } from './db.js';
import { setIo } from './io.js';

// Load environment variables
dotenv.config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Initialize Express app
const app = express();
const httpServer = createServer(app);
const io = new Server(httpServer, {
  cors: {
    origin: 'http://localhost:5173',
    methods: ['GET', 'POST']
  }
});
const PORT = process.env.PORT || 3000;

// Middleware
app.use(cors());
app.use(express.json());

// Request logging middleware
app.use((req, res, next) => {
  console.log(`${new Date().toISOString()} ${req.method} ${req.url}`);
  next();
});

// MCP endpoint - all HTTP methods (Streamable HTTP transport)
app.all('/mcp', handleMcpRequest);

// API routes (order matters - specific routes before general ones)
app.use('/api/accounts', accountsRouter); // Account management (create, login)
app.use('/api/characters', charactersRouter); // Character management (CRUD) - includes /api/characters/abilities
app.use('/api/queue', matchmakingRouter); // Matchmaking queue (CRUD)
app.use('/api/battles', battlesRouter); // Battle management (CRUD)
app.use('/api', apiRouter); // Existing read-only routes (leaderboard, etc.) - must be last

// Static files (future web client)
const publicPath = path.join(__dirname, '../../public');
app.use(express.static(publicPath));

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

// 404 handler (must be before error handler)
app.use(notFoundHandler);

// Error handler (must be last)
app.use(errorHandler);

// WebSocket connection handling
io.on('connection', (socket) => {
  console.log(`WebSocket client connected: ${socket.id}`);

  // Handle battle subscription
  socket.on('subscribe_battle', (battleId) => {
    socket.join(`battle_${battleId}`);
    console.log(`Socket ${socket.id} subscribed to battle ${battleId}`);
  });

  // Handle battle unsubscription
  socket.on('unsubscribe_battle', (battleId) => {
    socket.leave(`battle_${battleId}`);
    console.log(`Socket ${socket.id} unsubscribed from battle ${battleId}`);
  });

  // Handle disconnection
  socket.on('disconnect', () => {
    console.log(`WebSocket client disconnected: ${socket.id}`);
  });
});

// Register io singleton (breaks circular dependency with API routers)
setIo(io);

// Run DB migrations on startup
async function runMigrations() {
  try {
    await run(`ALTER TABLE accounts ADD COLUMN api_key TEXT`);
    console.log('Migration: added api_key column to accounts');
  } catch (e) {
    // Column already exists - expected on subsequent starts
  }
}

// Start server
runMigrations();
httpServer.listen(PORT, () => {
  console.log(`===================================`);
  console.log(`LLM Battle Web Server`);
  console.log(`Server running on http://localhost:${PORT}`);
  console.log(`API Base URL: http://localhost:${PORT}/api`);
  console.log(`WebSocket Server: Ready`);
  console.log(`===================================`);
});

// Graceful shutdown
process.on('SIGINT', () => {
  console.log('\nShutting down server...');
  process.exit(0);
});
