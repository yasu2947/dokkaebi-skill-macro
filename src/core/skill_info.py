"""스킬 정보 데이터클래스 + 딜사이클 계산 알고리즘."""
from __future__ import annotations

import math
import uuid
from dataclasses import asdict, dataclass
from typing import Any


def new_skill_id() -> str:
    """스킬 라이브러리용 고유 ID 생성 (8자 hex)."""
    return uuid.uuid4().hex[:8]

_MAX_PRIORITY = 7  # 슬롯 최대치

# ── 우선도 변환 헬퍼 (UI string ↔ 내부 int) ─────────────────────────────────

def priority_str_to_int(s: str) -> int:
    """UI 버튼 키(first/normal/last) → 내부 int."""
    return {"first": 1, "normal": 0, "last": _MAX_PRIORITY}.get(s, 0)


def priority_int_to_str(n: int) -> str:
    """내부 int → UI 버튼 키."""
    if n == 1:
        return "first"
    if n >= _MAX_PRIORITY:
        return "last"
    return "normal"


@dataclass
class SkillInfo:
    name: str = ""
    dmg_mult: float = 1.0
    cooldown_sec: float = 0.0
    hits: int = 1
    speed_pct: float = 0.0
    enabled_in_cycle: bool = True
    """사용자 지정 우선도 (1=최우선 … 7=최후순, 0=자동/미설정)."""
    priority: int = 0
    """이동기 여부 — True이면 rotation 맨 뒤로."""
    is_movement: bool = False

    @property
    def effective_cooldown(self) -> float:
        """10초 쿨 + 18% 스킬속도 → 10 * (1 - 0.18) = 8.2초."""
        return max(0.0, self.cooldown_sec * (1.0 - self.speed_pct / 100.0))

    @property
    def dps_weight(self) -> float:
        cd = self.effective_cooldown
        return (self.dmg_mult * self.hits / cd) if cd > 0 else 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "SkillInfo":
        return cls(
            name=str(d.get("name", "")),
            dmg_mult=float(d.get("dmg_mult", 1.0)),
            cooldown_sec=float(d.get("cooldown_sec", 0.0)),
            hits=int(d.get("hits", 1)),
            speed_pct=float(d.get("speed_pct", 0.0)),
            enabled_in_cycle=bool(d.get("enabled_in_cycle", True)),
            priority=int(d.get("priority", 0)),
            is_movement=bool(d.get("is_movement", False)),
        )


def normalize_skill_infos(raw: Any, slot_count: int) -> list[SkillInfo]:
    """config 로드 시 skill_infos 필드를 SkillInfo 리스트로 정규화."""
    result: list[SkillInfo] = []
    if isinstance(raw, list):
        for item in raw[:slot_count]:
            if isinstance(item, dict):
                result.append(SkillInfo.from_dict(item))
            else:
                result.append(SkillInfo())
    while len(result) < slot_count:
        result.append(SkillInfo())
    return result[:slot_count]


def _sort_key(info: SkillInfo, slot_idx: int) -> tuple:
    """딜사이클 정렬 키.

    1순위: 이동기 여부 (이동기=후순위)
    2순위: 사용자 우선도 (1이 가장 높음, 0=미설정은 DPS로 결정)
    3순위: DPS 가중치 내림차순
    4순위: 슬롯 번호 오름차순
    """
    is_move = 1 if info.is_movement else 0
    if info.priority > 0:
        pri = info.priority
    else:
        # 0=미설정 → DPS로 역산 (DPS 높을수록 우선도 높음 → 작은 숫자)
        pri = _MAX_PRIORITY + 1
    dps_inv = -info.dps_weight
    return (is_move, pri, dps_inv, slot_idx)


def apply_recommended_priorities(infos: list[SkillInfo]) -> list[SkillInfo]:
    """DPS 기준으로 모든 스킬에 순위(1=최우선, 2, 3…)를 자동 배정.

    - 비이동기: DPS 높은 순으로 1, 2, 3 … (최대 6)
    - 이동기: 비이동기 개수+1 (맨 뒤)
    원본 리스트를 수정하지 않고 새 리스트를 반환.
    """
    result = [SkillInfo.from_dict(info.to_dict()) for info in infos]
    eligible = [
        i for i, info in enumerate(result)
        if info.enabled_in_cycle and info.effective_cooldown > 0
    ]
    if not eligible:
        return result

    non_move = sorted(
        [i for i in eligible if not result[i].is_movement],
        key=lambda i: (-result[i].dps_weight, i),
    )
    move_idxs = [i for i in eligible if result[i].is_movement]

    for rank, idx in enumerate(non_move):
        result[idx].priority = rank + 1  # 1=최우선, 2, 3 … (상한 없음)

    move_pri = len(non_move) + 1
    for idx in move_idxs:
        result[idx].priority = move_pri  # 이동기는 비이동기 다음 순위

    return result


def compute_rotation(infos: list[SkillInfo], slot_gap_sec: float) -> list[int]:
    """Greedy scheduler: 우선도 + 이동기 플래그 + DPS 기반 딜사이클 순서 반환.

    - enabled_in_cycle=True & cooldown_sec > 0 인 슬롯만 포함.
    - 이동기(is_movement=True) 슬롯은 다른 슬롯보다 항상 후순위.
    - priority > 0 이면 해당 숫자 순서대로 (1=최우선).
    - priority == 0 이면 DPS 가중치 기준 자동 결정.
    - 쿨 대기 중에도 우선도 높은 스킬 먼저 기다림.
    - 유효 슬롯이 없으면 빈 리스트 반환.
    """
    eligible = [
        i for i, info in enumerate(infos)
        if info.enabled_in_cycle and info.effective_cooldown > 0
    ]
    if not eligible:
        return []

    # 우선도 기준 정적 순서 (쿨 동시 회복 시 이 순서로 발동)
    static_order = sorted(eligible, key=lambda i: _sort_key(infos[i], i))

    gap = max(0.0, slot_gap_sec)
    next_avail = {i: 0.0 for i in eligible}
    use_count = {i: 0 for i in eligible}

    target_uses = 2
    max_steps = len(eligible) * target_uses * 20
    rotation: list[int] = []
    t = 0.0

    for _ in range(max_steps):
        if all(use_count[i] >= target_uses for i in eligible):
            break

        # 현재 시각에 쿨 돌아온 슬롯 → static_order 기준으로 가장 높은 우선도 선택
        ready = [i for i in static_order if next_avail[i] <= t + 1e-6]
        if ready:
            best = ready[0]  # static_order가 이미 우선도 순이므로 첫 번째
            rotation.append(best)
            use_count[best] += 1
            next_avail[best] = t + infos[best].effective_cooldown
            t += gap
        else:
            # 모두 쿨 중 → 가장 우선도 높은(static_order 앞) 슬롯 기준으로 대기
            t = min(next_avail[i] for i in eligible)

    # 한 주기(모든 슬롯이 처음 등장하는 구간)만 추출
    seen: set[int] = set()
    one_cycle: list[int] = []
    for idx in rotation:
        if idx not in seen:
            seen.add(idx)
            one_cycle.append(idx)
        if seen == set(eligible):
            break

    return one_cycle if len(one_cycle) == len(eligible) else rotation


def rotation_summary(infos: list[SkillInfo], rotation: list[int]) -> str:
    """사람이 읽기 좋은 딜사이클 요약 문자열."""
    if not rotation:
        return "(스킬 정보 미설정 또는 활성 슬롯 없음)"
    parts = []
    for idx in rotation:
        if idx < len(infos):
            info = infos[idx]
            label = info.name or f"슬롯{idx + 1}"
            tag = " [이동기]" if info.is_movement else ""
            parts.append(f"{label}{tag}")
        else:
            parts.append(f"슬롯{idx + 1}")
    return " → ".join(parts)


def slot_placement_recommendation(
    infos: list[SkillInfo],
    rotation: list[int],
) -> str:
    """딜사이클 순서 기반 스왑 최소화 배치 추천.

    - 스왑 없이 한 바에 모두 들어가면 그렇게 안내.
    - 스왑이 필요한 경우 rotation 앞부분→1바, 나머지→2바로 나눠 추천.
      (연속으로 쓰는 스킬끼리 같은 바에 두어야 스왑 도중 놓치지 않음)
    """
    if not rotation:
        return ""

    def _name(i: int) -> str:
        if i < len(infos):
            return infos[i].name or f"슬롯{i + 1}"
        return f"슬롯{i + 1}"

    n = len(rotation)
    # 4개 이하면 한 바로 충분
    if n <= 4:
        names = " → ".join(_name(i) for i in rotation)
        return f"스왑 불필요 — 전체 1바 배치\n  1바: {names}"

    # 이동기는 마지막에 배치하는 게 일반적으로 유리 → rotation 이미 반영됨
    # 앞 절반(ceil)을 1바, 나머지를 2바로 분리
    split = math.ceil(n / 2)
    bar1 = rotation[:split]
    bar2 = rotation[split:]

    bar1_names = ", ".join(_name(i) for i in bar1)
    bar2_names = ", ".join(_name(i) for i in bar2)
    swap_after = _name(bar1[-1])
    swap_before = _name(bar2[0])

    lines = [
        "※ 스왑이 있을 경우 아래 배치를 추천합니다.",
        f"  1바: {bar1_names}",
        f"  2바: {bar2_names}",
        f"  스왑 타이밍: 「{swap_after}」 사용 직후 → 스왑 → 「{swap_before}」",
        "  (쿨이 긴 스킬은 2바에 배치해 스왑 중 기다리게 하면 손실 최소화)",
    ]
    return "\n".join(lines)
