from __future__ import annotations

import json
import platform
from urllib.error import URLError
from urllib.request import Request, urlopen
import webbrowser

from molinaro.version import APP_NAME, APP_REPOSITORY, APP_VERSION, version_key


LATEST_RELEASE_URL = f"https://api.github.com/repos/{APP_REPOSITORY}/releases/latest"


def detect_asset_keyword() -> str:
    system = platform.system().lower()
    if "windows" in system:
        return "windows-portable.zip"
    if "linux" in system:
        return ".deb"
    return ""


def fetch_latest_release(timeout: int = 5) -> dict[str, object] | None:
    request = Request(
        LATEST_RELEASE_URL,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"{APP_NAME}/{APP_VERSION}",
        },
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except (URLError, TimeoutError, json.JSONDecodeError):
        return None


def extract_download_url(release: dict[str, object]) -> str:
    keyword = detect_asset_keyword()
    assets = release.get("assets", [])
    if isinstance(assets, list):
        for asset in assets:
            if not isinstance(asset, dict):
                continue
            name = str(asset.get("name", ""))
            if keyword and keyword in name.lower():
                return str(asset.get("browser_download_url", release.get("html_url", "")))
        for asset in assets:
            if isinstance(asset, dict) and str(asset.get("name", "")).lower().endswith(".zip"):
                return str(asset.get("browser_download_url", release.get("html_url", "")))
    return str(release.get("html_url", ""))


def check_for_updates() -> dict[str, str] | None:
    release = fetch_latest_release()
    if not release:
        return None

    tag_name = str(release.get("tag_name", "")).lstrip("v")
    if version_key(tag_name) <= version_key(APP_VERSION):
        return None

    return {
        "version": tag_name,
        "name": str(release.get("name", tag_name)),
        "url": extract_download_url(release),
        "html_url": str(release.get("html_url", "")),
        "published_at": str(release.get("published_at", "")),
    }


def open_download_page(url: str) -> None:
    if url:
        webbrowser.open(url)
