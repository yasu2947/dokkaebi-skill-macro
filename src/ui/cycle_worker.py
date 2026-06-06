"""cycle_worker: macro execution worker.

Modes:
  - Normal (1-cycle / repeat / raid): existing logic
  - Deal Cycle: image-match based rotation (infinite)
  - Training Dummy: deal cycle + 60s limit + left-click fill

Common: key-press confirm + 1 retry on miss.
"""
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
    slot_fired = pyqtSignal(int)  # 0-based

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._stop = False
        # mss.mss() instance ? created once in run(), reused to prevent GDI flash
        self._sct = None
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
        self.slot_priorities: list[int] = []
        self.slot_skill_enabled: list[bool] = []
        self.slot_swap_enabled: list[bool] = []
        self.slot_swap_skill_enabled: list[bool] = []
        self.slot_swap_priorities: list[int] = []
        # deal-cycle mode
        self.cycle_mode: bool = False
        self.dummy_mode: bool = False  # deprecated, kept for compatibility
        self.skill_infos_data: list[dict] = []       # ?1 ??? ?? ??
        self.swap_skill_infos_data: list[dict] = []  # ?2 ??? ?? ??

    def request_stop(self) -> None:
        self._stop = True

    # ?? utilities ?????????????????????????????????????????????????????????????

    def _load_tpl(self, path: Path) -> np.ndarray | None:
        if not path.is_file():
            return None
        arr = cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_COLOR)
        return arr

    def _pri_sort_key(self, p: int, i: int) -> tuple[int, int, int]:
        """0=??(???), 1-6=?? ???, 7=???."""
        if p == 0:
            return (1, 0, i)   # ??: ?? ??, ?? ??? ?
        if p >= 7:
            return (2, p, i)   # ??: ??? ??
        return (0, p, i)       # 1-6: ? ??, ?? ????

    def _order_indices(self, indices: list[int]) -> list[int]:
        return sorted(indices, key=lambda i: self._pri_sort_key(
            self._pri[i] if i < len(self._pri) else 0, i
        ))

    def _order_swap_indices(self, keys: list[int]) -> list[int]:
        return sorted(keys, key=lambda i: self._pri_sort_key(
            self._swap_pri[i] if i < len(self._swap_pri) else 0, i
        ))

    def _skill_on(self, i: int) -> bool:
        en = self.slot_skill_enabled
        return i >= len(en) or bool(en[i])

    def _swap_slot_on(self, i: int) -> bool:
        en = self.slot_swap_enabled
        return i < len(en) and bool(en[i])

    def _swap_skill_on(self, i: int) -> bool:
        en = self.slot_swap_skill_enabled
        return i >= len(en) or bool(en[i])

    def _fire_key_with_confirm(
        self,
        key: str,
        slots: list[Rect],
        slot_idx: int,
        template: np.ndarray,
        gap: float,
    ) -> bool:
        """Press key and re-check image. Retry once if key was missed.

        Returns True if fired (image changed after press), False on key error.
        """
        try:
            tap_key(key)
        except ValueError as ex:
            self.log.emit(f"?? {slot_idx + 1} ? ??: {ex}")
            return False

        time.sleep(max(0.05, self.post_press_delay_ms / 1000.0))

        # re-check: if still ready ? key was missed
        try:
            sub2 = grab_bgr(slots[slot_idx], self._sct)
        except Exception:  # noqa: BLE001
            time.sleep(gap)
            return True  # capture failed ? assume fired

        if match_score(sub2, template) >= self.threshold:
            # missed key ? retry once
            self.log.emit(f"?? {slot_idx + 1} ?? ?? ? ???")
            try:
                tap_key(key)
            except ValueError:
                pass
            time.sleep(max(0.05, self.post_press_delay_ms / 1000.0))

        self.slot_fired.emit(slot_idx)
        time.sleep(gap)
        return True
    # ?? drain pending (normal / auto-swap) ????????????????????????????????????

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
                    sub = grab_bgr(slots[i], self._sct)
                except Exception as ex:  # noqa: BLE001
                    self.log.emit(f"?? ??: {ex}")
                    still.append(i)
                    continue

                score = match_score(sub, templates[i])
                if score >= self.threshold:
                    self.log.emit(f"?? {i + 1} ??? ({key!r})  match={score:.3f}")
                    self._fire_key_with_confirm(key, slots, i, templates[i], gap)
                    fired_any = True
                else:
                    still.append(i)
            cur = self._order_indices(still)
            if cur and not fired_any and not self._stop:
                time.sleep(self.poll_interval_ms / 1000.0)
                if cur:
                    self.log.emit(
                        f"?? ? [{', '.join(str(i + 1) for i in cur)}] ???..."
                    )
        return cur

    # ?? deal cycle / dummy mode ????????????????????????????????????????????????

    def _run_one_bar(
        self,
        active: list[int],
        infos,
        templates: dict[int, np.ndarray],
        next_avail: dict[int, float],
        slots: list[Rect],
        gap: float,
        poll: float,
        deadline: float,
        mode_name: str,
        one_pass: bool = True,
    ) -> None:
        """?? ? ?? ? ??? ?? ?? ?? ??. ?? ??.

        one_pass=True : ? ?? 1?? ?? ? ?? (?? ?? ? ???).
        one_pass=False: deadline?? ?? ??.
        """
        remaining = set(active) if one_pass else None

        while not self._stop and time.monotonic() < deadline:
            if one_pass and not remaining:
                break  # ? ??? ??

            pool = list(remaining) if one_pass else active
            now = time.monotonic()

            # ?? ? ?? ? ??? ? ??
            ready = sorted(
                [i for i in pool if next_avail[i] <= now + 1e-6],
                key=lambda i: self._pri_sort_key(
                    self._pri[i] if i < len(self._pri) else 0, i
                ),
            )

            if not ready:
                # ?? ??? ?? ?? gap ?? ? ? ?? ?? ? ???
                time.sleep(poll)
                continue

            # ??? ??? ??? ??? ??
            fired_this = False
            for target in ready:
                try:
                    sub = grab_bgr(slots[target], self._sct)
                except Exception as ex:  # noqa: BLE001
                    self.log.emit(f"?? ??: {ex}")
                    continue
                score = match_score(sub, templates[target])
                if score >= self.threshold:
                    key = self.skill_keys[target] if target < len(self.skill_keys) else "2"
                    eff_cd = infos[target].effective_cooldown
                    self.log.emit(
                        f"[{mode_name}] ?? {target + 1} ({key!r}) "
                        f"match={score:.3f}  ?={eff_cd:.1f}s"
                    )
                    self._fire_key_with_confirm(key, slots, target, templates[target], gap)
                    if infos[target].is_movement:
                        try:
                            for _ in range(2):
                                tap_key("space")
                                time.sleep(0.02)
                        except Exception:
                            pass
                    next_avail[target] = time.monotonic() + max(eff_cd, gap)
                    if one_pass:
                        remaining.discard(target)  # type: ignore[union-attr]
                    fired_this = True
                    break
            if not fired_this:
                time.sleep(poll)


    def _run_cycle_loop(self, slots: list[Rect]) -> None:
        """???? (??) ?? ???? (60? ??). ?? ?? ??."""
        from src.core.skill_info import compute_rotation, normalize_skill_infos

        n = self.slot_count
        bar1_infos = normalize_skill_infos(self.skill_infos_data, n)
        bar2_infos = normalize_skill_infos(self.swap_skill_infos_data, n)
        gap = max(self.slot_gap_ms, self.post_press_delay_ms) / 1000.0
        poll = self.poll_interval_ms / 1000.0

        bar1_rotation = compute_rotation(bar1_infos, gap)
        bar2_rotation = compute_rotation(bar2_infos, gap) if self.auto_swap else []

        if not bar1_rotation:
            self.log.emit("????: ?1 ?? ?? ?? ? ???? ???? ??? ??? ?????.")
            return

        # ?1 ??? ?? (?? 1)
        bar1_tpl: dict[int, np.ndarray] = {}
        for i in set(bar1_rotation):
            p = self.template_dir / template_filename_for_slot(i)
            t = self._load_tpl(p)
            if t is not None:
                bar1_tpl[i] = t
            else:
                self.log.emit(f"????: ?? {i + 1} ?? 1 ??? ?? ({p.name})")

        bar1_active = [i for i in bar1_rotation if i in bar1_tpl]
        if not bar1_active:
            self.log.emit("????: ?1 ??? ??. ?? ??? ?? 1? ?? ?????.")
            return

        # ?2 ??? ?? (?? 2) ? ?? ?? ON ??
        bar2_tpl: dict[int, np.ndarray] = {}
        if bar2_rotation:
            for i in set(bar2_rotation):
                p = self.template_dir / template_filename_swap(i)
                t = self._load_tpl(p)
                if t is not None:
                    bar2_tpl[i] = t
        bar2_active = [i for i in bar2_rotation if i in bar2_tpl]

        # ??? ??? ??
        bar1_next: dict[int, float] = {i: 0.0 for i in bar1_active}
        bar2_next: dict[int, float] = {i: 0.0 for i in bar2_active}
        swap_key = self.swap_key.strip().lower() or "f"
        swap_wait = max(0, self.swap_delay_ms) / 1000.0

        deadline = float("inf")
        mode_name = "????"

        bar1_str = " ? ".join(
            f"{bar1_infos[i].name or f'??{i+1}'}" for i in bar1_active
        )
        self.log.emit(f"[{mode_name}] ?1: {bar1_str}")
        if bar2_active:
            bar2_str = " ? ".join(
                f"{bar2_infos[i].name or f'??{i+1}'}" for i in bar2_active
            )
            self.log.emit(f"[{mode_name}] ?2: {bar2_str}")

        if not bar2_active:
            self._run_one_bar(
                bar1_active, bar1_infos, bar1_tpl, bar1_next,
                slots, gap, poll, deadline, f"{mode_name}/?1",
                one_pass=False,
            )
        else:
            current_bar = 1

            def _scan(bar_idx: int, now_: float) -> list[int]:
                active_ = bar1_active if bar_idx == 1 else bar2_active
                tpls_   = bar1_tpl   if bar_idx == 1 else bar2_tpl
                next_   = bar1_next  if bar_idx == 1 else bar2_next
                pri_    = self._pri  if bar_idx == 1 else self._swap_pri
                result  = []
                for i in sorted(
                    (x for x in active_ if next_[x] <= now_),
                    key=lambda x: self._pri_sort_key(pri_[x] if x < len(pri_) else 0, x),
                ):
                    try:
                        sc = match_score(grab_bgr(slots[i], self._sct), tpls_[i])
                    except Exception:
                        continue
                    if sc >= self.threshold:
                        result.append(i)
                return result

            def _fire_on(target: int, bar_idx: int) -> None:
                infos_ = bar1_infos if bar_idx == 1 else bar2_infos
                tpls_  = bar1_tpl   if bar_idx == 1 else bar2_tpl
                next_  = bar1_next  if bar_idx == 1 else bar2_next
                key_   = self.skill_keys[target] if target < len(self.skill_keys) else "2"
                eff_cd = infos_[target].effective_cooldown
                self.log.emit(
                    f"[{mode_name}/?{bar_idx}] ??{target+1}"
                    f" ({key_!r})  ?={eff_cd:.1f}s"
                )
                self._fire_key_with_confirm(key_, slots, target, tpls_[target], gap)
                if infos_[target].is_movement:
                    try:
                        for _ in range(2):
                            tap_key("space")
                            time.sleep(0.02)
                    except Exception:
                        pass
                next_[target] = time.monotonic() + max(eff_cd, gap)

            def _swap_to(bar_idx: int) -> bool:
                nonlocal current_bar
                try:
                    tap_key(swap_key)
                    self.log.emit(f"[{mode_name}] ?{bar_idx}? ?? ({swap_key!r})")
                except ValueError as ex:
                    self.log.emit(f"?? ??: {ex}")
                    return False
                time.sleep(swap_wait)
                current_bar = bar_idx
                return True

            while not self._stop and time.monotonic() < deadline:
                now = time.monotonic()
                other = 2 if current_bar == 1 else 1

                # 1) ?? ? ???
                vis = _scan(current_bar, now)
                if vis:
                    _fire_on(vis[0], current_bar)
                    continue

                # 2) ?? ? ??? (?? ?? ?? - ?? ?? ??)
                vis2 = _scan(other, now)
                if vis2:
                    current_bar = other   # ?? ?? ?? ??, ?? ??
                    _fire_on(vis2[0], current_bar)
                    continue

                # 3) ???? ???? ? ?? ? ??? ?? ?? ??
                cur_cd  = any(bar1_next[i] <= now for i in bar1_active) if current_bar == 1                           else any(bar2_next[i] <= now for i in bar2_active)
                oth_cd  = any(bar2_next[i] <= now for i in bar2_active) if current_bar == 1                           else any(bar1_next[i] <= now for i in bar1_active)
                if oth_cd and not cur_cd:
                    _swap_to(other)
                    continue

                # 4) ?? ? ? ? ?? ?? ???? ???? ??
                all_n = [bar1_next[i] for i in bar1_active] + [bar2_next[i] for i in bar2_active]
                soonest = min(all_n) - now
                time.sleep(min(max(0.0, soonest), poll))

        self.log.emit("???? ??.")

    # ?? main run ???????????????????????????????????????????????????????????????

    def run(self) -> None:  # type: ignore[override]
        import mss as _mss
        self._stop = False
        self._pri = normalize_slot_priorities(self.slot_priorities, self.slot_count)
        self._swap_pri = normalize_slot_priorities(
            self.slot_swap_priorities, self.slot_count
        )

        if self.slot_rects is not None and len(self.slot_rects) == self.slot_count:
            slots = self.slot_rects
        else:
            roi = rect_from_dict(self.roi_dict)
            if roi is None:
                self.log.emit("??? ??? ????. ?? ?? ?? ??? ??? ?????.")
                self.finished_ok.emit()
                return
            slots = split_horizontal(roi, self.slot_count)

        self.template_dir.mkdir(parents=True, exist_ok=True)

        # Open mss context once for the entire worker run.
        # Creating a new context per grab() repeatedly initialises Windows GDI DC,
        # which causes visible console flashes.
        with _mss.mss() as sct:
            self._sct = sct
            self._run_inner(slots)
            self._sct = None

        self.finished_ok.emit()

    def _run_inner(self, slots: list[Rect]) -> None:
        """Dispatch to the correct mode. finished_ok is emitted by run() ? do NOT emit here."""

        # ?? deal cycle / dummy ??
        if self.cycle_mode:
            self._run_cycle_loop(slots)
            if self._stop:
                self.log.emit("??? ??.")
            return


        # ?? normal 1-cycle ??
        templates: dict[int, np.ndarray] = {}
        for i in range(self.slot_count):
            tpl_path = self.template_dir / template_filename_for_slot(i)
            tpl = self._load_tpl(tpl_path)
            if tpl is None:
                self.log.emit(f"?? {i + 1}: ??? ?? ({tpl_path.name}) ? ???")
                continue
            templates[i] = tpl

        if not templates:
            self.log.emit("??? ??? ????.")
            return

        pending = self._order_indices(
            [i for i in templates if self._skill_on(i)]
        )
        global_deadline = time.monotonic() + self.slot_timeout_sec
        left = self._drain_pending(slots, templates, pending, global_deadline)

        if self._stop:
            self.log.emit("??? ??.")
            return
        if left:
            self.log.emit(
                f"?? [{', '.join(str(i + 1) for i in left)}]: ?? ?? ? ?? ? ?."
            )
            self.log.emit("1??? ??.")
            return

        # ?? auto-swap round 2 ??
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
                        f"?? ??: ?? {i + 1} ? {p.name} ?? (?? ? ??)"
                    )

            if tpl2:
                try:
                    self.log.emit(
                        f"?? ? ({sk!r}) ?? ? {self.swap_delay_ms}ms ?? ? 2???"
                    )
                    tap_key(sk)
                except ValueError as ex:
                    self.log.emit(f"?? ? ??: {ex}")
                else:
                    entered_swap_round2 = True
                    time.sleep(max(0, self.swap_delay_ms) / 1000.0)
                    pending2 = self._order_swap_indices(list(tpl2.keys()))
                    dl2 = time.monotonic() + self.slot_timeout_sec
                    left2 = self._drain_pending(slots, tpl2, pending2, dl2)
                    if self._stop:
                        self.log.emit("??? ??.")
                    elif left2:
                        self.log.emit(
                            f"[?? ?] ?? [{', '.join(str(i + 1) for i in left2)}]: "
                            "?? ?? ? ?? ? ?."
                        )
            elif any(self._swap_slot_on(i) for i in range(self.slot_count)):
                self.log.emit(
                    "?? ??: ?? ?? ??? ??? swap PNG? ?? 2???? ?????."
                )

        if entered_swap_round2 and not self._stop:
            try:
                self.log.emit("?? ??? ??: ?? ? ? ? ? ??")
                tap_key(sk)
                time.sleep(max(0, self.swap_delay_ms) / 1000.0)
            except ValueError as ex:
                self.log.emit(f"?? ?? ? ??: {ex}")

        if not self._stop:
            self.log.emit("1??? ??.")
