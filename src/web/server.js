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
import { setIo } from './io.js';

// Load environment variables
dotenv.config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Initialize Express app
const app = express();
const httpServer = createServer(app);
const PORT = process.env.PORT || 3000;

// CORS origins: comma-separated list in CORS_ORIGINS env var
const allowedOrigins = process.env.CORS_ORIGINS
  ? process.env.CORS_ORIGINS.split(',').map(o => o.trim())
  : ['http://localhost:5173', 'http://localhost:3000'];

const io = new Server(httpServer, {
  cors: {
    origin: allowedOrigins,
    methods: ['GET', 'POST']
  }
});

// Middleware
app.use(cors({ origin: allowedOrigins }));
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

// Serve React client build
const clientBuildPath = path.join(__dirname, 'client/dist');
app.use(express.static(clientBuildPath));

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

// SPA fallback - serve index.html for all non-API routes
app.get('*', (req, res, next) => {
  if (req.path.startsWith('/api') || req.path.startsWith('/mcp') || req.path === '/health') {
    return next();
  }
  res.sendFile(path.join(clientBuildPath, 'index.html'), err => { if (err) next(); });
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

// Start server
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
