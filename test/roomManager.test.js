import test from 'node:test';
import assert from 'node:assert/strict';
import RoomManager from '../server/roomManager.js';

// Mock Socket.io
class MockSocket {
  constructor(id) {
    this.id = id;
    this.rooms = new Set();
    this.emitted = [];
  }
  join(room) {
    this.rooms.add(room);
  }
  leave(room) {
    this.rooms.delete(room);
  }
  emit(event, data) {
    this.emitted.push({ event, data });
  }
}

class MockIo {
  constructor() {
    this.broadcasts = [];
    this.sockets = {
      sockets: new Map()
    };
  }
  to(room) {
    return {
      emit: (event, data) => {
        this.broadcasts.push({ room, event, data });
      }
    };
  }
}

test('RoomManager - Full Lifecycle Flow', () => {
  const io = new MockIo();
  const rm = new RoomManager(io);

  const socketHost = new MockSocket('sock_host');
  io.sockets.sockets.set(socketHost.id, socketHost);

  // 1. Create Room
  const createRes = rm.createRoom(socketHost, {
    playerName: 'HostUser',
    settings: { lang: 'ar', roundDuration: 30, totalRounds: 3 }
  });

  assert.equal(createRes.success, true);
  assert.equal(createRes.roomCode.length, 5);
  const roomCode = createRes.roomCode;
  const hostId = createRes.playerId;

  // 2. Join Room (Player 2)
  const socketP2 = new MockSocket('sock_p2');
  io.sockets.sockets.set(socketP2.id, socketP2);
  const joinRes = rm.joinRoom(socketP2, {
    roomCode,
    playerName: 'Player2'
  });

  assert.equal(joinRes.success, true);
  const p2Id = joinRes.playerId;

  // 3. Start Game
  const startRes = rm.startGame(socketHost);
  assert.equal(startRes.success, true);

  const room = rm.rooms.get(roomCode);
  assert.equal(room.status, 'ROLLING');
  assert.ok(room.currentLetter);

  // Set letter deterministically for test
  room.currentLetter = 'أ';

  // Advance to PLAYING manually for test
  rm.startActivePlay(roomCode);
  assert.equal(room.status, 'PLAYING');

  // 4. Update drafts
  rm.updatePlayerDraft(socketHost, {
    boy: 'أحمد',
    animal: 'أسد',
    country: 'ألمانيا'
  });
  rm.updatePlayerDraft(socketP2, {
    boy: 'أحمد',
    animal: 'أرنب',
    country: 'فرنسا'
  });

  // 5. Trigger Stop
  const stopRes = rm.triggerStop(socketHost);
  assert.equal(stopRes.success, true);
  assert.equal(room.status, 'REVIEW');

  // 6. Review & Voting
  // Host votes to reject P2's country (starts with ف when letter is أ)
  const voteRes = rm.castVote(socketHost, {
    categoryId: 'country',
    targetPlayerId: p2Id,
    vote: false
  });
  assert.equal(voteRes.success, true);

  // 7. Finish Review
  const finishRes = rm.finishReview(socketHost);
  assert.equal(finishRes.success, true);
  assert.equal(room.status, 'LEADERBOARD');

  // Verify scoring
  const hostPlayer = room.players[hostId];
  const p2Player = room.players[p2Id];
  assert.ok(hostPlayer.score > 0, 'Host scored points');
  assert.ok(p2Player.score >= 0, 'Player 2 scores calculated');
});
