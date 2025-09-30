@echo off
echo Starting Gemini IRD Pricer...

REM Start Backend
echo Starting Backend...
cd backend
start "Backend" cmd /k "..\\.venv\\Scripts\\python.exe main.py"

REM Wait a moment then start Frontend  
timeout /t 3 >nul
echo Starting Frontend...
cd ..\frontend
start "Frontend" cmd /k "npm run dev"

echo.
echo Both servers starting:
echo - Backend: http://localhost:8000
echo - Frontend: http://localhost:5173
echo.
echo You can close this window.
