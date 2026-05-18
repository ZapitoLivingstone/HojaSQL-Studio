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
python generar_build_info.py
python -m PyInstaller --clean --onefile --windowed --icon chopper.ico --name HojaSQLStudio --add-data "assets\\hojasql.png;assets" --add-data "chopper.ico;." --add-data "build_info.json;." consultar_xlsx.py

if exist "portable-windows" rmdir /s /q "portable-windows"
mkdir "portable-windows"
copy "dist\HojaSQLStudio.exe" "portable-windows\HojaSQLStudio.exe" >nul
copy "chopper.ico" "portable-windows\chopper.ico" >nul
copy "README.md" "portable-windows\README.md" >nul

powershell -NoProfile -ExecutionPolicy Bypass -Command "if (Test-Path 'HojaSQLStudio-windows-portable.zip') { Remove-Item 'HojaSQLStudio-windows-portable.zip' }; Compress-Archive -Path 'portable-windows\*' -DestinationPath 'HojaSQLStudio-windows-portable.zip'"

set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if exist "%ISCC%" (
  "%ISCC%" "packaging\windows\HojaSQLStudio.iss"
) else (
  echo.
  echo Inno Setup 6 no esta instalado. Se omitio el instalador .exe.
  echo Instala Inno Setup para generar dist\HojaSQLStudio-setup.exe
)

echo.
echo Ejecutable listo:
echo   portable-windows\HojaSQLStudio.exe
echo.
echo ZIP listo para enviar:
echo   HojaSQLStudio-windows-portable.zip
if exist "dist\HojaSQLStudio-setup.exe" (
echo.
echo Instalador listo:
echo   dist\HojaSQLStudio-setup.exe
)
pause
