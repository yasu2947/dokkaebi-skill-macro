"""포커스 없을 때 휠로 값이 바뀌지 않도록 (스크롤 영역 내 스핀박스)."""
from __future__ import annotations

from PyQt6.QtGui import QWheelEvent
from PyQt6.QtWidgets import QDoubleSpinBox, QSpinBox


class NoWheelSpinBox(QSpinBox):
    def wheelEvent(self, e: QWheelEvent) -> None:
        if not self.hasFocus():
            e.ignore()
            return
        super().wheelEvent(e)


class NoWheelDoubleSpinBox(QDoubleSpinBox):
    def wheelEvent(self, e: QWheelEvent) -> None:
        if not self.hasFocus():
            e.ignore()
            return
        super().wheelEvent(e)
