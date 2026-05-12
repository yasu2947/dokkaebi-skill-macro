"""전체 화면 드래그로 ROI 선택."""
from __future__ import annotations

from PyQt6.QtCore import QPoint, QRect, Qt
from PyQt6.QtGui import QColor, QCursor, QGuiApplication, QMouseEvent, QPainter, QPen
from PyQt6.QtWidgets import QDialog, QWidget

from src.ui.screen_coords import logical_global_rect_to_mss_physical


class RoiPickerDialog(QDialog):
    """반투명 오버레이에서 드래그 사각형 선택 후 화면 좌표 QRect 반환."""

    def __init__(self, screen_geo: QRect, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        # 부모가 있을 때 Tool 을 같이 쓰면 Windows DWM 에서 잠깐 제목줄만 있는 유령 창이
        # 뜨는 사례가 있어, 오버레이는 최상위일 때만 Tool 로 태스크바에 안 남깁니다.
        flags = (
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        if parent is None:
            flags |= Qt.WindowType.Tool
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setGeometry(screen_geo)
        self._start: QPoint | None = None
        self._current: QPoint | None = None
        self._result: QRect | None = None
        self.setCursor(Qt.CursorShape.CrossCursor)

    def result_rect(self) -> QRect | None:
        return self._result

    def mousePressEvent(self, e: QMouseEvent) -> None:
        if e.button() == Qt.MouseButton.LeftButton:
            self._start = e.globalPosition().toPoint()
            self._current = self._start
            self.update()

    def mouseMoveEvent(self, e: QMouseEvent) -> None:
        if self._start is not None:
            self._current = e.globalPosition().toPoint()
            self.update()

    def mouseReleaseEvent(self, e: QMouseEvent) -> None:
        if e.button() == Qt.MouseButton.LeftButton and self._start is not None:
            end = e.globalPosition().toPoint()
            r = QRect(self._start, end).normalized()
            if r.width() >= 4 and r.height() >= 4:
                self._result = r
                self.accept()
            else:
                self._start = None
                self._current = None
                self.update()

    def keyPressEvent(self, e) -> None:  # type: ignore[override]
        if e.key() == Qt.Key.Key_Escape:
            self.reject()

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(0, 0, 0, 120))
        if self._start is not None and self._current is not None:
            g1 = self.mapFromGlobal(self._start)
            g2 = self.mapFromGlobal(self._current)
            r = QRect(g1, g2).normalized()
            p.fillRect(r, QColor(85, 167, 255, 55))
            pen = QPen(QColor("#55a7ff"))
            pen.setWidth(2)
            p.setPen(pen)
            p.drawRect(r)


def pick_roi_fullscreen(parent: QWidget | None = None) -> QRect | None:
    """커서가 있는 화면에서 ROI 선택. 취소 시 None.

    parent: 메인 창 등을 넘기면 오버레이가 앱에 묶여 Windows 유령/깜빡 창이 줄어듭니다.
    """
    pos = QCursor.pos()
    screen = QGuiApplication.screenAt(pos) or QGuiApplication.primaryScreen()
    if screen is None:
        return None
    geo = screen.geometry()
    dlg = RoiPickerDialog(geo, parent=parent)
    if dlg.exec() != QDialog.DialogCode.Accepted:
        return None
    r = dlg.result_rect()
    if r is None:
        return None
    # mss는 모니터 물리 픽셀 기준 — HiDPI에서 Qt 전역 좌표와 불일치 보정
    return logical_global_rect_to_mss_physical(r)
