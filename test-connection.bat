@echo off
echo ==========================================
echo     Connection Troubleshooting
echo ==========================================
echo.

echo Testing Backend Connection...
echo.

echo [1] Testing Health Endpoint:
curl -s http://localhost:8000/api/health
echo.

echo [2] Testing Yield Curve Endpoint:
curl -s -H "Origin: http://localhost:5173" http://localhost:8000/api/yield-curve | findstr "yield_curve"
echo.

echo [3] Testing CORS Headers:
curl -I -H "Origin: http://localhost:5173" http://localhost:8000/api/health | findstr "access-control"
echo.

echo [4] Checking if Frontend is running:
curl -s -I http://localhost:5173/ | findstr "HTTP"
echo.

echo ==========================================
echo If you see HTTP 200 responses above, 
echo both servers are working correctly.
echo ==========================================
pause
