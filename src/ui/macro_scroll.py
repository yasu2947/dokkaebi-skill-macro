"""스크롤 영역에서 휠이 스핀박스로 새지 않고 항상 스크롤만 되게."""
from __future__ import annotations

from PyQt6.QtGui import QWheelEvent
from PyQt6.QtWidgets import QScrollArea


class MacroScrollArea(QScrollArea):
    """자식 위젯에 포커스가 있어도 휠은 세로 스크롤만 (숫자 필드 값 변화 방지)."""

    def wheelEvent(self, e: QWheelEvent) -> None:
        bar = self.verticalScrollBar()
        delta = e.angleDelta().y()
        if delta == 0:
            e.ignore()
            return
        step = bar.singleStep() * 3
        bar.setValue(bar.value() - (delta // 120) * step)
        e.accept()
