"""프로젝트 루트 (개발: 저장소 루트, PyInstaller EXE: %APPDATA%/DokkaebiSkillMacro)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

_APP_DIR_NAME = "DokkaebiSkillMacro"


def project_root() -> Path:
    """사용자 데이터 루트 경로.
    EXE: %APPDATA%\\DokkaebiSkillMacro\\  (config·templates·presets 저장)
    개발: 저장소 루트
    """
    if getattr(sys, "frozen", False):
        appdata = os.environ.get("APPDATA", "")
        base = Path(appdata) if appdata else Path.home() / "AppData" / "Roaming"
        return base / _APP_DIR_NAME
    return Path(__file__).resolve().parent.parent.parent


def packaged_subdir(sub: str) -> Path | None:
    """번들 하위 폴더 (contents/font, contents/images 등).
    onefile은 _MEIPASS 우선, 개발은 저장소 루트, exe 옆도 시도."""
    candidates: list[Path] = []
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            candidates.append(Path(meipass) / sub)
    repo = Path(__file__).resolve().parent.parent.parent
    candidates.append(repo / sub)
    if getattr(sys, "frozen", False):
        candidates.append(project_root() / sub)
    for p in candidates:
        if p.is_dir():
            return p
    return None


def app_font_dir() -> Path | None:
    """로컬 번들 폰트 디렉터리."""
    return packaged_subdir("contents/font")


def yasu_logo_path() -> Path | None:
    """contents/images/yasu.png (브랜딩)."""
    d = packaged_subdir("contents/images")
    if d is None:
        return None
    for name in ("yasu.png", "Yasu.png"):
        p = d / name
        if p.is_file():
            return p
    return None


