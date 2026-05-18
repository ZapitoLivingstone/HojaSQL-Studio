from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess

from molinaro.version import APP_VERSION


ROOT = Path(__file__).resolve().parents[1]
DIST_DIR = ROOT / "dist"
PACKAGE_ROOT = ROOT / "build" / "deb-root"
APP_DIR = PACKAGE_ROOT / "opt" / "hojasql-studio"
DEBIAN_DIR = PACKAGE_ROOT / "DEBIAN"
APPlications_DIR = PACKAGE_ROOT / "usr" / "share" / "applications"
PIXMAPS_DIR = PACKAGE_ROOT / "usr" / "share" / "pixmaps"
OUTPUT_DEB = ROOT / f"hojasql-studio_{APP_VERSION}_amd64.deb"


def main() -> None:
    source_dir = DIST_DIR / "HojaSQLStudio"
    executable = source_dir / "HojaSQLStudio"
    if not executable.exists():
        raise SystemExit("No encuentro dist/HojaSQLStudio. Ejecuta primero build_linux.sh hasta el paso de PyInstaller.")

    if OUTPUT_DEB.exists():
        OUTPUT_DEB.unlink()

    if PACKAGE_ROOT.exists():
        shutil.rmtree(PACKAGE_ROOT)

    APP_DIR.parent.mkdir(parents=True, exist_ok=True)
    DEBIAN_DIR.mkdir(parents=True, exist_ok=True)
    APPlications_DIR.mkdir(parents=True, exist_ok=True)
    PIXMAPS_DIR.mkdir(parents=True, exist_ok=True)

    shutil.copytree(source_dir, APP_DIR)
    shutil.copy2(ROOT / "assets" / "hojasql.png", PIXMAPS_DIR / "hojasql-studio.png")
    shutil.copy2(ROOT / "packaging" / "linux" / "hojasql-studio.desktop", APPlications_DIR / "hojasql-studio.desktop")
    shutil.copy2(ROOT / "packaging" / "linux" / "postinst", DEBIAN_DIR / "postinst")
    os.chmod(DEBIAN_DIR / "postinst", 0o755)

    control = f"""Package: hojasql-studio
Version: {APP_VERSION}
Section: office
Priority: optional
Architecture: amd64
Maintainer: ZapitoLivingstone
Depends: libgl1, libx11-6
Description: HojaSQL Studio
 Consulta archivos Excel usando SQL en una interfaz grafica.
"""
    (DEBIAN_DIR / "control").write_text(control, encoding="utf-8")

    subprocess.run(["dpkg-deb", "--build", str(PACKAGE_ROOT), str(OUTPUT_DEB)], check=True)
    print(OUTPUT_DEB)


if __name__ == "__main__":
    main()
