#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

source .venv/bin/activate
python -m pip install -r requirements-build.txt
python crear_icono.py
python -m PyInstaller --clean --onedir --windowed --name HojaSQLStudio --icon chopper.ico --add-data "assets/hojasql.png:assets" --add-data "chopper.ico:." consultar_xlsx.py
