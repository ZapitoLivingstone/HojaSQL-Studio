#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

PORTABLE_DIR="$(pwd)"
APP_SOURCE_DIR="${PORTABLE_DIR}/HojaSQLStudio"
APP_SOURCE_BIN="${APP_SOURCE_DIR}/HojaSQLStudio"

if [ ! -x "${APP_SOURCE_BIN}" ]; then
  echo "No encuentro el ejecutable portable en ${APP_SOURCE_BIN}"
  exit 1
fi

XDG_DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
XDG_STATE_HOME="${XDG_STATE_HOME:-$HOME/.local/state}"
INSTALL_ROOT="${HOME}/.local/opt/hojasql-studio"
BIN_DIR="${HOME}/.local/bin"
DESKTOP_DIR="${XDG_DATA_HOME}/applications"
ICON_DIR="${XDG_DATA_HOME}/icons/hicolor/256x256/apps"
APP_DIR="${INSTALL_ROOT}/app"
WRAPPER_PATH="${BIN_DIR}/hojasql-studio"
DESKTOP_PATH="${DESKTOP_DIR}/hojasql-studio.desktop"
ICON_PATH="${ICON_DIR}/hojasql-studio.png"

mkdir -p "${APP_DIR}" "${BIN_DIR}" "${DESKTOP_DIR}" "${ICON_DIR}" "${XDG_STATE_HOME}"

rm -rf "${APP_DIR}"
cp -a "${APP_SOURCE_DIR}" "${APP_DIR}"
install -Dm644 "${PORTABLE_DIR}/hojasql.png" "${ICON_PATH}"

cat > "${WRAPPER_PATH}" <<EOF
#!/usr/bin/env bash
set -euo pipefail

find_tcl_lib_dir() {
  local candidate
  for candidate in \
    "\$HOME/.local/share/mise/installs/python/3.13.13/lib" \
    "\$HOME/.local/share/mise/installs/python/3.14.5/lib" \
    /usr/lib \
    /usr/local/lib
  do
    if [ -f "\${candidate}/libtcl9.0.so" ]; then
      printf '%s\n' "\${candidate}"
      return 0
    fi
  done
  return 1
}

if TCL_LIB_DIR="\$(find_tcl_lib_dir)"; then
  export LD_LIBRARY_PATH="\${TCL_LIB_DIR}\${LD_LIBRARY_PATH:+:\${LD_LIBRARY_PATH}}"
fi

exec "${APP_DIR}/HojaSQLStudio" "\$@"
EOF
chmod 755 "${WRAPPER_PATH}"

cat > "${DESKTOP_PATH}" <<EOF
[Desktop Entry]
Type=Application
Version=1.0
Name=HojaSQL Studio
Comment=Consulta archivos Excel usando SQL en una interfaz grafica
Exec=${WRAPPER_PATH} %F
TryExec=${WRAPPER_PATH}
Icon=hojasql-studio
Terminal=false
Categories=Office;
MimeType=application/vnd.ms-excel;application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;application/vnd.ms-excel.sheet.macroEnabled.12;
StartupWMClass=HojaSQLStudio
EOF
chmod 644 "${DESKTOP_PATH}"

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "${DESKTOP_DIR}" >/dev/null 2>&1 || true
fi

if command -v gtk-update-icon-cache >/dev/null 2>&1; then
  gtk-update-icon-cache "${XDG_DATA_HOME}/icons/hicolor" >/dev/null 2>&1 || true
fi

echo "Instalacion completada."
echo "Launcher: ${DESKTOP_PATH}"
echo "Ejecutable: ${WRAPPER_PATH}"
echo "Aplicacion: ${APP_DIR}/HojaSQLStudio"
