@echo off
setlocal EnableExtensions

REM Battery Cell Design Tool (Windows) launcher.
REM - Creates/uses a local venv in .venv
REM - Installs requirements
REM - Launches the Streamlit app at http://localhost:8501

set "PROJECT_DIR=%~dp0"
cd /d "%PROJECT_DIR%"

REM Pick a Python launcher (prefer 'py' on Windows) and enforce a supported version.
REM This project is known to work well on Python 3.12+.
REM Very new Python versions (e.g. 3.14) may not have wheels for numpy/matplotlib/pyarrow yet,
REM causing pip to attempt source builds and fail with compiler errors.
where py >nul 2>nul
if %errorlevel%==0 (
  REM Prefer Python 3.12 if installed.
  py -3.12 -c "import sys; raise SystemExit(0)" >nul 2>nul
  if %errorlevel%==0 (
    set "PYLAUNCH=py -3.12"
  ) else (
    set "PYLAUNCH=py"
  )
) else (
  set "PYLAUNCH=python"
)

REM Validate Python version (require >=3.12 and <3.14 for best Windows wheel availability).
for /f "usebackq tokens=*" %%v in (`%PYLAUNCH% -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"`) do set "PYVER=%%v"
if "%PYVER%"=="" (
  echo Failed to detect Python version. Ensure Python is installed.
  pause
  exit /b 1
)

for /f "tokens=1,2 delims=." %%a in ("%PYVER%") do (
  set "PYMAJOR=%%a"
  set "PYMINOR=%%b"
)

if not "%PYMAJOR%"=="3" (
  echo Unsupported Python version: %PYVER%
  echo Please install Python 3.12 (recommended) or 3.13 and try again.
  pause
  exit /b 1
)

if %PYMINOR% LSS 12 (
  echo Unsupported Python version: %PYVER%
  echo Please install Python 3.12 (recommended) or 3.13 and try again.
  pause
  exit /b 1
)

if %PYMINOR% GEQ 14 (
  echo Python %PYVER% detected.
  echo On Windows, pip may fail because some dependencies do not yet ship wheels for Python %PYVER%.
  echo Please install Python 3.12 (recommended) or 3.13, then re-run this launcher.
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

