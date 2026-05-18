from __future__ import annotations

import argparse
from pathlib import Path

from molinaro.ui import MolinaroApp
from molinaro.version import APP_NAME


def main() -> None:
    parser = argparse.ArgumentParser(description=f"Consulta archivos Excel con SQL en {APP_NAME}.")
    parser.add_argument("xlsx", nargs="?", help="Ruta de un archivo Excel para abrir al iniciar.")
    args = parser.parse_args()

    initial_path = Path(args.xlsx).expanduser().resolve() if args.xlsx else None
    app = MolinaroApp(initial_path=initial_path)
    app.run()


if __name__ == "__main__":
    main()
