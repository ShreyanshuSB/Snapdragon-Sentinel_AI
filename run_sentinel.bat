@echo off
setlocal enabledelayedexpansion

echo =====================================================================
echo   SENTINEL -- Privacy-First Local Multimodal AI Companion
echo   Windows One-Click Launcher
echo =====================================================================
echo.

:: Detect root directory
set "ROOT_DIR=%~dp0"
cd /d "%ROOT_DIR%"

:: Check for .env file; copy from .env.example if missing
if not exist ".env" (
    if exist ".env.example" (
        echo [*] .env not found. Initializing from .env.example...
        copy ".env.example" ".env" >nul
        echo [OK] Created .env configuration file.
    ) else (
        echo [!] Warning: Neither .env nor .env.example found.
    )
)

:: Locate Python executable
set "PYTHON_EXE="
if exist ".venv\Scripts\python.exe" (
    set "PYTHON_EXE=.venv\Scripts\python.exe"
) else (
    where python >nul 2>&1
    if !errorlevel! equ 0 (
        set "PYTHON_EXE=python"
    ) else (
        where py >nul 2>&1
        if !errorlevel! equ 0 (
            set "PYTHON_EXE=py"
        )
    )
)

if "%PYTHON_EXE%"=="" (
    echo [ERROR] Python not found. Please install Python 3.10+ or configure a virtualenv in .venv.
    pause
    exit /b 1
)

echo [*] Using Python: %PYTHON_EXE%

:: Run pre-flight verification
echo [*] Running installation pre-flight check...
"%PYTHON_EXE%" scripts\verify_installation.py
if %errorlevel% neq 0 (
    echo [!] Pre-flight verification reported missing dependencies.
    echo [*] Attempting to proceed, but services may fail if dependencies are missing.
    echo.
)

:: Locate Node / NPM for frontend
where npm >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js and NPM must be installed on PATH to run the Next.js frontend.
    pause
    exit /b 1
)

:: Ensure frontend dependencies exist
if not exist "frontend\node_modules" (
    echo [*] Installing frontend dependencies (npm install)...
    cd /d "%ROOT_DIR%frontend"
    call npm install
    cd /d "%ROOT_DIR%"
)

echo.
echo =====================================================================
echo   Starting SENTINEL Services
echo   - Backend  : http://localhost:8000 (FastAPI Docs: /docs)
echo   - Frontend : http://localhost:3000 (Next.js Application)
echo =====================================================================
echo.

:: Launch Backend in separate window
start "SENTINEL Backend (FastAPI)" cmd /k "cd /d %ROOT_DIR% && set PYTHONPATH=backend && %PYTHON_EXE% -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload"

:: Launch Frontend in separate window
start "SENTINEL Frontend (Next.js)" cmd /k "cd /d %ROOT_DIR%frontend && npm run dev"

echo [*] Both services launched in separate console windows.
echo [*] Open your web browser to: http://localhost:3000
echo.
pause
