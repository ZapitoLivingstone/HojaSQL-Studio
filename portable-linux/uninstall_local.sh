#!/usr/bin/env bash
set -euo pipefail

XDG_DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
INSTALL_ROOT="${HOME}/.local/opt/hojasql-studio"
BIN_PATH="${HOME}/.local/bin/hojasql-studio"
DESKTOP_PATH="${XDG_DATA_HOME}/applications/hojasql-studio.desktop"
ICON_PATH="${XDG_DATA_HOME}/icons/hicolor/256x256/apps/hojasql-studio.png"

rm -rf "${INSTALL_ROOT}"
rm -f "${BIN_PATH}" "${DESKTOP_PATH}" "${ICON_PATH}"

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "${XDG_DATA_HOME}/applications" >/dev/null 2>&1 || true
fi

if command -v gtk-update-icon-cache >/dev/null 2>&1; then
  gtk-update-icon-cache "${XDG_DATA_HOME}/icons/hicolor" >/dev/null 2>&1 || true
fi

echo "HojaSQL Studio fue desinstalado de tu carpeta local."
