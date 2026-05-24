@echo off
setlocal

REM Przejdź do katalogu projektu (lokalizacja tego pliku .bat)
cd /d "%~dp0"

echo [TravelMate] Uruchamianie nowego GUI Tailwind (FastAPI + PWA)...

REM Preferuj interpreter z lokalnego virtualenv
if exist ".venv\Scripts\python.exe" (
    start "" http://127.0.0.1:8000
    ".venv\Scripts\python.exe" -m travelmate.api.main
) else (
    echo [TravelMate] Nie znaleziono .venv\Scripts\python.exe
    echo [TravelMate] Uruchamiam przez globalny interpreter 'python'.
    start "" http://127.0.0.1:8000
    python -m travelmate.api.main
)

endlocal
