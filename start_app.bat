@echo off
cd /d "%~dp0"
echo.
echo  Pub Assist
echo  ----------
echo  Install dependencies if needed:
echo    pip install -r requirements_app.txt
echo.
echo  Starting server at http://127.0.0.1:7654
echo  Press Ctrl+C to stop.
echo.
uvicorn app:app --reload --host 127.0.0.1 --port 7654
pause
