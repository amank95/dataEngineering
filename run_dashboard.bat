@echo off
echo Starting Data Engineering Dashboard...
echo.
echo Make sure the API is running in another terminal:
echo   python run_all.py --start-api
echo.
echo Starting Streamlit dashboard...
streamlit run dashboard.py
