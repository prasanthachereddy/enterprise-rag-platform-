@echo off
setlocal
cd /d "%~dp0"

echo [0/4] Checking that Python 3.11 is available...
py -3.11 --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python 3.11 was not found. Nothing was changed. Install Python 3.11, then run this again.
    exit /b 1
)

echo [1/4] Removing existing virtual environment if present...
if exist .venv rmdir /s /q .venv

echo [2/4] Creating fresh Python 3.11 virtual environment...
py -3.11 -m venv .venv
if errorlevel 1 goto :fail

echo [3/4] Upgrading pip and installing the package in editable mode with dev and cloud extras...
.venv\Scripts\python -m pip install --upgrade pip
if errorlevel 1 goto :fail
.venv\Scripts\python -m pip install -e ".[dev,cloud]"
if errorlevel 1 goto :fail

echo [4/4] Verifying installation...
.venv\Scripts\python --version
.venv\Scripts\python -c "import sys; assert sys.version_info[:2] == (3, 11), sys.version; import enterprise_rag.config; from enterprise_rag.evaluation.golden import load_golden; print('SUCCESS: Python 3.11 and enterprise_rag loaded')"
if errorlevel 1 goto :fail

echo.
echo DONE. Now run:  call .venv\Scripts\activate.bat
exit /b 0

:fail
echo ERROR: a step failed. Read the messages above and send them to me.
exit /b 1