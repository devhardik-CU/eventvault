#!/usr/bin/env bash
# Starts the real backend on a throw-away SQLite database, seeds it, runs the frontend UI tests against it, then cleans up.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
export DATABASE_URL="sqlite:///$TMP/it.db" UPLOAD_DIR="$TMP/uploads" ENVIRONMENT=test
cd "$ROOT/backend" && source .venv/bin/activate
python -m app.seed
uvicorn app.main:app --port 8000 --log-level warning &
API_PID=$!
trap 'kill $API_PID 2>/dev/null || true; rm -rf "$TMP"' EXIT
for i in $(seq 1 30); do curl -sf http://127.0.0.1:8000/api/health >/dev/null && break; sleep 0.5; done
cd "$ROOT/frontend" && VITE_API_URL=http://127.0.0.1:8000 npm test
