"""사이드바 내비용: 호버 시 살짝 커지고, 클릭 지점에서 원형 리플이 퍼짐."""
from __future__ import annotations

from dataclasses import dataclass

from PyQt6.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    QRectF,
    Qt,
    QTimer,
    pyqtProperty,
)
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QPushButton


@dataclass
class _Ripple:
    cx: float
    cy: float
    t: float  # 0 → 1


class NavRippleButton(QPushButton):
    """Material/물방울 느낌의 리플 + 호버 시 높이·글자 살짝 확대."""

    def __init__(
        self,
        text: str = "",
        parent=None,
        *,
        base_height: int = 46,
        ripple_color: QColor | None = None,
        corner_radius: float = 6.0,
        expand_on_hover: bool = True,
    ) -> None:
        super().__init__(text, parent)
        self._base_h = base_height
        self.setMinimumHeight(base_height)
        self._corner_r = max(0.0, float(corner_radius))
        self._expand_on_hover = expand_on_hover
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)

        self._ripple_rgb = ripple_color or QColor(74, 222, 128)
        self._ripples: list[_Ripple] = []

        self._ripple_timer = QTimer(self)
        self._ripple_timer.setInterval(16)
        self._ripple_timer.timeout.connect(self._tick_ripples)

        self._hover_expand = 0.0
        self._hover_anim = QPropertyAnimation(self, b"hoverExpand", self)
        self._hover_anim.setDuration(200)
        self._hover_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._base_pt = 14.0
        f = self.font()
        f.setPointSizeF(self._base_pt)
        self.setFont(f)

    def setRippleAccent(self, c: QColor) -> None:
        """다크/라이트 테마에 맞춰 리플 색만 교체."""
        self._ripple_rgb = QColor(c)
        self.update()

    def hoverExpand(self) -> float:
        return self._hover_expand

    def setHoverExpand(self, v: float) -> None:
        v = max(0.0, min(1.0, float(v)))
        self._hover_expand = v
        if self._expand_on_hover:
            h = self._base_h + int(6 * v)
            self.setMinimumHeight(h)
            f = QFont(self.font())
            f.setPointSizeF(self._base_pt + 0.85 * v)
            self.setFont(f)
        self.update()

    hoverExpand = pyqtProperty(float, hoverExpand, setHoverExpand)

    def enterEvent(self, event) -> None:  # type: ignore[override]
        self._hover_anim.stop()
        self._hover_anim.setStartValue(self._hover_expand)
        self._hover_anim.setEndValue(1.0)
        self._hover_anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # type: ignore[override]
        self._hover_anim.stop()
        self._hover_anim.setStartValue(self._hover_expand)
        self._hover_anim.setEndValue(0.0)
        self._hover_anim.start()
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position()
            self._add_ripple(pos.x(), pos.y())
        super().mousePressEvent(event)

    def _add_ripple(self, cx: float, cy: float) -> None:
        self._ripples.append(_Ripple(cx, cy, 0.0))
        if not self._ripple_timer.isActive():
            self._ripple_timer.start()

    def _tick_ripples(self) -> None:
        dt = 0.07
        nxt: list[_Ripple] = []
        for r in self._ripples:
            nt = r.t + dt
            if nt < 1.0:
                nxt.append(_Ripple(r.cx, r.cy, nt))
        self._ripples = nxt
        if not self._ripples:
            self._ripple_timer.stop()
        self.update()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        super().paintEvent(event)
        if not self._ripples:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        clip = QPainterPath()
        rf = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        if self._corner_r <= 0.0:
            clip.addRect(rf)
        else:
            clip.addRoundedRect(rf, self._corner_r, self._corner_r)
        p.setClipPath(clip)
        diag = (self.width() ** 2 + self.height() ** 2) ** 0.5
        max_r = diag * 0.65

        base = self._ripple_rgb
        for r in self._ripples:
            t = min(1.0, r.t)
            ease = 1.0 - (1.0 - t) ** 3
            radius = max_r * ease
            alpha = int(100 * (1.0 - t))
            if alpha < 2 or radius < 1.0:
                continue
            fill = QColor(base)
            fill.setAlpha(alpha)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(fill)
            p.drawEllipse(QRectF(r.cx - radius, r.cy - radius, 2 * radius, 2 * radius))

            ring_a = int(55 * (1.0 - t))
            if ring_a > 3:
                pen = QPen(QColor(255, 255, 255, ring_a))
                pen.setWidthF(1.2)
                p.setPen(pen)
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawEllipse(QRectF(r.cx - radius, r.cy - radius, 2 * radius, 2 * radius))
        p.end()
