"""키 문자열 → pynput 입력 (키보드 + 마우스 버튼)."""
from __future__ import annotations

import time

from pynput.keyboard import Key, Controller as KeyController
from pynput.mouse import Button, Controller as MouseController

# 전역 컨트롤러 (스레드에서 짧게 사용)
_kb = KeyController()
_ms = MouseController()

_SPECIAL_KEYS: dict[str, Key] = {
    "space": Key.space,
    "enter": Key.enter,
    "return": Key.enter,
    "tab": Key.tab,
    "esc": Key.esc,
    "escape": Key.esc,
    "shift": Key.shift,
    "ctrl": Key.ctrl,
    "control": Key.ctrl,
    "alt": Key.alt,
    "backspace": Key.backspace,
    "delete": Key.delete,
    "up": Key.up,
    "down": Key.down,
    "left": Key.left,
    "right": Key.right,
    "home": Key.home,
    "end": Key.end,
    "page_up": Key.page_up,
    "page_down": Key.page_down,
    "f1": Key.f1,
    "f2": Key.f2,
    "f3": Key.f3,
    "f4": Key.f4,
    "f5": Key.f5,
    "f6": Key.f6,
    "f7": Key.f7,
    "f8": Key.f8,
    "f9": Key.f9,
    "f10": Key.f10,
    "f11": Key.f11,
    "f12": Key.f12,
}


def _mouse_button(spec: str) -> Button | None:
    s = spec.strip().lower().replace(" ", "")
    if s in ("mouse4", "mb4", "x1", "side1", "back"):
        return Button.x1
    if s in ("mouse5", "mb5", "x2", "side2", "forward"):
        return Button.x2
    if s in ("mouse1", "mb_left", "leftclick", "lclick"):
        return Button.left
    if s in ("mouse2", "mb_right", "rightclick", "rclick"):
        return Button.right
    if s in ("mouse3", "mb_middle", "middle", "mclick"):
        return Button.middle
    return None


def parse_key_spec(spec: str) -> tuple[str, str]:
    """('mouse', name) 또는 ('key', key_repr)"""
    raw = spec.strip()
    if not raw:
        raise ValueError("빈 키 설정")
    low = raw.lower()
    mb = _mouse_button(low)
    if mb is not None:
        return ("mouse", low)
    if low in _SPECIAL_KEYS:
        return ("key", low)
    if len(raw) == 1:
        return ("key", raw)
    raise ValueError(f"지원하지 않는 키: {raw!r} (예: 3, f, space, mouse4)")


def tap_key(spec: str, hold_s: float = 0.02) -> None:
    """키 또는 마우스 버튼을 짧게 누름."""
    kind, name = parse_key_spec(spec)
    if kind == "mouse":
        btn = _mouse_button(name)
        if btn is None:
            return
        _ms.press(btn)
        time.sleep(hold_s)
        _ms.release(btn)
        return
    if name in _SPECIAL_KEYS:
        k = _SPECIAL_KEYS[name]
        _kb.press(k)
        time.sleep(hold_s)
        _kb.release(k)
        return
    if len(name) == 1:
        ch = name
        _kb.press(ch)
        time.sleep(hold_s)
        _kb.release(ch)
        return
    raise ValueError(f"tap_key: {spec!r}")


def key_hint_text() -> str:
    return (
        "키보드: 한 글자(2,f) 또는 space, enter, shift, f1 …\n"
        "마우스: mouse4 / mouse5 (측면), mb_left, mb_right, mb_middle"
    )


def normalized_key_spec(spec: str) -> str:
    return spec.strip().lower()


def pynput_key_press_matches_spec(key: object, spec: str) -> bool:
    """pynput keyboard.Listener on_press 콜백의 key 와 스킬/스왑 스펙 문자열 비교."""
    s = normalized_key_spec(spec)
    if not s:
        return False
    try:
        if s in _SPECIAL_KEYS:
            return key == _SPECIAL_KEYS[s]
        if hasattr(key, "char") and key.char and len(s) == 1:
            return key.char.lower() == s
    except Exception:  # noqa: BLE001
        return False
    return False


def pynput_mouse_click_matches_spec(button: object, spec: str) -> bool:
    """pynput mouse.Listener on_click 의 button 과 스펙(마우스만) 비교."""
    mb = _mouse_button(normalized_key_spec(spec))
    return mb is not None and button == mb
