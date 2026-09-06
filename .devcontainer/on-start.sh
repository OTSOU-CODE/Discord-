#!/usr/bin/env bash
# Move to repository root directory regardless of invocation path
cd "$(dirname "$0")/.." || exit 1

# Ensure script stops on unexpected error if needed, but allow pkill to not crash
pkill -f 'node server.js' 2>/dev/null || true

# Start the game server in the background
nohup node server.js > /tmp/categories-server.log 2>&1 &

echo "======================================================"
echo "🚌 Categories Game (أتوبيس كومبلي) Server Started!"
echo "📡 Listening on Port 3000"
if [ -n "$CODESPACE_NAME" ]; then
  DOMAIN="${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN:-app.github.dev}"
  echo "🐙 GitHub Codespaces Public URL (Zero External Services):"
  echo "   https://${CODESPACE_NAME}-3000.${DOMAIN}"
fi
echo "📄 Logs: /tmp/categories-server.log"
echo "======================================================"
