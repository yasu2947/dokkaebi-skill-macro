"""앱 설정 로드/저장 (JSON)."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from src.core.paths import project_root
from src.core.skill_info import SkillInfo, new_skill_id, normalize_skill_infos


def default_config_path() -> Path:
    return project_root() / "config.json"


def _default_keys(n: int) -> list[str]:
    base = ["2", "3", "4", "5", "6", "7", "8"]
    if n <= len(base):
        return list(base[:n])
    out = (base * ((n + 6) // 7))[:n]
    return out


@dataclass
class AppConfig:
    monitor_width: int = 1920
    monitor_height: int = 1080
    mc_width: int = 1920
    mc_height: int = 1080
    template_dir: str = "templates"
    swap_key: str = "f"
    """스킬바 전체 영역 (화면 좌표, 픽셀). 없으면 None."""
    skill_bar_roi: dict[str, int] | None = None
    """가로로 균등 분할할 슬롯 수 (1~7)."""
    slot_count: int = 7
    """슬롯마다 매칭에 쓸 키 문자열 (길이 = slot_count)."""
    skill_keys: list[str] = field(default_factory=lambda: _default_keys(7))
    """슬롯별 직접 지정 범위(mss 픽셀). 길이가 slot_count이면 균등 분할 대신 사용."""
    slot_rois: list[dict[str, int]] | None = None
    """TM_CCOEFF_NORMED 기준 이 값 이상이면 스킬 준비로 간주."""
    match_threshold: float = 0.88
    """슬롯당 최대 대기 시간(초). 넘기면 다음 슬롯으로."""
    slot_timeout_sec: float = 120.0
    """매칭 폴링 간격 (ms)."""
    poll_interval_ms: int = 80
    """키 입력 후 짧은 대기 (ms)."""
    post_press_delay_ms: int = 60
    """스킬 발동 후 다음 스킬까지 대기 (ms). 0 = 즉시."""
    slot_gap_ms: int = 120
    """1사이클 전역 단축키. 빈 문자열 = 없음."""
    run_hotkey: str = ""
    # 자동 스왑: 1라운드 후 swap 키 → 스왑 켠 슬롯만 slot_XX_swap.png 로 2라운드
    auto_swap_enabled: bool = False
    swap_delay_ms: int = 450
    """슬롯별 발동 우선도 (0=자동/순서대로, 1=최우선 … 7=최후순). 길이 slot_count."""
    slot_priorities: list[int] = field(default_factory=list)
    """1라운드(준비 PNG)에서 해당 슬롯을 쓸지 여부. 길이 slot_count."""
    slot_skill_enabled: list[bool] = field(default_factory=list)
    """슬롯마다 스왑(②) 템플릿·우선순위 사용 여부. 길이 slot_count."""
    slot_swap_enabled: list[bool] = field(default_factory=lambda: [False] * 7)
    """스왑 2라운드에서 슬롯별 swap PNG 발동 우선도 (0=자동, 1=최우선 … 7=최후순). 길이 slot_count."""
    slot_swap_priorities: list[int] = field(default_factory=lambda: [0] * 7)
    """2라운드(스왑 PNG)에서 해당 슬롯을 쓸지 여부. True=기본값(1라운드 설정 따름). 길이 slot_count."""
    slot_swap_skill_enabled: list[bool] = field(default_factory=list)
    """슬롯별 스킬 정보 (배율·쿨타임·타수·스킬속도). 길이 = slot_count. (레거시 — skill_library로 대체)"""
    skill_infos: list[dict] = field(default_factory=list)
    """딜사이클/허수아비 모드 활성화 여부."""
    cycle_mode_enabled: bool = False
    """허수아비 모드 활성화 여부 (cycle_mode가 True이고 이것도 True면 1분 제한 + 평타)."""
    dummy_mode_enabled: bool = False
    """스킬 라이브러리 — 슬롯 개수와 무관하게 등록된 모든 스킬. 각 항목: id·name·dmg_mult·cooldown_sec·hits·speed_pct·priority·is_movement·enabled_in_cycle."""
    skill_library: list[dict] = field(default_factory=list)
    """바1 슬롯 i 에 배치된 스킬 ID (skill_library의 id). 길이 = slot_count."""
    slot_skill_ids: list[str] = field(default_factory=list)
    """바2(스왑) 슬롯 i 에 배치된 스킬 ID. 길이 = slot_count."""
    swap_slot_skill_ids: list[str] = field(default_factory=list)
    """스킬 속도 일괄 설정값 (%)."""
    global_speed_pct: float = 0.0
    """마지막으로 계산된 딜사이클 rotation (skill_library 인덱스 목록)."""
    last_rotation: list[int] = field(default_factory=list)

    def template_path(self, base: Path | None = None) -> Path:
        root = base or project_root()
        p = Path(self.template_dir)
        if not p.is_absolute():
            p = root / p
        return p


def normalize_slot_priorities(raw: Any, slot_count: int) -> list[int]:
    """슬롯별 발동 우선도: 0=자동(순서대로), 1=최우선 … 7=최후순. 길이는 slot_count.

    구버전 문자열("first"→1, "normal"→0, "last"→7) 하위 호환 지원.
    """
    _legacy = {"first": 1, "high": 1, "우선": 1, "normal": 0, "mid": 0, "보통": 0, "last": 7, "low": 7, "후순": 7}
    out: list[int] = []
    if isinstance(raw, list):
        for x in raw[:slot_count]:
            if isinstance(x, int):
                out.append(max(0, min(7, x)))
            elif isinstance(x, str):
                out.append(_legacy.get(x.strip().lower(), 0))
            else:
                try:
                    out.append(max(0, min(7, int(x))))
                except (ValueError, TypeError):
                    out.append(0)
    while len(out) < slot_count:
        out.append(0)
    return out[:slot_count]


def normalize_slot_skill_enabled(raw: Any, slot_count: int) -> list[bool]:
    out: list[bool] = []
    if isinstance(raw, list):
        for x in raw[:slot_count]:
            out.append(bool(x))
    while len(out) < slot_count:
        out.append(True)
    return out[:slot_count]


def normalize_slot_swap_enabled(raw: Any, slot_count: int) -> list[bool]:
    out: list[bool] = []
    if isinstance(raw, list):
        for x in raw[:slot_count]:
            out.append(bool(x))
    while len(out) < slot_count:
        out.append(False)
    return out[:slot_count]


def normalize_slot_swap_skill_enabled(raw: Any, slot_count: int) -> list[bool]:
    """2라운드 스왑 슬롯 활성 여부. 기본값 True (1라운드와 동일)."""
    out: list[bool] = []
    if isinstance(raw, list):
        for x in raw[:slot_count]:
            out.append(bool(x))
    while len(out) < slot_count:
        out.append(True)
    return out[:slot_count]


def _normalize_skill_keys(keys: Any, slot_count: int) -> list[str]:
    if not isinstance(keys, list) or not keys:
        return _default_keys(slot_count)
    out = [str(x).strip() or "2" for x in keys][:slot_count]
    while len(out) < slot_count:
        out.append("2")
    return out


def load_config(path: Path | None = None) -> AppConfig:
    p = path or default_config_path()
    if not p.is_file():
        return AppConfig()
    try:
        data: dict[str, Any] = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return AppConfig()

    slot_count = int(data.get("slot_count", 7))
    slot_count = max(1, min(7, slot_count))

    roi = data.get("skill_bar_roi")
    if roi is not None and not isinstance(roi, dict):
        roi = None

    keys_raw = data.get("skill_keys")
    if isinstance(keys_raw, list) and len(keys_raw) == 14 and "slot_count" not in data:
        # 구버전: 14키 → 앞 7개만 사용
        keys_raw = keys_raw[:7]
        slot_count = 7
    skill_keys = _normalize_skill_keys(keys_raw, slot_count)
    slot_priorities = normalize_slot_priorities(data.get("slot_priorities"), slot_count)
    slot_skill_enabled = normalize_slot_skill_enabled(data.get("slot_skill_enabled"), slot_count)
    slot_swap_skill_enabled = normalize_slot_swap_skill_enabled(
        data.get("slot_swap_skill_enabled"), slot_count
    )
    slot_swap_priorities = normalize_slot_priorities(
        data.get("slot_swap_priorities"), slot_count
    )

    raw_sw_en = data.get("slot_swap_enabled")
    if isinstance(raw_sw_en, list):
        slot_swap_enabled = normalize_slot_swap_enabled(raw_sw_en, slot_count)
    else:
        migrated = [False] * slot_count
        if bool(data.get("swap_use_alt_slot1", False)) and slot_count >= 1:
            migrated[0] = True
        if bool(data.get("swap_use_alt_slot2", False)) and slot_count >= 2:
            migrated[1] = True
        slot_swap_enabled = normalize_slot_swap_enabled(migrated, slot_count)

    slot_rois_raw = data.get("slot_rois")
    slot_rois: list[dict[str, int]] | None = None
    if isinstance(slot_rois_raw, list) and len(slot_rois_raw) >= slot_count:
        parsed: list[dict[str, int]] = []
        ok = True
        for item in slot_rois_raw[:slot_count]:
            if not isinstance(item, dict):
                ok = False
                break
            try:
                parsed.append(
                    {
                        "left": int(item["left"]),
                        "top": int(item["top"]),
                        "width": int(item["width"]),
                        "height": int(item["height"]),
                    }
                )
            except (KeyError, TypeError, ValueError):
                ok = False
                break
        if ok:
            slot_rois = parsed

    raw_skill_infos = data.get("skill_infos")
    skill_infos_obj = normalize_skill_infos(raw_skill_infos, slot_count)

    # 스킬 라이브러리 로드 (없으면 기존 skill_infos에서 마이그레이션)
    raw_library = data.get("skill_library")
    if isinstance(raw_library, list) and raw_library:
        skill_library = [d for d in raw_library if isinstance(d, dict)]
    else:
        skill_library = []
        for si in skill_infos_obj:
            if si.name or si.cooldown_sec > 0:
                d = si.to_dict()
                d["id"] = new_skill_id()
                skill_library.append(d)

    raw_slot_ids = data.get("slot_skill_ids")
    if isinstance(raw_slot_ids, list):
        slot_skill_ids = [str(x) for x in raw_slot_ids[:slot_count]]
    else:
        lib_ids = [d.get("id", "") for d in skill_library[:slot_count]]
        slot_skill_ids = lib_ids
    while len(slot_skill_ids) < slot_count:
        slot_skill_ids.append("")

    raw_swap_ids = data.get("swap_slot_skill_ids")
    if isinstance(raw_swap_ids, list):
        swap_slot_skill_ids = [str(x) for x in raw_swap_ids[:slot_count]]
    else:
        swap_slot_skill_ids = [""] * slot_count
    while len(swap_slot_skill_ids) < slot_count:
        swap_slot_skill_ids.append("")

    return AppConfig(
        monitor_width=int(data.get("monitor_width", 1920)),
        monitor_height=int(data.get("monitor_height", 1080)),
        mc_width=int(data.get("mc_width", 1920)),
        mc_height=int(data.get("mc_height", 1080)),
        template_dir=str(data.get("template_dir", "templates")),
        swap_key=str(data.get("swap_key", "f")),
        skill_bar_roi=roi,
        slot_count=slot_count,
        skill_keys=skill_keys,
        slot_priorities=slot_priorities,
        slot_skill_enabled=slot_skill_enabled,
        slot_swap_enabled=slot_swap_enabled,
        slot_swap_priorities=slot_swap_priorities,
        slot_swap_skill_enabled=slot_swap_skill_enabled,
        slot_rois=slot_rois,
        match_threshold=float(data.get("match_threshold", 0.88)),
        slot_timeout_sec=float(data.get("slot_timeout_sec", 120.0)),
        poll_interval_ms=int(data.get("poll_interval_ms", 80)),
        post_press_delay_ms=int(data.get("post_press_delay_ms", 60)),
        slot_gap_ms=int(data.get("slot_gap_ms", 120)),
        run_hotkey=str(data.get("run_hotkey", "")),
        auto_swap_enabled=bool(data.get("auto_swap_enabled", False)),
        swap_delay_ms=int(data.get("swap_delay_ms", 450)),
        skill_infos=[si.to_dict() for si in skill_infos_obj],
        cycle_mode_enabled=bool(data.get("cycle_mode_enabled", False)),
        dummy_mode_enabled=bool(data.get("dummy_mode_enabled", False)),
        skill_library=skill_library,
        slot_skill_ids=slot_skill_ids,
        swap_slot_skill_ids=swap_slot_skill_ids,
        global_speed_pct=float(data.get("global_speed_pct", 0.0)),
        last_rotation=[int(x) for x in data.get("last_rotation", []) if isinstance(x, (int, float))],
    )


def save_config(cfg: AppConfig, path: Path | None = None) -> None:
    p = path or default_config_path()
    payload = asdict(cfg)
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def template_filename_for_slot(slot_index: int) -> str:
    """0 기반 슬롯 인덱스 → 파일명."""
    return f"slot_{slot_index + 1:02d}_ready.png"


def template_filename_swap(slot_index: int) -> str:
    """스왑 후 같은 슬롯 위치의 다른 스킬용 PNG (0 기반)."""
    return f"slot_{slot_index + 1:02d}_swap.png"
