@echo off
echo Installing dependencies...
pip install -r backend/requirements.txt
echo.
echo Starting Financial Benchmark server...
echo Open http://localhost:5000 in your browser
echo.
cd backend
python main.py
