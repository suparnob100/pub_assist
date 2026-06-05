@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

echo.
echo  Pub Assist installer
echo  --------------------
echo.

call :find_python
if not defined PY_CMD (
  echo Python 3.10 or newer was not found.
  where winget >nul 2>nul
  if errorlevel 1 (
    echo.
    echo winget was not found, so this installer cannot install Python automatically.
    echo Please install Python from https://www.python.org/downloads/ and run this installer again.
    start https://www.python.org/downloads/
    pause
    exit /b 1
  )

  echo Installing Python 3.12 with winget...
  winget install --id Python.Python.3.12 -e --source winget --accept-package-agreements --accept-source-agreements
  if errorlevel 1 (
    echo.
    echo Python installation failed. Please install Python manually and run this installer again.
    pause
    exit /b 1
  )

  call :find_python
  if not defined PY_CMD (
    echo.
    echo Python appears to be installed, but this terminal cannot find it yet.
    echo Close this window, open a new Command Prompt, and run install_app.bat again.
    pause
    exit /b 1
  )
)

echo Using Python command: %PY_CMD%

if not exist ".venv\Scripts\python.exe" (
  echo Creating local virtual environment in .venv...
  %PY_CMD% -m venv .venv
  if errorlevel 1 (
    echo.
    echo Could not create the virtual environment.
    pause
    exit /b 1
  )
) else (
  echo Reusing existing .venv.
)

echo Upgrading pip...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto :pip_failed

echo Installing Pub Assist requirements...
".venv\Scripts\python.exe" -m pip install -r requirements_app.txt
if errorlevel 1 goto :pip_failed

call :check_node

echo.
echo Pub Assist is ready.
echo Launch it with start_app.bat.
echo.
pause
exit /b 0

:pip_failed
echo.
echo Dependency installation failed. Check the error above, then run install_app.bat again.
pause
exit /b 1

:check_node
echo.
where node >nul 2>nul
if errorlevel 1 (
  echo Optional BibTeX Cleaner engines: Node.js was not found.
  set "INSTALL_NODE="
  set /p INSTALL_NODE=Install Node.js LTS now for BibTeX Cleaner support? [y/N]:
  if /I "!INSTALL_NODE!"=="Y" (
    where winget >nul 2>nul
    if errorlevel 1 (
      echo winget was not found, so this installer cannot install Node.js automatically.
      echo Please install Node.js LTS from https://nodejs.org/ and run this installer again.
      start https://nodejs.org/
      goto :eof
    )
    echo Installing Node.js LTS with winget...
    winget install --id OpenJS.NodeJS.LTS -e --source winget --accept-package-agreements --accept-source-agreements
    if errorlevel 1 (
      echo Node.js installation failed. You can install it later from https://nodejs.org/.
      goto :eof
    )
    where node >nul 2>nul
    if errorlevel 1 (
      echo Node.js was installed, but this Command Prompt cannot find it yet.
      echo Close this window, open a new Command Prompt, and run install_app.bat again.
      goto :eof
    )
  ) else (
    echo Skipping Node.js installation. BibTeX Cleaner website-bundle and npm/npx routes will be unavailable.
    goto :eof
  )
)
echo Optional BibTeX Cleaner website-bundle route: Node.js found.
where npx >nul 2>nul
if errorlevel 1 (
  echo Optional BibTeX Cleaner npm/npx route: npx was not found.
) else (
  echo Optional BibTeX Cleaner npm/npx route: npx found.
  echo   Pub Assist can run: npx --yes bibtex-tidy@latest
)
goto :eof

:find_python
set "PY_CMD="
py -3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul
if not errorlevel 1 (
  set "PY_CMD=py -3"
  goto :eof
)
python -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul
if not errorlevel 1 (
  set "PY_CMD=python"
  goto :eof
)
goto :eof
