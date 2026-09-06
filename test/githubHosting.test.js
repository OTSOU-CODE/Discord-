import test from 'node:test';
import assert from 'node:assert/strict';
import { normalizeServerUrl, isCodespaceHost, isStaticHost, getInviteUrl, resolveServerUrl, SERVER_STORAGE_KEY } from '../src/socket.js';
import { calculateRoundScores } from '../server/scoring.js';

test('GitHub Hosting - URL Normalization Engine', () => {
  // Protocol inference for GitHub Codespaces domains and local ports
  assert.equal(normalizeServerUrl('improved-winner-g4p9w7q75v5f6r7-3000.app.github.dev'), 'https://improved-winner-g4p9w7q75v5f6r7-3000.app.github.dev');
  assert.equal(normalizeServerUrl('improved-winner-g4p9w7q75v5f6r7-3000.app.github.dev/'), 'https://improved-winner-g4p9w7q75v5f6r7-3000.app.github.dev');
  assert.equal(normalizeServerUrl('localhost:3000'), 'http://localhost:3000');
  assert.equal(normalizeServerUrl('127.0.0.1:3000/'), 'http://127.0.0.1:3000');
  assert.equal(normalizeServerUrl('192.168.1.50:3000'), 'http://192.168.1.50:3000');
  
  // Existing protocols preserved
  assert.equal(normalizeServerUrl('https://improved-winner-3000.app.github.dev'), 'https://improved-winner-3000.app.github.dev');
  assert.equal(normalizeServerUrl('http://my-domain.com/'), 'http://my-domain.com');
  assert.equal(normalizeServerUrl('  https://trailing.slash.com/// '), 'https://trailing.slash.com');

  // Query parameter and fragment stripping from backend inputs
  assert.equal(normalizeServerUrl('https://my-codespace-3000.app.github.dev/?ref=test#section'), 'https://my-codespace-3000.app.github.dev');
  assert.equal(normalizeServerUrl('http://localhost:3000?foo=bar'), 'http://localhost:3000');

  // Edge cases & invalid inputs
  assert.equal(normalizeServerUrl(''), '');
  assert.equal(normalizeServerUrl(null), '');
  assert.equal(normalizeServerUrl(undefined), '');
});

test('GitHub Hosting - Codespaces and Static Host Identification', () => {
  // In Node environment without window
  assert.equal(isCodespaceHost(), false);
  assert.equal(isStaticHost(), false);

  // Mock GitHub Codespaces environment
  global.window = {
    location: {
      hostname: 'expert-octo-parakeet-3000.app.github.dev'
    }
  };
  assert.equal(isCodespaceHost(), true);
  assert.equal(isStaticHost(), false); // Codespaces is a full server, NOT a static host

  // Mock GitHub Pages environment
  global.window = {
    location: {
      hostname: 'username.github.io'
    }
  };
  assert.equal(isCodespaceHost(), false);
  assert.equal(isStaticHost(), true);

  delete global.window;
});

test('GitHub Hosting - resolveServerUrl Precedence and Host Protection', () => {
  const store = {};
  const mockLocalStorage = {
    getItem: (key) => store[key] || null,
    setItem: (key, val) => { store[key] = String(val); },
    removeItem: (key) => { delete store[key]; }
  };
  global.localStorage = mockLocalStorage;

  try {
    // 1. On GitHub Codespaces: window.location.origin is prioritized over stale localStorage
    mockLocalStorage.setItem(SERVER_STORAGE_KEY, 'http://stale-old-server.com');
    global.window = {
      location: {
        hostname: 'improved-winner-3000.app.github.dev',
        origin: 'https://improved-winner-3000.app.github.dev',
        pathname: '/',
        search: ''
      }
    };
    assert.equal(resolveServerUrl(), 'https://improved-winner-3000.app.github.dev', 'Codespaces origin must override stale localStorage');

    // 2. On GitHub Pages without server: returns empty string
    mockLocalStorage.removeItem(SERVER_STORAGE_KEY);
    global.window = {
      location: {
        hostname: 'username.github.io',
        origin: 'https://username.github.io',
        pathname: '/Categories/',
        search: ''
      }
    };
    assert.equal(resolveServerUrl(), '', 'GitHub Pages with no server returns empty string');

    // 3. On GitHub Pages with configured Codespace server: returns configured Codespace URL
    mockLocalStorage.setItem(SERVER_STORAGE_KEY, 'https://improved-winner-3000.app.github.dev');
    assert.equal(resolveServerUrl(), 'https://improved-winner-3000.app.github.dev');

    // 4. URL ?server= param overrides and saves to localStorage
    global.window.location.search = '?server=https://other-codespace-3000.app.github.dev';
    assert.equal(resolveServerUrl(), 'https://other-codespace-3000.app.github.dev');
    assert.equal(mockLocalStorage.getItem(SERVER_STORAGE_KEY), 'https://other-codespace-3000.app.github.dev');
  } finally {
    delete global.window;
    delete global.localStorage;
  }
});

test('GitHub Hosting - Universal Invite URL Generation', () => {
  // In Node environment without window
  assert.equal(getInviteUrl('ABCDE'), '');

  try {
    // Simulate browser environment on GitHub Pages
    global.window = {
      location: {
        origin: 'https://username.github.io',
        pathname: '/Categories/'
      }
    };
    const ghPagesInvite = getInviteUrl('K8M2P');
    assert.ok(ghPagesInvite.startsWith('https://username.github.io/Categories/?join=K8M2P'));

    // Simulate browser environment on GitHub Codespaces
    global.window = {
      location: {
        origin: 'https://expert-octo-parakeet-3000.app.github.dev',
        pathname: '/'
      }
    };
    const codespaceInvite = getInviteUrl('X9Y2Z');
    assert.equal(codespaceInvite, 'https://expert-octo-parakeet-3000.app.github.dev/?join=X9Y2Z');
  } finally {
    delete global.window;
  }
});

test('Solo Practice - Client-Side Scoring Engine & Verification', () => {
  const soloPlayerId = 'p_solo';
  const roundAnswers = {
    [soloPlayerId]: {
      boy: 'أحمد',
      girl: 'أمل',
      animal: 'الأسد',
      plant: 'أناناس',
      object: 'أريكة',
      city: 'أبها',
      country: 'ألمانيا',
      profession: 'أستاذ',
      color: 'أبيض'
    }
  };

  const results = calculateRoundScores({
    letter: 'أ',
    lang: 'ar',
    playerIds: [soloPlayerId],
    answers: roundAnswers,
    votes: {}
  });

  // Verify both playerRoundPoints and playerScores exist and are accurate
  assert.ok(results.playerRoundPoints);
  assert.ok(results.playerScores);
  assert.equal(results.playerRoundPoints[soloPlayerId], 90, '9 valid Arabic answers with letter أ = 90 pts');
  assert.equal(results.playerScores[soloPlayerId], 90);

  // Verify each category awarded 10 points
  Object.values(results.categoryResults).forEach(cat => {
    const status = cat.playerStatuses[soloPlayerId];
    assert.equal(status.isValid, true);
    assert.equal(status.points, 10);
    assert.equal(status.pointReason, 'unique');
  });

  // Verify peer vote override in solo mode (auto-check failed wrong letter overridden by player approval)
  const resultsWithVote = calculateRoundScores({
    letter: 'B',
    lang: 'en',
    playerIds: [soloPlayerId],
    answers: {
      [soloPlayerId]: {
        boy: 'Peter' // Wrong letter for B
      }
    },
    votes: {
      'boy:p_solo': { [soloPlayerId]: true } // Player explicitly approved
    }
  });
  assert.equal(resultsWithVote.categoryResults.boy.playerStatuses[soloPlayerId].isValid, true, 'Approved by vote');
  assert.equal(resultsWithVote.playerRoundPoints[soloPlayerId], 10);
});
