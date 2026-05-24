#!/bin/bash
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "🚀 Starting AI Cost & Cache Dashboard..."
echo ""

# --- Backend ---
echo "📦 Installing backend dependencies..."
cd "$ROOT/backend"

if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "✅ Created backend/.env from .env.example (DEMO_MODE=true)"
fi

pip3 install -r requirements.txt -q

echo "🔧 Starting backend on http://localhost:8001 ..."
uvicorn main:app --host 0.0.0.0 --port 8001 --reload &
BACKEND_PID=$!

# --- Frontend ---
echo ""
echo "📦 Installing frontend dependencies..."
cd "$ROOT/frontend"
npm install --silent

echo "🎨 Starting frontend on http://localhost:5173 ..."
npm run dev &
FRONTEND_PID=$!

echo ""
echo "✅ Dashboard is running!"
echo "   Frontend: http://localhost:5173"
echo "   Backend:  http://localhost:8001"
echo "   API docs: http://localhost:8001/docs"
echo ""
echo "Press Ctrl+C to stop both servers."

# Wait and clean up on exit
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo 'Stopped.'" EXIT
wait
