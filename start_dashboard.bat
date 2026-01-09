@echo off
echo ========================================
echo Starting MLOps Dashboard System
echo ========================================
echo.
echo Step 1: Starting FastAPI Server...
echo.
start "MLOps API Server" cmd /k "cd /d %~dp0 && uvicorn api:app --reload --port 8000"
timeout /t 5 /nobreak >nul
echo.
echo Step 2: Starting Streamlit Dashboard...
echo.
start "MLOps Dashboard" cmd /k "cd /d %~dp0 && streamlit run streamlit_app.py"
echo.
echo ========================================
echo Both services are starting!
echo ========================================
echo.
echo API Server: http://127.0.0.1:8000
echo Dashboard: http://localhost:8501
echo.
echo Press any key to exit this window...
pause >nul
