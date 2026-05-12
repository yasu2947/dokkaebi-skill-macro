"""접기/펼치기 섹션."""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QToolButton, QVBoxLayout, QWidget


class CollapsibleSection(QWidget):
    def __init__(self, title: str, content: QWidget, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._title = title
        self._content = content
        self._toggle = QToolButton(self)
        self._toggle.setText(f"▼  {title}")
        self._toggle.setCheckable(True)
        self._toggle.setChecked(True)
        self._toggle.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self._toggle.setStyleSheet(
            "QToolButton { color: #e9d5ff; font-weight: 900; font-size: 13px; "
            "border: none; padding: 6px 4px; text-align: left; }"
            "QToolButton:hover { color: #fef3c7; }"
        )
        self._toggle.toggled.connect(self._on_toggled)

        head = QHBoxLayout()
        head.addWidget(self._toggle, 1)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        lay.addLayout(head)
        lay.addWidget(self._content)

    def _on_toggled(self, checked: bool) -> None:
        self._content.setVisible(checked)
        self._toggle.setText(f"▼  {self._title}" if checked else f"▶  {self._title}")
