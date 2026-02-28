import express from 'express';
import cors from 'cors';
import path from 'path';
import { fileURLToPath } from 'url';
import { createServer } from 'http';
import { Server } from 'socket.io';
import apiRouter from './api.js';

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

// API routes
app.use('/api', apiRouter);

// Static files (future web client)
const publicPath = path.join(__dirname, '../../public');
app.use(express.static(publicPath));

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

// 404 handler
app.use((req, res) => {
  res.status(404).json({ error: 'Not found' });
});

// Error handler
app.use((err, req, res, next) => {
  console.error('Error:', err);
  res.status(500).json({ error: 'Internal server error' });
});

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

// Export io for use in other modules
export { io };

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
