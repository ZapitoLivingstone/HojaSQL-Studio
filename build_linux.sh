#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

PYTHON_BIN="${HOJASQL_PYTHON:-python3}"

if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  echo "No encuentro el interprete ${PYTHON_BIN}."
  echo "Usa HOJASQL_PYTHON=python3.13 ./build_linux.sh o instala Python 3.12/3.13."
  exit 1
fi

TK_VERSION="$("${PYTHON_BIN}" - <<'PY'
import tkinter
print(tkinter.TkVersion)
PY
)"

if [ "${TK_VERSION}" = "9.0" ]; then
  echo "Build Linux cancelado: ${PYTHON_BIN} usa Tk ${TK_VERSION}."
  echo "PyInstaller en este entorno genera un portable roto con libtcl9.0.so."
  echo "Reconstruye con Python 3.12 o 3.13, por ejemplo:"
  echo "  HOJASQL_PYTHON=python3.13 ./build_linux.sh"
  exit 1
fi

if [ -x ".venv/bin/python" ]; then
  VENV_VERSION="$(
    .venv/bin/python - <<'PY'
import sys
print(f"{sys.version_info.major}.{sys.version_info.minor}")
PY
  )"
  TARGET_VERSION="$(
    "${PYTHON_BIN}" - <<'PY'
import sys
print(f"{sys.version_info.major}.{sys.version_info.minor}")
PY
  )"
  if [ "${VENV_VERSION}" != "${TARGET_VERSION}" ]; then
    echo "Recreando .venv: usa Python ${VENV_VERSION} pero el build pide ${TARGET_VERSION}."
    rm -rf .venv
  fi
fi

if [ ! -d ".venv" ]; then
  "${PYTHON_BIN}" -m venv .venv
fi

source .venv/bin/activate
python -m pip install -r requirements-build.txt
python crear_icono.py
python generar_build_info.py
rm -rf build/HojaSQLStudio dist/HojaSQLStudio
python -m PyInstaller --clean --onedir --windowed --name HojaSQLStudio --icon chopper.ico --add-data "assets/hojasql.png:assets" --add-data "chopper.ico:." --add-data "build_info.json:." consultar_xlsx.py

rm -rf portable-linux/HojaSQLStudio
cp -r dist/HojaSQLStudio portable-linux/HojaSQLStudio
cp HojaSQLStudio.desktop portable-linux/HojaSQLStudio.desktop
cp assets/hojasql.png portable-linux/hojasql.png
cp packaging/linux/install_local.sh portable-linux/install_local.sh
cp packaging/linux/uninstall_local.sh portable-linux/uninstall_local.sh
chmod +x portable-linux/abrir_consola_excel_portable.sh
chmod +x portable-linux/HojaSQLStudio.desktop
chmod +x portable-linux/install_local.sh
chmod +x portable-linux/uninstall_local.sh

if [ -f "HojaSQLStudio-linux-portable.zip" ]; then
  rm -f "HojaSQLStudio-linux-portable.zip"
fi

if [ -f "HojaSQLStudio-linux-portable.tar.gz" ]; then
  rm -f "HojaSQLStudio-linux-portable.tar.gz"
fi

python - <<'PY'
from pathlib import Path
import tarfile
import zipfile

zip_output = Path("HojaSQLStudio-linux-portable.zip")
tar_output = Path("HojaSQLStudio-linux-portable.tar.gz")
base = Path("portable-linux")
with zipfile.ZipFile(zip_output, "w", zipfile.ZIP_DEFLATED) as zf:
    for path in base.rglob("*"):
        if path.is_file():
            zf.write(path, path.relative_to(base.parent))
with tarfile.open(tar_output, "w:gz") as tf:
    for path in base.rglob("*"):
        tf.add(path, path.relative_to(base.parent))
print(zip_output)
print(tar_output)
PY

if command -v dpkg-deb >/dev/null 2>&1; then
  python scripts/build_linux_deb.py
else
  echo "dpkg-deb no esta disponible. Se omitio la generacion del .deb."
fi
