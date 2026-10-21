@echo off
setlocal EnableExtensions

REM Annapurna AI one-click Windows launcher.
REM The first run installs Node and Python dependencies; later runs start immediately.

set "PROJECT_ROOT=%~dp0"
cd /d "%PROJECT_ROOT%"

where node >nul 2>nul
if errorlevel 1 goto :missing_node

where npm >nul 2>nul
if errorlevel 1 goto :missing_node

where py >nul 2>nul
if errorlevel 1 (
    where python >nul 2>nul
    if errorlevel 1 goto :missing_python
    set "PYTHON=python"
) else (
    set "PYTHON=py"
)

if not exist "node_modules\" (
    echo Installing frontend dependencies. This happens only on the first run...
    call npm install
    if errorlevel 1 goto :install_failed
)

if not exist "backend\.venv\Scripts\python.exe" (
    echo Creating the backend Python environment. This happens only on the first run...
    %PYTHON% -m venv "backend\.venv"
    if errorlevel 1 goto :install_failed
    "backend\.venv\Scripts\python.exe" -m pip install --upgrade pip
    if errorlevel 1 goto :install_failed
    "backend\.venv\Scripts\python.exe" -m pip install -r "backend\requirements.txt"
    if errorlevel 1 goto :install_failed
)

"backend\.venv\Scripts\python.exe" -c "import alembic" >nul 2>nul
if errorlevel 1 (
    echo Updating backend dependencies for this project version...
    "backend\.venv\Scripts\python.exe" -m pip install -r "backend\requirements.txt"
    if errorlevel 1 goto :install_failed
)

if not exist ".env" (
    copy ".env.example" ".env" >nul
    echo Created .env from .env.example. Add API keys there to enable live integrations.
)

echo Applying local database migrations...
pushd "backend"
".venv\Scripts\python.exe" -m alembic upgrade head
if errorlevel 1 (
    popd
    goto :install_failed
)
popd

echo Starting Annapurna AI...
start "Annapurna Backend" /min cmd /k "cd /d ""%PROJECT_ROOT%backend"" ^&^& ""%PROJECT_ROOT%backend\.venv\Scripts\python.exe"" -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
start "Annapurna Frontend" /min cmd /k "cd /d ""%PROJECT_ROOT%"" ^&^& npm run dev"

timeout /t 3 /nobreak >nul
start "" "http://127.0.0.1:5173"
echo Annapurna AI is running at http://127.0.0.1:5173
echo Keep the two Annapurna command windows open while using the app.
exit /b 0

:missing_node
echo Node.js 20 or newer is required. Install it from https://nodejs.org/ and run this file again.
pause
exit /b 1

:missing_python
echo Python 3.11 or newer is required. Install it from https://www.python.org/downloads/ and run this file again.
pause
exit /b 1

:install_failed
echo Setup failed. Check your internet connection and the messages above, then run this file again.
pause
exit /b 1
