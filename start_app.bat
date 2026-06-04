@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "PYTHON_CMD="
if exist ".venv\Scripts\python.exe" (
  set "PYTHON_CMD=.venv\Scripts\python.exe"
) else (
  py -3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul
  if not errorlevel 1 set "PYTHON_CMD=py -3"
)

if not defined PYTHON_CMD (
  python -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul
  if not errorlevel 1 set "PYTHON_CMD=python"
)

if not defined PYTHON_CMD (
  echo.
  echo Python 3.10 or newer was not found.
  echo Run install_app.bat first.
  echo.
  pause
  exit /b 1
)

echo.
echo  Pub Assist
echo  ----------
echo  Using: %PYTHON_CMD%
echo  If dependencies are missing, run install_app.bat first.
echo.
echo  Starting server at http://127.0.0.1:7654
echo  Press Ctrl+C to stop.
echo.
%PYTHON_CMD% -m uvicorn app:app --reload --host 127.0.0.1 --port 7654
pause
