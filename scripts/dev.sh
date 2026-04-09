#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"

cd "$BACKEND_DIR"

uv sync

cleanup() {
  local exit_code=$?
  trap - EXIT INT TERM
  kill "${API_PID:-}" "${CHAINLIT_PID:-}" 2>/dev/null || true
  wait "${API_PID:-}" "${CHAINLIT_PID:-}" 2>/dev/null || true
  exit "$exit_code"
}

trap cleanup EXIT INT TERM

uv run uvicorn app.main:app --app-dir src --reload --host 127.0.0.1 --port 8000 &
API_PID=$!

uv run chainlit run src/chainlit_app.py --headless --watch --host 127.0.0.1 --port 3000 &
CHAINLIT_PID=$!

echo "FastAPI:  http://127.0.0.1:8000"
echo "Chainlit: http://127.0.0.1:3000"

while true; do
  if ! kill -0 "$API_PID" 2>/dev/null; then
    wait "$API_PID"
    break
  fi

  if ! kill -0 "$CHAINLIT_PID" 2>/dev/null; then
    wait "$CHAINLIT_PID"
    break
  fi

  sleep 1
done
