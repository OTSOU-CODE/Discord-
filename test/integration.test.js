import test, { before, after } from 'node:test';
import assert from 'node:assert/strict';
import { io } from 'socket.io-client';

process.env.NODE_ENV = 'test';
const { server } = await import('../server.js');

let baseUrl;
let testPort;

before(async () => {
  await new Promise((resolve) => {
    server.listen(0, '127.0.0.1', () => {
      testPort = server.address().port;
      baseUrl = `http://127.0.0.1:${testPort}`;
      resolve();
    });
  });
});

after(async () => {
  await new Promise((resolve) => {
    server.close(resolve);
  });
});

test('Integration - HTTP Endpoints & Static Files', async () => {
  // Test /api/health
  const healthRes = await fetch(`${baseUrl}/api/health`);
  assert.equal(healthRes.status, 200);
  const healthData = await healthRes.json();
  assert.equal(healthData.status, 'ok');

  // Test /api/network
  const networkRes = await fetch(`${baseUrl}/api/network`);
  assert.equal(networkRes.status, 200);
  const networkData = await networkRes.json();
  assert.ok(networkData.port);
  assert.ok(Array.isArray(networkData.localIps));
  assert.equal(networkData.categories.length, 9);

  // Test static index.html served from dist
  const rootRes = await fetch(`${baseUrl}/`);
  assert.equal(rootRes.status, 200);
  const rootHtml = await rootRes.text();
  assert.ok(rootHtml.includes('<!doctype html>'));
  assert.ok(rootHtml.includes('أتوبيس كومبلي'));

  // Test CORS response for GitHub Pages origin
  const ghPagesOrigin = 'https://username.github.io';
  const corsRes = await fetch(`${baseUrl}/api/health`, {
    headers: { 'Origin': ghPagesOrigin }
  });
  assert.equal(corsRes.status, 200);
  assert.equal(corsRes.headers.get('access-control-allow-origin'), ghPagesOrigin);
  assert.equal(corsRes.headers.get('access-control-allow-credentials'), 'true');

  // Test CORS preflight (OPTIONS) for GitHub Pages origin
  const optionsRes = await fetch(`${baseUrl}/api/health`, {
    method: 'OPTIONS',
    headers: {
      'Origin': ghPagesOrigin,
      'Access-Control-Request-Method': 'GET',
      'Access-Control-Request-Headers': 'Accept'
    }
  });
  assert.ok(optionsRes.status === 204 || optionsRes.status === 200);
  assert.equal(optionsRes.headers.get('access-control-allow-origin'), ghPagesOrigin);
  assert.equal(optionsRes.headers.get('access-control-allow-credentials'), 'true');
});

test('Integration - Real-time Socket.io Flow between two clients', async () => {
  // 1. Connect Host
  const client1 = io(baseUrl, {
    transports: ['websocket'],
    forceNew: true
  });

  await new Promise((resolve) => client1.on('connect', resolve));
  assert.ok(client1.id, 'Host client connected');

  // 2. Create Room
  const createPromise = new Promise((resolve) => {
    client1.emit('CREATE_ROOM', {
      playerName: 'HostAlice',
      settings: { lang: 'en', roundDuration: 30, totalRounds: 3, includeRare: false }
    }, resolve);
  });

  const createRes = await createPromise;
  assert.equal(createRes.success, true);
  assert.equal(createRes.roomCode.length, 5);
  const roomCode = createRes.roomCode;
  const hostId = createRes.playerId;

  // 3. Connect Player 2
  const client2 = io(baseUrl, {
    transports: ['websocket'],
    forceNew: true
  });

  await new Promise((resolve) => client2.on('connect', resolve));

  // 4. Join Room
  const joinPromise = new Promise((resolve) => {
    client2.emit('JOIN_ROOM', {
      roomCode,
      playerName: 'BobPlayer'
    }, resolve);
  });

  const joinRes = await joinPromise;
  assert.equal(joinRes.success, true);
  const p2Id = joinRes.playerId;

  // 5. Host updates settings in lobby
  const updateSettingsPromise = new Promise((resolve) => {
    client1.emit('UPDATE_SETTINGS', {
      settings: { roundDuration: 45, totalRounds: 5 }
    }, resolve);
  });
  const updateSettingsRes = await updateSettingsPromise;
  assert.equal(updateSettingsRes.success, true);
  assert.equal(updateSettingsRes.settings.roundDuration, 45);

  // 6. Host Starts Game
  const rollingPromise = new Promise((resolve) => {
    client2.on('ROUND_ROLLING', resolve);
  });

  client1.emit('START_GAME');
  const rollingData = await rollingPromise;
  assert.ok(rollingData.letter);
  assert.equal(rollingData.roundNumber, 1);
  const roundLetter = rollingData.letter;

  // 7. Wait for active play transition
  const activePlayPromise = new Promise((resolve) => {
    client2.on('ROUND_STARTED', resolve);
  });
  const activePlayData = await activePlayPromise;
  assert.equal(activePlayData.letter, roundLetter);

  // 8. Player drafts update
  const progressPromise = new Promise((resolve) => {
    client1.on('PLAYER_PROGRESS', (data) => {
      if (data.playerId === p2Id && data.progress === 2) {
        resolve(data);
      }
    });
  });

  client2.emit('UPDATE_DRAFT', {
    draft: {
      boy: roundLetter + 'onny',
      animal: roundLetter + 'ear'
    }
  });

  const progressData = await progressPromise;
  assert.equal(progressData.progress, 2);

  // 9. Concurrent STOP presses test: Both clients press STOP almost at once
  const stopPromise = new Promise((resolve) => {
    client1.on('ROUND_STOPPED', resolve);
  });

  const stopCall1 = new Promise((resolve) => client2.emit('TRIGGER_STOP', {}, resolve));
  const stopCall2 = new Promise((resolve) => client1.emit('TRIGGER_STOP', {}, resolve));

  const [resStop1, resStop2] = await Promise.all([stopCall1, stopCall2]);
  const stopData = await stopPromise;
  assert.ok(stopData.stoppedBy);
  // At least one succeeded, the second handled gracefully
  assert.ok(resStop1.success || resStop2.success);

  // 10. Test Self-Voting Prevention: Alice tries to vote for her own word -> MUST FAIL
  const selfVotePromise = new Promise((resolve) => {
    client1.emit('CAST_VOTE', {
      categoryId: 'boy',
      targetPlayerId: hostId,
      vote: true
    }, resolve);
  });
  const selfVoteRes = await selfVotePromise;
  assert.equal(selfVoteRes.success, false, 'Self-voting should be rejected');
  assert.equal(selfVoteRes.error, 'CANNOT_VOTE_FOR_SELF');

  // 11. Valid Peer Vote: Alice votes on Bob's animal
  const peerVotePromise = new Promise((resolve) => {
    client2.on('VOTE_UPDATED', resolve);
  });

  client1.emit('CAST_VOTE', {
    categoryId: 'animal',
    targetPlayerId: p2Id,
    vote: true
  });

  const voteData = await peerVotePromise;
  assert.equal(voteData.categoryId, 'animal');
  assert.equal(voteData.targetPlayerId, p2Id);

  // 12. Host finishes review -> leaderboard
  const scoresPromise = new Promise((resolve) => {
    client2.on('ROUND_SCORES', resolve);
  });

  client1.emit('FINISH_REVIEW');
  const scoresData = await scoresPromise;
  assert.equal(scoresData.roundNumber, 1);
  assert.ok(scoresData.leaderboard.length >= 2);

  // Clean up sockets
  client1.disconnect();
  client2.disconnect();
});
