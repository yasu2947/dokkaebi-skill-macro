"""GitHub Releases 기반 자동 업데이트 유틸리티."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
import urllib.request

GITHUB_OWNER = "yasu2947"
GITHUB_REPO = "dokkaebi-skill-macro"
GITHUB_API_LATEST = (
    f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"
)
ASSET_NAME = "DokkaebiSkillMacro.exe"


@dataclass
class UpdateInfo:
    tag: str
    version: str
    download_url: str
    release_notes: str


def _parse_version(v: str) -> tuple[int, ...]:
    try:
        return tuple(int(x) for x in v.lstrip("v").split("."))
    except ValueError:
        return (0,)


def is_newer(remote_tag: str, current_version: str) -> bool:
    return _parse_version(remote_tag) > _parse_version(current_version)


def check_update(current_version: str, timeout: float = 5.0) -> UpdateInfo | None:
    """GitHub 최신 릴리즈와 비교. 업데이트 있으면 UpdateInfo 반환, 없으면 None."""
    try:
        req = urllib.request.Request(
            GITHUB_API_LATEST,
            headers={"User-Agent": f"DokkaebiSkillMacro/{current_version}"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data: dict = json.loads(resp.read())

        tag = data.get("tag_name", "")
        if not tag or not is_newer(tag, current_version):
            return None

        download_url = ""
        for asset in data.get("assets", []):
            if asset.get("name", "").lower() == ASSET_NAME.lower():
                download_url = asset["browser_download_url"]
                break

        notes = data.get("body", "").strip()
        return UpdateInfo(
            tag=tag,
            version=tag.lstrip("v"),
            download_url=download_url,
            release_notes=notes,
        )
    except Exception:
        return None


def download_update(
    url: str,
    dest: Path,
    progress_cb: Callable[[float], None] | None = None,
) -> bool:
    """url → dest 에 다운로드. 성공 True."""
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(
            url,
            headers={"User-Agent": f"DokkaebiSkillMacro-Updater"},
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            total = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            with open(dest, "wb") as f:
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_cb and total:
                        progress_cb(downloaded / total)
        return True
    except Exception:
        return False


def current_exe_path() -> Path | None:
    """실행 중인 EXE 경로 (--onefile 모드에서만 유효)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve()
    return None


def apply_update_and_restart(new_exe: Path) -> None:
    """새 EXE로 현재 EXE를 교체하고 재시작. 프로세스 종료 포함."""
    current = current_exe_path()
    if current is None:
        return

    pid = os.getpid()
    script = (
        "$p={pid}; $t=0;"
        "while((Get-Process -Id $p -EA SilentlyContinue) -and $t -lt 20){{"
        "Start-Sleep -m 300; $t+=0.3}}"
        "Copy-Item -Path '{new}' -Destination '{cur}' -Force;"
        "Start-Process '{cur}'"
    ).format(pid=pid, new=str(new_exe), cur=str(current))

    subprocess.Popen(
        ["powershell", "-WindowStyle", "Hidden", "-NonInteractive", "-Command", script],
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    sys.exit(0)
