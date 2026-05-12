"""슬롯 ①·②차 우선순위 — QComboBox / QMenu 없이 단일 버튼 순환.

EXE에서 QComboBox 드롭용 QFrame·QToolButton 연동 QMenu가 cold init에
top-level 로 잡혀 작은 창 깜빡임이 날 수 있음. 팝업 없이 QPushButton만 사용.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QPushButton, QWidget

_KEYS: tuple[str, ...] = ("first", "normal", "last")
_LABELS: dict[str, str] = {"first": "우선", "normal": "보통", "last": "후순"}


class SlotPriorityMenuButton(QPushButton):
    """클릭 시 우선 → 보통 → 후순 순환. currentData / setCurrentKey 호환."""

    valueChanged = pyqtSignal()

    def __init__(self, object_name: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName(object_name)
        self._idx: int = 1  # normal
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(
            "①차·②차 우선순위. 클릭할 때마다 「우선 → 보통 → 후순」 순으로 바뀝니다."
        )
        self.clicked.connect(self._on_click)
        self._sync_text()

    def _on_click(self) -> None:
        self._idx = (self._idx + 1) % 3
        self._sync_text()
        self.valueChanged.emit()

    def _sync_text(self) -> None:
        key = _KEYS[self._idx]
        self.setText(_LABELS[key])

    def currentData(self) -> str | None:
        return _KEYS[self._idx]

    def setCurrentKey(self, key: str) -> None:
        if key in _KEYS:
            self._idx = _KEYS.index(key)
        else:
            self._idx = 1
        self._sync_text()

    def hidePopup(self) -> None:
        """QComboBox 호환 — 팝업 없음."""
        pass
