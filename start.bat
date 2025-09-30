@echo off
setlocal

echo ==========================================
echo    Gemini IRD Pricer - Full Application
echo ==========================================
echo.

REM Get the current directory (project root)
set PROJECT_ROOT=%~dp0
cd /d "%PROJECT_ROOT%"

echo [1/3] Checking prerequisites...

REM Check if virtual environment exists
if not exist ".venv\Scripts\python.exe" (
    echo ERROR: Python virtual environment not found!
    echo Please ensure .venv directory exists with Python installed.
    pause
    exit /b 1
)

REM Check if node_modules exists in frontend
if not exist "frontend\node_modules" (
    echo ERROR: Frontend dependencies not installed!
    echo Please run 'npm install' in the frontend directory first.
    pause
    exit /b 1
)

echo ✓ Prerequisites check passed

echo.
echo [2/3] Starting Backend (FastAPI)...
cd backend
start "IRD Pricer Backend - Port 8000" cmd /k ""%PROJECT_ROOT%.venv\Scripts\python.exe" main.py"
cd "%PROJECT_ROOT%"

echo [3/4] Waiting for backend to initialize...
timeout /t 5 /nobreak >nul

echo [4/4] Testing backend connection...
curl -s http://localhost:8000/api/health >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo WARNING: Backend may not be ready yet. Frontend will retry automatically.
) else (
    echo ✓ Backend is responding
)

echo [4/4] Starting Frontend (React/Vite)...
cd frontend
start "IRD Pricer Frontend - Port 5173" cmd /k "npm run dev"
cd "%PROJECT_ROOT%"

echo.
echo ==========================================
echo           🚀 Application Ready!
echo ==========================================
echo.
echo   Frontend:  http://localhost:5173/
echo   Backend:   http://localhost:8000/api/
echo   API Docs:  http://localhost:8000/docs
echo.
echo Both servers are starting in separate command windows:
echo   - Backend window: "IRD Pricer Backend - Port 8000"
echo   - Frontend window: "IRD Pricer Frontend - Port 5173" 
echo.
echo To stop the application:
echo   - Close both server windows, or
echo   - Press Ctrl+C in each window
echo.
echo This window can be closed after the servers start.
echo.
pause
