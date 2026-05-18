@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv" (
  where py >nul 2>nul
  if %errorlevel%==0 (
    py -m venv .venv
  ) else (
    python -m venv .venv
  )
)

call .venv\Scripts\activate.bat
python -m pip install -r requirements.txt
python consultar_xlsx.py %*
