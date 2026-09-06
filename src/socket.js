import { io } from 'socket.io-client';

export const SERVER_STORAGE_KEY = 'categories_server_url';

export const SESSION_KEYS = {
  ROOM_CODE: 'categories_room_code',
  PLAYER_ID: 'categories_player_id',
  PLAYER_TOKEN: 'categories_player_token',
  PLAYER_NAME: 'categories_player_name'
};

/**
 * Normalizes user-provided or URL server strings
 * Handles missing http(s):// protocols and trailing slashes
 */
export function normalizeServerUrl(rawUrl) {
  if (!rawUrl || typeof rawUrl !== 'string') return '';
  let url = rawUrl.trim();
  if (!url) return '';

  try {
    const hasProtocol = /^https?:\/\//i.test(url);
    const parsed = new URL(hasProtocol ? url : `http://${url}`);
    const isLocal = /^(localhost|127\.0\.0\.1|192\.168\.|10\.|172\.(1[6-9]|2[0-9]|3[0-1]))/i.test(parsed.hostname);
    const protocol = hasProtocol ? parsed.protocol : (isLocal ? 'http:' : 'https:');

    // Auto-upgrade remote HTTP to HTTPS on HTTPS origin to avoid mixed content block
    const finalProtocol = (typeof window !== 'undefined' && window.location.protocol === 'https:' && !isLocal)
      ? 'https:'
      : protocol;

    let cleanPath = parsed.pathname.replace(/\/+$/, '');
    return `${finalProtocol}//${parsed.host}${cleanPath}`;
  } catch (e) {
    let clean = url.replace(/\/+$/, '');
    if (!/^https?:\/\//i.test(clean)) {
      const isLocal = /^(localhost|127\.0\.0\.1|192\.168\.|10\.|172\.(1[6-9]|2[0-9]|3[0-1]))/i.test(clean);
      clean = isLocal ? `http://${clean}` : `https://${clean}`;
    }
    return clean;
  }
}

/**
 * Checks if running on a static hosting service like GitHub Pages
 */
export function isStaticHost() {
  if (typeof window === 'undefined') return false;
  const host = window.location.hostname.toLowerCase();
  return host.endsWith('github.io') ||
         host.endsWith('vercel.app') ||
         host.endsWith('netlify.app') ||
         host.endsWith('pages.dev');
}

/**
 * Resolves the target backend server URL with clear precedence:
 * 1. URL search param: ?server=... (auto-persisted to localStorage)
 * 2. Saved localStorage custom server URL
 * 3. Build-time environment variable VITE_SERVER_URL
 * 4. Local Vite dev environment (port 5173 -> localhost:3000)
 * 5. Current window.location.origin (if self-hosted / Node server)
 * 6. Empty string if on GitHub Pages with no backend configured
 */
export function resolveServerUrl() {
  if (typeof window === 'undefined') return 'http://localhost:3000';

  // 1. Explicit URL query parameter (?server=...)
  try {
    const params = new URLSearchParams(window.location.search);
    const serverParam = params.get('server');
    if (serverParam) {
      const normalized = normalizeServerUrl(serverParam);
      if (normalized) {
        localStorage.setItem(SERVER_STORAGE_KEY, normalized);
        return normalized;
      }
    }
  } catch (e) {
    // Ignore URL parse error
  }

  // 2. If running directly on a non-static host (e.g. GitHub Codespaces *.app.github.dev or local Express)
  // The server IS our origin! Stale localStorage from other domains must not override current live host.
  if (!isStaticHost()) {
    if (typeof import.meta !== 'undefined' && import.meta.env?.DEV && window?.location?.port === '5173') {
      return `http://${window.location.hostname}:3000`;
    }
    return window.location.origin;
  }

  // 3. Saved user setting in localStorage (for GitHub Pages clients connecting to Codespaces)
  try {
    const saved = localStorage.getItem(SERVER_STORAGE_KEY);
    if (saved) {
      const normalized = normalizeServerUrl(saved);
      if (normalized) return normalized;
    }
  } catch (e) {
    // Ignore localStorage error
  }

  // 4. Build-time variable
  if (typeof import.meta !== 'undefined' && import.meta.env?.VITE_SERVER_URL) {
    const normalized = normalizeServerUrl(import.meta.env.VITE_SERVER_URL);
    if (normalized) return normalized;
  }

  // 5. On static host without explicit server
  return '';
}

export const ACTIVE_SERVER_URL = resolveServerUrl();

// Effective socket target (fallback to origin if unconfigured, autoConnect will be controlled)
const effectiveSocketUrl = ACTIVE_SERVER_URL || (typeof window !== 'undefined' ? window.location.origin : '');
const isBrowser = typeof window !== 'undefined';
const shouldAutoConnect = isBrowser && Boolean(ACTIVE_SERVER_URL || !isStaticHost());

export const socket = io(effectiveSocketUrl, {
  transports: ['websocket', 'polling'],
  autoConnect: shouldAutoConnect,
  reconnection: true,
  reconnectionAttempts: 10,
  reconnectionDelay: 1000,
  timeout: 20000
});

export function getServerUrl() {
  if (typeof window !== 'undefined') {
    return resolveServerUrl();
  }
  return ACTIVE_SERVER_URL || 'http://localhost:3000';
}

export function hasConfiguredServer() {
  return Boolean(getServerUrl());
}

/**
 * Builds a universal invite URL for friends to join the room.
 * Embeds ?join=CODE and &server=... whenever running on GitHub Pages or remote backend.
 */
export function getInviteUrl(roomCode) {
  if (typeof window === 'undefined') return '';
  try {
    const url = new URL(window.location.origin + window.location.pathname);
    if (roomCode) {
      url.searchParams.set('join', roomCode);
    }
    const srv = getServerUrl();
    if (srv && srv !== window.location.origin) {
      url.searchParams.set('server', srv);
    }
    return url.toString();
  } catch (e) {
    return roomCode ? `${window.location.origin}${window.location.pathname}?join=${roomCode}` : window.location.href;
  }
}

export function getApiUrl(path) {
  const base = getServerUrl();
  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  return `${base}${cleanPath}`;
}

/**
 * Checks if running directly inside a GitHub Codespace
 */
export function isCodespaceHost() {
  if (typeof window === 'undefined') return false;
  const host = window.location.hostname.toLowerCase();
  return host.includes('.app.github.dev') || host.includes('.github.dev');
}

export async function testServerHealth(url) {
  const normalized = normalizeServerUrl(url);
  if (!normalized) {
    return { ok: false, error: 'Please enter a valid server URL' };
  }

  // Detect HTTPS -> HTTP mixed content block upfront
  if (typeof window !== 'undefined' && window.location.protocol === 'https:' && /^http:\/\//i.test(normalized)) {
    const isLocal = /^http:\/\/(localhost|127\.0\.0\.1)/i.test(normalized);
    if (!isLocal) {
      return { 
        ok: false, 
        error: 'Mixed Content Blocked: Since GitHub Pages is HTTPS, your backend server must also use HTTPS (e.g. your GitHub Codespaces public URL https://<name>-3000.app.github.dev).' 
      };
    }
  }

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 7000);

    const res = await fetch(`${normalized}/api/health`, {
      method: 'GET',
      headers: { 'Accept': 'application/json' },
      signal: controller.signal
    });
    clearTimeout(timeoutId);

    if (res.ok) {
      const data = await res.json();
      if (data?.status === 'ok') {
        return { ok: true, data };
      }
    }
    return { ok: false, error: `Server responded with HTTP ${res.status}` };
  } catch (err) {
    if (err.name === 'AbortError') {
      return { ok: false, error: 'Connection timed out (server took too long to respond. Check if your GitHub Codespace is active).' };
    }
    if (typeof window !== 'undefined' && window.location.protocol === 'https:' && /^http:\/\//i.test(normalized)) {
      return {
        ok: false,
        error: 'Blocked by browser (Mixed Content): HTTPS sites cannot make requests to insecure HTTP servers. Please use an HTTPS URL like your GitHub Codespaces URL.'
      };
    }
    return { ok: false, error: err.message || 'Failed to connect to server' };
  }
}

export function setServerUrl(newUrl) {
  const normalized = normalizeServerUrl(newUrl);
  if (normalized) {
    localStorage.setItem(SERVER_STORAGE_KEY, normalized);
  } else {
    localStorage.removeItem(SERVER_STORAGE_KEY);
  }

  // Update current URL search params so on reload it does not revert to old ?server= param
  try {
    const url = new URL(window.location.href);
    if (normalized) {
      url.searchParams.set('server', normalized);
    } else {
      url.searchParams.delete('server');
    }
    window.location.href = url.toString();
  } catch (e) {
    window.location.reload();
  }
}

export function resetServerUrl() {
  localStorage.removeItem(SERVER_STORAGE_KEY);
  try {
    const url = new URL(window.location.href);
    url.searchParams.delete('server');
    window.location.href = url.toString();
  } catch (e) {
    window.location.reload();
  }
}

export function saveSession({ roomCode, playerId, playerToken, playerName }) {
  if (roomCode) sessionStorage.setItem(SESSION_KEYS.ROOM_CODE, roomCode);
  if (playerId) sessionStorage.setItem(SESSION_KEYS.PLAYER_ID, playerId);
  if (playerToken) sessionStorage.setItem(SESSION_KEYS.PLAYER_TOKEN, playerToken);
  if (playerName) localStorage.setItem(SESSION_KEYS.PLAYER_NAME, playerName);
}

export function getSavedSession() {
  return {
    roomCode: sessionStorage.getItem(SESSION_KEYS.ROOM_CODE) || '',
    playerId: sessionStorage.getItem(SESSION_KEYS.PLAYER_ID) || '',
    playerToken: sessionStorage.getItem(SESSION_KEYS.PLAYER_TOKEN) || '',
    playerName: localStorage.getItem(SESSION_KEYS.PLAYER_NAME) || ''
  };
}

export function clearSession() {
  sessionStorage.removeItem(SESSION_KEYS.ROOM_CODE);
  sessionStorage.removeItem(SESSION_KEYS.PLAYER_ID);
  sessionStorage.removeItem(SESSION_KEYS.PLAYER_TOKEN);
}
