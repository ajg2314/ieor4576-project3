#!/usr/bin/env bash
set -euo pipefail

export API_URL="${API_URL:-http://127.0.0.1:8000}"
export PORT="${PORT:-8080}"

uv run uvicorn backend.main:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!

cleanup() {
  kill "$BACKEND_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

cd frontend
npm run start
