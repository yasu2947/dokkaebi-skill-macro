"""전역 단축키 리스너 — pynput 기반, 1사이클 트리거용."""
from __future__ import annotations

from PyQt6.QtCore import QMetaObject, QObject, Qt, pyqtSignal, pyqtSlot

from pynput import keyboard as kb_mod, mouse as ms_mod

from src.core.keyparse import _SPECIAL_KEYS, _mouse_button


class HotkeyListener(QObject):
    """지정 키/마우스 버튼 전역 감지 → triggered 시그널 (Qt 메인 스레드로 큐잉).

    사용법:
        listener = HotkeyListener(parent)
        listener.triggered.connect(some_slot)
        listener.set_key("mouse4")   # or "f9", "space", "mb_left" …
        listener.start()
        # …
        listener.stop()
    """

    triggered = pyqtSignal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._spec: str = ""
        self._kb_listener: kb_mod.Listener | None = None
        self._ms_listener: ms_mod.Listener | None = None

    @pyqtSlot()
    def _deliver_trigger(self) -> None:
        """pynput 스레드가 아닌 Qt 메인 스레드에서만 triggered 를 보냄."""
        self.triggered.emit()

    def _queue_trigger(self) -> None:
        QMetaObject.invokeMethod(
            self,
            "_deliver_trigger",
            Qt.ConnectionType.QueuedConnection,
        )

    # ── public API ───────────────────────────────────────────────────────────

    def set_key(self, spec: str) -> None:
        """키 스펙 변경. 동일 키면 재시작 생략."""
        normalized = spec.strip().lower()
        if normalized == self._spec and self.is_running():
            return
        was_running = self.is_running()
        self.stop()
        self._spec = normalized
        if was_running and self._spec:
            self.start()

    def start(self) -> None:
        if not self._spec or self.is_running():
            return
        if _mouse_button(self._spec) is not None:
            self._ms_listener = ms_mod.Listener(on_click=self._on_click)
            self._ms_listener.daemon = True
            self._ms_listener.start()
        else:
            self._kb_listener = kb_mod.Listener(on_press=self._on_press)
            self._kb_listener.daemon = True
            self._kb_listener.start()

    def stop(self) -> None:
        if self._kb_listener:
            try:
                self._kb_listener.stop()
            except Exception:  # noqa: BLE001
                pass
            self._kb_listener = None
        if self._ms_listener:
            try:
                self._ms_listener.stop()
            except Exception:  # noqa: BLE001
                pass
            self._ms_listener = None

    def is_running(self) -> bool:
        return bool(self._kb_listener or self._ms_listener)

    def current_key(self) -> str:
        return self._spec

    # ── pynput 콜백 (백그라운드 스레드) ──────────────────────────────────────

    def _on_press(self, key: object) -> None:
        """키보드 이벤트 핸들러."""
        spec = self._spec
        try:
            if spec in _SPECIAL_KEYS:
                if key == _SPECIAL_KEYS[spec]:
                    self._queue_trigger()
            elif hasattr(key, "char") and key.char and key.char.lower() == spec:
                self._queue_trigger()
        except Exception:  # noqa: BLE001
            pass

    def _on_click(self, _x: int, _y: int, button: object, pressed: bool) -> None:
        """마우스 클릭 이벤트 핸들러."""
        if not pressed:
            return
        mb = _mouse_button(self._spec)
        if mb is not None and button == mb:
            self._queue_trigger()
