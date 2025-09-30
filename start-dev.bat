@echo off
echo Starting Gemini IRD Pricer Development Servers...

echo Starting Backend (FastAPI)...
start "Backend" cmd /k "cd backend && python main.py"

echo Waiting 3 seconds for backend to start...
timeout /t 3 /nobreak >nul

echo Starting Frontend (React)...
start "Frontend" cmd /k "cd frontend && npm run dev"

echo Both servers should now be starting:
echo - Backend: http://localhost:8000
echo - Frontend: http://localhost:3000
echo - API Docs: http://localhost:8000/docs
pause
