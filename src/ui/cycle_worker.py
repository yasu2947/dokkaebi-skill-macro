"""1사이클: 준비된 슬롯을 순서대로 발동, 미발동 슬롯은 재시도. 옵션: 자동 스왑 2라운드."""
from __future__ import annotations

import time
from pathlib import Path

import cv2
import numpy as np
from PyQt6.QtCore import QObject, QThread, pyqtSignal

from src.core.capture import grab_bgr
from src.core.config import (
    normalize_slot_priorities,
    template_filename_for_slot,
    template_filename_swap,
)
from src.core.keyparse import tap_key
from src.core.matcher import match_score
from src.core.regions import Rect, rect_from_dict, split_horizontal


class CycleWorker(QThread):
    log = pyqtSignal(str)
    finished_ok = pyqtSignal()
    slot_fired = pyqtSignal(int)  # 0 기반

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._stop = False
        self.roi_dict: dict[str, int] | None = None
        self.slot_count: int = 7
        self.skill_keys: list[str] = []
        self.template_dir: Path = Path(".")
        self.threshold: float = 0.88
        self.slot_timeout_sec: float = 120.0
        self.poll_interval_ms: int = 80
        self.post_press_delay_ms: int = 120
        self.slot_gap_ms: int = 200
        self.slot_rects: list[Rect] | None = None
        self.swap_key: str = "f"
        self.auto_swap: bool = False
        self.swap_delay_ms: int = 450
        self.slot_priorities: list[str] = []
        self.slot_skill_enabled: list[bool] = []
        self.slot_swap_enabled: list[bool] = []
        self.slot_swap_skill_enabled: list[bool] = []
        self.slot_swap_priorities: list[str] = []
        self._swap_pri_norm: list[str] = []
        self.raid_mode: bool = False
        self.raid_idle_sec: float = 3.0

    def request_stop(self) -> None:
        self._stop = True

    def _load_tpl(self, path: Path) -> np.ndarray | None:
        if not path.is_file():
            return None
        arr = cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_COLOR)
        return arr

    def _tier_rank(self, i: int) -> int:
        t = self._pri[i] if i < len(self._pri) else "normal"
        return {"first": 0, "normal": 1, "last": 2}.get(t, 1)

    def _order_indices(self, indices: list[int]) -> list[int]:
        return sorted(indices, key=lambda i: (self._tier_rank(i), i))

    def _tier_swap(self, i: int) -> int:
        t = self._swap_pri_norm[i] if i < len(self._swap_pri_norm) else "normal"
        return {"first": 0, "normal": 1, "last": 2}.get(t, 1)

    def _order_swap_indices(self, keys: list[int]) -> list[int]:
        return sorted(keys, key=lambda i: (self._tier_swap(i), i))

    def _skill_on(self, i: int) -> bool:
        en = self.slot_skill_enabled
        return i >= len(en) or bool(en[i])

    def _swap_slot_on(self, i: int) -> bool:
        en = self.slot_swap_enabled
        return i < len(en) and bool(en[i])

    def _swap_skill_on(self, i: int) -> bool:
        """2라운드 스왑 PNG 발동 여부 — slot_swap_skill_enabled, 없으면 True."""
        en = self.slot_swap_skill_enabled
        return i >= len(en) or bool(en[i])

    def _templates_for_raid(self, swapped: bool) -> dict[int, np.ndarray]:
        tpl: dict[int, np.ndarray] = {}
        for i in range(self.slot_count):
            if swapped:
                if not self._swap_slot_on(i) or not self._swap_skill_on(i):
                    continue
                p = self.template_dir / template_filename_swap(i)
            else:
                if not self._skill_on(i):
                    continue
                p = self.template_dir / template_filename_for_slot(i)
            t = self._load_tpl(p)
            if t is not None:
                tpl[i] = t
        return tpl

    def _do_swap(self, sk: str, swapped: bool) -> bool:
        """스왑 키를 누르고 swapped 상태를 반전. 성공하면 True."""
        try:
            tap_key(sk)
            time.sleep(max(0, self.swap_delay_ms) / 1000.0)
            return True
        except ValueError as ex:
            self.log.emit(f"스왑 키 오류: {ex}")
            return False

    def _run_raid_loop(self, slots: list[Rect]) -> None:
        self.template_dir.mkdir(parents=True, exist_ok=True)
        swapped = False
        last_fire: float | None = None
        fired_set: set[int] = set()  # 현재 바에서 이번 사이클에 발동된 슬롯
        poll = self.poll_interval_ms / 1000.0
        gap = max(self.slot_gap_ms, self.post_press_delay_ms) / 1000.0
        sk = self.swap_key.strip().lower() or "f"
        idle = max(0.1, float(self.raid_idle_sec))

        self.log.emit(f"레이드 모드 (유휴 {idle:.1f}s → 스왑) — 중단은 실행 키 또는 [중단]")

        while not self._stop:
            templates = self._templates_for_raid(swapped)
            if not templates:
                self.log.emit("레이드: 현재 바에 매칭 가능한 템플릿이 없습니다. 잠시 대기…")
                time.sleep(poll)
                if last_fire is not None and (time.monotonic() - last_fire) >= idle:
                    self.log.emit("레이드: 템플릿 없음 상태 유지 → 스왑 시도")
                    if self._do_swap(sk, swapped):
                        swapped = not swapped
                        fired_set = set()
                        last_fire = time.monotonic()
                continue

            all_slot_indices = set(templates.keys())

            if swapped:
                ordered = self._order_swap_indices(list(templates.keys()))
            else:
                ordered = self._order_indices(list(templates.keys()))

            fired = False
            for i in ordered:
                if i in fired_set:
                    continue
                if self._stop:
                    return
                try:
                    sub = grab_bgr(slots[i])
                except Exception as ex:  # noqa: BLE001
                    self.log.emit(f"캡처 오류: {ex}")
                    time.sleep(poll)
                    break
                score = match_score(sub, templates[i])
                if score >= self.threshold:
                    key = self.skill_keys[i] if i < len(self.skill_keys) else "2"
                    try:
                        tap_key(key)
                    except ValueError as ex:
                        self.log.emit(f"슬롯 {i + 1} 키 오류: {ex}")
                        continue
                    self.log.emit(
                        f"레이드 슬롯 {i + 1} ({key!r}) match={score:.3f} bar={'스왑' if swapped else '준비'}"
                    )
                    self.slot_fired.emit(i)
                    fired_set.add(i)
                    last_fire = time.monotonic()
                    fired = True
                    time.sleep(gap)
                    break

            # 모든 슬롯이 이번 사이클에 발동됐으면 즉시 스왑
            if all_slot_indices.issubset(fired_set):
                self.log.emit("레이드: 모든 슬롯 발동 완료 → 즉시 스왑")
                if self._do_swap(sk, swapped):
                    swapped = not swapped
                    fired_set = set()
                    last_fire = time.monotonic()
                continue

            if fired:
                continue

            time.sleep(poll)
            # 아직 발동 못한 슬롯이 있으나 idle 동안 발동 없으면 스왑 (쿨타임 대기 상태)
            if last_fire is not None and (time.monotonic() - last_fire) >= idle:
                self.log.emit(f"레이드: {idle:.1f}s 동안 발동 없음 → 스왑")
                if self._do_swap(sk, swapped):
                    swapped = not swapped
                    fired_set = set()
                    last_fire = time.monotonic()

    def _drain_pending(
        self,
        slots: list[Rect],
        templates: dict[int, np.ndarray],
        pending: list[int],
        global_deadline: float,
    ) -> list[int]:
        gap = max(self.slot_gap_ms, self.post_press_delay_ms) / 1000.0
        cur = self._order_indices(list(pending))
        while cur and not self._stop and time.monotonic() < global_deadline:
            still: list[int] = []
            fired_any = False
            for i in cur:
                if self._stop:
                    break
                if i not in templates:
                    continue
                key = self.skill_keys[i] if i < len(self.skill_keys) else "2"
                try:
                    sub = grab_bgr(slots[i])
                except Exception as ex:  # noqa: BLE001
                    self.log.emit(f"캡처 오류: {ex}")
                    still.append(i)
                    continue

                score = match_score(sub, templates[i])
                if score >= self.threshold:
                    try:
                        tap_key(key)
                    except ValueError as ex:
                        self.log.emit(f"슬롯 {i + 1} 키 오류: {ex}")
                        continue
                    self.log.emit(f"슬롯 {i + 1} 발동 ({key!r})  match={score:.3f}")
                    self.slot_fired.emit(i)
                    fired_any = True
                    time.sleep(gap)
                else:
                    still.append(i)
            cur = self._order_indices(still)
            if cur and not fired_any and not self._stop:
                time.sleep(self.poll_interval_ms / 1000.0)
                if cur:
                    self.log.emit(
                        f"미발동 슬롯 [{', '.join(str(i + 1) for i in cur)}] 재시도…"
                    )
        return cur

    def run(self) -> None:  # type: ignore[override]
        self._stop = False
        self._pri = normalize_slot_priorities(self.slot_priorities, self.slot_count)
        self._swap_pri_norm = normalize_slot_priorities(
            self.slot_swap_priorities, self.slot_count
        )

        if self.slot_rects is not None and len(self.slot_rects) == self.slot_count:
            slots = self.slot_rects
        else:
            roi = rect_from_dict(self.roi_dict)
            if roi is None:
                self.log.emit("스킬바 범위가 없습니다. 막대 범위 또는 슬롯별 영역을 지정하세요.")
                self.finished_ok.emit()
                return
            slots = split_horizontal(roi, self.slot_count)

        self.template_dir.mkdir(parents=True, exist_ok=True)

        if self.raid_mode:
            self._run_raid_loop(slots)
            if self._stop:
                self.log.emit("사용자 중단.")
            self.finished_ok.emit()
            return

        templates: dict[int, np.ndarray] = {}
        for i in range(self.slot_count):
            tpl_path = self.template_dir / template_filename_for_slot(i)
            tpl = self._load_tpl(tpl_path)
            if tpl is None:
                self.log.emit(f"슬롯 {i + 1}: 템플릿 없음 ({tpl_path.name}) — 건너뜀")
                continue
            templates[i] = tpl

        if not templates:
            self.log.emit("처리할 슬롯이 없습니다.")
            self.finished_ok.emit()
            return

        pending = self._order_indices(
            [i for i in templates if self._skill_on(i)]
        )
        global_deadline = time.monotonic() + self.slot_timeout_sec
        left = self._drain_pending(slots, templates, pending, global_deadline)

        if self._stop:
            self.log.emit("사용자 중단.")
            self.finished_ok.emit()
            return
        if left:
            self.log.emit(
                f"슬롯 [{', '.join(str(i + 1) for i in left)}]: 대기 시간 내 준비 안 됨."
            )
            self.log.emit("1사이클 종료.")
            self.finished_ok.emit()
            return

        # ── 자동 스왑 2라운드 (스왑 켠 슬롯만 swap PNG) ───────────────────────
        sk = self.swap_key.strip().lower() or "f"
        entered_swap_round2 = False
        if self.auto_swap:
            tpl2: dict[int, np.ndarray] = {}
            for i in range(self.slot_count):
                if not self._swap_slot_on(i) or not self._swap_skill_on(i):
                    continue
                p = self.template_dir / template_filename_swap(i)
                t = self._load_tpl(p)
                if t is not None:
                    tpl2[i] = t
                else:
                    self.log.emit(
                        f"자동 스왑: 슬롯 {i + 1} — {p.name} 없음 (해당 칸 생략)"
                    )

            if tpl2:
                try:
                    self.log.emit(
                        f"스왑 키 ({sk!r}) 입력 → {self.swap_delay_ms}ms 대기 후 2라운드"
                    )
                    tap_key(sk)
                except ValueError as ex:
                    self.log.emit(f"스왑 키 오류: {ex}")
                else:
                    entered_swap_round2 = True
                    time.sleep(max(0, self.swap_delay_ms) / 1000.0)
                    pending2 = self._order_swap_indices(list(tpl2.keys()))
                    dl2 = time.monotonic() + self.slot_timeout_sec
                    left2 = self._drain_pending(slots, tpl2, pending2, dl2)
                    if self._stop:
                        self.log.emit("사용자 중단.")
                    elif left2:
                        self.log.emit(
                            f"[스왑 후] 슬롯 [{', '.join(str(i + 1) for i in left2)}]: "
                            "대기 시간 내 준비 안 됨."
                        )
            elif any(self._swap_slot_on(i) for i in range(self.slot_count)):
                self.log.emit(
                    "자동 스왑: 스왑 사용 슬롯에 유효한 swap PNG가 없어 2라운드를 건너뜁니다."
                )

        if entered_swap_round2 and not self._stop:
            try:
                self.log.emit("원래 스킬바 복귀: 스왑 키 한 번 더 입력")
                tap_key(sk)
                time.sleep(max(0, self.swap_delay_ms) / 1000.0)
            except ValueError as ex:
                self.log.emit(f"스왑 복귀 키 오류: {ex}")

        if not self._stop:
            self.log.emit("1사이클 종료.")
        self.finished_ok.emit()
