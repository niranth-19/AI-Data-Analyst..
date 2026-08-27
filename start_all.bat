@echo off
REM Start both servers for the AI Data Analyst project
REM Requires: PostgreSQL running, backend/.env configured, node_modules installed.

echo Starting backend on http://localhost:8000 ...
start "AI-Data-Analyst-Backend" cmd /c "cd /d %~dp0backend && .venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000"

echo Starting frontend on http://localhost:5173 ...
start "AI-Data-Analyst-Frontend" cmd /c "cd /d %~dp0frontend && npm run dev -- --port 5173"

echo.
echo Open http://localhost:5173 in your browser.
timeout /t 5 >nul