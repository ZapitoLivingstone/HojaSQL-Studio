#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

APP="./HojaSQLStudio/HojaSQLStudio"

if [ ! -x "$APP" ]; then
  APP="./HojaSQLStudio"
fi

if [ ! -x "$APP" ]; then
  echo "No encuentro el ejecutable HojaSQLStudio."
  echo "Este script debe estar junto a la carpeta portable."
  exit 1
fi

find_tcl_lib_dir() {
  local candidate
  for candidate in \
    "$HOME/.local/share/mise/installs/python/3.13.13/lib" \
    "$HOME/.local/share/mise/installs/python/3.14.5/lib" \
    /usr/lib \
    /usr/local/lib
  do
    if [ -f "${candidate}/libtcl9.0.so" ]; then
      printf '%s\n' "${candidate}"
      return 0
    fi
  done
  return 1
}

if TCL_LIB_DIR="$(find_tcl_lib_dir)"; then
  export LD_LIBRARY_PATH="${TCL_LIB_DIR}${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}"
fi

"$APP" "$@"
