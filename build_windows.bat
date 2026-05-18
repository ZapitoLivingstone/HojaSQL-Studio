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
python -m pip install -r requirements-build.txt
python crear_icono.py
python -m PyInstaller --clean --onefile --windowed --icon chopper.ico --name HojaSQLStudio --add-data "assets\\hojasql.png;assets" --add-data "chopper.ico;." consultar_xlsx.py

if exist "portable-windows" rmdir /s /q "portable-windows"
mkdir "portable-windows"
copy "dist\HojaSQLStudio.exe" "portable-windows\HojaSQLStudio.exe" >nul
copy "README.md" "portable-windows\README.md" >nul

powershell -NoProfile -ExecutionPolicy Bypass -Command "if (Test-Path 'HojaSQLStudio-windows-portable.zip') { Remove-Item 'HojaSQLStudio-windows-portable.zip' }; Compress-Archive -Path 'portable-windows\*' -DestinationPath 'HojaSQLStudio-windows-portable.zip'"

echo.
echo Ejecutable listo:
echo   portable-windows\HojaSQLStudio.exe
echo.
echo ZIP listo para enviar:
echo   HojaSQLStudio-windows-portable.zip
pause
