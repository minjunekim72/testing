@echo off
setlocal EnableExtensions

REM Battery Cell Design Tool (Windows) launcher.
REM - Creates/uses a local venv in .venv
REM - Installs requirements
REM - Launches the Streamlit app at http://localhost:8501

set "PROJECT_DIR=%~dp0"
cd /d "%PROJECT_DIR%"

REM Pick a Python launcher (prefer 'py' on Windows).
where py >nul 2>nul
if %errorlevel%==0 (
  set "PYLAUNCH=py"
) else (
  set "PYLAUNCH=python"
)

if not exist ".venv\Scripts\python.exe" (
  echo Creating virtual environment...
  %PYLAUNCH% -m venv .venv
  if %errorlevel% neq 0 (
    echo Failed to create venv. Ensure Python is installed.
    pause
    exit /b 1
  )
)

call ".venv\Scripts\activate.bat"
if %errorlevel% neq 0 (
  echo Failed to activate venv.
  pause
  exit /b 1
)

echo Installing/updating dependencies...
python -m pip install --upgrade pip setuptools wheel
if %errorlevel% neq 0 (
  echo Failed to upgrade pip/setuptools/wheel.
  pause
  exit /b 1
)

python -m pip install --prefer-binary -r requirements.txt
if %errorlevel% neq 0 (
  echo Failed to install dependencies.
  pause
  exit /b 1
)

echo Starting app...
python run.py

