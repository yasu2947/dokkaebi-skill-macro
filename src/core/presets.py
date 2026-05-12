"""이름 있는 슬롯 ROI 프리셋 (presets.json) + templates/<subdir>/ PNG 번들."""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from src.core.paths import project_root


def presets_path() -> Path:
    return project_root() / "presets.json"


def sanitize_preset_filename(name: str) -> str:
    s = name.strip()
    for c in '<>:"/\\|?*\n\r\t':
        s = s.replace(c, "_")
    s = s.strip(". ")
    return s or "unnamed"


def preset_bundle_dir(subdir: str) -> Path:
    """프리셋 PNG 저장 위치: 프로젝트(또는 exe 옆) templates/<subdir>/."""
    return project_root() / "templates" / sanitize_preset_filename(subdir)


def copy_slot_templates_into_bundle(src_dir: Path, subdir: str) -> int:
    """slot_*_ready.png / slot_*_swap.png 를 번들 폴더로 복사. 복사한 파일 수."""
    dest = preset_bundle_dir(subdir)
    dest.mkdir(parents=True, exist_ok=True)
    n = 0
    if not src_dir.is_dir():
        return 0
    for pat in ("slot_*_ready.png", "slot_*_swap.png"):
        for p in sorted(src_dir.glob(pat)):
            if p.is_file():
                shutil.copy2(p, dest / p.name)
                n += 1
    return n


def delete_preset_bundle(subdir: str) -> None:
    d = preset_bundle_dir(subdir)
    if d.is_dir():
        shutil.rmtree(d, ignore_errors=True)


def load_preset_library() -> list[dict[str, Any]]:
    p = presets_path()
    if not p.is_file():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    items = data.get("items")
    if not isinstance(items, list):
        return []
    out: list[dict[str, Any]] = []
    for it in items:
        if isinstance(it, dict) and isinstance(it.get("name"), str) and isinstance(it.get("slot_rois"), list):
            out.append(it)
    return out


def save_preset_library(items: list[dict[str, Any]]) -> None:
    p = presets_path()
    p.write_text(json.dumps({"items": items}, ensure_ascii=False, indent=2), encoding="utf-8")


def add_named_preset(
    name: str,
    slot_count: int,
    slot_rois: list[dict[str, int]],
    *,
    copy_templates_from: Path | None = None,
) -> tuple[str, int]:
    """프리셋 추가. PNG 복사 시 (template_subdir, 복사한 파일 수) 반환."""
    subdir = sanitize_preset_filename(name)
    items = load_preset_library()
    items = [x for x in items if x.get("name") != name]
    n_copied = 0
    if copy_templates_from is not None:
        n_copied = copy_slot_templates_into_bundle(copy_templates_from, subdir)
    items.append(
        {
            "name": name,
            "slot_count": slot_count,
            "slot_rois": slot_rois,
            "template_subdir": subdir,
        }
    )
    save_preset_library(items)
    return subdir, n_copied


def delete_named_preset(name: str) -> None:
    items = load_preset_library()
    sub: str | None = None
    kept: list[dict[str, Any]] = []
    for x in items:
        if x.get("name") == name:
            raw = x.get("template_subdir")
            if isinstance(raw, str) and raw.strip():
                sub = sanitize_preset_filename(raw)
            elif isinstance(x.get("name"), str):
                sub = sanitize_preset_filename(str(x["name"]))
        else:
            kept.append(x)
    if sub:
        delete_preset_bundle(sub)
    save_preset_library(kept)


def preset_template_rel_path(item: dict[str, Any]) -> str | None:
    """config.template_dir 에 넣을 상대 경로 templates/<subdir> 또는 없음."""
    raw = item.get("template_subdir")
    if isinstance(raw, str) and raw.strip():
        return f"templates/{sanitize_preset_filename(raw)}"
    return None
