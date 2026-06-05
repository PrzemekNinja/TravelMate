@echo off
echo Starting AI Cost and Cache Dashboard...
echo.

REM ── Backend ──────────────────────────────────────────────
echo Installing backend dependencies...
cd /d "%~dp0backend"

if not exist ".env" (
    copy .env.example .env
    echo Created backend\.env from .env.example
)

pip install -r requirements.txt -q

echo Starting backend on http://localhost:8001 ...
start "TravelMate Dashboard Backend" cmd /k "uvicorn main:app --host 0.0.0.0 --port 8001 --reload"

REM ── Frontend ─────────────────────────────────────────────
echo.
echo Installing frontend dependencies...
cd /d "%~dp0frontend"

call npm install --silent

echo Starting frontend on http://localhost:5173 ...
start "TravelMate Dashboard Frontend" cmd /k "npm run dev"

REM ── Done ─────────────────────────────────────────────────
echo.
echo Dashboard is running!
echo   Frontend: http://localhost:5173
echo   Backend:  http://localhost:8001
echo   API docs: http://localhost:8001/docs
echo.
echo Close the two terminal windows to stop the servers.
pause
