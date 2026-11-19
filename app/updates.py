"""Release checks and verified downloads; installation always requires a user action."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
import json
import re
import hashlib
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import ProxyHandler, Request, build_opener
from urllib.error import HTTPError

from storage import VERSION


# 与主链路 httpx(trust_env=False) 对齐：更新检查不读环境变量里的代理——
# 本机开发环境会注入指向 127.0.0.1 的死代理，静默吃掉所有请求。
urlopen = build_opener(ProxyHandler({})).open


# Public release-only repository verified for MG-RELAY-UPDATE-SOURCE-001.
# This product has its own release feed, isolated from future MicroGlow products.
GITHUB_REPOSITORY = "mazda6hk-coder/MicroGlow-Relay"
WEBSITE_MANIFEST = "https://www.microglow.com.cn/updates/relay/windows-x64.json"
_REPOSITORY_PATTERN = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")
_VERSION_PATTERN = re.compile(r"v?(\d+\.\d+)\Z", re.IGNORECASE)


@dataclass(frozen=True)
class UpdateResult:
    status: str
    latest_version: str = ""
    release_url: str = ""
    download_urls: tuple[str, ...] = ()
    sha256: str = ""
    size: int = 0
    notes: str = ""


def _version_value(label: str) -> Decimal:
    match = _VERSION_PATTERN.fullmatch(label.strip())
    if match is None:
        raise ValueError("Unsupported release version")
    return Decimal(match.group(1))


def check_for_update(repository: str = GITHUB_REPOSITORY, current_version: str = VERSION) -> UpdateResult:
    repository = repository.strip()
    if not repository:
        return UpdateResult("unconfigured")
    if not _REPOSITORY_PATTERN.fullmatch(repository) or ".." in repository:
        raise ValueError("Invalid GitHub repository")
    request = Request(
        f"https://api.github.com/repos/{repository}/releases/latest",
        headers={"Accept": "application/vnd.github+json", "User-Agent": "MicroGlow-Relay-update-check"},
    )
    try:
        with urlopen(request, timeout=8) as response:
            payload = response.read(65537)
    except HTTPError as error:
        if error.code == 404:
            # GitHub returns 404 when there is no latest published release.
            # Do not call this "up to date": no available release was checked.
            return UpdateResult("unavailable")
        raise
    if len(payload) > 65536:
        raise ValueError("Release response is too large")
    release = json.loads(payload)
    latest = release.get("tag_name") if isinstance(release, dict) else None
    if not isinstance(latest, str):
        raise ValueError("Release tag is missing")
    latest_value = _version_value(latest)
    current_value = _version_value(current_version)
    return UpdateResult(
        "available" if latest_value > current_value else "current",
        latest.lstrip("vV"),
        f"https://github.com/{repository}/releases/latest",
    )


def _trusted_url(url: str) -> str:
    value = urlsplit(url)
    if value.scheme != "https" or value.username or value.password or value.port not in (None, 443):
        raise ValueError("Update URL must use trusted HTTPS")
    if value.hostname == "www.microglow.com.cn" and value.path.startswith("/updates/relay/"):
        return url
    if value.hostname == "github.com" and value.path.startswith(f"/{GITHUB_REPOSITORY}/releases/download/"):
        return url
    raise ValueError("Untrusted update URL")


def _json(url: str) -> dict:
    req = Request(url, headers={"Accept": "application/json", "User-Agent": "MicroGlow-Relay-update-check"})
    with urlopen(req, timeout=8) as response:
        raw = response.read(65537)
    if len(raw) > 65536:
        raise ValueError("Update manifest too large")
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError("Invalid update manifest")
    return value


def _manifest(value: dict, current_version: str) -> UpdateResult:
    if value.get("schema") != 1 or value.get("product") != "MicroGlow-Relay" or value.get("platform") != "windows-x64":
        raise ValueError("Wrong update product or schema")
    if value.get("available") is False:
        return UpdateResult("unavailable")
    version = value.get("version", "")
    latest = _version_value(version)
    if latest <= _version_value(current_version):
        return UpdateResult("current", version)
    digest = value.get("sha256", "")
    size = value.get("size")
    urls = value.get("download_urls")
    if not isinstance(digest, str) or not re.fullmatch(r"[a-fA-F0-9]{64}", digest):
        raise ValueError("Missing installer checksum")
    if type(size) is not int or not 0 < size <= 512 * 1024 * 1024:
        raise ValueError("Invalid installer size")
    if not isinstance(urls, list) or not 1 <= len(urls) <= 3 or not all(isinstance(x, str) for x in urls):
        raise ValueError("Missing installer URL")
    return UpdateResult("available", version, download_urls=tuple(_trusted_url(x) for x in urls),
                        sha256=digest.lower(), size=size, notes=str(value.get("notes", ""))[:4000])


def check_downloadable_update(current_version: str = VERSION) -> UpdateResult:
    """GitHub update.json asset first; website fallback on unavailable/invalid primary."""
    try:
        release = _json(f"https://api.github.com/repos/{GITHUB_REPOSITORY}/releases/latest")
        if release.get("draft") or release.get("prerelease"):
            raise ValueError("Not a stable release")
        if _version_value(release.get("tag_name", "")) <= _version_value(current_version):
            return UpdateResult("current", release["tag_name"].lstrip("vV"))
        asset = next(x for x in release.get("assets", []) if x.get("name") == "update.json")
        result = _manifest(_json(_trusted_url(asset["browser_download_url"])), current_version)
        if result.latest_version and _version_value(result.latest_version) != _version_value(release["tag_name"]):
            raise ValueError("Release and manifest versions differ")
        return result
    except Exception:
        return _manifest(_json(WEBSITE_MANIFEST), current_version)


def download_update(result: UpdateResult, directory: Path) -> Path:
    """Only a size+SHA256 verified, atomically completed file can reach the installer UI."""
    if result.status != "available" or not result.download_urls:
        raise ValueError("No downloadable update")
    _version_value(result.latest_version)
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"MicroGlow-Relay-{result.latest_version}-Setup.exe"

    def valid(path):
        if not path.is_file() or path.stat().st_size != result.size:
            return False
        with path.open("rb") as stream:
            return hashlib.file_digest(stream, "sha256").hexdigest() == result.sha256

    if valid(target):
        return target
    temporary = target.with_suffix(".exe.part")
    failure = None
    for url in result.download_urls:
        try:
            _trusted_url(url)
            req = Request(url, headers={"User-Agent": "MicroGlow-Relay-update-download"})
            with urlopen(req, timeout=30) as response, temporary.open("wb") as file:
                received = 0
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    received += len(chunk)
                    if received > result.size:
                        raise ValueError("Installer exceeds declared size")
                    file.write(chunk)
            if not valid(temporary):
                raise ValueError("Installer size or SHA256 mismatch")
            temporary.replace(target)
            return target
        except Exception as error:
            failure = error
            temporary.unlink(missing_ok=True)
    raise RuntimeError("Update download failed; existing application unchanged") from failure
