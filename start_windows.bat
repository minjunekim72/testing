@echo off
setlocal EnableExtensions

REM Battery Cell Design Tool (Windows) launcher.
REM - Creates/uses a local venv in .venv
REM - Installs requirements
REM - Launches the Streamlit app at http://localhost:8501

set "PROJECT_DIR=%~dp0"
cd /d "%PROJECT_DIR%"

REM Pick a Python launcher (prefer 'py' on Windows) and enforce a supported version.
REM Recommended: Python 3.12 (best wheel availability on Windows).
REM Python 3.14+ often lacks wheels for numpy/matplotlib/pyarrow, leading to source builds + compiler errors.
set "PYLAUNCH=python"
where py >nul 2>nul
if not errorlevel 1 (
  REM Prefer Python 3.12 if installed; otherwise fall back to default 'py'.
  py -3.12 -V >nul 2>nul
  if not errorlevel 1 (
    set "PYLAUNCH=py -3.12"
  ) else (
    set "PYLAUNCH=py"
  )
)

REM Validate version via exit code (avoid fragile string parsing).
%PYLAUNCH% -c "import sys; sys.exit(0 if (3,12) <= sys.version_info[:2] < (3,14) else 1)" >nul 2>nul
if errorlevel 1 (
  echo Unsupported Python detected for Windows dependency installs.
  echo Please install and use Python 3.12 (recommended) or 3.13, then re-run.
  echo Tip: run `py -0p` to see installed versions.
  pause
  exit /b 1
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

set "VENV_PY=%PROJECT_DIR%.venv\Scripts\python.exe"
if not exist "%VENV_PY%" (
  echo Could not find venv python at: %VENV_PY%
  pause
  exit /b 1
)

echo Installing/updating dependencies...
 "%VENV_PY%" -m pip install --upgrade pip setuptools wheel
if %errorlevel% neq 0 (
  echo Failed to upgrade pip/setuptools/wheel.
  pause
  exit /b 1
)

 "%VENV_PY%" -m pip install --prefer-binary -r requirements.txt
if %errorlevel% neq 0 (
  echo Failed to install dependencies.
  pause
  exit /b 1
)

echo Starting app...
 "%VENV_PY%" run.py

