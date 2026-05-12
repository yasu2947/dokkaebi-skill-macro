"""Qt 전역 논리 좌표 → mss 물리 픽셀 사각형."""
from __future__ import annotations

import mss
from PyQt6.QtCore import QRect
from PyQt6.QtGui import QGuiApplication


def logical_global_rect_to_mss_physical(r: QRect) -> QRect:
    """
    ROI 피커의 전역 논리 좌표를 mss 캡처 좌표로 변환.

    - 단순히 left/top에 DPR를 곱하면 멀티 모니터에서 기준점이 틀어져
      슬롯이 옆으로 밀린 캡처가 나올 수 있습니다.
    - Qt `QScreen.geometry()`(논리)와 같은 인덱스의 `mss.monitors[i+1]`(물리)의
      가로·세로 비율로, **해당 화면 안에서의 상대 위치**를 매핑합니다.
    """
    if r.isNull() or not r.isValid():
        return r

    c = r.center()
    screen = QGuiApplication.screenAt(c) or QGuiApplication.primaryScreen()
    if screen is None:
        return r

    g = screen.geometry()
    qt_screens = QGuiApplication.screens()
    try:
        idx = qt_screens.index(screen)
    except ValueError:
        idx = 0

    with mss.mss() as sct:
        mons = sct.monitors[1:]
        if not mons:
            return r
        m = mons[idx] if idx < len(mons) else mons[0]

    sx = m["width"] / max(1, g.width())
    sy = m["height"] / max(1, g.height())

    rel_l = r.left() - g.left()
    rel_t = r.top() - g.top()
    phys_l = int(round(m["left"] + rel_l * sx))
    phys_t = int(round(m["top"] + rel_t * sy))
    phys_w = int(max(1, round(r.width() * sx)))
    phys_h = int(max(1, round(r.height() * sy)))
    return QRect(phys_l, phys_t, phys_w, phys_h)
