#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

if [[ ! -f "$BACKEND_DIR/.env" ]]; then
  echo "Missing $BACKEND_DIR/.env"
  echo "Create it from backend/.env.example before starting the project."
  exit 1
fi

cleanup() {
  if [[ -n "${BACKEND_PID:-}" ]]; then
    kill "$BACKEND_PID" >/dev/null 2>&1 || true
  fi
  if [[ -n "${FRONTEND_PID:-}" ]]; then
    kill "$FRONTEND_PID" >/dev/null 2>&1 || true
  fi
}

trap cleanup EXIT INT TERM

(
  cd "$BACKEND_DIR"
  exec uv run uvicorn app.main:app --app-dir src --reload --host 0.0.0.0 --port 8000
) &
BACKEND_PID=$!

(
  cd "$FRONTEND_DIR"
  exec bun run dev
) &
FRONTEND_PID=$!

wait "$BACKEND_PID" "$FRONTEND_PID"
