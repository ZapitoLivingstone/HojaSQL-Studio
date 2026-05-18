#!/usr/bin/env bash
set -e

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

"$APP" "$@"
