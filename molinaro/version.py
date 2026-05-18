from __future__ import annotations

import json
from pathlib import Path
import re

from molinaro.resources import resource_path


APP_REPOSITORY = "ZapitoLivingstone/HojaSQL-Studio"
DEFAULT_BUILD_INFO = {
    "app_name": "HojaSQL Studio",
    "version": "0.0.0-dev",
    "channel": "dev",
    "commit": "workspace",
}


def load_build_info() -> dict[str, str]:
    build_info_path = resource_path("build_info.json")
    try:
        if build_info_path.exists():
            return DEFAULT_BUILD_INFO | json.loads(build_info_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        pass
    return DEFAULT_BUILD_INFO.copy()


BUILD_INFO = load_build_info()
APP_NAME = BUILD_INFO["app_name"]
APP_VERSION = BUILD_INFO["version"]
APP_CHANNEL = BUILD_INFO["channel"]
APP_COMMIT = BUILD_INFO["commit"]


def version_key(version: str) -> tuple[int, ...]:
    digits = re.findall(r"\d+", version)
    return tuple(int(part) for part in digits) if digits else (0,)

