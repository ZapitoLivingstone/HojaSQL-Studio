from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess


OUTPUT = Path("build_info.json")


def git_output(args: list[str], fallback: str) -> str:
    try:
        return subprocess.check_output(args, text=True).strip()
    except Exception:
        return fallback


def main() -> None:
    version = os.environ.get("APP_VERSION", "0.0.0-dev")
    channel = os.environ.get("APP_CHANNEL", "stable" if version != "0.0.0-dev" else "dev")
    commit = os.environ.get("GITHUB_SHA") or git_output(["git", "rev-parse", "--short", "HEAD"], "workspace")
    payload = {
        "app_name": "HojaSQL Studio",
        "version": version,
        "channel": channel,
        "commit": commit[:12],
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Build info generado: {OUTPUT}")


if __name__ == "__main__":
    main()
