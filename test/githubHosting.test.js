import test from 'node:test';
import assert from 'node:assert/strict';
import { normalizeServerUrl } from '../src/socket.js';

test('GitHub Hosting - URL Normalization Engine', () => {
  // Protocol inference for domain and port patterns
  assert.equal(normalizeServerUrl('my-game.onrender.com'), 'https://my-game.onrender.com');
  assert.equal(normalizeServerUrl('my-game.onrender.com/'), 'https://my-game.onrender.com');
  assert.equal(normalizeServerUrl('localhost:3000'), 'http://localhost:3000');
  assert.equal(normalizeServerUrl('127.0.0.1:3000/'), 'http://127.0.0.1:3000');
  assert.equal(normalizeServerUrl('192.168.1.50:3000'), 'http://192.168.1.50:3000');
  
  // Existing protocols preserved
  assert.equal(normalizeServerUrl('http://my-domain.com/'), 'http://my-domain.com');
  assert.equal(normalizeServerUrl('https://custom.trycloudflare.com'), 'https://custom.trycloudflare.com');
  assert.equal(normalizeServerUrl('  https://trailing.slash.com/// '), 'https://trailing.slash.com');

  // Query parameter and fragment stripping from backend inputs
  assert.equal(normalizeServerUrl('https://my-backend.onrender.com/?ref=test#section'), 'https://my-backend.onrender.com');
  assert.equal(normalizeServerUrl('http://localhost:3000?foo=bar'), 'http://localhost:3000');

  // Edge cases & invalid inputs
  assert.equal(normalizeServerUrl(''), '');
  assert.equal(normalizeServerUrl(null), '');
  assert.equal(normalizeServerUrl(undefined), '');
});

test('GitHub Hosting - Universal Invite URL Generation', async () => {
  const { getInviteUrl } = await import('../src/socket.js');
  
  // In Node environment without window
  assert.equal(getInviteUrl('ABCDE'), '');

  // Simulate browser environment on GitHub Pages
  global.window = {
    location: {
      origin: 'https://username.github.io',
      pathname: '/Categories/'
    }
  };

  const inviteUrl = getInviteUrl('K8M2P');
  assert.ok(inviteUrl.startsWith('https://username.github.io/Categories/?join=K8M2P'));

  // Clean up global mock
  delete global.window;
});
