"""첫 실행 환영 화면."""
from __future__ import annotations

from PyQt6.QtCore import (
    QEasingCurve,
    QEvent,
    QPropertyAnimation,
    QRectF,
    QSize,
    Qt,
    QTimer,
    pyqtProperty,
    pyqtSignal,
)
from PyQt6.QtGui import (
    QColor,
    QFont,
    QPainter,
    QPixmap,
    QResizeEvent,
    QShowEvent,
)
from PyQt6.QtWidgets import (
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.core.paths import yasu_logo_path
from src.ui.nav_ripple_button import NavRippleButton


# ─────────────────────────────── LogoHoverWidget ─────────────────────────────

class LogoHoverWidget(QWidget):
    """호버 시 이미지가 부드럽게 확대되는 로고 위젯."""

    def __init__(self, pixmap: QPixmap, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._base_pm = pixmap
        self._base_h = 160
        self._scale = 1.0
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        self._anim = QPropertyAnimation(self, b"logoScale", self)
        self._anim.setDuration(260)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    @pyqtProperty(float)
    def logoScale(self) -> float:
        return self._scale

    @logoScale.setter  # type: ignore[misc]
    def logoScale(self, v: float) -> None:
        self._scale = max(0.8, min(1.4, float(v)))
        self._update_size()
        self.update()

    def setBaseHeight(self, h: int) -> None:
        self._base_h = max(32, h)
        self._update_size()
        self.update()

    def _update_size(self) -> None:
        pm = self._base_pm
        if pm.isNull():
            return
        disp_h = int(self._base_h * self._scale)
        disp_w = int(disp_h * pm.width() / max(1, pm.height()))
        # extra padding so the scaled image has room
        pad = int(self._base_h * 0.15)
        self.setFixedSize(disp_w + pad * 2, disp_h + pad * 2)

    def enterEvent(self, event) -> None:  # type: ignore[override]
        self._anim.stop()
        self._anim.setStartValue(self._scale)
        self._anim.setEndValue(1.12)
        self._anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # type: ignore[override]
        self._anim.stop()
        self._anim.setStartValue(self._scale)
        self._anim.setEndValue(1.0)
        self._anim.start()
        super().leaveEvent(event)

    def paintEvent(self, _e) -> None:  # type: ignore[override]
        pm = self._base_pm
        if pm.isNull():
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        disp_h = int(self._base_h * self._scale)
        scaled = pm.scaledToHeight(disp_h, Qt.TransformationMode.SmoothTransformation)
        x = (self.width() - scaled.width()) // 2
        y = (self.height() - scaled.height()) // 2
        p.drawPixmap(x, y, scaled)
        p.end()

    def sizeHint(self) -> QSize:  # type: ignore[override]
        if self._base_pm.isNull():
            return QSize(160, 160)
        h = self._base_h
        w = int(h * self._base_pm.width() / max(1, self._base_pm.height()))
        return QSize(w + 30, h + 30)


# ─────────────────────────────── stylesheets ─────────────────────────────────

WELCOME_DARK = """
QWidget#WelcomeRoot {
  background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
    stop:0 #121722, stop:1 #1a2230);
  font-family: "Noto Sans KR", "Noto Sans", "Noto Sans CJK KR",
    "Malgun Gothic", "Malgun Gothic UI", "Apple SD Gothic Neo",
    "Segoe UI Variable Text", "Segoe UI", system-ui, sans-serif;
  font-size: 15px;
}
QWidget#WelcomePanel {
  background: transparent;
  border: none;
}
QLabel#wApp     { color: #4ade80; font-weight: 900; letter-spacing: -0.5px; }
QLabel#wSub     { color: #94a3b8; margin-top: 4px; }

QFrame#updateCard {
  background: rgba(24,30,40,0.55);
  border: none;
  border-radius: 0px;
}
QLabel#updateVer  { color: #4ade80; font-weight: 900; background: transparent; }
QLabel#updateDate { color: #94a3b8; background: transparent; }
QLabel#itemHead   { color: #f3f4f6; font-weight: 800; background: transparent; }
QLabel#itemDesc   { color: #9ca3af; background: transparent; }
QPushButton#prevToggle {
  background: transparent; border: none;
  color: #4e6a7a; padding: 0;
  text-align: left;
}
QPushButton#prevToggle:hover { color: #4ade80; }
QLabel#prevItem { color: #4e6a7a; }
QLabel#chgBullet { color: #4ade80; font-weight: 900; background: transparent; }
"""

WELCOME_LIGHT = """
QWidget#WelcomeRoot {
  background: #f8fafc;
  font-family: "Noto Sans KR", "Noto Sans", "Noto Sans CJK KR",
    "Malgun Gothic", "Malgun Gothic UI", "Apple SD Gothic Neo",
    "Segoe UI Variable Text", "Segoe UI", system-ui, sans-serif;
  font-size: 15px;
}
QWidget#WelcomeScrollInner { background: #f8fafc; }
QWidget#WelcomePanel {
  background: transparent;
  border: none;
}
QLabel#wApp     { color: #3b82f6; font-weight: 900; letter-spacing: -0.5px; }
QLabel#wSub     { color: #64748b; margin-top: 4px; }

QFrame#updateCard {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 0px;
}
QLabel#updateVer  { color: #3b82f6; font-weight: 900; background: transparent; }
QLabel#updateDate { color: #94a3b8; background: transparent; }
QLabel#itemHead   { color: #1e293b; font-weight: 800; background: transparent; }
QLabel#itemDesc   { color: #64748b; background: transparent; }
QPushButton#prevToggle {
  background: transparent; border: none;
  color: #94a3b8; padding: 0;
  text-align: left;
}
QPushButton#prevToggle:hover { color: #3b82f6; }
QLabel#prevItem { color: #94a3b8; }
QLabel#chgBullet { color: #3b82f6; font-weight: 900; background: transparent; }
"""


# ─────────────────────────────── helpers ─────────────────────────────────────

def _changelog_card(
    parent: QWidget,
    version: str,
    date: str,
    items: list[tuple[str, str]],
    prev_version: str,
    prev_lines: list[str],
) -> tuple[QFrame, QWidget, dict[str, object]]:
    card = QFrame(parent)
    card.setObjectName("updateCard")
    card.setMinimumWidth(320)
    card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    vl = QVBoxLayout(card)
    vl.setContentsMargins(24, 20, 24, 22)
    vl.setSpacing(12)

    scale_refs: dict[str, object] = {
        "vl": vl,
        "heads": [],
        "descs": [],
        "bullets": [],
        "prev_items": [],
    }

    head = QHBoxLayout()
    ver_lbl = QLabel(f"✦  UPDATE v{version}", card)
    ver_lbl.setObjectName("updateVer")
    ver_lbl.setWordWrap(True)
    date_lbl = QLabel(date, card)
    date_lbl.setObjectName("updateDate")
    scale_refs["ver"] = ver_lbl
    scale_refs["date"] = date_lbl
    head.addWidget(ver_lbl)
    head.addStretch(1)
    head.addWidget(date_lbl)
    vl.addLayout(head)

    heads: list[QLabel] = []
    descs: list[QLabel] = []
    bullets: list[QLabel] = []
    for headline, desc in items:
        row = QHBoxLayout()
        row.setContentsMargins(0, 4, 0, 4)
        row.setSpacing(12)
        row.setAlignment(Qt.AlignmentFlag.AlignTop)
        bullet = QLabel("•", card)
        bullet.setObjectName("chgBullet")
        bullet.setFixedWidth(14)
        bullet.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        col = QVBoxLayout()
        col.setSpacing(4)
        h_lbl = QLabel(headline, card)
        h_lbl.setObjectName("itemHead")
        h_lbl.setWordWrap(True)
        h_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        d_lbl = QLabel(desc, card)
        d_lbl.setObjectName("itemDesc")
        d_lbl.setWordWrap(True)
        d_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        col.addWidget(h_lbl)
        col.addWidget(d_lbl)
        row.addWidget(bullet, 0, Qt.AlignmentFlag.AlignTop)
        row.addLayout(col, 1)
        vl.addLayout(row)
        heads.append(h_lbl)
        descs.append(d_lbl)
        bullets.append(bullet)
    scale_refs["heads"] = heads
    scale_refs["descs"] = descs
    scale_refs["bullets"] = bullets

    prev_btn = QPushButton(f"→  이전 버전 (v{prev_version})  ▾", card)
    prev_btn.setObjectName("prevToggle")
    prev_btn.setFlat(True)
    vl.addWidget(prev_btn)
    scale_refs["prev_btn"] = prev_btn

    prev_widget = QWidget(card)
    prev_widget.setObjectName("prevWidget")
    pv = QVBoxLayout(prev_widget)
    pv.setContentsMargins(20, 4, 0, 0)
    pv.setSpacing(4)
    prev_items: list[QLabel] = []
    for line in prev_lines:
        lbl = QLabel(f"• {line}", prev_widget)
        lbl.setObjectName("prevItem")
        lbl.setWordWrap(True)
        pv.addWidget(lbl)
        prev_items.append(lbl)
    prev_widget.setVisible(False)
    vl.addWidget(prev_widget)
    scale_refs["prev_items"] = prev_items
    scale_refs["prev_inner"] = pv

    def _toggle_prev() -> None:
        vis = not prev_widget.isVisible()
        prev_widget.setVisible(vis)
        prev_btn.setText(f"→  이전 버전 (v{prev_version})  {'▴' if vis else '▾'}")

    prev_btn.clicked.connect(_toggle_prev)
    return card, prev_widget, scale_refs


# ─────────────────────────────── WelcomePage ─────────────────────────────────

class WelcomePage(QWidget):
    continue_clicked = pyqtSignal()
    theme_changed = pyqtSignal(str)

    _REF_PANEL_W = 1240.0
    _REF_PANEL_H = 640.0

    def __init__(
        self,
        version: str,
        changelog_lines: list[tuple[str, str]],
        log_date: str,
        prev_version: str = "",
        prev_lines: list[str] | None = None,
        is_dark: bool = True,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("WelcomeRoot")
        self._is_dark = True

        self._logo_widget: LogoHoverWidget | None = None
        self._logo_pm: QPixmap | None = None

        # 루트 레이아웃: QScrollArea 하나만 채움 (내용이 길면 스크롤)
        _root_vl = QVBoxLayout(self)
        _root_vl.setContentsMargins(0, 0, 0, 0)
        _root_vl.setSpacing(0)

        self._scroll = QScrollArea(self)
        self._scroll.setObjectName("welcomeScroll")
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setStyleSheet(
            "QScrollArea#welcomeScroll { background: transparent; border: none; }"
            "QScrollBar:vertical { width: 6px; background: transparent; }"
            "QScrollBar::handle:vertical { background: #2a3344; border-radius: 3px; min-height: 24px; }"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }"
        )
        _root_vl.addWidget(self._scroll)

        # 스크롤 영역 내부 위젯 (여기에 outer margins + 세로 중앙 정렬)
        _scroll_inner = QWidget()
        _scroll_inner.setObjectName("WelcomeScrollInner")
        _scroll_inner.setStyleSheet("background: transparent;")
        self._scroll.setWidget(_scroll_inner)

        outer = QVBoxLayout(_scroll_inner)
        outer.setContentsMargins(48, 36, 48, 40)
        outer.setSpacing(0)
        self._outer_layout = outer

        outer.addStretch(1)

        center = QWidget(_scroll_inner)
        center.setObjectName("WelcomePanel")
        center.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        cl = QVBoxLayout(center)
        cl.setContentsMargins(8, 8, 8, 8)
        cl.setSpacing(22)
        cl.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        self._center = center
        self._center_layout = cl

        # ── 로고 (호버 확대) ──────────────────────────────────────────────────
        logo_path = yasu_logo_path()
        if logo_path is not None:
            pm = QPixmap(str(logo_path))
            if not pm.isNull():
                self._logo_pm = pm
                self._logo_widget = LogoHoverWidget(pm, center)
                cl.addWidget(self._logo_widget, 0, Qt.AlignmentFlag.AlignHCenter)

        # ── 제목 (큰 초록 텍스트) ─────────────────────────────────────────────
        self._title_lbl = QLabel("도깨비 스킬 매크로", center)
        self._title_lbl.setObjectName("wApp")
        self._title_lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        cl.addWidget(self._title_lbl)

        self._sub_lbl = QLabel("한월 RPG · 스킬바 이미지 매칭 도구", center)
        self._sub_lbl.setObjectName("wSub")
        self._sub_lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        cl.addWidget(self._sub_lbl)

        # ── changelog card ───────────────────────────────────────────────────
        self._card, _, self._chg_refs = _changelog_card(
            center, version, log_date, changelog_lines,
            prev_version or "0.3.0", prev_lines or [],
        )
        cl.addWidget(self._card, 0, Qt.AlignmentFlag.AlignHCenter)

        # ── 계속하기 버튼 (리플 애니메이션) ─────────────────────────────────
        self._btn = NavRippleButton(
            "계속하기",
            parent=center,
            ripple_color=QColor(255, 255, 255, 180),
            corner_radius=0.0,
            expand_on_hover=False,
        )
        self._btn.setObjectName("wContinue")
        self._btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn.clicked.connect(self._on_continue_clicked)
        self._btn.setStyleSheet("""
            NavRippleButton#wContinue {
                background: #4ade80;
                border: none;
                border-radius: 0px;
                color: #0f172a;
                font-weight: 900;
                padding: 18px 32px;
            }
            NavRippleButton#wContinue:hover { background: #36c96f; }
        """)
        cl.addWidget(self._btn, 0, Qt.AlignmentFlag.AlignHCenter)

        outer.addWidget(center, 0, Qt.AlignmentFlag.AlignHCenter)
        outer.addStretch(1)

        # 페이드아웃용 opacity effect (계속하기 클릭 시)
        self._fade_effect = QGraphicsOpacityEffect(self)
        self._fade_effect.setOpacity(1.0)
        self.setGraphicsEffect(self._fade_effect)
        self._fade_out_anim = QPropertyAnimation(self._fade_effect, b"opacity", self)
        self._fade_out_anim.setDuration(380)
        self._fade_out_anim.setStartValue(1.0)
        self._fade_out_anim.setEndValue(0.0)
        self._fade_out_anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        self._fade_out_anim.finished.connect(self._emit_continue)

        self._scale_timer = QTimer(self)
        self._scale_timer.setSingleShot(True)
        self._scale_timer.setInterval(48)
        self._scale_timer.timeout.connect(self._apply_welcome_scale)

        self._apply_theme("dark")
        QTimer.singleShot(0, self._apply_welcome_scale)

    def showEvent(self, event: QShowEvent) -> None:  # type: ignore[override]
        super().showEvent(event)
        QTimer.singleShot(0, self._apply_welcome_scale)

    def changeEvent(self, e: QEvent) -> None:  # type: ignore[override]
        super().changeEvent(e)
        # 창 복원(최소화→복원) 시 레이아웃 재계산
        if e.type() == QEvent.Type.WindowStateChange:
            QTimer.singleShot(0, self._apply_welcome_scale)

    def resizeEvent(self, event: QResizeEvent) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._scale_timer.start()

    def _apply_welcome_scale(self) -> None:
        om = self._outer_layout.contentsMargins()
        # 스크롤 뷰포트 너비 기준 (스크롤바 공간 제외)
        vp_w = self._scroll.viewport().width() if self._scroll.viewport() else self.width()
        avail_w = max(280, vp_w - om.left() - om.right())
        avail_h = max(320, self.height() - om.top() - om.bottom())
        panel_w = int(min(1280, max(260, avail_w * 0.95)))
        # 폰트·로고 스케일은 너비 기준 (높이 제한 제거)
        s = max(0.50, min(1.0, avail_w / self._REF_PANEL_W))

        self._center.setFixedWidth(panel_w)
        self._outer_layout.setContentsMargins(
            max(16, int(48 * s)), max(14, int(36 * s)),
            max(16, int(48 * s)), max(16, int(40 * s)),
        )
        self._center_layout.setSpacing(max(10, int(22 * s)))

        if self._logo_widget is not None and self._logo_pm is not None:
            self._logo_widget.setBaseHeight(max(72, int(168 * s)))

        def _pt(lbl: QLabel, pt: float) -> None:
            f = QFont(lbl.font())
            f.setPointSizeF(pt)
            lbl.setFont(f)

        def _pt_btn(btn: QPushButton, pt: float) -> None:
            f = QFont(btn.font())
            f.setPointSizeF(pt)
            btn.setFont(f)

        # 제목을 로고처럼 크게 (44pt 기준)
        _pt(self._title_lbl, 44.0 * s)
        _pt(self._sub_lbl, 16.0 * s)

        refs = self._chg_refs
        vl = refs.get("vl")
        if isinstance(vl, QVBoxLayout):
            vl.setContentsMargins(
                max(12, int(24 * s)), max(10, int(20 * s)),
                max(12, int(24 * s)), max(12, int(22 * s)),
            )
            vl.setSpacing(max(8, int(12 * s)))

        ver = refs.get("ver")
        if isinstance(ver, QLabel):
            _pt(ver, 15.0 * s)
        date = refs.get("date")
        if isinstance(date, QLabel):
            _pt(date, 13.0 * s)
        for lbl in refs.get("heads", []) or []:
            if isinstance(lbl, QLabel):
                _pt(lbl, 15.0 * s)
        for lbl in refs.get("descs", []) or []:
            if isinstance(lbl, QLabel):
                _pt(lbl, 13.0 * s)
        for lbl in refs.get("bullets", []) or []:
            if isinstance(lbl, QLabel):
                _pt(lbl, 15.0 * s)

        prev_btn = refs.get("prev_btn")
        if isinstance(prev_btn, QPushButton):
            _pt_btn(prev_btn, 13.0 * s)
        for lbl in refs.get("prev_items", []) or []:
            if isinstance(lbl, QLabel):
                _pt(lbl, 12.0 * s)

        pv = refs.get("prev_inner")
        if isinstance(pv, QVBoxLayout):
            pv.setContentsMargins(max(10, int(20 * s)), max(2, int(4 * s)), 0, 0)
            pv.setSpacing(max(2, int(4 * s)))

        self._card.setMinimumWidth(max(200, int(panel_w * 0.92)))

        _pt_btn(self._btn, 19.0 * s)
        self._btn.setMinimumWidth(max(240, int(520 * s)))
        self._btn.setMinimumHeight(max(44, int(62 * s)))
        self._btn._base_h = max(44, int(62 * s))

    def _on_continue_clicked(self) -> None:
        """버튼 클릭 → 페이드아웃 → continue_clicked 시그널."""
        self._btn.setEnabled(False)
        self._fade_out_anim.start()

    def _emit_continue(self) -> None:
        self._fade_effect.setOpacity(1.0)
        self._btn.setEnabled(True)
        self.continue_clicked.emit()

    def _on_theme_toggle(self, checked: bool) -> None:
        mode = "light" if checked else "dark"
        self._apply_theme(mode)

    def apply_theme(self, mode: str) -> None:
        """MainWindow에서 테마 전환 시 호출."""
        self._apply_theme(mode)

    def _apply_theme(self, mode: str) -> None:
        self._is_dark = (mode == "dark")
        qss = WELCOME_DARK if self._is_dark else WELCOME_LIGHT
        self.setStyleSheet(qss)
        # 스크롤바 색 테마 연동
        sb_handle = "#2a3344" if self._is_dark else "#cbd5e1"
        self._scroll.setStyleSheet(
            "QScrollArea#welcomeScroll { background: transparent; border: none; }"
            f"QScrollBar:vertical {{ width: 6px; background: transparent; }}"
            f"QScrollBar::handle:vertical {{ background: {sb_handle}; border-radius: 3px; min-height: 24px; }}"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }"
        )
        # 계속하기 버튼 색: 다크=초록, 라이트=파랑
        if self._is_dark:
            btn_css = """
                NavRippleButton#wContinue {
                    background: #4ade80; border: none; border-radius: 0px;
                    color: #0f172a; font-weight: 900; padding: 18px 32px;
                }
                NavRippleButton#wContinue:hover { background: #36c96f; }
            """
        else:
            btn_css = """
                NavRippleButton#wContinue {
                    background: #3b82f6; border: none; border-radius: 0px;
                    color: #ffffff; font-weight: 900; padding: 18px 32px;
                }
                NavRippleButton#wContinue:hover { background: #2563eb; }
            """
        self._btn.setStyleSheet(btn_css)
        QTimer.singleShot(0, self._apply_welcome_scale)

    def skip_welcome_next_time(self) -> bool:
        return False
