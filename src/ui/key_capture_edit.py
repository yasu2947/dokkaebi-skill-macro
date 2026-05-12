"""클릭 후 키·마우스 버튼을 눌러 문자열로 할당 (직접 타이핑 없음)."""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFocusEvent, QKeyEvent, QMouseEvent
from PyQt6.QtWidgets import QLineEdit, QStyle


class KeyCaptureEdit(QLineEdit):
    """readOnly + 왼쪽 클릭으로 무장 후, 다음 입력 한 번만 기록."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setReadOnly(True)
        self.setClearButtonEnabled(False)
        self.setPlaceholderText("클릭 후 키 또는 마우스 버튼")
        self._armed = False
        self._ignore_left_release = False

    def setArmed(self, on: bool) -> None:
        self._armed = on
        if on:
            self.setPlaceholderText("입력 대기… Esc 취소")
            self.setProperty("armed", True)
        else:
            self.setPlaceholderText("클릭 후 키 또는 마우스 버튼")
            self.setProperty("armed", False)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def mousePressEvent(self, e: QMouseEvent) -> None:
        if e.button() == Qt.MouseButton.LeftButton:
            if not self._armed:
                self.setArmed(True)
                self._ignore_left_release = True
            self.setFocus(Qt.FocusReason.MouseFocusReason)
            e.accept()
            return
        super().mousePressEvent(e)

    def focusOutEvent(self, e: QFocusEvent) -> None:
        if self._armed:
            self.setArmed(False)
            self._ignore_left_release = False
        super().focusOutEvent(e)

    def keyPressEvent(self, e: QKeyEvent) -> None:
        if not self._armed:
            return super().keyPressEvent(e)

        if e.key() == Qt.Key.Key_Escape:
            self.setArmed(False)
            self._ignore_left_release = False
            e.accept()
            return

        mods = e.modifiers()
        bad = mods & (
            Qt.KeyboardModifier.ControlModifier
            | Qt.KeyboardModifier.AltModifier
            | Qt.KeyboardModifier.MetaModifier
        )
        if bad:
            e.accept()
            return

        key = e.key()
        text = e.text()

        spec: str | None = None

        if key == Qt.Key.Key_Space:
            spec = "space"
        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            spec = "enter"
        elif key == Qt.Key.Key_Tab:
            self.setArmed(False)
            self._ignore_left_release = False
            super().keyPressEvent(e)
            return
        elif key == Qt.Key.Key_Backspace:
            spec = "backspace"
        elif key == Qt.Key.Key_Delete:
            spec = "delete"
        elif key == Qt.Key.Key_Home:
            spec = "home"
        elif key == Qt.Key.Key_End:
            spec = "end"
        elif key == Qt.Key.Key_PageUp:
            spec = "page_up"
        elif key == Qt.Key.Key_PageDown:
            spec = "page_down"
        elif key == Qt.Key.Key_Up:
            spec = "up"
        elif key == Qt.Key.Key_Down:
            spec = "down"
        elif key == Qt.Key.Key_Left:
            spec = "left"
        elif key == Qt.Key.Key_Right:
            spec = "right"
        elif key == Qt.Key.Key_Shift:
            spec = "shift"
        elif key == Qt.Key.Key_Control:
            spec = "ctrl"
        elif key == Qt.Key.Key_Alt:
            spec = "alt"
        elif Qt.Key.Key_F1 <= key <= Qt.Key.Key_F12:
            spec = f"f{int(key) - int(Qt.Key.Key_F1) + 1}"
        elif text and len(text) == 1 and text.isprintable():
            spec = text.lower()

        if spec:
            self.setText(spec)
            self.setArmed(False)
            self._ignore_left_release = False
            e.accept()
            return

        e.accept()

    def mouseReleaseEvent(self, e: QMouseEvent) -> None:
        if not self._armed:
            super().mouseReleaseEvent(e)
            return

        if e.button() == Qt.MouseButton.LeftButton:
            if self._ignore_left_release:
                self._ignore_left_release = False
                e.accept()
                return
            self.setText("mb_left")
            self.setArmed(False)
            e.accept()
            return

        spec = _mouse_button_spec(e.button())
        if spec:
            self.setText(spec)
            self.setArmed(False)
            self._ignore_left_release = False
            e.accept()
            return

        super().mouseReleaseEvent(e)


def _mouse_button_spec(btn: Qt.MouseButton) -> str | None:
    if btn == Qt.MouseButton.LeftButton:
        return "mb_left"
    if btn == Qt.MouseButton.RightButton:
        return "mb_right"
    if btn == Qt.MouseButton.MiddleButton:
        return "mb_middle"
    if btn == Qt.MouseButton.BackButton:
        return "mouse4"
    if btn == Qt.MouseButton.ForwardButton:
        return "mouse5"
    return None
