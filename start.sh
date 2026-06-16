#!/bin/bash
set -e

echo "=== Issue Aggregator Dev ==="
echo ""

cleanup() {
  echo ""
  echo "Shutting down..."
  kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
  wait $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
}

trap cleanup EXIT INT TERM

echo "[1/2] Starting backend on http://localhost:8000 ..."
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd ..

echo "[2/2] Starting frontend on http://localhost:5173 ..."
cd frontend
npm run dev -- --host 0.0.0.0 &
FRONTEND_PID=$!
cd ..

echo ""
echo "Backend:  http://localhost:8000"
echo "Frontend: http://localhost:5173"
echo "API Docs: http://localhost:8000/docs  (if ENABLE_API_DOCS=true)"
echo ""
echo "Press Ctrl+C to stop both services."
echo ""

wait
