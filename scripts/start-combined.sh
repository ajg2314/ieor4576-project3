#!/usr/bin/env bash
set -euo pipefail

export API_URL="${API_URL:-http://127.0.0.1:8000}"
export PORT="${PORT:-8080}"

echo "Starting StoryCoach backend on http://127.0.0.1:8000"
uv run uvicorn backend.main:app --host 127.0.0.1 --port 8000 --log-level info &
BACKEND_PID=$!

cleanup() {
  kill "$BACKEND_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "Waiting for backend health check"
for _ in $(seq 1 60); do
  if node -e "fetch('http://127.0.0.1:8000/health').then(r => process.exit(r.ok ? 0 : 1)).catch(() => process.exit(1))"; then
    echo "Backend health check passed"
    break
  fi

  if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
    echo "Backend process exited before health check passed"
    wait "$BACKEND_PID"
    exit 1
  fi

  sleep 1
done

if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
  echo "Backend process is not running"
  exit 1
fi

cd frontend
echo "Starting StoryCoach frontend on 0.0.0.0:${PORT}"
npm run start -- --hostname 0.0.0.0 --port "$PORT"
