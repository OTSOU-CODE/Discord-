import express from 'express';
import http from 'http';
import { Server } from 'socket.io';
import cors from 'cors';
import path from 'path';
import os from 'os';
import { fileURLToPath } from 'url';
import RoomManager from './server/roomManager.js';
import { CATEGORIES } from './server/categories.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const PORT = process.env.PORT || 3000;
const HOST = '0.0.0.0';

const app = express();
app.set('trust proxy', 1); // Trust first proxy (Cloudflare, ngrok, caddy, nginx)

// Configure CORS for Express: origin: true dynamically reflects origin to satisfy credentials
app.use(cors({
  origin: true,
  methods: ['GET', 'POST', 'OPTIONS'],
  credentials: true
}));

app.use(express.json());

const server = http.createServer(app);

// Configure Socket.io with robust reverse proxy & tunnel compatibility
const io = new Server(server, {
  cors: {
    origin: (origin, callback) => callback(null, true),
    methods: ['GET', 'POST'],
    credentials: true
  },
  transports: ['websocket', 'polling'],
  allowUpgrades: true,
  pingTimeout: 30000,
  pingInterval: 25000,
  maxHttpBufferSize: 1e6, // 1MB
  connectTimeout: 45000
});

const roomManager = new RoomManager(io);

// Helper to get local network IP addresses, prioritizing real Wi-Fi/Ethernet adapters
function getNetworkAddresses() {
  const interfaces = os.networkInterfaces();
  const physical = [];
  const virtual = [];

  for (const name of Object.keys(interfaces)) {
    const isVirtual = /vethernet|hyper-v|virtual|vbox|vmware|docker|wsl/i.test(name);
    for (const iface of interfaces[name]) {
      if (iface.family === 'IPv4' && !iface.internal) {
        if (isVirtual) {
          virtual.push(iface.address);
        } else {
          physical.push(iface.address);
        }
      }
    }
  }
  return [...physical, ...virtual];
}

// API endpoint for client to discover network address for sharing / QR code
app.get('/api/network', (req, res) => {
  const ips = getNetworkAddresses();
  const hostHeader = req.headers.host;
  const protocol = req.headers['x-forwarded-proto'] || req.protocol;

  res.json({
    port: PORT,
    localIps: ips,
    currentHost: `${protocol}://${hostHeader}`,
    suggestedLocalUrl: ips.length > 0 ? `http://${ips[0]}:${PORT}` : `http://localhost:${PORT}`,
    roomCount: roomManager.getRoomCount(),
    categories: CATEGORIES
  });
});

// Health check endpoint
app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', time: new Date().toISOString() });
});

// Socket.io event handling
io.on('connection', (socket) => {
  // 1. Create Room
  socket.on('CREATE_ROOM', (data, callback) => {
    try {
      const result = roomManager.createRoom(socket, data || {});
      if (typeof callback === 'function') callback(result);
    } catch (err) {
      console.error('Error in CREATE_ROOM:', err);
      if (typeof callback === 'function') callback({ success: false, error: 'SERVER_ERROR' });
    }
  });

  // 2. Join Room
  socket.on('JOIN_ROOM', (data, callback) => {
    try {
      const result = roomManager.joinRoom(socket, data || {});
      if (typeof callback === 'function') callback(result);
    } catch (err) {
      console.error('Error in JOIN_ROOM:', err);
      if (typeof callback === 'function') callback({ success: false, error: 'SERVER_ERROR' });
    }
  });

  // 3. Update Settings (Host only)
  socket.on('UPDATE_SETTINGS', (data, callback) => {
    try {
      const result = roomManager.updateSettings(socket, data?.settings || {});
      if (typeof callback === 'function') callback(result);
    } catch (err) {
      console.error('Error in UPDATE_SETTINGS:', err);
      if (typeof callback === 'function') callback({ success: false, error: 'SERVER_ERROR' });
    }
  });

  // 4. Kick Player (Host only)
  socket.on('KICK_PLAYER', (data, callback) => {
    try {
      const result = roomManager.kickPlayer(socket, data?.targetPlayerId);
      if (typeof callback === 'function') callback(result);
    } catch (err) {
      console.error('Error in KICK_PLAYER:', err);
      if (typeof callback === 'function') callback({ success: false, error: 'SERVER_ERROR' });
    }
  });

  // 5. Start Game (Host only)
  socket.on('START_GAME', (data, callback) => {
    try {
      const result = roomManager.startGame(socket);
      if (typeof callback === 'function') callback(result);
    } catch (err) {
      console.error('Error in START_GAME:', err);
      if (typeof callback === 'function') callback({ success: false, error: 'SERVER_ERROR' });
    }
  });

  // 6. Update Draft (real-time typing sync & progress broadcast)
  socket.on('UPDATE_DRAFT', (data) => {
    try {
      roomManager.updatePlayerDraft(socket, data?.draft);
    } catch (err) {
      console.error('Error in UPDATE_DRAFT:', err);
    }
  });

  // 7. Trigger STOP (Player finished or hit STOP button)
  socket.on('TRIGGER_STOP', (data, callback) => {
    try {
      const result = roomManager.triggerStop(socket);
      if (typeof callback === 'function') callback(result);
    } catch (err) {
      console.error('Error in TRIGGER_STOP:', err);
      if (typeof callback === 'function') callback({ success: false, error: 'SERVER_ERROR' });
    }
  });

  // 8. Submit Final Answers
  socket.on('SUBMIT_ANSWERS', (data) => {
    try {
      roomManager.submitPlayerAnswers(socket, data?.answers);
    } catch (err) {
      console.error('Error in SUBMIT_ANSWERS:', err);
    }
  });

  // 9. Cast Vote on Contested Word
  socket.on('CAST_VOTE', (data, callback) => {
    try {
      const result = roomManager.castVote(socket, data || {});
      if (typeof callback === 'function') callback(result);
    } catch (err) {
      console.error('Error in CAST_VOTE:', err);
      if (typeof callback === 'function') callback({ success: false, error: 'SERVER_ERROR' });
    }
  });

  // 10. Change Review Category
  socket.on('CHANGE_REVIEW_CATEGORY', (data) => {
    try {
      roomManager.changeReviewCategory(socket, data?.categoryIndex);
    } catch (err) {
      console.error('Error in CHANGE_REVIEW_CATEGORY:', err);
    }
  });

  // 11. Finish Review (Commit scores & show leaderboard)
  socket.on('FINISH_REVIEW', (data, callback) => {
    try {
      const result = roomManager.finishReview(socket);
      if (typeof callback === 'function') callback(result);
    } catch (err) {
      console.error('Error in FINISH_REVIEW:', err);
      if (typeof callback === 'function') callback({ success: false, error: 'SERVER_ERROR' });
    }
  });

  // 12. Next Round
  socket.on('NEXT_ROUND', (data, callback) => {
    try {
      const result = roomManager.nextRound(socket);
      if (typeof callback === 'function') callback(result);
    } catch (err) {
      console.error('Error in NEXT_ROUND:', err);
      if (typeof callback === 'function') callback({ success: false, error: 'SERVER_ERROR' });
    }
  });

  // 13. Restart Game
  socket.on('RESTART_GAME', (data, callback) => {
    try {
      const result = roomManager.restartGame(socket);
      if (typeof callback === 'function') callback(result);
    } catch (err) {
      console.error('Error in RESTART_GAME:', err);
      if (typeof callback === 'function') callback({ success: false, error: 'SERVER_ERROR' });
    }
  });

  // Leave Room handler
  socket.on('LEAVE_ROOM', () => {
    try {
      roomManager.handleDisconnect(socket);
    } catch (err) {
      console.error('Error in LEAVE_ROOM:', err);
    }
  });

  // Disconnect handler
  socket.on('disconnect', () => {
    try {
      roomManager.handleDisconnect(socket);
    } catch (err) {
      console.error('Error in disconnect:', err);
    }
  });
});

// Serve frontend build in production
const distPath = path.join(__dirname, 'dist');
app.use(express.static(distPath));

// Fallback to index.html for SPA routing
app.get('*', (req, res) => {
  res.sendFile(path.join(distPath, 'index.html'));
});

// Start HTTP + WebSocket Server (only when executed directly, not during test imports)
if (process.env.NODE_ENV !== 'test') {
  server.listen(PORT, HOST, () => {
    const ips = getNetworkAddresses();
    console.log('\n======================================================');
    console.log('🚌 Categories Game (أتوبيس كومبلي) Server Running!');
    console.log('======================================================');
    console.log(`📡 Bound:        http://${HOST}:${PORT}`);
    console.log(`💻 Local:        http://localhost:${PORT}`);
    if (ips.length > 0) {
      ips.forEach(ip => {
        console.log(`📱 Wi-Fi / LAN:  http://${ip}:${PORT}`);
      });
    }
    console.log('------------------------------------------------------');
    console.log('🌐 For Reverse Proxies (Cloudflare Tunnel / ngrok):');
    console.log('   - cloudflared tunnel --url http://localhost:3000');
    console.log('   - ngrok http 3000');
    console.log('======================================================\n');
  });
}

export { app, server, io, roomManager, getNetworkAddresses, PORT, HOST };
