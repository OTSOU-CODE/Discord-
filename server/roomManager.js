import crypto from 'crypto';
import { getLetterPool, doesWordStartWithLetter, normalizeAnswer } from './alphabet.js';
import { CATEGORIES } from './categories.js';
import { calculateRoundScores } from './scoring.js';

class RoomManager {
  constructor(io) {
    this.io = io;
    this.rooms = new Map(); // roomCode -> roomState
    this.socketToPlayer = new Map(); // socketId -> { roomCode, playerId }
    this.timers = new Map(); // roomCode -> timeoutId / intervalId
  }

  generateRoomCode() {
    const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'; // exclude confusing chars (0, O, 1, I)
    let code = '';
    for (let i = 0; i < 5; i++) {
      code += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    return this.rooms.has(code) ? this.generateRoomCode() : code;
  }

  generatePlayerToken() {
    return crypto.randomBytes(16).toString('hex');
  }

  createRoom(socket, { playerName, settings }) {
    const roomCode = this.generateRoomCode();
    const playerId = 'p_' + crypto.randomBytes(4).toString('hex');
    const playerToken = this.generatePlayerToken();

    const initialSettings = {
      lang: settings?.lang || 'ar',
      roundDuration: Number(settings?.roundDuration) || 60,
      totalRounds: Number(settings?.totalRounds) || 5,
      includeRare: Boolean(settings?.includeRare)
    };

    const room = {
      code: roomCode,
      hostId: playerId,
      settings: initialSettings,
      status: 'LOBBY', // LOBBY, ROLLING, PLAYING, REVIEW, LEADERBOARD, GAME_OVER
      currentRound: 0,
      currentLetter: null,
      usedLetters: [],
      rollingStartTime: null,
      roundStartTime: null,
      roundEndTime: null,
      stopTriggeredBy: null,
      players: {
        [playerId]: {
          id: playerId,
          name: (playerName || 'Host').trim().slice(0, 20),
          isHost: true,
          connected: true,
          socketId: socket.id,
          token: playerToken,
          score: 0,
          roundScores: [],
          draft: {},
          progress: 0,
          submitted: false
        }
      },
      answers: {}, // { [roundNumber]: { [playerId]: { [catId]: string } } }
      review: {
        categoryIndex: 0,
        votes: {}, // `${catId}:${targetPlayerId}` -> { [voterId]: boolean }
        results: null
      }
    };

    this.rooms.set(roomCode, room);
    this.socketToPlayer.set(socket.id, { roomCode, playerId });
    socket.join(roomCode);

    return {
      success: true,
      roomCode,
      playerId,
      playerToken,
      room: this.sanitizeRoomForClient(room)
    };
  }

  joinRoom(socket, { roomCode, playerName, playerToken }) {
    const code = (roomCode || '').toUpperCase().trim();
    const room = this.rooms.get(code);

    if (!room) {
      return { success: false, error: 'ROOM_NOT_FOUND' };
    }

    // Check reconnection with existing token
    if (playerToken) {
      const existingPlayer = Object.values(room.players).find(p => p.token === playerToken);
      if (existingPlayer) {
        existingPlayer.socketId = socket.id;
        existingPlayer.connected = true;
        this.socketToPlayer.set(socket.id, { roomCode: code, playerId: existingPlayer.id });
        socket.join(code);

        this.broadcastRoomUpdate(code);
        return {
          success: true,
          roomCode: code,
          playerId: existingPlayer.id,
          playerToken: existingPlayer.token,
          myDraft: existingPlayer.draft || {},
          room: this.sanitizeRoomForClient(room)
        };
      }
    }

    // Block new players if game is already playing or review
    if (room.status !== 'LOBBY' && room.status !== 'GAME_OVER') {
      return { success: false, error: 'GAME_ALREADY_IN_PROGRESS' };
    }

    // Max players limit per room
    if (Object.keys(room.players).length >= 16) {
      return { success: false, error: 'ROOM_FULL' };
    }

    const playerId = 'p_' + crypto.randomBytes(4).toString('hex');
    const newToken = this.generatePlayerToken();

    room.players[playerId] = {
      id: playerId,
      name: (playerName || `Player ${Object.keys(room.players).length + 1}`).trim().slice(0, 20),
      isHost: false,
      connected: true,
      socketId: socket.id,
      token: newToken,
      score: 0,
      roundScores: [],
      draft: {},
      progress: 0,
      submitted: false
    };

    this.socketToPlayer.set(socket.id, { roomCode: code, playerId });
    socket.join(code);

    this.broadcastRoomUpdate(code);

    return {
      success: true,
      roomCode: code,
      playerId,
      playerToken: newToken,
      room: this.sanitizeRoomForClient(room)
    };
  }

  updateSettings(socket, newSettings) {
    const mapping = this.socketToPlayer.get(socket.id);
    if (!mapping) return { success: false, error: 'NOT_IN_ROOM' };

    const room = this.rooms.get(mapping.roomCode);
    if (!room) return { success: false, error: 'ROOM_NOT_FOUND' };
    if (room.hostId !== mapping.playerId) return { success: false, error: 'NOT_HOST' };
    if (room.status !== 'LOBBY') return { success: false, error: 'GAME_ALREADY_STARTED' };

    if (newSettings.lang && ['ar', 'en', 'fr'].includes(newSettings.lang)) {
      room.settings.lang = newSettings.lang;
    }
    if (newSettings.roundDuration && [30, 45, 60, 90, 120].includes(Number(newSettings.roundDuration))) {
      room.settings.roundDuration = Number(newSettings.roundDuration);
    }
    if (newSettings.totalRounds && [3, 5, 7, 10].includes(Number(newSettings.totalRounds))) {
      room.settings.totalRounds = Number(newSettings.totalRounds);
    }
    if (typeof newSettings.includeRare === 'boolean') {
      room.settings.includeRare = newSettings.includeRare;
    }

    this.broadcastRoomUpdate(room.code);
    return { success: true, settings: room.settings };
  }

  kickPlayer(socket, targetPlayerId) {
    const mapping = this.socketToPlayer.get(socket.id);
    if (!mapping) return { success: false, error: 'NOT_IN_ROOM' };

    const room = this.rooms.get(mapping.roomCode);
    if (!room || room.hostId !== mapping.playerId) return { success: false, error: 'NOT_HOST' };
    if (targetPlayerId === room.hostId) return { success: false, error: 'CANNOT_KICK_HOST' };

    const targetPlayer = room.players[targetPlayerId];
    if (targetPlayer) {
      if (targetPlayer.socketId) {
        const targetSocket = this.io.sockets.sockets.get(targetPlayer.socketId);
        if (targetSocket) {
          targetSocket.leave(room.code);
          targetSocket.emit('KICKED', { reason: 'Kicked by room host' });
        }
        this.socketToPlayer.delete(targetPlayer.socketId);
      }
      delete room.players[targetPlayerId];
      this.broadcastRoomUpdate(room.code);
    }

    return { success: true };
  }

  startGame(socket) {
    const mapping = this.socketToPlayer.get(socket.id);
    if (!mapping) return { success: false, error: 'NOT_IN_ROOM' };

    const room = this.rooms.get(mapping.roomCode);
    if (!room || room.hostId !== mapping.playerId) return { success: false, error: 'NOT_HOST' };
    if (room.status !== 'LOBBY' && room.status !== 'GAME_OVER') {
      return { success: false, error: 'INVALID_STATE' };
    }

    // Reset game counters if coming from GAME_OVER or starting fresh
    if (room.status === 'GAME_OVER') {
      room.currentRound = 0;
      room.usedLetters = [];
      Object.values(room.players).forEach(p => {
        p.score = 0;
        p.roundScores = [];
      });
    }

    this.startRoundRolling(room);
    return { success: true };
  }

  startRoundRolling(room) {
    room.currentRound += 1;
    room.status = 'ROLLING';
    room.stopTriggeredBy = null;

    // Reset player round drafts
    Object.values(room.players).forEach(p => {
      p.draft = {};
      p.progress = 0;
      p.submitted = false;
    });

    // Select random letter from pool
    const pool = getLetterPool(room.settings.lang, room.settings.includeRare);
    const availableLetters = pool.filter(l => !room.usedLetters.includes(l));
    const chosenLettersPool = availableLetters.length > 0 ? availableLetters : pool;
    const letter = chosenLettersPool[Math.floor(Math.random() * chosenLettersPool.length)];

    room.currentLetter = letter;
    room.usedLetters.push(letter);
    room.rollingStartTime = Date.now();

    const rollDurationMs = 3000;
    this.io.to(room.code).emit('ROUND_ROLLING', {
      letter,
      rollDurationMs,
      roundNumber: room.currentRound,
      totalRounds: room.settings.totalRounds,
      pool
    });

    this.clearRoomTimer(room.code);

    // After 3 seconds rolling animation, start active play phase
    const timer = setTimeout(() => {
      this.startActivePlay(room.code);
    }, rollDurationMs);

    this.timers.set(room.code, timer);
  }

  startActivePlay(roomCode) {
    const room = this.rooms.get(roomCode);
    if (!room) return;

    room.status = 'PLAYING';
    room.roundStartTime = Date.now();
    room.roundEndTime = Date.now() + room.settings.roundDuration * 1000;

    this.io.to(room.code).emit('ROUND_STARTED', {
      letter: room.currentLetter,
      roundNumber: room.currentRound,
      totalRounds: room.settings.totalRounds,
      roundEndTime: room.roundEndTime,
      duration: room.settings.roundDuration
    });

    this.clearRoomTimer(room.code);

    // Set authoritative server timer for round expiration
    const timer = setTimeout(() => {
      this.handleRoundEnd(room.code, null, 'TIMER_EXPIRED');
    }, room.settings.roundDuration * 1000);

    this.timers.set(room.code, timer);
  }

  updatePlayerDraft(socket, draft) {
    const mapping = this.socketToPlayer.get(socket.id);
    if (!mapping) return;

    const room = this.rooms.get(mapping.roomCode);
    if (!room || room.status !== 'PLAYING') return;

    const player = room.players[mapping.playerId];
    if (!player) return;

    player.draft = draft || {};
    // Calculate progress: count non-empty trimmed fields
    const filledCount = CATEGORIES.filter(c => (player.draft[c.id] || '').trim().length > 0).length;
    player.progress = filledCount;

    // Broadcast real-time progress update to room
    this.io.to(room.code).emit('PLAYER_PROGRESS', {
      playerId: player.id,
      progress: filledCount
    });
  }

  triggerStop(socket) {
    const mapping = this.socketToPlayer.get(socket.id);
    if (!mapping) return { success: false, error: 'NOT_IN_ROOM' };

    const room = this.rooms.get(mapping.roomCode);
    if (!room || room.status !== 'PLAYING') return { success: false, error: 'NOT_IN_PLAY' };

    const player = room.players[mapping.playerId];
    if (!player) return { success: false, error: 'PLAYER_NOT_FOUND' };

    this.handleRoundEnd(room.code, player, 'STOP_BUTTON');
    return { success: true };
  }

  handleRoundEnd(roomCode, triggeringPlayer, reason) {
    const room = this.rooms.get(roomCode);
    if (!room || room.status !== 'PLAYING') return;

    this.clearRoomTimer(roomCode);

    room.status = 'REVIEW';
    room.stopTriggeredBy = triggeringPlayer ? { id: triggeringPlayer.id, name: triggeringPlayer.name } : null;

    // Broadcast instant freeze event to all players
    this.io.to(room.code).emit('ROUND_STOPPED', {
      reason,
      stoppedBy: room.stopTriggeredBy
    });

    // Save answers for this round
    if (!room.answers[room.currentRound]) {
      room.answers[room.currentRound] = {};
    }

    Object.values(room.players).forEach(p => {
      room.answers[room.currentRound][p.id] = { ...p.draft };
    });

    // Initialize review stage
    room.review = {
      categoryIndex: 0,
      votes: {}, // `${catId}:${playerId}` -> { [voterId]: boolean }
      results: null
    };

    // Calculate initial preview scores
    this.recomputeReviewScores(room);

    // Broadcast transition to review
    this.io.to(room.code).emit('REVIEW_PHASE_STARTED', {
      roundNumber: room.currentRound,
      letter: room.currentLetter,
      answers: room.answers[room.currentRound],
      categoryIndex: 0,
      review: room.review,
      stoppedBy: room.stopTriggeredBy
    });
  }

  submitPlayerAnswers(socket, answers) {
    const mapping = this.socketToPlayer.get(socket.id);
    if (!mapping) return;

    const room = this.rooms.get(mapping.roomCode);
    if (!room) return;

    const player = room.players[mapping.playerId];
    if (!player) return;

    // Update with final answers if draft was updated
    if (answers && typeof answers === 'object') {
      player.draft = { ...player.draft, ...answers };
      if (!room.answers[room.currentRound]) {
        room.answers[room.currentRound] = {};
      }
      room.answers[room.currentRound][player.id] = { ...player.draft };
      this.recomputeReviewScores(room);
      // Broadcast updated answers to review room
      this.io.to(room.code).emit('REVIEW_PHASE_STARTED', {
        roundNumber: room.currentRound,
        letter: room.currentLetter,
        answers: room.answers[room.currentRound],
        categoryIndex: room.review.categoryIndex || 0,
        review: room.review,
        stoppedBy: room.stopTriggeredBy
      });
    }
  }

  castVote(socket, { categoryId, targetPlayerId, vote }) {
    const mapping = this.socketToPlayer.get(socket.id);
    if (!mapping) return { success: false, error: 'NOT_IN_ROOM' };

    const room = this.rooms.get(mapping.roomCode);
    if (!room || room.status !== 'REVIEW') return { success: false, error: 'NOT_IN_REVIEW' };

    const voterId = mapping.playerId;
    // Disallow voting for oneself
    if (voterId === targetPlayerId) {
      return { success: false, error: 'CANNOT_VOTE_FOR_SELF' };
    }

    const voteKey = `${categoryId}:${targetPlayerId}`;

    if (!room.review.votes[voteKey]) {
      room.review.votes[voteKey] = {};
    }

    // Toggle vote if clicked same vote again
    if (room.review.votes[voteKey][voterId] === vote) {
      delete room.review.votes[voteKey][voterId];
    } else {
      room.review.votes[voteKey][voterId] = Boolean(vote);
    }

    // Recalculate results based on updated votes
    this.recomputeReviewScores(room);

    this.io.to(room.code).emit('VOTE_UPDATED', {
      categoryId,
      targetPlayerId,
      votes: room.review.votes[voteKey],
      review: room.review
    });

    return { success: true };
  }

  changeReviewCategory(socket, categoryIndex) {
    const mapping = this.socketToPlayer.get(socket.id);
    if (!mapping) return;

    const room = this.rooms.get(mapping.roomCode);
    if (!room || room.status !== 'REVIEW') return;

    const idx = Math.max(0, Math.min(CATEGORIES.length - 1, Number(categoryIndex) || 0));
    room.review.categoryIndex = idx;

    this.io.to(room.code).emit('REVIEW_CATEGORY_CHANGED', { categoryIndex: idx });
  }

  recomputeReviewScores(room) {
    const activePlayerIds = Object.keys(room.players);
    const roundAnswers = room.answers[room.currentRound] || {};

    const { categoryResults, playerRoundPoints } = calculateRoundScores({
      letter: room.currentLetter,
      lang: room.settings.lang,
      playerIds: activePlayerIds,
      answers: roundAnswers,
      votes: room.review.votes
    });

    room.review.results = {
      categoryResults,
      playerRoundPoints
    };
  }

  finishReview(socket) {
    const mapping = this.socketToPlayer.get(socket.id);
    if (!mapping) return { success: false, error: 'NOT_IN_ROOM' };

    const room = this.rooms.get(mapping.roomCode);
    if (!room || room.hostId !== mapping.playerId) return { success: false, error: 'NOT_HOST' };
    if (room.status !== 'REVIEW') return { success: false, error: 'NOT_IN_REVIEW' };

    // Final calculation and score commitment
    this.recomputeReviewScores(room);
    const results = room.review.results;

    // Update cumulative scores
    Object.entries(results.playerRoundPoints).forEach(([pId, pts]) => {
      const player = room.players[pId];
      if (player) {
        player.score += pts;
        player.roundScores.push({
          round: room.currentRound,
          letter: room.currentLetter,
          points: pts
        });
      }
    });

    const isLastRound = room.currentRound >= room.settings.totalRounds;
    room.status = isLastRound ? 'GAME_OVER' : 'LEADERBOARD';

    // Generate ranked leaderboard
    const leaderboard = Object.values(room.players)
      .map(p => ({
        id: p.id,
        name: p.name,
        score: p.score,
        roundPoints: results.playerRoundPoints[p.id] || 0,
        isHost: p.isHost
      }))
      .sort((a, b) => b.score - a.score);

    this.io.to(room.code).emit('ROUND_SCORES', {
      roundNumber: room.currentRound,
      letter: room.currentLetter,
      results,
      leaderboard,
      isLastRound,
      roomStatus: room.status
    });

    return { success: true };
  }

  nextRound(socket) {
    const mapping = this.socketToPlayer.get(socket.id);
    if (!mapping) return { success: false, error: 'NOT_IN_ROOM' };

    const room = this.rooms.get(mapping.roomCode);
    if (!room || room.hostId !== mapping.playerId) return { success: false, error: 'NOT_HOST' };
    if (room.status !== 'LEADERBOARD') return { success: false, error: 'NOT_IN_LEADERBOARD' };

    if (room.currentRound >= room.settings.totalRounds) {
      room.status = 'GAME_OVER';
      this.broadcastRoomUpdate(room.code);
      return { success: true };
    }

    this.startRoundRolling(room);
    return { success: true };
  }

  restartGame(socket) {
    const mapping = this.socketToPlayer.get(socket.id);
    if (!mapping) return { success: false, error: 'NOT_IN_ROOM' };

    const room = this.rooms.get(mapping.roomCode);
    if (!room || room.hostId !== mapping.playerId) return { success: false, error: 'NOT_HOST' };

    room.status = 'LOBBY';
    room.currentRound = 0;
    room.currentLetter = null;
    room.usedLetters = [];
    room.answers = {};
    room.stopTriggeredBy = null;

    Object.values(room.players).forEach(p => {
      p.score = 0;
      p.roundScores = [];
      p.draft = {};
      p.progress = 0;
      p.submitted = false;
    });

    this.broadcastRoomUpdate(room.code);
    return { success: true };
  }

  handleDisconnect(socket) {
    const mapping = this.socketToPlayer.get(socket.id);
    if (!mapping) return;

    const { roomCode, playerId } = mapping;
    this.socketToPlayer.delete(socket.id);

    const room = this.rooms.get(roomCode);
    if (!room) return;

    const player = room.players[playerId];
    if (player) {
      player.connected = false;
      player.socketId = null;

      // In LOBBY, if host leaves, assign next player as host or clean up room
      if (room.status === 'LOBBY') {
        if (player.isHost) {
          const remainingPlayerIds = Object.keys(room.players).filter(id => id !== playerId);
          if (remainingPlayerIds.length > 0) {
            const nextHostId = remainingPlayerIds[0];
            room.hostId = nextHostId;
            room.players[nextHostId].isHost = true;
            delete room.players[playerId];
          } else {
            // Destroy empty room
            this.clearRoomTimer(roomCode);
            this.rooms.delete(roomCode);
            return;
          }
        } else {
          delete room.players[playerId];
        }
      } else {
        // Active game phases: if host disconnects, promote next connected player to host
        // so review or next round transitions are never deadlocked
        if (player.isHost) {
          const connectedPlayers = Object.values(room.players).filter(p => p.id !== playerId && p.connected);
          if (connectedPlayers.length > 0) {
            const nextHost = connectedPlayers[0];
            room.hostId = nextHost.id;
            nextHost.isHost = true;
            player.isHost = false;
          }
        }

        // Clean up empty room if all players are disconnected
        const allDisconnected = Object.values(room.players).every(p => !p.connected);
        if (allDisconnected) {
          this.clearRoomTimer(roomCode);
          this.rooms.delete(roomCode);
          return;
        }
      }

      this.broadcastRoomUpdate(roomCode);
    }
  }

  clearRoomTimer(roomCode) {
    if (this.timers.has(roomCode)) {
      clearTimeout(this.timers.get(roomCode));
      this.timers.delete(roomCode);
    }
  }

  broadcastRoomUpdate(roomCode) {
    const room = this.rooms.get(roomCode);
    if (room) {
      this.io.to(roomCode).emit('ROOM_UPDATED', {
        room: this.sanitizeRoomForClient(room)
      });
    }
  }

  sanitizeRoomForClient(room) {
    // Exclude private tokens from general broadcast
    const sanitizedPlayers = {};
    Object.entries(room.players).forEach(([id, p]) => {
      sanitizedPlayers[id] = {
        id: p.id,
        name: p.name,
        isHost: p.isHost,
        connected: p.connected,
        score: p.score,
        progress: p.progress,
        submitted: p.submitted
      };
    });

    return {
      code: room.code,
      hostId: room.hostId,
      settings: room.settings,
      status: room.status,
      currentRound: room.currentRound,
      currentLetter: room.currentLetter,
      usedLetters: room.usedLetters,
      roundStartTime: room.roundStartTime,
      roundEndTime: room.roundEndTime,
      stopTriggeredBy: room.stopTriggeredBy,
      players: sanitizedPlayers,
      review: room.review,
      answers: room.answers[room.currentRound] || null
    };
  }

  getRoomCount() {
    return this.rooms.size;
  }
}

export default RoomManager;
