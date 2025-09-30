@echo off
echo ==========================================
echo    Gemini IRD Pricer - Full Application
echo ==========================================
echo.

echo [1/3] Starting Backend (FastAPI)...
cd backend
start "IRD Pricer Backend" cmd /k "C:\Source\GeminiIRDPricer\.venv\Scripts\python.exe main.py"
cd ..

echo [2/3] Waiting for backend to initialize...
timeout /t 5 /nobreak >nul

echo [3/3] Starting Frontend (React)...
cd frontend
start "IRD Pricer Frontend" cmd /k "npm run dev"
cd ..

echo.
echo ==========================================
echo           🚀 Application Ready!
echo ==========================================
echo.
echo   Frontend:  http://localhost:5173/
echo   Backend:   http://localhost:8000/api/
echo   API Docs:  http://localhost:8000/docs
echo.
echo Both servers are starting in separate windows.
echo Close this window when done testing.
echo.
pause
