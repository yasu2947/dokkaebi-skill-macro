"""스킬바 범위(사각형)를 슬롯 단위로 가로 분할."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Rect:
    left: int
    top: int
    width: int
    height: int

    @property
    def right(self) -> int:
        return self.left + self.width

    @property
    def bottom(self) -> int:
        return self.top + self.height

    def as_mss_dict(self) -> dict[str, int]:
        return {"left": self.left, "top": self.top, "width": self.width, "height": self.height}


def split_horizontal(roi: Rect, slot_count: int) -> list[Rect]:
    """가로를 slot_count 등분. int 나눗셈 누적 오차 대신 경계를 반올림."""
    if slot_count < 1:
        return []
    out: list[Rect] = []
    for i in range(slot_count):
        left_f = roi.left + i * roi.width / slot_count
        right_f = roi.left + (i + 1) * roi.width / slot_count
        left = int(round(left_f))
        right = int(round(right_f))
        w = max(1, right - left)
        out.append(Rect(left, roi.top, w, roi.height))
    return out


def rect_from_dict(d: dict | None) -> Rect | None:
    if not d or not isinstance(d, dict):
        return None
    try:
        return Rect(
            int(d["left"]),
            int(d["top"]),
            int(d["width"]),
            int(d["height"]),
        )
    except (KeyError, TypeError, ValueError):
        return None


def rect_to_dict(r: Rect) -> dict[str, int]:
    return {"left": r.left, "top": r.top, "width": r.width, "height": r.height}


def slot_rects_for_capture(
    slot_rois: list[dict[str, int]] | None,
    skill_bar_roi: dict[str, int] | None,
    slot_count: int,
) -> list[Rect] | None:
    """
    슬롯별 저장 범위가 slot_count개 모두 유효하면 그대로 사용.
    아니면 skill_bar_roi를 가로 균등 분할.
    """
    if slot_rois and len(slot_rois) == slot_count:
        rects: list[Rect] = []
        for d in slot_rois:
            r = rect_from_dict(d)
            if r is None:
                break
            rects.append(r)
        else:
            return rects
    roi = rect_from_dict(skill_bar_roi)
    if roi is None:
        return None
    return split_horizontal(roi, slot_count)
