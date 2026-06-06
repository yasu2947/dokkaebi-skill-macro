"""메인 창 — Server Engine 스타일 사이드바 + 탭 레이아웃."""
from __future__ import annotations

import ctypes
import os
import sys
from pathlib import Path

import cv2
import numpy as np
from PyQt6.QtCore import QEasingCurve, QEvent, QObject, QPoint, QPropertyAnimation, QRectF, QSettings, Qt, QThread, QTimer, pyqtProperty, pyqtSignal
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QGuiApplication,
    QIcon,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGraphicsOpacityEffect,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from src.app_meta import (
    APP_NAME,
    APP_VERSION,
    CHANGELOG_DATE,
    CHANGELOG_LINES,
    PREV_LINES,
    PREV_VERSION,
)

from src.core.capture import grab_bgr
from src.core.config import (
    AppConfig,
    default_config_path,
    load_config,
    normalize_slot_priorities,
    normalize_slot_skill_enabled,
    normalize_slot_swap_enabled,
    normalize_slot_swap_skill_enabled,
    save_config,
    template_filename_for_slot,
    template_filename_swap,
)
from src.core import presets as presets_mod
from src.core.paths import project_root, yasu_logo_path
from src.core.regions import slot_rects_for_capture
from src.ui.cycle_worker import CycleWorker
from src.ui.hotkey_listener import HotkeyListener
from src.ui.key_capture_edit import KeyCaptureEdit
from src.ui.macro_scroll import MacroScrollArea
from src.ui.nav_ripple_button import NavRippleButton
from src.ui.roi_picker import pick_roi_fullscreen
from src.ui.welcome_page import WelcomePage
from src.ui.widgets_no_wheel import NoWheelDoubleSpinBox, NoWheelSpinBox

def _close_all_qt_popups() -> None:
    """PyQt6에는 QApplication.closeAllPopups() 가 없음 — 열린 팝업(콤보 등)을 순서대로 닫음."""
    for _ in range(64):
        w = QApplication.activePopupWidget()
        if w is None:
            break
        w.close()


# ─────────────────────────────── Stylesheets ─────────────────────────────────

# Noto Sans KR 우선(설치된 PC에서만 적용). 없으면 맑은 고딕·Segoe 로 자동 폴백.
_FONT = (
    'font-family: "Noto Sans KR", "Noto Sans", "Noto Sans CJK KR", '
    '"Malgun Gothic", "Malgun Gothic UI", "Apple SD Gothic Neo", '
    '"Segoe UI Variable Text", "Segoe UI", system-ui, sans-serif;'
)
_R = "6px"

DARK_QSS = f"""
QMainWindow, QWidget {{ background-color: #171b22; color: #e5e7eb; {_FONT} font-size: 15px; }}

/* ── 커스텀 타이틀바 ── */
QWidget#customTitleBar {{
  background: #0d1117;
  border-bottom: 1px solid #1e2733;
}}
QLabel#titleBarIcon {{ background: transparent; }}
QLabel#titleBarTitle {{
  color: #c9d1d9;
  font-size: 13px;
  font-weight: 700;
  background: transparent;
  letter-spacing: 0.3px;
}}
QLabel#titleBarVer {{
  color: #4b5563;
  font-size: 11px;
  background: transparent;
}}
QPushButton#titleBtn {{
  background: transparent;
  border: none;
  color: #9ca3af;
  font-size: 13px;
  padding: 0;
}}
QPushButton#titleBtn:hover {{
  background: #2a3344;
  color: #f3f4f6;
}}
QPushButton#titleBtnMax {{
  background: transparent;
  border: none;
  color: #9ca3af;
  font-size: 11px;
  padding: 0;
}}
QPushButton#titleBtnMax:hover {{
  background: #2a3344;
  color: #f3f4f6;
}}
QPushButton#titleBtnClose {{
  background: transparent;
  border: none;
  color: #9ca3af;
  font-size: 12px;
  padding: 0;
}}
QPushButton#titleBtnClose:hover {{
  background: #e53935;
  color: #ffffff;
}}

/* ── header (서버 엔진식: 어두운 바 + 얇은 구분선) ── */
QWidget#headerBar {{
  background-color: #1a1d24;
  border: none;
  min-height: 54px;
  max-height: 54px;
}}
QLabel#headerTitle {{ color: #f9fafb; font-size: 16px; font-weight: 800; }}
QPushButton#headerBtn {{
  background: #252b36;
  border: none;
  border-radius: {_R};
  color: #e5e7eb;
  padding: 7px 14px;
  font-weight: 700;
  font-size: 13px;
}}
QPushButton#headerBtn:hover {{
  background: #2f3742;
  color: #4ade80;
}}

/* ── sidebar: 카테고리 + 블록 ── */
QWidget#sidebar {{
  background-color: #1a1f28;
  border: none;
  min-width: 224px;
  max-width: 268px;
}}
QLabel#sidebarBrand {{
  color: #6b7280;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 2px;
  padding: 10px 14px 4px 14px;
}}
QLabel#navCat {{
  color: #6b7280;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 1.2px;
  padding: 12px 14px 2px 14px;
}}
QFrame#navBlock {{
  background: #1e2430;
  border: none;
  border-radius: {_R};
}}
QPushButton#navBtn {{
  background: transparent;
  border: none;
  border-radius: {_R};
  color: #94a3b8;
  padding: 11px 12px 11px 12px;
  text-align: left;
  font-size: 14px;
  font-weight: 600;
}}
QPushButton#navBtn:hover {{
  background: rgba(74,222,128,0.08);
  color: #e5e7eb;
}}
QPushButton#navBtn:checked {{
  background: rgba(74,222,128,0.14);
  color: #4ade80;
}}

QWidget#contentWrap {{ background: #171b22; }}
QScrollArea {{ border: none; outline: none; background: transparent; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QFrame {{ border: none; }}
QFrame#card {{
  background: #232a38;
  border: none;
  border-radius: {_R};
}}
QScrollBar:vertical {{ background: #1a1f28; width: 8px; border-radius: 4px; }}
QScrollBar::handle:vertical {{ background: #3d4654; border-radius: 4px; min-height: 24px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}

QLabel#cardTitle {{
  color: #9ca3af;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 1.2px;
}}

/* 섹션 헤더 — 별도 띠 색 없음 (카드 배경과 동일하게) */
QWidget#sectionHeaderBar {{
  background: transparent;
  border: none;
  padding-bottom: 2px;
  margin-bottom: 6px;
}}
QWidget#skillSlotsPage QWidget#sectionHeaderBar {{
  background: transparent;
}}
QLabel#sectionHeaderTitle {{
  color: #f3f4f6;
  font-size: 16px;
  font-weight: 800;
}}
QPushButton#sectionActionBtn {{
  background: #252b36;
  border: none;
  border-radius: {_R};
  color: #cbd5e1;
  padding: 7px 14px;
  font-weight: 700;
  font-size: 13px;
  min-width: 84px;
}}
QPushButton#sectionActionBtn:hover {{
  background: #323a48;
  color: #bbf7d0;
}}
QPushButton#ghostIconBtn {{
  background: transparent;
  border: none;
  border-radius: {_R};
  color: #94a3b8;
  padding: 0px;
  font-weight: 700;
  font-size: 16px;
  min-width: 40px;
  max-width: 40px;
  min-height: 34px;
  max-height: 34px;
}}
QPushButton#ghostIconBtn:hover {{
  background: rgba(74,222,128,0.10);
  color: #4ade80;
}}
QPushButton#ghostIconBtn:disabled {{
  color: #4b5563;
  background: transparent;
}}

QWidget#bottomBar {{
  background: #1a1f28;
  border: none;
  min-height: 56px;
  max-height: 56px;
}}

QLabel {{
  color: #9ca3af;
  background: transparent;
  border: none;
}}
QLabel#formLabel {{
  color: #94a3b8;
  background: transparent;
  border: none;
  padding: 0 10px 0 0;
  font-size: 14px;
}}
QLabel#formMath {{
  color: #6b7280;
  background: transparent;
  border: none;
  padding: 0 4px;
  font-size: 14px;
}}
QLabel#sectionLabel {{ color: #e5e7eb; font-weight: 700; font-size: 14px; }}
QLabel#hintLabel {{ color: #6b7280; font-size: 12px; }}
QLabel#statusLabel {{ color: #4ade80; font-size: 12px; }}
QLabel#slotNumLabel {{ color: #4ade80; font-weight: 900; font-size: 14px; }}

/* 체크박스: Fusion 기본 검은 띠 제거 */
QCheckBox {{
  background: transparent;
  color: #cbd5e1;
  spacing: 8px;
}}
QCheckBox::indicator {{
  width: 18px;
  height: 18px;
  border-radius: 4px;
  border: 1px solid #475569;
  background: #252b36;
}}
QCheckBox::indicator:checked {{
  background: #4ade80;
  border: 1px solid #4ade80;
}}
QCheckBox::indicator:hover {{
  border: 1px solid #64748b;
}}

QWidget#slotRowWrap {{
  border-radius: {_R};
  border: none;
  background: transparent;
}}
QWidget#slotRowWrap:hover {{
  background: transparent;
}}

/* 스킬 라이브러리 헤더 */
QWidget#skillLibHeader {{
  background: #21262d;
  border-radius: {_R};
}}
QLabel#skillLibHeaderLabel {{
  color: #c9d1d9;
  font-size: 11px;
  font-weight: bold;
}}

QSpinBox, QLineEdit, QDoubleSpinBox {{
  background: #161b22;
  border: none;
  border-radius: {_R};
  padding: 9px 12px;
  min-height: 34px;
  font-size: 14px;
  color: #e5e7eb;
}}
QSpinBox:focus, QLineEdit:focus, QDoubleSpinBox:focus {{
  background: #1c2330;
}}
QAbstractSpinBox::up-button, QAbstractSpinBox::down-button {{
  border: none;
  background: transparent;
  width: 18px;
}}
QLineEdit[armed="true"] {{ border: none; background: rgba(74,222,128,0.12); }}

/* 스킬 슬롯 탭: 행 띠·호버 번짐 제거, 입력·버튼만 은은하게 구분 (전역 QLineEdit/QPushButton보다 뒤에 둠) */
QWidget#skillSlotsPage {{
  background: transparent;
}}
QWidget#skillSlotsPage QWidget#slotRowsHost {{
  background: transparent;
}}
QWidget#skillSlotsPage QFrame#card {{
  background: #262d3c;
  border: none;
}}
QWidget#skillSlotsPage QWidget#slotRowWrap {{
  background: transparent;
  border: none;
}}
QWidget#skillSlotsPage QWidget#slotRowWrap:hover {{
  background: transparent;
}}
QWidget#skillSlotsPage QLineEdit {{
  background: rgba(255,255,255,0.06);
  border: none;
  border-radius: {_R};
  padding: 9px 12px;
  min-height: 38px;
  font-size: 14px;
  color: #e5e7eb;
}}
QWidget#skillSlotsPage QLineEdit:focus {{
  background: rgba(74,222,128,0.10);
}}
QWidget#skillSlotsPage QLineEdit#slotKeyEdit {{
  max-width: 168px;
  min-width: 100px;
}}
QWidget#skillSlotsPage QLineEdit[armed="true"] {{
  border: none;
  background: rgba(74,222,128,0.14);
}}
QPushButton#slotRowBtn {{
  background: rgba(255,255,255,0.07);
  border: none;
  border-radius: {_R};
  color: #d1d5db;
  padding: 8px 12px;
  font-weight: 600;
  font-size: 13px;
}}
QPushButton#slotRowBtn:hover {{
  background: rgba(74,222,128,0.14);
  color: #f1f5f9;
}}
QPushButton#slotRowBtn:pressed {{
  background: rgba(74,222,128,0.22);
}}
QWidget#skillSlotsPage QPushButton#slotPriCombo {{
  background: rgba(255,255,255,0.07);
  border: none;
  border-radius: {_R};
  padding: 4px 6px;
  min-height: 30px;
  max-height: 34px;
  max-width: 100px;
  min-width: 86px;
  font-size: 12px;
  font-weight: 600;
  color: #d1d5db;
}}
QWidget#skillSlotsPage QPushButton#slotPriCombo:hover {{
  background: rgba(255,255,255,0.10);
}}
QWidget#skillSlotsPage QPushButton#slotPriCombo:pressed {{
  background: rgba(255,255,255,0.14);
}}
QWidget#skillSlotsPage QPushButton#slotSwapPriCombo {{
  background: rgba(255,255,255,0.07);
  border: none;
  border-radius: {_R};
  padding: 4px 6px;
  min-height: 30px;
  max-height: 32px;
  min-width: 76px;
  max-width: 92px;
  font-size: 11px;
  font-weight: 600;
  color: #d1d5db;
}}
QWidget#skillSlotsPage QPushButton#slotSwapPriCombo:hover {{
  background: rgba(255,255,255,0.10);
}}
QWidget#skillSlotsPage QPushButton#slotSwapPriCombo:pressed {{
  background: rgba(255,255,255,0.14);
}}
QPushButton#skillInfoPriBtn {{
  background: rgba(255,255,255,0.07);
  border: none;
  border-radius: {_R};
  padding: 2px 4px;
  min-height: 28px;
  max-height: 32px;
  font-size: 12px;
  font-weight: 600;
  color: #d1d5db;
}}
QPushButton#skillInfoPriBtn:hover {{ background: rgba(255,255,255,0.10); }}
QPushButton#skillInfoPriBtn:pressed {{ background: rgba(255,255,255,0.14); }}
QWidget#skillSlotsPage QLabel#slotMiniLbl {{
  color: #94a3b8;
  font-size: 11px;
  font-weight: 700;
  background: transparent;
}}
QWidget#skillSlotsPage QCheckBox#slotSkillChk {{
  color: #94a3b8;
  font-size: 11px;
  font-weight: 600;
}}
QWidget#skillSlotsPage QCheckBox#slotSkillChk::indicator {{
  width: 14px; height: 14px;
}}
QWidget#skillSlotsPage QCheckBox#slotSwapSkillChk {{
  color: #86efac;
  font-size: 11px;
  font-weight: 600;
}}
QWidget#skillSlotsPage QCheckBox#slotSwapSkillChk::indicator {{
  width: 14px; height: 14px;
}}
QWidget#skillSlotsPage QCheckBox#slotSwapChk {{
  color: #7dd3fc;
  font-size: 11px;
  font-weight: 600;
}}
QPushButton#presetCard {{
  background: #1c2330;
  border: 2px solid #2a3344;
  border-radius: {_R};
  color: #e5e7eb;
  text-align: center;
}}
QPushButton#presetCard[selected="true"] {{
  border: 2px solid #4ade80;
  background: #1e2a22;
}}

QComboBox {{
  background: #161b22;
  border: none;
  border-radius: {_R};
  padding: 9px 12px;
  min-height: 34px;
  font-size: 14px;
  color: #e5e7eb;
}}
QComboBox:focus {{ background: #1c2330; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{
  background: #1e2430;
  border: none;
  color: #e5e7eb;
  selection-background-color: #2a3344;
}}
QPushButton {{
  background: #252b36;
  border: none;
  border-radius: {_R};
  color: #cbd5e1;
  padding: 9px 16px;
  font-weight: 700;
  font-size: 14px;
}}
QPushButton:hover {{ background: #2f3848; color: #e5e7eb; }}
QPushButton:disabled {{ opacity: 0.42; }}
QPushButton#primary {{
  background: #4ade80;
  border: none;
  color: #0f172a;
  font-weight: 800;
  border-radius: {_R};
  padding: 10px 22px;
  font-size: 14px;
}}
QPushButton#primary:hover {{ background: #36c96f; }}
QPushButton#danger {{
  background: #2a1520;
  border: none;
  color: #f87171;
  border-radius: {_R};
  padding: 9px 16px;
  font-weight: 700;
  font-size: 14px;
}}
QPushButton#danger:hover {{ background: #3a1a28; color: #fca5a5; }}
QPushButton#linkBtn {{
  background: transparent;
  border: none;
  color: #4ade80;
  font-weight: 700;
  font-size: 13px;
  padding: 5px 10px;
}}
QPushButton#linkBtn:hover {{ color: #bbf7d0; }}
QLabel#accentHint {{ color: #4ade80; font-size: 12px; font-weight: 600; background: transparent; }}
QSlider::groove:horizontal {{
  background: #2a3344;
  height: 4px;
  border-radius: 2px;
}}
QSlider::handle:horizontal {{
  background: #4ade80;
  width: 14px;
  height: 14px;
  border-radius: 7px;
  margin: -5px 0;
}}
QSlider::sub-page:horizontal {{
  background: #4ade80;
  border-radius: 2px;
}}
QSlider::add-page:horizontal {{
  background: #2a3344;
  border-radius: 2px;
}}
"""

LIGHT_QSS = f"""
QMainWindow, QWidget {{ background-color: #f8fafc; color: #1e293b; {_FONT} font-size: 15px; }}

/* ── 커스텀 타이틀바 ── */
QWidget#customTitleBar {{
  background: #ffffff;
  border-bottom: 1px solid #e2e8f0;
}}
QLabel#titleBarIcon {{ background: transparent; }}
QLabel#titleBarTitle {{
  color: #1e293b;
  font-size: 13px;
  font-weight: 700;
  background: transparent;
  letter-spacing: 0.3px;
}}
QLabel#titleBarVer {{
  color: #94a3b8;
  font-size: 11px;
  background: transparent;
}}
QPushButton#titleBtn {{
  background: transparent;
  border: none;
  color: #64748b;
  font-size: 13px;
  padding: 0;
}}
QPushButton#titleBtn:hover {{
  background: #f1f5f9;
  color: #1e293b;
}}
QPushButton#titleBtnMax {{
  background: transparent;
  border: none;
  color: #64748b;
  font-size: 11px;
  padding: 0;
}}
QPushButton#titleBtnMax:hover {{
  background: #f1f5f9;
  color: #1e293b;
}}
QPushButton#titleBtnClose {{
  background: transparent;
  border: none;
  color: #64748b;
  font-size: 12px;
  padding: 0;
}}
QPushButton#titleBtnClose:hover {{
  background: #ef4444;
  color: #ffffff;
}}

/* ── header ── */
QWidget#headerBar {{
  background-color: #ffffff;
  border-bottom: 1px solid #e2e8f0;
  min-height: 54px;
  max-height: 54px;
}}
QLabel#headerTitle {{ color: #1e293b; font-size: 16px; font-weight: 800; }}
QPushButton#headerBtn {{
  background: #f1f5f9;
  border: none;
  border-radius: {_R};
  color: #475569;
  padding: 7px 14px;
  font-weight: 700;
  font-size: 13px;
}}
QPushButton#headerBtn:hover {{
  background: #e2e8f0;
  color: #3b82f6;
}}

/* ── sidebar ── */
QWidget#sidebar {{
  background-color: #f1f5f9;
  border-right: 1px solid #e2e8f0;
  min-width: 224px;
  max-width: 268px;
}}
QLabel#sidebarBrand {{
  color: #94a3b8;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 2px;
  padding: 10px 14px 4px 14px;
}}
QLabel#navCat {{
  color: #94a3b8;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 1.2px;
  padding: 12px 14px 2px 14px;
}}
QFrame#navBlock {{
  background: transparent;
  border: none;
  border-radius: {_R};
}}
QPushButton#navBtn {{
  background: transparent;
  border: none;
  border-radius: {_R};
  color: #64748b;
  padding: 11px 12px;
  text-align: left;
  font-size: 14px;
  font-weight: 600;
}}
QPushButton#navBtn:hover {{
  background: #e8effd;
  color: #1e293b;
}}
QPushButton#navBtn:checked {{
  background: #dbeafe;
  color: #2563eb;
}}

QWidget#contentWrap {{ background: #f8fafc; }}
QScrollArea {{ border: none; outline: none; background: transparent; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QFrame {{ border: none; }}
QFrame#card {{
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: {_R};
}}
QScrollBar:vertical {{ background: #f1f5f9; width: 8px; border-radius: 4px; }}
QScrollBar::handle:vertical {{ background: #cbd5e1; border-radius: 4px; min-height: 24px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}

QLabel#cardTitle {{
  color: #64748b;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 1.2px;
}}

/* 섹션 헤더 */
QWidget#sectionHeaderBar {{
  background: transparent;
  border: none;
  padding-bottom: 2px;
  margin-bottom: 6px;
}}
QWidget#skillSlotsPage QWidget#sectionHeaderBar {{
  background: transparent;
}}
QLabel#sectionHeaderTitle {{
  color: #1e293b;
  font-size: 16px;
  font-weight: 800;
}}
QPushButton#sectionActionBtn {{
  background: #f1f5f9;
  border: none;
  border-radius: {_R};
  color: #475569;
  padding: 7px 14px;
  font-weight: 700;
  font-size: 13px;
  min-width: 84px;
}}
QPushButton#sectionActionBtn:hover {{
  background: #e2e8f0;
  color: #3b82f6;
}}
QPushButton#ghostIconBtn {{
  background: transparent;
  border: none;
  border-radius: {_R};
  color: #94a3b8;
  padding: 0px;
  font-weight: 700;
  font-size: 16px;
  min-width: 40px;
  max-width: 40px;
  min-height: 34px;
  max-height: 34px;
}}
QPushButton#ghostIconBtn:hover {{
  background: #eff6ff;
  color: #3b82f6;
}}
QPushButton#ghostIconBtn:disabled {{
  color: #cbd5e1;
  background: transparent;
}}

QWidget#bottomBar {{
  background: #f1f5f9;
  border-top: 1px solid #e2e8f0;
  min-height: 56px;
  max-height: 56px;
}}

QLabel {{
  color: #64748b;
  background: transparent;
  border: none;
}}
QLabel#formLabel {{
  color: #475569;
  background: transparent;
  border: none;
  padding: 0 10px 0 0;
  font-size: 14px;
}}
QLabel#formMath {{
  color: #94a3b8;
  background: transparent;
  border: none;
  padding: 0 4px;
  font-size: 14px;
}}
QLabel#sectionLabel {{ color: #1e293b; font-weight: 700; font-size: 14px; }}
QLabel#hintLabel {{ color: #94a3b8; font-size: 12px; }}
QLabel#statusLabel {{ color: #10b981; font-size: 12px; }}
QLabel#slotNumLabel {{ color: #3b82f6; font-weight: 900; font-size: 14px; }}

/* 체크박스 */
QCheckBox {{
  background: transparent;
  color: #475569;
  spacing: 8px;
}}
QCheckBox::indicator {{
  width: 18px;
  height: 18px;
  border-radius: 4px;
  border: 1px solid #cbd5e1;
  background: #ffffff;
}}
QCheckBox::indicator:checked {{
  background: #3b82f6;
  border: 1px solid #3b82f6;
}}
QCheckBox::indicator:hover {{
  border: 1px solid #93c5fd;
}}

QWidget#slotRowWrap {{
  border-radius: {_R};
  border: none;
  background: transparent;
}}

/* 스킬 라이브러리 헤더 */
QWidget#skillLibHeader {{
  background: #e2e8f0;
  border-radius: {_R};
}}
QLabel#skillLibHeaderLabel {{
  color: #334155;
  font-size: 11px;
  font-weight: bold;
}}

QSpinBox, QLineEdit, QDoubleSpinBox {{
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: {_R};
  padding: 9px 12px;
  min-height: 34px;
  font-size: 14px;
  color: #1e293b;
}}
QSpinBox:focus, QLineEdit:focus, QDoubleSpinBox:focus {{
  background: #eff6ff;
  border: 1px solid #93c5fd;
}}
QAbstractSpinBox::up-button, QAbstractSpinBox::down-button {{
  border: none;
  background: transparent;
  width: 18px;
}}
QLineEdit[armed="true"] {{ border: 1px solid #3b82f6; background: #eff6ff; }}

/* 스킬 슬롯 */
QWidget#skillSlotsPage {{ background: transparent; }}
QWidget#skillSlotsPage QWidget#slotRowsHost {{ background: transparent; }}
QWidget#skillSlotsPage QFrame#card {{
  background: #ffffff;
  border: 1px solid #e2e8f0;
}}
QWidget#skillSlotsPage QWidget#slotRowWrap {{ background: transparent; border: none; }}
QWidget#skillSlotsPage QLineEdit {{
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: {_R};
  padding: 9px 12px;
  min-height: 38px;
  font-size: 14px;
  color: #1e293b;
}}
QWidget#skillSlotsPage QLineEdit:focus {{
  background: #eff6ff;
  border: 1px solid #93c5fd;
}}
QWidget#skillSlotsPage QLineEdit#slotKeyEdit {{
  max-width: 168px;
  min-width: 100px;
}}
QWidget#skillSlotsPage QLineEdit[armed="true"] {{
  border: 1px solid #3b82f6;
  background: #eff6ff;
}}
QPushButton#slotRowBtn {{
  background: #f1f5f9;
  border: none;
  border-radius: {_R};
  color: #475569;
  padding: 8px 12px;
  font-weight: 600;
  font-size: 13px;
}}
QPushButton#slotRowBtn:hover {{
  background: #dbeafe;
  color: #1e293b;
}}
QPushButton#slotRowBtn:pressed {{ background: #bfdbfe; }}
QWidget#skillSlotsPage QPushButton#slotPriCombo {{
  background: #f1f5f9;
  border: none;
  border-radius: {_R};
  padding: 4px 6px;
  min-height: 30px;
  max-height: 34px;
  max-width: 100px;
  min-width: 86px;
  font-size: 12px;
  font-weight: 600;
  color: #475569;
}}
QWidget#skillSlotsPage QPushButton#slotPriCombo:hover {{ background: #e2e8f0; }}
QWidget#skillSlotsPage QPushButton#slotSwapPriCombo {{
  background: #f1f5f9;
  border: none;
  border-radius: {_R};
  padding: 4px 6px;
  min-height: 30px;
  max-height: 32px;
  min-width: 76px;
  max-width: 92px;
  font-size: 11px;
  font-weight: 600;
  color: #475569;
}}
QWidget#skillSlotsPage QPushButton#slotSwapPriCombo:hover {{ background: #e2e8f0; }}
QPushButton#skillInfoPriBtn {{
  background: #f1f5f9;
  border: none;
  border-radius: {_R};
  padding: 2px 4px;
  min-height: 28px;
  max-height: 32px;
  font-size: 12px;
  font-weight: 600;
  color: #475569;
}}
QPushButton#skillInfoPriBtn:hover {{ background: #e2e8f0; }}
QPushButton#skillInfoPriBtn:pressed {{ background: #cbd5e1; }}
QWidget#skillSlotsPage QLabel#slotMiniLbl {{
  color: #64748b;
  font-size: 11px;
  font-weight: 700;
  background: transparent;
}}
QWidget#skillSlotsPage QCheckBox#slotSkillChk {{
  color: #64748b;
  font-size: 11px;
  font-weight: 600;
}}
QWidget#skillSlotsPage QCheckBox#slotSkillChk::indicator {{ width: 14px; height: 14px; }}
QWidget#skillSlotsPage QCheckBox#slotSwapSkillChk {{
  color: #059669;
  font-size: 11px;
  font-weight: 600;
}}
QWidget#skillSlotsPage QCheckBox#slotSwapSkillChk::indicator {{ width: 14px; height: 14px; }}
QWidget#skillSlotsPage QCheckBox#slotSwapChk {{
  color: #0ea5e9;
  font-size: 11px;
  font-weight: 600;
}}
QPushButton#presetCard {{
  background: #f8fafc;
  border: 2px solid #e2e8f0;
  border-radius: {_R};
  color: #1e293b;
  text-align: center;
}}
QPushButton#presetCard[selected="true"] {{
  border: 2px solid #3b82f6;
  background: #eff6ff;
}}

QComboBox {{
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: {_R};
  padding: 9px 12px;
  min-height: 34px;
  font-size: 14px;
  color: #1e293b;
}}
QComboBox:focus {{ background: #eff6ff; border: 1px solid #93c5fd; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{
  background: #ffffff;
  border: 1px solid #e2e8f0;
  color: #1e293b;
  selection-background-color: #dbeafe;
}}
QPushButton {{
  background: #f1f5f9;
  border: none;
  border-radius: {_R};
  color: #475569;
  padding: 9px 16px;
  font-weight: 700;
  font-size: 14px;
}}
QPushButton:hover {{ background: #e2e8f0; color: #1e293b; }}
QPushButton:disabled {{ opacity: 0.42; }}
QPushButton#primary {{
  background: #3b82f6;
  border: none;
  color: #ffffff;
  font-weight: 800;
  border-radius: {_R};
  padding: 10px 22px;
  font-size: 14px;
}}
QPushButton#primary:hover {{ background: #2563eb; }}
QPushButton#danger {{
  background: #fef2f2;
  border: none;
  color: #dc2626;
  border-radius: {_R};
  padding: 9px 16px;
  font-weight: 700;
  font-size: 14px;
}}
QPushButton#danger:hover {{ background: #fee2e2; color: #b91c1c; }}
QPushButton#linkBtn {{
  background: transparent;
  border: none;
  color: #3b82f6;
  font-weight: 700;
  font-size: 13px;
  padding: 5px 10px;
}}
QPushButton#linkBtn:hover {{ color: #2563eb; }}
QLabel#accentHint {{ color: #3b82f6; font-size: 12px; font-weight: 600; background: transparent; }}
QSlider::groove:horizontal {{
  background: #e2e8f0;
  height: 4px;
  border-radius: 2px;
}}
QSlider::handle:horizontal {{
  background: #3b82f6;
  width: 14px;
  height: 14px;
  border-radius: 7px;
  margin: -5px 0;
}}
QSlider::sub-page:horizontal {{
  background: #3b82f6;
  border-radius: 2px;
}}
QSlider::add-page:horizontal {{
  background: #e2e8f0;
  border-radius: 2px;
}}
"""

# ─────────────────────────────── MainWindow ──────────────────────────────────
# (카테고리 제목, [(단색 기호, 라벨, 페이지 인덱스), ...])
_NAV_GROUPS: list[tuple[str, list[tuple[str, str, int]]]] = [
    ("캡처", [("◫", "캡처 설정", 0)]),
    ("매크로 설정", [
        ("≡", "매칭 설정", 1),
        ("⊞", "스킬 슬롯", 2),
        ("★", "스킬 정보", 6),
        ("⌗", "프리셋", 3),
    ]),
    ("실행", [("▶", "실행", 4)]),
    ("정보", [("ℹ", "버전 정보", 5)]),
]


def _nav_label_for_index(idx: int) -> str:
    for _, items in _NAV_GROUPS:
        for _sym, lab, i in items:
            if i == idx:
                return lab
    return "?"


class _Spinner(QWidget):
    """회전하는 호(arc) 로딩 스피너."""

    def __init__(self, parent: QWidget, size: int = 28, color: str = "#4ade80") -> None:
        super().__init__(parent)
        self.setFixedSize(size, size)
        self._color = color
        self._angle = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._step)

    def start(self) -> None:
        self._timer.start(25)

    def stop(self) -> None:
        self._timer.stop()

    def set_color(self, color: str) -> None:
        self._color = color
        self.update()

    def _step(self) -> None:
        self._angle = (self._angle + 9) % 360
        self.update()

    def paintEvent(self, _e) -> None:  # type: ignore[override]
        from PyQt6.QtGui import QPen
        from PyQt6.QtCore import Qt as _Qt
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        s = min(self.width(), self.height())
        margin = 3
        rect = QRectF(margin, margin, s - margin * 2, s - margin * 2)
        pen = QPen(QColor(self._color), 2.5)
        pen.setCapStyle(_Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.drawArc(rect, -self._angle * 16, 270 * 16)
        p.end()


class _InitWorker(QThread):
    """백그라운드 초기화: 디렉터리 생성 → 버전 체크."""

    ready = pyqtSignal(str)      # 완료 메시지
    status = pyqtSignal(str)     # 스플래시 상태 레이블용
    update_found = pyqtSignal(object)  # UpdateInfo 또는 None

    def run(self) -> None:
        import time as _time
        from src.core.paths import project_root
        from src.core.config import load_config, save_config
        from src.core.updater import check_update
        from src.app_meta import APP_VERSION

        t0 = _time.monotonic()

        self.status.emit("파일 탐색 중...")
        root = project_root()
        root.mkdir(parents=True, exist_ok=True)
        (root / "templates").mkdir(exist_ok=True)
        cfg_path = root / "config.json"
        if not cfg_path.exists():
            save_config(load_config())

        self.status.emit("버전 확인 중...")
        info = check_update(APP_VERSION, timeout=4.0)
        self.update_found.emit(info)

        elapsed = _time.monotonic() - t0
        _time.sleep(max(0.0, 1.0 - elapsed))

        self.ready.emit("준비 완료")


class SplashScreen(QWidget):
    """앱 시작 전 독립 창으로 표시되는 스플래시. 페이드인 → InitWorker → 페이드아웃 후 done 시그널."""

    done = pyqtSignal()

    def __init__(self, is_dark: bool = True) -> None:
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool,
        )
        self._is_dark = is_dark
        self._init_ready = False
        self._fade_in_done = False
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(640, 400)

        # 화면 중앙에 배치
        screen = QGuiApplication.primaryScreen()
        if screen:
            sg = screen.availableGeometry()
            self.move(
                sg.x() + (sg.width() - self.width()) // 2,
                sg.y() + (sg.height() - self.height()) // 2,
            )

        # 내부 레이아웃
        inner = QVBoxLayout(self)
        inner.setContentsMargins(24, 24, 24, 28)
        inner.setSpacing(10)
        inner.setAlignment(Qt.AlignmentFlag.AlignCenter)

        pm_lbl = QLabel(self)
        pm_lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        pm_lbl.setStyleSheet("background: transparent;")
        logo_path = yasu_logo_path()
        if logo_path is not None:
            pm = QPixmap(str(logo_path))
            if not pm.isNull():
                pm_lbl.setPixmap(
                    pm.scaledToHeight(160, Qt.TransformationMode.SmoothTransformation)
                )
        inner.addWidget(pm_lbl)

        title_color = "#34c46a" if is_dark else "#3b82f6"
        title = QLabel("도깨비 스킬 매크로", self)
        title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        title.setStyleSheet(
            f"color: {title_color}; background: transparent;"
            "font-size: 22pt; font-weight: 800;"
        )
        inner.addWidget(title)

        # 스피너 + 상태 레이블
        bottom_row = QHBoxLayout()
        bottom_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bottom_row.setSpacing(8)
        spinner_color = "#34c46a" if is_dark else "#3b82f6"
        self._spinner = _Spinner(self, size=22, color=spinner_color)
        bottom_row.addWidget(self._spinner)
        self._status_lbl = QLabel("파일 탐색 중...", self)
        status_color = "#8b949e" if is_dark else "#64748b"
        self._status_lbl.setStyleSheet(
            f"color: {status_color}; background: transparent; font-size: 11px;"
        )
        bottom_row.addWidget(self._status_lbl)
        inner.addLayout(bottom_row)

        self._effect = QGraphicsOpacityEffect(self)
        self._effect.setOpacity(0.0)
        self.setGraphicsEffect(self._effect)

        self._fade_in = QPropertyAnimation(self._effect, b"opacity", self)
        self._fade_in.setDuration(800)
        self._fade_in.setStartValue(0.0)
        self._fade_in.setEndValue(1.0)
        self._fade_in.setEasingCurve(QEasingCurve.Type.OutQuart)
        self._fade_in.finished.connect(self._on_fade_in_done)

        self._fade_out = QPropertyAnimation(self._effect, b"opacity", self)
        self._fade_out.setDuration(450)
        self._fade_out.setStartValue(1.0)
        self._fade_out.setEndValue(0.0)
        self._fade_out.setEasingCurve(QEasingCurve.Type.InCubic)
        self._fade_out.finished.connect(self._on_fade_out_done)

    def paintEvent(self, _e) -> None:  # type: ignore[override]
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), 16.0, 16.0)
        grad = QLinearGradient(0.0, 0.0, 0.0, float(self.height()))
        if self._is_dark:
            grad.setColorAt(0.0, QColor("#0d1117"))
            grad.setColorAt(1.0, QColor("#131b26"))
        else:
            grad.setColorAt(0.0, QColor("#f8fafc"))
            grad.setColorAt(1.0, QColor("#f1f5f9"))
        p.fillPath(path, QBrush(grad))
        p.end()

    def start(self) -> None:
        self._spinner.start()
        self._fade_in.start()

    def set_status(self, msg: str) -> None:
        self._status_lbl.setText(msg)

    def on_update_found(self, info: object) -> None:
        """업데이트 발견 시 상태 레이블 업데이트."""
        if info is not None:
            from src.core.updater import UpdateInfo
            if isinstance(info, UpdateInfo):
                self._status_lbl.setText(f"업데이트 발견: {info.tag}")

    def on_init_ready(self, _msg: str) -> None:
        """_InitWorker 완료 시 호출."""
        self._init_ready = True
        self._spinner.stop()
        if self._fade_in_done:
            QTimer.singleShot(150, self._fade_out.start)

    def _on_fade_in_done(self) -> None:
        self._fade_in_done = True
        if self._init_ready:
            QTimer.singleShot(150, self._fade_out.start)

    def _on_fade_out_done(self) -> None:
        self.hide()
        self.done.emit()


class _ResizeHandle(QWidget):
    """프레임리스 창 테두리에 배치되는 투명 리사이즈 핸들."""

    def __init__(
        self,
        window: QMainWindow,
        edges: Qt.Edge,
        cursor: Qt.CursorShape,
        parent: QWidget,
    ) -> None:
        super().__init__(parent)
        self._window = window
        self._edges = edges
        self.setCursor(cursor)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setStyleSheet("background: transparent;")

    def mousePressEvent(self, e) -> None:  # type: ignore[override]
        if e.button() == Qt.MouseButton.LeftButton:
            wh = self._window.windowHandle()
            if wh is not None:
                wh.startSystemResize(self._edges)
        super().mousePressEvent(e)


class ThemeToggle(QWidget):
    """타이틀바용 슬라이딩 다크/라이트 토글 스위치."""

    toggled = pyqtSignal(str)  # "dark" or "light"

    def __init__(self, is_dark: bool = True, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._dark = is_dark
        self._t: float = 0.0 if is_dark else 1.0
        self.setFixedSize(44, 22)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("라이트 모드" if is_dark else "다크 모드")
        self._anim = QPropertyAnimation(self, b"togglePos", self)
        self._anim.setDuration(200)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    # ── pyqtProperty ──────────────────────────────────────────────────────────

    @pyqtProperty(float)  # type: ignore[misc]
    def togglePos(self) -> float:
        return self._t

    @togglePos.setter  # type: ignore[misc]
    def togglePos(self, v: float) -> None:
        self._t = float(v)
        self.update()

    # ── public ────────────────────────────────────────────────────────────────

    def set_theme(self, mode: str) -> None:
        """애니메이션 없이 즉시 동기화."""
        self._dark = (mode == "dark")
        self._t = 0.0 if self._dark else 1.0
        self.update()

    # ── paint ─────────────────────────────────────────────────────────────────

    def paintEvent(self, _e) -> None:  # type: ignore[override]
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        t = self._t

        # 트랙 색: 다크=#34c46a(살짝 어두운 초록) → 라이트=#3b82f6(파랑) 보간
        tr = QColor(
            int(0x34 + (0x3B - 0x34) * t),
            int(0xC4 + (0x82 - 0xC4) * t),
            int(0x6A + (0xF6 - 0x6A) * t),
        )
        p.setBrush(tr)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(0, 0, w, h, h // 2, h // 2)

        # 썸(thumb)
        pad = 3
        td = h - pad * 2
        tx = int(pad + t * (w - h))
        p.setBrush(QColor("#ffffff"))
        p.drawEllipse(tx, pad, td, td)
        p.end()

    # ── mouse ─────────────────────────────────────────────────────────────────

    def mousePressEvent(self, e) -> None:  # type: ignore[override]
        if e.button() == Qt.MouseButton.LeftButton:
            self._dark = not self._dark
            self._anim.stop()
            self._anim.setStartValue(self._t)
            self._anim.setEndValue(0.0 if self._dark else 1.0)
            self._anim.start()
            self.setToolTip("라이트 모드" if self._dark else "다크 모드")
            self.toggled.emit("dark" if self._dark else "light")
        super().mousePressEvent(e)


class CustomTitleBar(QWidget):
    """Discord/Notion 스타일 커스텀 타이틀바. 드래그 이동, 최소화·최대화·닫기."""

    theme_toggled = pyqtSignal(str)  # "dark" or "light"

    def __init__(self, window: QMainWindow, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._window = window
        self._maximized = False
        self.setObjectName("customTitleBar")
        self.setFixedHeight(38)

        hl = QHBoxLayout(self)
        hl.setContentsMargins(10, 0, 4, 0)
        hl.setSpacing(0)

        # 아이콘
        ico_lbl = QLabel(self)
        ico_lbl.setObjectName("titleBarIcon")
        lp = yasu_logo_path()
        if lp:
            pm = QPixmap(str(lp))
            if not pm.isNull():
                ico_lbl.setPixmap(
                    pm.scaledToHeight(20, Qt.TransformationMode.SmoothTransformation)
                )
        hl.addWidget(ico_lbl)
        hl.addSpacing(7)

        # 제목
        ttl = QLabel("도깨비 스킬 매크로", self)
        ttl.setObjectName("titleBarTitle")
        hl.addWidget(ttl)
        hl.addStretch(1)

        # 버전
        ver = QLabel(f"v{APP_VERSION}", self)
        ver.setObjectName("titleBarVer")
        hl.addWidget(ver)
        hl.addSpacing(10)

        # 다크/라이트 토글
        self._theme_toggle = ThemeToggle(is_dark=(window._current_theme == "dark"), parent=self)
        self._theme_toggle.toggled.connect(self.theme_toggled)
        hl.addWidget(self._theme_toggle, 0, Qt.AlignmentFlag.AlignVCenter)
        hl.addSpacing(6)

        def _make_btn(text: str, obj: str, size: int = 40) -> QPushButton:
            b = QPushButton(text, self)
            b.setObjectName(obj)
            b.setFixedSize(size, 38)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            return b

        self._btn_min = _make_btn("─", "titleBtn", 40)
        self._btn_min.clicked.connect(window.showMinimized)
        hl.addWidget(self._btn_min)

        self._btn_max = _make_btn("□", "titleBtnMax", 40)
        self._btn_max.clicked.connect(self._toggle_maximize)
        hl.addWidget(self._btn_max)

        btn_close = _make_btn("✕", "titleBtnClose", 46)
        btn_close.clicked.connect(window.close)
        hl.addWidget(btn_close)

    def _toggle_maximize(self) -> None:
        if self._maximized:
            self._maximized = False
            self._btn_max.setText("□")
            self._window.showNormal()
        else:
            self._maximized = True
            self._btn_max.setText("❐")
            self._window.showMaximized()

    def set_theme(self, mode: str) -> None:
        """외부에서 테마 변경 시 토글 동기화."""
        if hasattr(self, "_theme_toggle"):
            self._theme_toggle.set_theme(mode)

    def mousePressEvent(self, e) -> None:  # type: ignore[override]
        if e.button() == Qt.MouseButton.LeftButton:
            wh = self._window.windowHandle()
            if wh is not None:
                wh.startSystemMove()
        super().mousePressEvent(e)

    def mouseDoubleClickEvent(self, e) -> None:  # type: ignore[override]
        if e.button() == Qt.MouseButton.LeftButton:
            self._toggle_maximize()
        super().mouseDoubleClickEvent(e)


class SpinnerWidget(QWidget):
    """회전하는 로딩 스피너(원형 호/Arc)."""

    def __init__(self, color: QColor | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(26, 26)
        self._color = color or QColor("#4ade80")
        self._shadow = QColor("#1e2d3d")

        self._angle: float = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(40)
        self._timer.timeout.connect(self._on_tick)
        self.hide()

    def start(self) -> None:
        self.show()
        self._timer.start()

    def stop(self) -> None:
        self._timer.stop()
        self.hide()
        self._angle = 0.0
        self.update()

    def _on_tick(self) -> None:
        self._angle = (self._angle + 22.5) % 360.0
        self.update()

    def paintEvent(self, _e) -> None:  # type: ignore[override]
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 배경 호
        bg_pen = QPen(self._shadow)
        bg_pen.setWidth(3)
        bg_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(bg_pen)

        rect = self.rect().adjusted(4, 4, -4, -4)
        p.drawArc(rect, 0, 90 * 16)

        # 회전 호
        fg_pen = QPen(self._color)
        fg_pen.setWidth(3)
        fg_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(fg_pen)

        start_angle_16 = int(self._angle * 16.0)
        p.drawArc(rect, start_angle_16, 90 * 16)
        p.end()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        # 커스텀 타이틀바: OS 프레임 제거 (초기에 한 번만 설정)
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setMinimumSize(1140, 720)
        _lp = yasu_logo_path()
        if _lp is not None:
            self.setWindowIcon(QIcon(str(_lp)))

        self._cfg = load_config()
        self._roi_dict: dict[str, int] | None = (
            dict(self._cfg.skill_bar_roi) if self._cfg.skill_bar_roi else None
        )
        self._skill_edits: list[KeyCaptureEdit] = []
        self._slot_pri_combos: list[QSpinBox] = []
        self._slot_skill_enabled_cbs: list[QCheckBox] = []
        self._slot_swap_skill_enabled_cbs: list[QCheckBox] = []  # ② 독립 토글
        self._slot_pri2_combos: list[QSpinBox] = []
        self._slot_save2_btns: list[QPushButton] = []
        self._slot_swap_toggles: list[QCheckBox] = []
        self._slot_skill_combos: list[QComboBox] = []    # 바1 슬롯-스킬 선택
        self._swap_skill_combos: list[QComboBox] = []    # 바2 슬롯-스킬 선택
        self._worker: CycleWorker | None = None
        self._pending_update_info: object = None
        self._pending_new_exe = None
        self._skill_info_row_widgets: list[dict] = []
        self._settings = QSettings("Yasu2947", "DokkaebiSkillMacro")
        self._current_theme: str = self._settings.value("theme", "dark", type=str)  # type: ignore[assignment]
        self._hotkey_listener = HotkeyListener(self)
        self._slot_roi_list: list[dict[str, int] | None] = MainWindow._slot_roi_list_from_cfg(self._cfg)
        self._preset_scroll: QScrollArea | None = None
        self._preset_grid_inner: QWidget | None = None
        self._preset_cards: dict[str, QPushButton] = {}
        self._selected_preset_name: str | None = None
        self._nav_btns: list[QPushButton] = []
        self._spinner: SpinnerWidget | None = None

        # 루트: 커스텀 타이틀바 + 스택
        _root = QWidget(self)
        _root.setObjectName("rootContainer")
        _root_vl = QVBoxLayout(_root)
        _root_vl.setContentsMargins(0, 0, 0, 0)
        _root_vl.setSpacing(0)

        self._title_bar = CustomTitleBar(self, parent=_root)
        self._title_bar.theme_toggled.connect(self._apply_theme)
        _root_vl.addWidget(self._title_bar)

        self._stack = QStackedWidget(_root)
        _root_vl.addWidget(self._stack, 1)

        self.setCentralWidget(_root)

        # 프레임리스 8방향 리사이즈 핸들 (nativeEvent 대신 Qt startSystemResize 사용)
        _root.installEventFilter(self)
        self._resize_handles: list[QWidget] = []
        self._root_ref = _root
        QTimer.singleShot(0, self._install_resize_handles)

        # ── Welcome page ────────────────────────────────────────────────────
        self._welcome = WelcomePage(
            APP_VERSION, CHANGELOG_LINES, CHANGELOG_DATE,
            prev_version=PREV_VERSION, prev_lines=PREV_LINES,
            is_dark=(self._current_theme == "dark"),
            parent=self._stack,
        )
        self._welcome.continue_clicked.connect(self._on_welcome_continue)
        self._welcome.theme_changed.connect(self._apply_theme)
        self._stack.addWidget(self._welcome)

        self._slot_rebuild_timer = QTimer(self)
        self._slot_rebuild_timer.setSingleShot(True)
        self._slot_rebuild_timer.setInterval(120)
        self._slot_rebuild_timer.timeout.connect(self._rebuild_slot_rows)

        self._stack.addWidget(self._build_macro_page())

        self._place_window()

        # Hotkey — pynput Listener 시작을 윈도우 표시 이후로 지연
        self._hotkey_listener.triggered.connect(self._on_hotkey_triggered)
        QTimer.singleShot(600, lambda: self._apply_hotkey(self._cfg.run_hotkey or ""))
        self.ed_run_hotkey.textChanged.connect(
            lambda _t: self._apply_hotkey(self.ed_run_hotkey.text().strip())
        )

        self._stack.setCurrentIndex(0)  # 항상 환영 화면부터

        # 저장된 테마를 UI 전체에 적용 (다크가 아닌 경우)
        if self._current_theme != "dark":
            QTimer.singleShot(0, lambda: self._apply_theme(self._current_theme))

        self.setUpdatesEnabled(True)

    # ═══════════════════════════ MACRO PAGE BUILD ════════════════════════════

    def _build_macro_page(self) -> QWidget:
        page = QWidget(self._stack)
        vl = QVBoxLayout(page)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(0)

        vl.addWidget(self._build_header_bar(page))

        mid = QWidget(page)
        hl = QHBoxLayout(mid)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(0)
        hl.addWidget(self._build_sidebar(mid))

        self._content_stack = QStackedWidget(mid)
        self._content_stack.setObjectName("contentWrap")
        self._content_stack.addWidget(self._wrap_scroll(self._page_screen_roi()))     # 0
        self._content_stack.addWidget(self._wrap_scroll(self._page_match_settings()))  # 1
        self._content_stack.addWidget(self._wrap_scroll(self._page_skill_slots()))     # 2
        self._content_stack.addWidget(self._wrap_scroll(self._page_presets()))         # 3
        self._content_stack.addWidget(self._wrap_scroll(self._page_run()))             # 4
        self._content_stack.addWidget(self._wrap_scroll(self._page_version_info()))    # 5
        self._content_stack.addWidget(self._wrap_scroll(self._page_skill_info()))      # 6
        hl.addWidget(self._content_stack, 1)

        vl.addWidget(mid, 1)
        vl.addWidget(self._build_bottom_bar(page))
        return page

    # ── header bar ────────────────────────────────────────────────────────────

    def _build_header_bar(self, parent: QWidget | None = None) -> QWidget:
        bar = QWidget(parent)
        bar.setObjectName("headerBar")
        hl = QHBoxLayout(bar)
        hl.setContentsMargins(16, 0, 16, 0)
        hl.setSpacing(10)

        btn_back = QPushButton("‹")
        btn_back.setObjectName("headerBtn")
        btn_back.setFixedWidth(40)
        btn_back.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        btn_back.clicked.connect(self._show_welcome)

        hl.addWidget(btn_back)
        _hlogo = yasu_logo_path()
        if _hlogo is not None:
            pm = QPixmap(str(_hlogo))
            if not pm.isNull():
                lg = QLabel(bar)
                lg.setPixmap(pm.scaledToHeight(30, Qt.TransformationMode.SmoothTransformation))
                lg.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
                hl.addWidget(lg)

        self._header_title = QLabel(f"도깨비 스킬 매크로  |  {_nav_label_for_index(0)}")
        self._header_title.setObjectName("headerTitle")

        ver = QLabel(f"v{APP_VERSION}")
        ver.setStyleSheet("color:rgba(255,255,255,0.55);font-size:12px;")

        self._btn_theme = QPushButton("☀ 라이트" if self._current_theme == "dark" else "🌙 다크")
        self._btn_theme.setObjectName("headerBtn")
        self._btn_theme.clicked.connect(self._toggle_theme)
        # 사용자 요청: 서버 엔진 다크 톤으로 고정(라이트 전환 UI 제거)
        self._btn_theme.setVisible(False)

        hl.addWidget(self._header_title)
        hl.addSpacing(8)
        hl.addWidget(ver)
        hl.addStretch(1)
        hl.addWidget(self._btn_theme)
        return bar

    # ── sidebar ───────────────────────────────────────────────────────────────

    def _build_sidebar(self, parent: QWidget | None = None) -> QWidget:
        side = QWidget(parent)
        side.setObjectName("sidebar")
        vl = QVBoxLayout(side)
        vl.setContentsMargins(0, 8, 0, 12)
        vl.setSpacing(0)

        brand = QLabel("SKILL MACRO")
        brand.setObjectName("sidebarBrand")
        vl.addWidget(brand)

        ripple_accent = (
            QColor(0, 173, 181)
            if self._current_theme == "light"
            else QColor(74, 222, 128)
        )
        for cat_title, items in _NAV_GROUPS:
            cat = QLabel(cat_title.upper())
            cat.setObjectName("navCat")
            vl.addWidget(cat)

            block = QFrame(side)
            block.setObjectName("navBlock")
            bl = QVBoxLayout(block)
            bl.setContentsMargins(6, 6, 6, 6)
            bl.setSpacing(4)

            for sym, label, page_idx in items:
                btn = NavRippleButton(
                    f"{sym}  {label}",
                    parent=block,
                    ripple_color=ripple_accent,
                    corner_radius=0.0 if self._current_theme == "light" else 6.0,
                )
                btn.setObjectName("navBtn")
                btn.setCheckable(True)
                btn.setFlat(True)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.setProperty("navPage", page_idx)
                pi = page_idx
                btn.clicked.connect(lambda _=False, n=pi: self._switch_page(n))
                bl.addWidget(btn)
                self._nav_btns.append(btn)

            vl.addWidget(block)

        if self._nav_btns:
            for b in self._nav_btns:
                b.setChecked(int(b.property("navPage") or 0) == 0)

        vl.addStretch(1)
        return side

    def _switch_page(self, idx: int) -> None:
        if idx == self._content_stack.currentIndex():
            return
        self._content_stack.setCurrentIndex(idx)
        self._header_title.setText(
            f"도깨비 스킬 매크로  |  {_nav_label_for_index(idx)}"
        )
        for btn in self._nav_btns:
            btn.setChecked(int(btn.property("navPage") or -1) == idx)
        if idx == 5 and self._pending_update_info is not None:
            self._apply_update_info_to_ui(self._pending_update_info)
            self._pending_update_info = None

    def _ensure_macro_page_front(self) -> None:
        """웰컴 화면이면 매크로 본 화면으로 전환 (실행 탭·로그 표시용)."""
        if self._stack.currentIndex() == 0:
            self._stack.setCurrentIndex(1)

    # ── bottom bar ─────────────────────────────────────────────────────────────

    def _build_bottom_bar(self, parent: QWidget | None = None) -> QWidget:
        bar = QWidget(parent)
        bar.setObjectName("bottomBar")
        hl = QHBoxLayout(bar)
        hl.setContentsMargins(210, 0, 20, 0)
        btn_reload = QPushButton("↻  다시 불러오기")
        btn_save = QPushButton("저장")
        btn_save.setObjectName("primary")
        btn_reload.clicked.connect(self._reload)
        btn_save.clicked.connect(self._save)
        hl.addStretch(1)
        hl.addWidget(btn_reload)
        hl.addSpacing(8)
        hl.addWidget(btn_save)
        return bar

    # ── helpers ───────────────────────────────────────────────────────────────

    def _wrap_scroll(self, content: QWidget) -> MacroScrollArea:
        # content_stack을 parent로 지정 → top-level HWND 생성 방지 (reparent 시 flash 제거)
        sa = MacroScrollArea(self._content_stack)
        sa.setWidgetResizable(True)
        sa.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        sa.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        sa.setFrameShape(QFrame.Shape.NoFrame)
        sa.viewport().setAutoFillBackground(False)
        sa.setWidget(content)
        return sa

    def _card(self, parent: QWidget, title: str = "") -> tuple[QFrame, QVBoxLayout]:
        frame = QFrame(parent)
        frame.setObjectName("card")
        vl = QVBoxLayout(frame)
        vl.setContentsMargins(18, 14, 18, 16)
        vl.setSpacing(10)
        if title:
            lbl = QLabel(title.upper())
            lbl.setObjectName("cardTitle")
            vl.addWidget(lbl)
        return frame, vl

    def _form_label(self, text: str) -> QLabel:
        lb = QLabel(text)
        lb.setObjectName("formLabel")
        lb.setAlignment(
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeading
        )
        return lb

    @staticmethod
    def _form_math_label(text: str) -> QLabel:
        m = QLabel(text)
        m.setObjectName("formMath")
        m.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return m

    def _form_row(self, label: str, widget: QWidget) -> QHBoxLayout:
        hl = QHBoxLayout()
        hl.setSpacing(12)
        hl.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        lbl = self._form_label(label)
        lbl.setFixedWidth(160)
        hl.addWidget(lbl, 0, Qt.AlignmentFlag.AlignVCenter)
        hl.addWidget(widget, 1, Qt.AlignmentFlag.AlignVCenter)
        return hl

    # ═══════════════════════════ PAGE BUILDERS ═══════════════════════════════

    def _page_screen_roi(self) -> QWidget:
        page = QWidget(self)
        vl = QVBoxLayout(page)
        vl.setContentsMargins(32, 24, 32, 28)
        vl.setSpacing(16)

        # ── 스킬바 범위 카드 ─────────────────────────────────────────────────
        card2, cv2 = self._card(page, "스킬바 범위 지정")
        self.lbl_roi = QLabel(self._roi_status_text())
        self.lbl_roi.setObjectName("statusLabel")
        self.lbl_roi.setWordWrap(True)
        cv2.addWidget(self.lbl_roi)

        btn_row = QHBoxLayout()
        btn_pick = QPushButton("+  스킬바 범위 지정")
        btn_pick.clicked.connect(self._pick_roi)
        btn_clear = QPushButton("초기화")
        btn_clear.setObjectName("danger")
        btn_clear.clicked.connect(self._clear_roi)
        btn_row.addWidget(btn_pick)
        btn_row.addWidget(btn_clear)
        btn_row.addStretch(1)
        cv2.addLayout(btn_row)

        self._lbl_roi_mode = QLabel()
        self._lbl_roi_mode.setObjectName("hintLabel")
        self._lbl_roi_mode.setWordWrap(True)
        cv2.addWidget(self._lbl_roi_mode)
        vl.addWidget(card2)

        vl.addStretch(1)
        return page

    def _page_match_settings(self) -> QWidget:
        page = QWidget(self)
        vl = QVBoxLayout(page)
        vl.setContentsMargins(32, 24, 32, 28)
        vl.setSpacing(16)

        # ── 슬롯 & 템플릿 카드 ─────────────────────────────────────────────
        card, cv = self._card(page, "슬롯 · 템플릿")
        form = QFormLayout()
        form.setSpacing(12)
        form.setHorizontalSpacing(18)
        form.setFormAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
        )

        self.sp_slots = NoWheelSpinBox()
        self.sp_slots.setRange(1, 7)
        self.sp_slots.blockSignals(True)
        self.sp_slots.setValue(self._cfg.slot_count)
        self.sp_slots.blockSignals(False)

        ed_tpl_row = QHBoxLayout(); ed_tpl_row.setSpacing(6)
        self.ed_template = QLineEdit()
        self.ed_template.setText(self._cfg.template_dir)
        btn_browse = QPushButton("찾아보기…")
        btn_browse.clicked.connect(self._browse_template_dir)
        ed_tpl_row.addWidget(self.ed_template, 1)
        ed_tpl_row.addWidget(btn_browse)

        form.addRow(self._form_label("슬롯 수"), self.sp_slots)
        form.addRow(self._form_label("템플릿 폴더"), ed_tpl_row)
        cv.addLayout(form)
        hint = QLabel(
            "슬롯은 최대 7개입니다. 각 슬롯의 준비(저장 1)·스왑(저장 2) PNG가 이 폴더에 저장됩니다."
        )
        hint.setObjectName("hintLabel")
        cv.addWidget(hint)
        vl.addWidget(card)

        # ── 매칭 파라미터 카드 ──────────────────────────────────────────────
        card2, cv2 = self._card(page, "매칭 파라미터")
        form2 = QFormLayout()
        form2.setSpacing(12)
        form2.setHorizontalSpacing(18)
        form2.setFormAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
        )

        self.dbl_threshold = NoWheelDoubleSpinBox()
        self.dbl_threshold.setRange(0.5, 1.0); self.dbl_threshold.setDecimals(3)
        self.dbl_threshold.setSingleStep(0.01); self.dbl_threshold.setValue(self._cfg.match_threshold)

        self.dbl_timeout = NoWheelDoubleSpinBox()
        self.dbl_timeout.setRange(1.0, 600.0); self.dbl_timeout.setDecimals(1)
        self.dbl_timeout.setValue(self._cfg.slot_timeout_sec)
        self.dbl_timeout.setSuffix(" 초")

        self.sp_poll = NoWheelSpinBox()
        self.sp_poll.setRange(20, 500); self.sp_poll.setValue(self._cfg.poll_interval_ms)
        self.sp_poll.setSuffix(" ms")

        self.sp_after = NoWheelSpinBox()
        self.sp_after.setRange(0, 2000); self.sp_after.setValue(self._cfg.post_press_delay_ms)
        self.sp_after.setSuffix(" ms")

        self.sp_slot_gap = NoWheelSpinBox()
        self.sp_slot_gap.setRange(0, 2000); self.sp_slot_gap.setValue(self._cfg.slot_gap_ms)
        self.sp_slot_gap.setSuffix(" ms")

        self.ed_swap = KeyCaptureEdit(card2)
        self.ed_swap.setText(self._cfg.swap_key)

        self.sp_swap_delay = NoWheelSpinBox()
        self.sp_swap_delay.setRange(200, 3000)
        self.sp_swap_delay.setSingleStep(50)
        self.sp_swap_delay.setValue(self._cfg.swap_delay_ms)
        self.sp_swap_delay.setSuffix(" ms")

        form2.addRow(self._form_label("매칭 임계값"), self.dbl_threshold)
        form2.addRow(self._form_label("전체 대기 시간"), self.dbl_timeout)
        form2.addRow(self._form_label("폴링 간격"), self.sp_poll)
        form2.addRow(self._form_label("키 입력 후 대기"), self.sp_after)
        form2.addRow(self._form_label("스킬 간 딜레이"), self.sp_slot_gap)
        form2.addRow(self._form_label("스왑 키"), self.ed_swap)
        form2.addRow(self._form_label("스왑 후 대기"), self.sp_swap_delay)
        cv2.addLayout(form2)

        hint2 = QLabel("전체 대기 시간: 모든 슬롯이 발동될 때까지 재시도하는 총 한도.")
        hint2.setObjectName("hintLabel"); hint2.setWordWrap(True)
        cv2.addWidget(hint2)
        vl.addWidget(card2)

        vl.addStretch(1)

        # slots 값 변경 연결 (레이아웃 다 만들어진 후)
        self.sp_slots.valueChanged.connect(self._on_slot_count_changed)
        return page

    def _slot_add_row(self) -> None:
        n = self.sp_slots.value()
        if n < 7:
            self.sp_slots.setValue(n + 1)

    def _open_template_folder(self) -> None:
        """설정된 templates 폴더를 파일 탐색기로 엽니다."""
        from src.core.paths import project_root
        td = project_root() / (self._cfg.template_dir or "templates")
        td.mkdir(parents=True, exist_ok=True)
        os.startfile(str(td))

    def _slot_remove_row(self) -> None:
        n = self.sp_slots.value()
        if n > 1:
            self.sp_slots.setValue(n - 1)

    def _sync_slot_hdr_buttons(self) -> None:
        n = self.sp_slots.value()
        if getattr(self, "_slot_hdr_add_btn", None):
            self._slot_hdr_add_btn.setEnabled(n < 7)
        if getattr(self, "_slot_hdr_rem_btn", None):
            self._slot_hdr_rem_btn.setEnabled(n > 1)

    def _page_skill_slots(self) -> QWidget:
        page = QWidget(self)
        page.setObjectName("skillSlotsPage")
        vl = QVBoxLayout(page)
        vl.setContentsMargins(32, 24, 32, 28)
        vl.setSpacing(16)

        card, cv = self._card(page, "")
        hdr = QWidget(page)
        hdr.setObjectName("sectionHeaderBar")
        hdr.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        hdr.setStyleSheet("background: transparent;")
        hh = QHBoxLayout(hdr)
        hh.setContentsMargins(0, 0, 0, 0)
        hh.setSpacing(10)
        ht = QLabel("스킬 슬롯")
        ht.setObjectName("sectionHeaderTitle")
        hh.addWidget(ht, 0, Qt.AlignmentFlag.AlignVCenter)
        hh.addStretch(1)
        hdr_btns = QWidget(hdr)
        hb = QHBoxLayout(hdr_btns)
        hb.setContentsMargins(0, 0, 0, 0)
        hb.setSpacing(6)
        hb.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight)
        # 📁 템플릿 폴더 열기 버튼
        btn_open_tmpl = QPushButton("📁")
        btn_open_tmpl.setObjectName("ghostIconBtn")
        btn_open_tmpl.setToolTip("템플릿 이미지 폴더 열기")
        btn_open_tmpl.setFixedSize(34, 34)
        btn_open_tmpl.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_open_tmpl.clicked.connect(self._open_template_folder)
        hb.addWidget(btn_open_tmpl, 0, Qt.AlignmentFlag.AlignVCenter)

        self._slot_hdr_rem_btn = QPushButton("\u2212")
        self._slot_hdr_rem_btn.setObjectName("ghostIconBtn")
        self._slot_hdr_rem_btn.setToolTip("마지막 슬롯 제거 (최소 1)")
        self._slot_hdr_rem_btn.clicked.connect(self._slot_remove_row)
        self._slot_hdr_add_btn = QPushButton("+")
        self._slot_hdr_add_btn.setObjectName("ghostIconBtn")
        self._slot_hdr_add_btn.setToolTip("슬롯 한 칸 추가 (최대 7)")
        self._slot_hdr_add_btn.clicked.connect(self._slot_add_row)
        pair_font = QFont(QApplication.font())
        pair_font.setPointSize(15)
        pair_font.setBold(True)
        for b in (self._slot_hdr_rem_btn, self._slot_hdr_add_btn):
            b.setFont(pair_font)
            b.setFixedSize(40, 34)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            hb.addWidget(b, 0, Qt.AlignmentFlag.AlignVCenter)
        hh.addWidget(hdr_btns, 0, Qt.AlignmentFlag.AlignVCenter)
        cv.addWidget(hdr)

        hint = QLabel(
            "각 줄: ①차 순서(우선·보통·후순) → 키 → [영역] → [저장 1] PNG. "
            "[스왑]을 켜면 ②차 순서·[저장 2]가 나타납니다(자동 스왑 2라운드). "
            "[사용]을 끄면 해당 슬롯은 1·2라운드 모두 건너뜁니다. "
            "슬롯은 최대 7개(저장 1+2로 슬롯당 최대 2장의 템플릿)입니다."
        )
        hint.setObjectName("hintLabel")
        hint.setWordWrap(True)
        cv.addWidget(hint)

        self._slot_rows_host = QWidget(card)
        self._slot_rows_host.setObjectName("slotRowsHost")
        self._slot_rows_inner = QVBoxLayout(self._slot_rows_host)
        self._slot_rows_inner.setSpacing(4)
        cv.addWidget(self._slot_rows_host, 1)

        self._rebuild_slot_rows()
        self._sync_slot_hdr_buttons()
        vl.addWidget(card)

        key_card, kv = self._card(page, "키 입력 방법")
        key_hint = QLabel(
            "입력란을 클릭한 뒤 키 또는 마우스 버튼을 누르면 자동 인식됩니다.\n"
            "왼쪽 클릭은 한 번 더 눌러야 mb_left로 저장됩니다.\n"
            "지원: 단일 문자(2, f), space, enter, shift, f1~f12, mouse4, mouse5, mb_left, mb_right"
        )
        key_hint.setObjectName("hintLabel"); key_hint.setWordWrap(True)
        kv.addWidget(key_hint)
        vl.addWidget(key_card)

        vl.addStretch(1)
        self._refresh_roi_mode_label()
        return page

    def _page_presets(self) -> QWidget:
        page = QWidget(self)
        vl = QVBoxLayout(page)
        vl.setContentsMargins(32, 24, 32, 28)
        vl.setSpacing(16)

        card, cv = self._card(page, "프리셋 관리")

        tip = QLabel(
            "각 슬롯 [슬롯 영역]을 모두 지정한 뒤 저장하면 ROI와 "
            "현재 템플릿 폴더의 slot_*_ready.png / slot_*_swap.png 가 "
            "프로젝트 templates/<이름>/ 에 함께 저장됩니다. "
            "불러오면 ROI와 템플릿 경로가 함께 적용됩니다."
        )
        tip.setObjectName("hintLabel")
        tip.setWordWrap(True)
        cv.addWidget(tip)

        self._preset_scroll = QScrollArea(card)
        self._preset_scroll.setWidgetResizable(True)
        self._preset_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._preset_scroll.setMinimumHeight(180)
        self._preset_grid_inner = QWidget(self._preset_scroll)
        self._preset_grid_inner.setObjectName("presetGridInner")
        gl = QGridLayout(self._preset_grid_inner)
        gl.setSpacing(10)
        gl.setContentsMargins(4, 4, 4, 4)
        self._preset_scroll.setWidget(self._preset_grid_inner)
        cv.addWidget(self._preset_scroll, 1)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_save_p = QPushButton("프리셋 저장…")
        btn_save_p.setObjectName("primary")
        btn_save_p.clicked.connect(self._on_preset_save)
        btn_load_p = QPushButton("불러오기")
        btn_load_p.clicked.connect(self._on_preset_load)
        btn_del_p = QPushButton("삭제")
        btn_del_p.setObjectName("danger")
        btn_del_p.clicked.connect(self._on_preset_delete)
        btn_row.addWidget(btn_save_p)
        btn_row.addWidget(btn_load_p)
        btn_row.addWidget(btn_del_p)
        btn_row.addStretch(1)
        cv.addLayout(btn_row)
        vl.addWidget(card)

        self._refresh_preset_grid()
        vl.addStretch(1)
        return page

    def _page_run(self) -> QWidget:
        page = QWidget(self)
        page.setObjectName("runPage")
        vl = QVBoxLayout(page)
        vl.setContentsMargins(32, 24, 32, 28)
        vl.setSpacing(16)

        # ── 실행 키 바인딩 ─────────────────────────────────────────────────────
        card_hk, cv_hk = self._card(page, "실행 키 바인딩")
        form_hk = QFormLayout()
        form_hk.setSpacing(12)
        form_hk.setHorizontalSpacing(18)
        self.ed_run_hotkey = KeyCaptureEdit(card_hk)
        self.ed_run_hotkey.setText(self._cfg.run_hotkey or "")
        self.ed_run_hotkey.setPlaceholderText("클릭 후 키/마우스 버튼 — 없으면 비워두기")
        form_hk.addRow(self._form_label("실행 키"), self.ed_run_hotkey)
        cv_hk.addLayout(form_hk)
        hk_hint = QLabel(
            "게임 중에도 이 키로 1사이클을 시작합니다. 실행 중일 때 같은 키를 누르면 중단됩니다.\n"
            "예: mouse4, mouse5, f9, space, mb_left\n"
            "※ 키보드 실행 키가 안 먹으면 Windows 입력기를 영문으로 두거나, mouse4·mouse5처럼 마우스 측면키를 쓰는 것을 권장합니다. "
            "게임이 관리자 권한이면 이 프로그램도 '관리자 권한으로 실행'해야 전역 단축키가 동작할 수 있습니다."
        )
        hk_hint.setObjectName("hintLabel"); hk_hint.setWordWrap(True)
        cv_hk.addWidget(hk_hint)
        vl.addWidget(card_hk)

        card_as, cv_as = self._card(page, "자동 스왑")
        self._chk_auto_run = QCheckBox(
            "자동 스왑 사용 (1라운드 종료 후 스왑 키 입력 → [스왑] 켠 슬롯의 저장 2 PNG로 2라운드)"
        )
        self._chk_auto_run.setChecked(self._cfg.auto_swap_enabled)
        self._chk_auto_run.setCursor(Qt.CursorShape.PointingHandCursor)
        cv_as.addWidget(self._chk_auto_run)
        as_hint = QLabel(
            "슬롯마다 [스왑]과 ②차 순서는 스킬 슬롯 탭에서 설정합니다.\n"
            "2라운드가 끝나면 항상 스왑 키를 한 번 더 눌러 원래 스킬바로 돌아갑니다."
        )
        as_hint.setObjectName("hintLabel")
        as_hint.setWordWrap(True)
        cv_as.addWidget(as_hint)
        vl.addWidget(card_as)

        # ── 딜사이클 모드 카드 ────────────────────────────────────────────────
        card_dc, cv_dc = self._card(page, "딜사이클 모드")
        self._chk_cycle = QCheckBox("딜사이클 모드 사용 (스킬 정보 탭 쿨타임 기반 최적 순서 · 중단까지 무한)")
        self._chk_cycle.setChecked(self._cfg.cycle_mode_enabled)
        self._chk_cycle.setCursor(Qt.CursorShape.PointingHandCursor)
        self._chk_cycle.toggled.connect(self._on_cycle_mode_toggled)
        cv_dc.addWidget(self._chk_cycle)

        self._lbl_cycle_rotation = QLabel("")
        self._lbl_cycle_rotation.setObjectName("accentHint")
        self._lbl_cycle_rotation.setWordWrap(True)
        cv_dc.addWidget(self._lbl_cycle_rotation)

        dc_hint = QLabel(
            "스킬 정보 탭에서 슬롯별 정보(쿨타임·배율·타수)를 입력하세요.\n"
            "실행 버튼(또는 단축키)이 딜사이클 모드로 자동 전환됩니다."
        )
        dc_hint.setObjectName("hintLabel")
        dc_hint.setWordWrap(True)
        cv_dc.addWidget(dc_hint)
        vl.addWidget(card_dc)

        # ── 실행 카드 ───────────────────────────────────────────────────────
        card_run, cv_run = self._card(page, "1사이클 실행")
        run_desc = QLabel(
            "슬롯 1→N 순서로 준비 상태(템플릿 매칭)인 스킬을 발동합니다.\n"
            "미발동 슬롯은 전체 대기 시간 내에서 자동 재시도됩니다."
        )
        run_desc.setWordWrap(True)
        cv_run.addWidget(run_desc)

        run_btn_row = QHBoxLayout(); run_btn_row.setSpacing(10)
        self.btn_run = QPushButton("1사이클 실행")
        self.btn_run.setObjectName("primary")
        self.btn_run.setMinimumHeight(48)
        self.btn_run.clicked.connect(self._run_cycle)
        self.btn_stop = QPushButton("중단")
        self.btn_stop.setObjectName("danger")
        self.btn_stop.setMinimumHeight(48)
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self._stop_cycle)
        run_btn_row.addWidget(self.btn_run, 2)
        run_btn_row.addWidget(self.btn_stop, 1)
        run_btn_row.addSpacing(12)
        self._spinner = SpinnerWidget(parent=self)
        run_btn_row.addWidget(self._spinner, 0, Qt.AlignmentFlag.AlignVCenter)
        run_btn_row.addStretch(1)
        cv_run.addLayout(run_btn_row)

        self.log_lbl = QLabel("")
        self.log_lbl.setObjectName("hintLabel")
        self.log_lbl.setWordWrap(True)
        self.log_lbl.setMinimumHeight(80)
        self.log_lbl.setAlignment(Qt.AlignmentFlag.AlignTop)
        cv_run.addWidget(self.log_lbl)
        vl.addWidget(card_run)

        vl.addStretch(1)
        self._sync_run_button_label()
        return page

    def _page_version_info(self) -> QWidget:
        from src.app_meta import APP_VERSION, CHANGELOG_DATE, CHANGELOG_LINES, PREV_VERSION, PREV_LINES

        page = QWidget(self)
        page.setObjectName("versionInfoPage")
        vl = QVBoxLayout(page)
        vl.setContentsMargins(32, 24, 32, 28)
        vl.setSpacing(16)

        # ── 업데이트 카드 ──
        card_up, cv_up = self._card(page, "업데이트")
        up_top = QHBoxLayout()
        self._lbl_update_status = QLabel(f"현재 버전: v{APP_VERSION}")
        self._lbl_update_status.setObjectName("hintLabel")
        up_top.addWidget(self._lbl_update_status, 1)
        self._btn_check_update = QPushButton("업데이트 확인")
        self._btn_check_update.setFixedWidth(120)
        self._btn_check_update.clicked.connect(self._check_update_manual)
        up_top.addWidget(self._btn_check_update)
        cv_up.addLayout(up_top)

        self._update_progress_row = QWidget()
        pr_layout = QHBoxLayout(self._update_progress_row)
        pr_layout.setContentsMargins(0, 4, 0, 0)
        pr_layout.setSpacing(8)
        self._update_progress = QProgressBar()
        self._update_progress.setRange(0, 100)
        self._update_progress.setValue(0)
        self._update_progress.setFixedHeight(8)
        self._update_progress.setTextVisible(False)
        pr_layout.addWidget(self._update_progress, 1)
        self._btn_apply_update = QPushButton("재시작하여 적용")
        self._btn_apply_update.setObjectName("primary")
        self._btn_apply_update.setFixedWidth(130)
        self._btn_apply_update.hide()
        self._btn_apply_update.clicked.connect(self._apply_update)
        pr_layout.addWidget(self._btn_apply_update)
        self._update_progress_row.hide()
        cv_up.addWidget(self._update_progress_row)
        vl.addWidget(card_up)

        # ── 현재 버전 체인지로그 ──
        card_cur, cv_cur = self._card(page, f"v{APP_VERSION}  ({CHANGELOG_DATE})")
        for headline, desc in CHANGELOG_LINES:
            row = QHBoxLayout()
            row.setSpacing(8)
            bullet = QLabel("•")
            bullet.setFixedWidth(12)
            bullet.setObjectName("accentHint")
            txt = QLabel(f"<b>{headline}</b>  {desc}")
            txt.setWordWrap(True)
            txt.setObjectName("hintLabel")
            row.addWidget(bullet)
            row.addWidget(txt, 1)
            cv_cur.addLayout(row)
        vl.addWidget(card_cur)

        card_prev, cv_prev = self._card(page, f"v{PREV_VERSION}  이전 변경사항")
        for line in PREV_LINES:
            row2 = QHBoxLayout()
            row2.setSpacing(8)
            b2 = QLabel("·")
            b2.setFixedWidth(12)
            b2.setObjectName("hintLabel")
            t2 = QLabel(line)
            t2.setWordWrap(True)
            t2.setObjectName("hintLabel")
            row2.addWidget(b2)
            row2.addWidget(t2, 1)
            cv_prev.addLayout(row2)
        vl.addWidget(card_prev)

        vl.addStretch(1)
        return page

    def on_update_found(self, info: object) -> None:
        """스플래시 InitWorker에서 업데이트 결과 수신."""
        self._pending_update_info = info
        if not hasattr(self, "_lbl_update_status"):
            return
        self._apply_update_info_to_ui(info)

    def _apply_update_info_to_ui(self, info: object) -> None:
        from src.app_meta import APP_VERSION
        from src.core.updater import UpdateInfo
        if info is None:
            self._lbl_update_status.setText(f"v{APP_VERSION}  ✓ 최신 버전")
            self._btn_check_update.setText("✓ 최신 버전")
            self._btn_check_update.setEnabled(False)
        elif isinstance(info, UpdateInfo):
            self._lbl_update_status.setText(
                f"v{APP_VERSION} → <b style='color:#4ade80'>{info.tag}</b>  업데이트 있음"
            )
            self._lbl_update_status.setTextFormat(Qt.TextFormat.RichText)
            self._btn_check_update.setText("다운로드")
            self._btn_check_update.setEnabled(True)
            self._btn_check_update.clicked.disconnect()
            self._btn_check_update.clicked.connect(lambda: self._start_download(info))

    def _check_update_manual(self) -> None:
        from src.app_meta import APP_VERSION
        from src.core.updater import check_update
        self._btn_check_update.setText("확인 중...")
        self._btn_check_update.setEnabled(False)
        def _do() -> None:
            info = check_update(APP_VERSION, timeout=6.0)
            self.on_update_found(info)
        from PyQt6.QtCore import QThreadPool, QRunnable
        class _R(QRunnable):
            def __init__(self, fn): super().__init__(); self._fn = fn
            def run(self): self._fn()
        QThreadPool.globalInstance().start(_R(_do))

    def _start_download(self, info: object) -> None:
        from src.core.updater import UpdateInfo, download_update
        from src.core.paths import project_root
        if not isinstance(info, UpdateInfo) or not info.download_url:
            QMessageBox.warning(self, "업데이트", "다운로드 URL을 찾을 수 없습니다.")
            return
        self._btn_check_update.setEnabled(False)
        self._btn_check_update.setText("다운로드 중...")
        self._update_progress_row.show()
        self._update_progress.setValue(0)
        self._pending_new_exe = project_root() / "update" / "DokkaebiSkillMacro.exe"

        def _progress(pct: float) -> None:
            self._update_progress.setValue(int(pct * 100))

        class _DL(QThread):
            done = pyqtSignal(bool)
            def __init__(self_, url, dest, cb):
                super().__init__()
                self_._url, self_._dest, self_._cb = url, dest, cb
            def run(self_):
                ok = download_update(self_._url, self_._dest, self_._cb)
                self_.done.emit(ok)

        self._dl_thread = _DL(info.download_url, self._pending_new_exe, _progress)
        self._dl_thread.done.connect(self._on_download_done)
        self._dl_thread.start()

    def _on_download_done(self, ok: bool) -> None:
        if ok:
            self._update_progress.setValue(100)
            self._btn_check_update.setText("다운로드 완료")
            self._btn_apply_update.show()
        else:
            self._btn_check_update.setText("다운로드 실패 — 재시도")
            self._btn_check_update.setEnabled(True)
            self._update_progress_row.hide()

    def _apply_update(self) -> None:
        from src.core.updater import apply_update_and_restart, current_exe_path
        if current_exe_path() is None:
            QMessageBox.information(self, "업데이트", "개발 모드에서는 자동 업데이트를 지원하지 않습니다.")
            return
        apply_update_and_restart(self._pending_new_exe)

    # ─────────────────────── Skill Info Page ──────────────────────────────────

    def _page_skill_info(self) -> QWidget:
        page = QWidget(self)
        page.setObjectName("skillInfoPage")
        vl = QVBoxLayout(page)
        vl.setContentsMargins(32, 24, 32, 28)
        vl.setSpacing(16)

        # ── 안내 ──
        card_hdr, cv_hdr = self._card(page, "스킬 라이브러리")
        hint = QLabel(
            "사용할 스킬을 자유롭게 등록하세요 (슬롯 개수 무관).\n"
            "이름 · 배율(×) · 쿨타임(초) · 타수를 입력 후 딜사이클 계산 → 추천 배치 적용하면\n"
            "스킬 슬롯 탭에 자동 배치됩니다. 스킬 속도(%)는 아래 일괄 설정에서 적용하세요."
        )
        hint.setObjectName("hintLabel")
        hint.setWordWrap(True)
        cv_hdr.addWidget(hint)
        vl.addWidget(card_hdr)

        # ── 스킬 목록 (스크롤 영역) ──
        card_rows, rows_cv = self._card(page, "등록된 스킬")
        self._skill_lib_rows_layout = rows_cv
        vl.addWidget(card_rows)

        # ── 스킬 추가 버튼 ──
        btn_add = QPushButton("+ 스킬 추가")
        btn_add.setMinimumHeight(36)
        btn_add.clicked.connect(self._add_skill_lib_row)
        rows_cv.addWidget(btn_add)

        # ── 일괄 설정 ──
        card_speed, cv_speed = self._card(page, "일괄 설정")
        spd_row = QHBoxLayout()
        spd_lbl = QLabel("스킬속도 % 일괄")
        spd_lbl.setObjectName("hintLabel")
        spd_row.addWidget(spd_lbl)
        self._dbl_global_speed = QDoubleSpinBox()
        self._dbl_global_speed.setRange(0.0, 80.0)
        self._dbl_global_speed.setSingleStep(0.5)
        self._dbl_global_speed.setSuffix(" %")
        self._dbl_global_speed.setFixedWidth(100)
        self._dbl_global_speed.setValue(self._cfg.global_speed_pct)
        spd_row.addWidget(self._dbl_global_speed)
        btn_apply_speed = QPushButton("적용")
        btn_apply_speed.setFixedWidth(60)
        btn_apply_speed.clicked.connect(self._apply_global_speed)
        spd_row.addWidget(btn_apply_speed)
        spd_row.addStretch(1)
        cv_speed.addLayout(spd_row)
        btn_rec_pri = QPushButton("★  DPS 기준 우선도 자동 설정")
        btn_rec_pri.setToolTip("배율×타수÷효과쿨 기준 자동 배정. 이동기는 항상 마지막.")
        btn_rec_pri.clicked.connect(self._apply_recommended_priorities)
        cv_speed.addWidget(btn_rec_pri)
        vl.addWidget(card_speed)

        # ── 딜사이클 미리보기 ──
        card_cycle, cv_cycle = self._card(page, "딜사이클 미리보기")
        self._lbl_cycle_preview = QLabel("(스킬 등록 후 계산하세요)")
        self._lbl_cycle_preview.setObjectName("hintLabel")
        self._lbl_cycle_preview.setWordWrap(True)
        btn_preview = QPushButton("딜사이클 계산")
        btn_preview.clicked.connect(self._refresh_cycle_preview)
        self._btn_apply_placement = QPushButton("추천 배치 슬롯에 적용")
        self._btn_apply_placement.setEnabled(False)
        self._btn_apply_placement.setToolTip(
            "계산된 추천 배치를 스킬 슬롯 탭의 슬롯-스킬 선택에 자동 반영합니다."
        )
        self._btn_apply_placement.clicked.connect(self._apply_placement_recommendation)
        cv_cycle.addWidget(self._lbl_cycle_preview)
        btn_row = QHBoxLayout()
        btn_row.addWidget(btn_preview)
        btn_row.addWidget(self._btn_apply_placement)
        btn_row.addStretch(1)
        cv_cycle.addLayout(btn_row)
        vl.addWidget(card_cycle)

        vl.addStretch(1)

        self._skill_lib_row_widgets: list[dict] = []
        self._last_placement: list[int] = list(self._cfg.last_rotation)
        self._load_skill_lib_rows()
        # 스킬 라이브러리 로드 후 슬롯 콤보 갱신 및 저장된 배치 복원
        self._refresh_slot_skill_combos()
        for _i, _cmb in enumerate(self._slot_skill_combos):
            _sid = self._cfg.slot_skill_ids[_i] if _i < len(self._cfg.slot_skill_ids) else ""
            self._set_combo_by_skill_id(_cmb, _sid)
        for _i, _cmb in enumerate(self._swap_skill_combos):
            _sid = self._cfg.swap_slot_skill_ids[_i] if _i < len(self._cfg.swap_slot_skill_ids) else ""
            self._set_combo_by_skill_id(_cmb, _sid)
        if hasattr(self, "_btn_apply_placement"):
            self._btn_apply_placement.setEnabled(bool(self._last_placement))
        return page

    # ── 스킬 라이브러리 행 관리 ──────────────────────────────────────────────

    def _skill_lib_col_header(self) -> None:
        """헤더 행 추가 (처음 한 번만) — 테이블 헤더처럼 강조."""
        ly = self._skill_lib_rows_layout
        _W = [88, 86, 80, 56, 68, 42, 42, 24]
        _H = ["스킬명", "배율(x)", "쿨타임(s)", "타수", "우선도\n(0=자동)", "이동기", "사이클", ""]
        _TIPS = [
            "스킬 식별 이름",
            "데미지 배율 (소수점 2자리)",
            "기본 쿨타임 (초)",
            "1회 발동 히트 수",
            "딜사이클 우선순위\n0=자동(DPS기준) | 1=최우선 | 7=최후순",
            "이동기 여부 — 체크 시 딜사이클 맨 뒤 배치",
            "딜사이클 포함 여부 — 체크 해제 시 제외",
            "",
        ]
        hdr_wrap = QWidget()
        hdr_wrap.setObjectName("skillLibHeader")
        hdr_layout = QHBoxLayout(hdr_wrap)
        hdr_layout.setSpacing(4)
        hdr_layout.setContentsMargins(0, 4, 0, 4)
        for txt, tip, w in zip(_H, _TIPS, _W):
            lbl = QLabel(txt)
            lbl.setObjectName("skillLibHeaderLabel")
            lbl.setFixedWidth(w)
            lbl.setWordWrap(True)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            if tip:
                lbl.setToolTip(tip)
            hdr_layout.addWidget(lbl)
        hdr_layout.addStretch(1)
        ly.insertWidget(0, hdr_wrap)

    def _add_skill_lib_row(self, skill_dict: dict | None = None) -> None:
        from src.core.skill_info import SkillInfo, new_skill_id
        from PyQt6.QtWidgets import QFrame
        ly = self._skill_lib_rows_layout

        # clicked 시그널은 bool(checked)를 전달하므로 dict가 아닌 경우 전부 새 행으로 처리
        if not isinstance(skill_dict, dict):
            skill_dict = SkillInfo().to_dict()
            skill_dict["id"] = new_skill_id()
        sid = str(skill_dict.get("id") or new_skill_id())
        info = SkillInfo.from_dict(skill_dict)

        _W = [88, 86, 80, 56, 68, 42, 42, 24]
        # 스킬 라이브러리 스핀박스는 글로벌 QSS padding(9px 12px)을 줄여서 폭 절약
        _SP_STYLE = "padding: 2px 5px;"

        wrap = QFrame()
        wrap.setObjectName("slotRowWrap")
        row = QHBoxLayout(wrap)
        row.setSpacing(4)
        row.setContentsMargins(0, 2, 0, 2)

        ed_name = QLineEdit(info.name)
        ed_name.setFixedWidth(_W[0])
        ed_name.setPlaceholderText("스킬명")
        ed_name.setToolTip("스킬 이름 (식별용)")
        ed_name.setStyleSheet("padding: 2px 6px;")
        row.addWidget(ed_name)

        dbl_mult = QDoubleSpinBox()
        dbl_mult.setRange(0.0, 9999.0); dbl_mult.setSingleStep(0.1)
        dbl_mult.setDecimals(2); dbl_mult.setValue(info.dmg_mult)
        dbl_mult.setSuffix(" x")
        dbl_mult.setFixedWidth(_W[1])
        dbl_mult.setStyleSheet(_SP_STYLE)
        dbl_mult.setToolTip("데미지 배율 (소수점 2자리)")
        row.addWidget(dbl_mult)

        dbl_cd = QDoubleSpinBox()
        dbl_cd.setRange(0.0, 600.0); dbl_cd.setSingleStep(0.5)
        dbl_cd.setDecimals(1); dbl_cd.setValue(info.cooldown_sec)
        dbl_cd.setSuffix(" s")
        dbl_cd.setFixedWidth(_W[2])
        dbl_cd.setStyleSheet(_SP_STYLE)
        dbl_cd.setToolTip("스킬 쿨타임 (초 단위)")
        row.addWidget(dbl_cd)

        sp_hits = QSpinBox()
        sp_hits.setRange(1, 99); sp_hits.setValue(info.hits)
        sp_hits.setFixedWidth(_W[3])
        sp_hits.setStyleSheet(_SP_STYLE)
        sp_hits.setToolTip("스킬 1회 발동 시 히트 수")
        row.addWidget(sp_hits)

        sp_pri = QSpinBox()
        sp_pri.setRange(0, 99)
        sp_pri.setValue(info.priority)
        sp_pri.setSpecialValueText("자동")  # 0 → "자동" 표시
        sp_pri.setFixedWidth(_W[4])
        sp_pri.setStyleSheet(_SP_STYLE)
        sp_pri.setToolTip(
            "딜사이클 우선순위\n"
            "0 = 자동 (DPS 기준 자동 결정)\n"
            "1 = 최우선 (가장 먼저 배치)\n"
            "7 = 최후순 (가장 나중에 배치)\n"
            "이동기 체크 시 이 값과 무관하게 항상 맨 뒤"
        )
        row.addWidget(sp_pri)

        chk_move = QCheckBox()
        chk_move.setChecked(info.is_movement)
        chk_move.setFixedWidth(_W[5])
        chk_move.setToolTip("이동기 체크 시 딜사이클 맨 뒤로 배치됩니다")
        row.addWidget(chk_move)

        chk_cycle = QCheckBox()
        chk_cycle.setChecked(info.enabled_in_cycle)
        chk_cycle.setFixedWidth(_W[6])
        chk_cycle.setToolTip("딜사이클 계산에 이 스킬 포함 여부")
        row.addWidget(chk_cycle)

        btn_del = QPushButton("×")
        btn_del.setFixedWidth(_W[7])
        btn_del.setToolTip("이 스킬 삭제")
        row.addWidget(btn_del)
        row.addStretch(1)

        # +스킬 추가 버튼 바로 앞(끝에서 두 번째)에 삽입
        insert_pos = ly.count() - 1
        ly.insertWidget(insert_pos, wrap)

        # speed_pct는 UI에서 직접 입력받지 않고 일괄설정 적용값을 보존
        widgets = {
            "id": sid, "wrap": wrap,
            "name": ed_name, "mult": dbl_mult, "cd": dbl_cd,
            "hits": sp_hits, "priority": sp_pri,
            "movement": chk_move, "cycle": chk_cycle,
            "speed_pct": float(skill_dict.get("speed_pct", 0.0)),
        }
        self._skill_lib_row_widgets.append(widgets)

        def _del(_, w=widgets):
            self._remove_skill_lib_row(w)

        btn_del.clicked.connect(_del)

        # 스킬 추가/삭제 시 슬롯 콤보 갱신
        ed_name.textChanged.connect(lambda _: self._refresh_slot_skill_combos())

    def _remove_skill_lib_row(self, widgets: dict) -> None:
        sid = widgets["id"]
        wrap = widgets["wrap"]
        self._skill_lib_row_widgets = [
            w for w in self._skill_lib_row_widgets if w["id"] != sid
        ]
        wrap.hide()
        wrap.deleteLater()
        self._refresh_slot_skill_combos()

    def _load_skill_lib_rows(self) -> None:
        """config의 skill_library로부터 UI 행 생성."""
        # 기존 행 정리
        ly = self._skill_lib_rows_layout
        for w in self._skill_lib_row_widgets:
            w["wrap"].deleteLater()
        self._skill_lib_row_widgets = []
        # 헤더가 없으면 추가
        if ly.count() <= 1:  # 추가 버튼만 있음
            self._skill_lib_col_header()
        for skill_dict in self._cfg.skill_library:
            self._add_skill_lib_row(skill_dict)

    def _collect_skill_library(self) -> list[dict]:
        """현재 UI 입력값으로부터 skill_library 수집."""
        from src.core.skill_info import SkillInfo
        result = []
        for w in self._skill_lib_row_widgets:
            d = SkillInfo(
                name=w["name"].text().strip(),
                dmg_mult=w["mult"].value(),
                cooldown_sec=w["cd"].value(),
                hits=w["hits"].value(),
                speed_pct=float(w.get("speed_pct", 0.0)),
                enabled_in_cycle=w["cycle"].isChecked(),
                priority=w["priority"].value(),  # QSpinBox → int 직접
                is_movement=w["movement"].isChecked(),
            ).to_dict()
            d["id"] = w["id"]
            result.append(d)
        return result

    # ── 하위 호환 (구 코드에서 호출하던 메서드 유지) ──────────────────────────

    def _collect_skill_infos(self) -> list[dict]:
        """레거시 호환: 현재 library 반환."""
        return self._collect_skill_library()

    def _rebuild_skill_info_rows(self) -> None:
        """레거시 호환: 라이브러리 UI 재로드."""
        if hasattr(self, "_skill_lib_row_widgets"):
            self._load_skill_lib_rows()

    def _reload_skill_infos(self) -> None:
        """레거시 호환."""
        if hasattr(self, "_skill_lib_row_widgets"):
            self._load_skill_lib_rows()

    # ── 일괄 설정 ─────────────────────────────────────────────────────────────

    def _apply_global_speed(self) -> None:
        if not hasattr(self, "_dbl_global_speed"):
            return
        spd = self._dbl_global_speed.value()
        for w in self._skill_lib_row_widgets:
            w["speed_pct"] = spd

    def _apply_recommended_priorities(self) -> None:
        from src.core.skill_info import SkillInfo, normalize_skill_infos, apply_recommended_priorities
        raw = self._collect_skill_library()
        infos = normalize_skill_infos(raw, len(raw))
        updated = apply_recommended_priorities(infos)
        for i, w in enumerate(self._skill_lib_row_widgets):
            if i < len(updated):
                w["priority"].setValue(updated[i].priority)  # QSpinBox.setValue

    # ── 딜사이클 미리보기 ──────────────────────────────────────────────────────

    def _refresh_cycle_preview(self) -> None:
        from src.core.skill_info import (
            SkillInfo, compute_rotation, normalize_skill_infos,
            rotation_summary, slot_placement_recommendation,
        )
        raw = self._collect_skill_library()
        n = len(raw)
        if n == 0:
            self._lbl_cycle_preview.setText("등록된 스킬이 없습니다.")
            self._btn_apply_placement.setEnabled(False)
            return
        infos = normalize_skill_infos(raw, n)
        gap = self._cfg.slot_gap_ms / 1000.0
        rotation = compute_rotation(infos, gap)
        self._last_placement = rotation  # 저장

        lines = [rotation_summary(infos, rotation)]
        rec = slot_placement_recommendation(infos, rotation)
        if rec:
            lines.append("")
            lines.append("── 배치 추천 ──")
            lines.append(rec)
        self._lbl_cycle_preview.setText("\n".join(lines))
        self._btn_apply_placement.setEnabled(bool(rotation))

    def _apply_placement_recommendation(self) -> None:
        """추천 rotation → 슬롯 탭 스킬 선택 콤보 + 우선도 스핀박스 자동 반영."""
        rotation = getattr(self, "_last_placement", [])
        if not rotation:
            QMessageBox.warning(self, "추천 배치", "먼저 '딜사이클 계산' 버튼을 눌러 사이클을 계산하세요.")
            return

        # 콤보박스를 최신 스킬 라이브러리로 갱신
        self._refresh_slot_skill_combos()

        library = self._collect_skill_library()
        slot_count = self.sp_slots.value() if hasattr(self, "sp_slots") else 1

        # 앞 slot_count 개 → 바1, 나머지 → 바2
        bar1_idxs = rotation[:slot_count]
        bar2_idxs = rotation[slot_count: slot_count * 2]

        bar1_combos = getattr(self, "_slot_skill_combos", [])
        bar2_combos = getattr(self, "_swap_skill_combos", [])
        pri_combos = getattr(self, "_slot_pri_combos", [])
        pri2_combos = getattr(self, "_slot_pri2_combos", [])

        for slot_i, lib_i in enumerate(bar1_idxs):
            if slot_i < len(bar1_combos) and lib_i < len(library):
                sid = library[lib_i]["id"]
                self._set_combo_by_skill_id(bar1_combos[slot_i], sid)
            if slot_i < len(pri_combos):
                pri_combos[slot_i].setValue(slot_i + 1)  # 순서대로 1, 2, 3 …

        for slot_i, lib_i in enumerate(bar2_idxs):
            if slot_i < len(bar2_combos) and lib_i < len(library):
                sid = library[lib_i]["id"]
                self._set_combo_by_skill_id(bar2_combos[slot_i], sid)
            if slot_i < len(pri2_combos):
                pri2_combos[slot_i].setValue(slot_i + 1)

        # 슬롯 탭으로 이동해 결과 바로 확인
        if hasattr(self, "_content_stack"):
            self._switch_page(2)  # 2 = 스킬 슬롯 탭

        QMessageBox.information(
            self, "적용 완료",
            f"추천 배치 {len(bar1_idxs)}개 슬롯을 반영했습니다.\n"
            "슬롯 탭에서 슬롯 영역 지정 및 템플릿 저장을 진행하세요."
        )

    # ═══════════════════════════ LOGIC METHODS ═══════════════════════════════

    def _on_welcome_continue(self) -> None:
        if self._welcome.skip_welcome_next_time():
            self._settings.setValue("skip_welcome", True)
        self._stack.setCurrentIndex(1)

    def _show_welcome(self) -> None:
        self._stack.setCurrentIndex(0)

    @staticmethod
    def _slot_roi_list_from_cfg(c: AppConfig) -> list[dict[str, int] | None]:
        n = c.slot_count
        if c.slot_rois and len(c.slot_rois) == n:
            return [dict(x) for x in c.slot_rois]
        return [None] * n

    def _serialize_slot_rois_for_config(self) -> list[dict[str, int]] | None:
        n = self.sp_slots.value()
        if len(self._slot_roi_list) != n:
            return None
        if all(x is not None for x in self._slot_roi_list):
            return [dict(x) for x in self._slot_roi_list]  # type: ignore[misc]
        return None

    def _refresh_roi_mode_label(self) -> None:
        if not hasattr(self, "sp_slots"):
            return
        n = self.sp_slots.value()
        filled = sum(1 for x in self._slot_roi_list if x is not None)
        if filled == n and n > 0:
            self._lbl_roi_mode.setText(
                f"슬롯 직접 영역 {n}/{n} 지정됨 — 이 좌표로 캡처·매칭합니다."
            )
        elif self._roi_dict:
            self._lbl_roi_mode.setText(
                "스킬바 범위만 지정됨 — 슬롯은 가로 균등 분할합니다. "
                "밀릴 경우 스킬 슬롯 탭에서 슬롯 영역을 직접 지정하세요."
            )
        else:
            self._lbl_roi_mode.setText(
                "[필요] 스킬바 범위 또는 각 슬롯 [슬롯 영역]을 지정해야 캡처·매칭이 됩니다."
            )

    def _apply_hotkey(self, spec: str) -> None:
        spec = spec.strip()
        if spec:
            self._hotkey_listener.set_key(spec)
            if not self._hotkey_listener.is_running():
                self._hotkey_listener.start()
        else:
            self._hotkey_listener.stop()

    def _on_hotkey_triggered(self) -> None:
        focused = QApplication.focusWidget()
        if isinstance(focused, KeyCaptureEdit):
            return
        self._run_cycle(from_hotkey=True)

    # ── 프레임리스 리사이즈 핸들 ─────────────────────────────────────────────────

    _RESIZE_M = 6  # 핸들 두께 (px)

    def _install_resize_handles(self) -> None:
        root = self._root_ref
        E = Qt.Edge
        C = Qt.CursorShape
        specs = [
            # (edges, cursor, col, row)  col/row: 0=near, 1=far, -1=full span
            (E.LeftEdge | E.TopEdge,     C.SizeFDiagCursor,  0, 0),
            (E.TopEdge,                  C.SizeVerCursor,    1, 0),
            (E.RightEdge | E.TopEdge,    C.SizeBDiagCursor,  2, 0),
            (E.LeftEdge,                 C.SizeHorCursor,    0, 1),
            (E.RightEdge,                C.SizeHorCursor,    2, 1),
            (E.LeftEdge | E.BottomEdge,  C.SizeBDiagCursor,  0, 2),
            (E.BottomEdge,               C.SizeVerCursor,    1, 2),
            (E.RightEdge | E.BottomEdge, C.SizeFDiagCursor,  2, 2),
        ]
        for edges, cursor, col, row in specs:
            h = _ResizeHandle(self, edges, cursor, root)
            self._resize_handles.append(h)
        self._reposition_resize_handles()
        for h in self._resize_handles:
            h.raise_()
            h.show()

    def _reposition_resize_handles(self) -> None:
        if not self._resize_handles:
            return
        root = self._root_ref
        W, H = root.width(), root.height()
        m = self._RESIZE_M
        c = m * 3  # 코너 크기
        E = Qt.Edge
        rects = {
            E.LeftEdge | E.TopEdge:     (0,     0,     c,     c),
            E.TopEdge:                  (c,     0,     W-c*2, m),
            E.RightEdge | E.TopEdge:    (W-c,   0,     c,     c),
            E.LeftEdge:                 (0,     c,     m,     H-c*2),
            E.RightEdge:                (W-m,   c,     m,     H-c*2),
            E.LeftEdge | E.BottomEdge:  (0,     H-c,   c,     c),
            E.BottomEdge:               (c,     H-m,   W-c*2, m),
            E.RightEdge | E.BottomEdge: (W-c,   H-c,   c,     c),
        }
        E2 = Qt.Edge
        edge_list = [
            E2.LeftEdge | E2.TopEdge, E2.TopEdge, E2.RightEdge | E2.TopEdge,
            E2.LeftEdge, E2.RightEdge,
            E2.LeftEdge | E2.BottomEdge, E2.BottomEdge, E2.RightEdge | E2.BottomEdge,
        ]
        for h, edge in zip(self._resize_handles, edge_list):
            x, y, w, hh = rects[edge]
            h.setGeometry(x, y, max(1, w), max(1, hh))

    def eventFilter(self, obj: QObject, e: QEvent) -> bool:  # type: ignore[override]
        if e.type() == QEvent.Type.Resize and obj is self._root_ref:
            self._reposition_resize_handles()
        return super().eventFilter(obj, e)

    def closeEvent(self, e) -> None:  # type: ignore[override]
        self._hotkey_listener.stop()
        super().closeEvent(e)

    def _apply_theme(self, mode: str) -> None:
        self._current_theme = mode
        self._settings.setValue("theme", mode)
        qss = DARK_QSS if mode == "dark" else LIGHT_QSS
        self.setStyleSheet(qss)
        # 액센트 색: 다크=초록, 라이트=파랑
        accent = QColor(74, 222, 128) if mode == "dark" else QColor(59, 130, 246)
        for b in getattr(self, "_nav_btns", []):
            if isinstance(b, NavRippleButton):
                b.setRippleAccent(accent)
        # 타이틀바 토글 동기화
        if hasattr(self, "_title_bar"):
            self._title_bar.set_theme(mode)
        # 환영 화면 테마 동기화
        if hasattr(self, "_welcome"):
            self._welcome.apply_theme(mode)

    def _toggle_theme(self) -> None:
        mode = "light" if self._current_theme == "dark" else "dark"
        self._apply_theme(mode)

    def _place_window(self) -> None:
        scr = QGuiApplication.primaryScreen()
        if scr is None:
            self.resize(1140, 720)
            return
        ag = scr.availableGeometry()
        w = max(1140, min(1280, ag.width() - 60))
        h = max(720, min(820, ag.height() - 60))
        self.resize(w, h)
        fg = self.frameGeometry()
        fg.moveCenter(ag.center())
        self.move(fg.topLeft())

    def _on_cycle_mode_toggled(self, checked: bool) -> None:
        pass
        self._sync_run_button_label()

    def _sync_run_button_label(self) -> None:
        if not hasattr(self, "btn_run"):
            return
        cycle = getattr(self, "_chk_cycle", None) and self._chk_cycle.isChecked()
        if cycle:
            self.btn_run.setText("딜사이클 시작")
        else:
            self.btn_run.setText("1사이클 실행")

    # ── preset management ─────────────────────────────────────────────────────

    def _clear_preset_card_styles(self) -> None:
        for btn in self._preset_cards.values():
            btn.setProperty("selected", False)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _on_preset_card_clicked(self, name: str) -> None:
        if self._selected_preset_name == name:
            self._selected_preset_name = None
            self._clear_preset_card_styles()
            return
        self._selected_preset_name = name
        self._clear_preset_card_styles()
        b = self._preset_cards.get(name)
        if b is not None:
            b.setProperty("selected", True)
            b.style().unpolish(b)
            b.style().polish(b)

    def _refresh_preset_grid(self) -> None:
        if self._preset_grid_inner is None:
            return
        lay = self._preset_grid_inner.layout()
        if lay is None:
            return
        while lay.count():
            item = lay.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        self._preset_cards.clear()
        self._selected_preset_name = None
        items = presets_mod.load_preset_library()
        cols = 3
        idx = 0
        for it in items:
            name = str(it.get("name", ""))
            if not name:
                continue
            btn = QPushButton(name)
            btn.setObjectName("presetCard")
            btn.setMinimumHeight(46)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setProperty("selected", False)
            nm = name
            btn.clicked.connect(lambda _=False, n=nm: self._on_preset_card_clicked(n))
            r, c = divmod(idx, cols)
            lay.addWidget(btn, r, c)
            self._preset_cards[name] = btn
            idx += 1

    def _preset_data_by_name(self, name: str) -> dict | None:
        for it in presets_mod.load_preset_library():
            if str(it.get("name", "")) == name:
                return it if isinstance(it, dict) else None
        return None

    def _on_preset_save(self) -> None:
        full = self._serialize_slot_rois_for_config()
        if not full:
            QMessageBox.warning(self, "프리셋", "슬롯마다 [슬롯 영역]을 모두 지정한 뒤 저장할 수 있습니다.")
            return
        name, ok = QInputDialog.getText(self, "프리셋 저장", "프리셋 이름:")
        if not ok or not name.strip():
            return
        nm = name.strip()
        sub, n_copy = presets_mod.add_named_preset(
            nm,
            self.sp_slots.value(),
            full,
            copy_templates_from=self._template_dir_resolved(),
        )
        self._refresh_preset_grid()
        QMessageBox.information(
            self,
            "저장됨",
            f"프리셋 「{nm}」을(를) 저장했습니다.\n"
            f"PNG {n_copy}개 → templates/{sub}/",
        )

    def _on_preset_load(self) -> None:
        name = self._selected_preset_name
        if not name:
            QMessageBox.warning(self, "프리셋", "불러올 프리셋 블록을 먼저 클릭하여 선택하세요.")
            return
        data = self._preset_data_by_name(name)
        if not isinstance(data, dict):
            return
        sc = max(1, min(7, int(data.get("slot_count", 7))))
        rois = data.get("slot_rois")
        if not isinstance(rois, list) or len(rois) < sc:
            QMessageBox.warning(self, "프리셋", "프리셋 데이터가 올바르지 않습니다.")
            return
        rois = rois[:sc]
        self._slot_roi_list = []
        for d in rois:
            if isinstance(d, dict):
                self._slot_roi_list.append(
                    {
                        "left": int(d["left"]),
                        "top": int(d["top"]),
                        "width": int(d["width"]),
                        "height": int(d["height"]),
                    }
                )
            else:
                self._slot_roi_list.append(None)
        while len(self._slot_roi_list) < sc:
            self._slot_roi_list.append(None)
        self.sp_slots.blockSignals(True)
        self.sp_slots.setValue(sc)
        self.sp_slots.blockSignals(False)
        self._slot_rebuild_timer.stop()
        self._rebuild_slot_rows()
        rel = presets_mod.preset_template_rel_path(data)
        if rel:
            self.ed_template.setText(rel)
        self._refresh_roi_mode_label()

        # 프리셋 로드 즉시 config.json에 저장 (재시작 후에도 영역 유지)
        cfg = self._gather()
        save_config(cfg)
        self._cfg = cfg

        QMessageBox.information(self, "불러오기", f"프리셋 「{data.get('name')}」을(를) 적용했습니다.")
        self._clear_preset_card_styles()
        self._selected_preset_name = None

    def _on_preset_delete(self) -> None:
        name = self._selected_preset_name
        if not name:
            QMessageBox.warning(self, "프리셋", "삭제할 프리셋 블록을 선택하세요.")
            return
        reply = QMessageBox.question(
            self,
            "프리셋 삭제",
            f"「{name}」 프리셋과 templates/{presets_mod.sanitize_preset_filename(name)}/ PNG를 삭제할까요?",
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        presets_mod.delete_named_preset(name)
        self._refresh_preset_grid()
        QMessageBox.information(self, "삭제됨", f"「{name}」 프리셋을 삭제했습니다.")

    # ── ROI picking ───────────────────────────────────────────────────────────

    def _roi_status_text(self) -> str:
        if not self._roi_dict:
            return "범위 미설정 — 게임 화면에서 스킬바 전체를 드래그로 지정하세요."
        r = self._roi_dict
        return (
            f"left={r['left']}  top={r['top']}  w={r['width']}  h={r['height']}\n"
            "※ Qt 화면과 mss 모니터를 짝지어 비율 변환합니다."
        )

    def _pick_roi(self) -> None:
        _close_all_qt_popups()
        try:
            rect = pick_roi_fullscreen(None)
        finally:
            self.raise_()
            self.activateWindow()
        if rect is None:
            return
        self._roi_dict = {"left": rect.left(), "top": rect.top(),
                          "width": rect.width(), "height": rect.height()}
        self.lbl_roi.setText(self._roi_status_text())
        self._refresh_roi_mode_label()

    def _clear_roi(self) -> None:
        self._roi_dict = None
        self.lbl_roi.setText(self._roi_status_text())
        self._refresh_roi_mode_label()

    def _pick_slot_roi(self, slot_index: int) -> None:
        _close_all_qt_popups()
        try:
            rect = pick_roi_fullscreen(None)
        finally:
            self.raise_()
            self.activateWindow()
        if rect is None:
            return
        n = self.sp_slots.value()
        while len(self._slot_roi_list) < n:
            self._slot_roi_list.append(None)
        self._slot_roi_list[slot_index] = {
            "left": rect.left(), "top": rect.top(),
            "width": rect.width(), "height": rect.height(),
        }
        self._refresh_roi_mode_label()

    def _flush_pending_slot_rebuild(self) -> None:
        """저장·실행 직전에 디바운스된 슬롯 행 재구성을 즉시 반영."""
        t = getattr(self, "_slot_rebuild_timer", None)
        if t is None or not t.isActive():
            return
        t.stop()
        self._rebuild_slot_rows()

    def _on_slot_count_changed(self, _v: int) -> None:
        n = self.sp_slots.value()
        while len(self._slot_roi_list) < n:
            self._slot_roi_list.append(None)
        self._slot_roi_list = self._slot_roi_list[:n]
        self._slot_rebuild_timer.start()
        self._refresh_roi_mode_label()
        self._rebuild_skill_info_rows()

    def _collect_keys_from_ui(self) -> list[str]:
        return [ed.text().strip() or "2" for ed in self._skill_edits]

    def _collect_priorities_from_ui(self) -> list[int]:
        return [cb.value() for cb in self._slot_pri_combos]

    def _on_slot_swap_toggled(self, idx: int, on: bool) -> None:
        self._set_row_swap_expanded(idx, on)

    def _set_row_swap_expanded(self, idx: int, on: bool) -> None:
        if idx < 0 or idx >= len(self._slot_pri2_combos):
            return
        self._slot_pri2_combos[idx].setVisible(on)
        self._slot_save2_btns[idx].setVisible(on)
        if idx < len(self._slot_skill_enabled_cbs):
            self._slot_skill_enabled_cbs[idx].setText("①" if on else "사용")
        if idx < len(self._slot_swap_skill_enabled_cbs):
            self._slot_swap_skill_enabled_cbs[idx].setVisible(on)
        if idx < len(self._swap_skill_combos):
            self._swap_skill_combos[idx].setVisible(on)

    def _rebuild_slot_rows(self) -> None:
        lay = getattr(self, "_slot_rows_inner", None)
        if lay is None:
            return
        n = self.sp_slots.value()

        cfg_pri = normalize_slot_priorities(self._cfg.slot_priorities, n)
        cfg_sk = normalize_slot_skill_enabled(self._cfg.slot_skill_enabled, n)
        cfg_pri2 = normalize_slot_priorities(self._cfg.slot_swap_priorities, n)
        cfg_sw_en = normalize_slot_swap_enabled(self._cfg.slot_swap_enabled, n)

        for cb in list(self._slot_pri_combos):
            cb.hidePopup()
        for cb in list(self._slot_pri2_combos):
            cb.hidePopup()
        _close_all_qt_popups()

        # ── 줄이기: 마지막 행부터 제거 ────────────────────────────────────────
        while len(self._skill_edits) > n:
            i = len(self._skill_edits) - 1
            wrap = self._skill_edits[i].parentWidget()
            if wrap is not None:
                lay.removeWidget(wrap)
                wrap.hide()
                wrap.deleteLater()
            self._skill_edits.pop()
            self._slot_pri_combos.pop()
            self._slot_pri2_combos.pop()
            self._slot_save2_btns.pop()
            self._slot_swap_toggles.pop()
            self._slot_skill_enabled_cbs.pop()
            if self._slot_swap_skill_enabled_cbs:
                self._slot_swap_skill_enabled_cbs.pop()
            if self._slot_skill_combos:
                self._slot_skill_combos.pop()
            if self._swap_skill_combos:
                self._swap_skill_combos.pop()

        # ── 늘리기: 끝에 새 행만 추가 ────────────────────────────────────────
        cfg_sk2 = normalize_slot_skill_enabled(self._cfg.slot_swap_skill_enabled, n)

        for i in range(len(self._skill_edits), n):
            wrap = QWidget(self._slot_rows_host)
            wrap.setObjectName("slotRowWrap")
            row = QHBoxLayout(wrap)
            row.setSpacing(6)
            row.setContentsMargins(0, 4, 0, 4)
            row.setAlignment(Qt.AlignmentFlag.AlignVCenter)

            num = QLabel(f"{i + 1:02d}")
            num.setObjectName("slotNumLabel")
            num.setFixedWidth(26)
            num.setAlignment(Qt.AlignmentFlag.AlignCenter)

            p0 = cfg_pri[i] if i < len(cfg_pri) else 0
            pri = QSpinBox(wrap)
            pri.setObjectName("slotPriCombo")
            pri.setRange(0, 7)
            pri.setValue(int(p0))
            pri.setFixedWidth(42)
            pri.setToolTip("슬롯 실행 우선도\n0=자동(슬롯순) | 1=최우선 | 7=최후순")
            pri.setStyleSheet("padding: 2px 4px;")

            ed = KeyCaptureEdit(wrap)
            ed.setObjectName("slotKeyEdit")
            ed.setMinimumWidth(80)
            ed.setMaximumWidth(100)
            if i < len(self._cfg.skill_keys):
                ed.setText(self._cfg.skill_keys[i])
            else:
                ed.setText(["2", "3", "4", "5", "6", "7", "8"][i % 7])

            btn_roi = QPushButton("영역")
            btn_roi.setObjectName("slotRowBtn")
            btn_roi.setMinimumWidth(52)
            btn_roi.setMaximumWidth(64)
            btn_ready = QPushButton("저장 1")
            btn_ready.setObjectName("slotRowBtn")
            btn_ready.setMinimumWidth(50)
            btn_ready.setMaximumWidth(68)
            btn_ready.setToolTip(template_filename_for_slot(i))
            btn_save2 = QPushButton("저장 2")
            btn_save2.setObjectName("slotRowBtn")
            btn_save2.setMinimumWidth(50)
            btn_save2.setMaximumWidth(68)
            btn_save2.setToolTip(template_filename_swap(i))

            p2v = cfg_pri2[i] if i < len(cfg_pri2) else 0
            pri2 = QSpinBox(wrap)
            pri2.setObjectName("slotSwapPriCombo")
            pri2.setRange(0, 7)
            pri2.setValue(int(p2v))
            pri2.setFixedWidth(42)
            pri2.setToolTip("스왑(바2) 슬롯 실행 우선도\n0=자동(슬롯순) | 1=최우선 | 7=최후순")
            pri2.setStyleSheet("padding: 2px 4px;")

            sw_on = cfg_sw_en[i] if i < len(cfg_sw_en) else False
            chk_swap = QCheckBox("스왑")
            chk_swap.setObjectName("slotSwapChk")
            chk_swap.setChecked(sw_on)
            chk_swap.setToolTip(
                "켜면 저장 2·②차 우선순위를 표시하고, 자동 스왑 2라운드에 이 슬롯을 넣습니다."
            )
            chk_swap.setCursor(Qt.CursorShape.PointingHandCursor)

            # ① 사용 체크박스 (스왑 ON 시 "①"로 표시)
            chk_skill = QCheckBox("①" if sw_on else "사용")
            chk_skill.setObjectName("slotSkillChk")
            chk_skill.setChecked(cfg_sk[i] if i < len(cfg_sk) else True)
            chk_skill.setToolTip("1라운드(준비 바)에서 이 슬롯을 사용")
            chk_skill.setCursor(Qt.CursorShape.PointingHandCursor)

            # ② 스왑 사용 체크박스 (스왑 ON 시만 표시)
            chk_swap_skill = QCheckBox("②")
            chk_swap_skill.setObjectName("slotSwapSkillChk")
            chk_swap_skill.setChecked(cfg_sk2[i] if i < len(cfg_sk2) else True)
            chk_swap_skill.setToolTip("2라운드(스왑 바)에서 이 슬롯을 사용 — 스왑 ON 시 독립 제어 가능")
            chk_swap_skill.setCursor(Qt.CursorShape.PointingHandCursor)
            chk_swap_skill.setVisible(sw_on)

            # ── 스킬 선택 콤보박스 (바1) ──
            cmb_skill1 = QComboBox(wrap)
            cmb_skill1.setObjectName("slotSkillCombo")
            cmb_skill1.setMinimumWidth(110)
            cmb_skill1.setMaximumWidth(160)
            cmb_skill1.setToolTip("이 슬롯에 배치할 스킬 선택 (바1)")
            self._populate_skill_combo(cmb_skill1)
            saved_id1 = (
                self._cfg.slot_skill_ids[i]
                if i < len(self._cfg.slot_skill_ids) else ""
            )
            self._set_combo_by_skill_id(cmb_skill1, saved_id1)

            # ── 스킬 선택 콤보박스 (바2/스왑) ──
            cmb_skill2 = QComboBox(wrap)
            cmb_skill2.setObjectName("slotSkillCombo")
            cmb_skill2.setMinimumWidth(110)
            cmb_skill2.setMaximumWidth(160)
            cmb_skill2.setToolTip("이 슬롯에 배치할 스킬 선택 (바2·스왑)")
            cmb_skill2.setVisible(sw_on)
            self._populate_skill_combo(cmb_skill2)
            saved_id2 = (
                self._cfg.swap_slot_skill_ids[i]
                if i < len(self._cfg.swap_slot_skill_ids) else ""
            )
            self._set_combo_by_skill_id(cmb_skill2, saved_id2)

            si = i
            btn_roi.clicked.connect(lambda _=False, x=si: self._pick_slot_roi(x))
            btn_ready.clicked.connect(
                lambda _=False, x=si: self._save_slot_template(x, swap=False)
            )
            btn_save2.clicked.connect(
                lambda _=False, x=si: self._save_slot_template(x, swap=True)
            )
            chk_swap.toggled.connect(lambda on, idx=si: self._on_slot_swap_toggled(idx, on))

            pri2.setVisible(sw_on)
            btn_save2.setVisible(sw_on)

            row.addWidget(num, 0, Qt.AlignmentFlag.AlignVCenter)
            row.addWidget(pri, 0, Qt.AlignmentFlag.AlignVCenter)
            row.addWidget(ed, 0, Qt.AlignmentFlag.AlignVCenter)
            row.addWidget(cmb_skill1, 0, Qt.AlignmentFlag.AlignVCenter)
            row.addWidget(btn_roi, 0, Qt.AlignmentFlag.AlignVCenter)
            row.addWidget(btn_ready, 0, Qt.AlignmentFlag.AlignVCenter)
            row.addWidget(chk_swap, 0, Qt.AlignmentFlag.AlignVCenter)
            row.addWidget(cmb_skill2, 0, Qt.AlignmentFlag.AlignVCenter)
            row.addWidget(pri2, 0, Qt.AlignmentFlag.AlignVCenter)
            row.addWidget(btn_save2, 0, Qt.AlignmentFlag.AlignVCenter)
            row.addWidget(chk_skill, 0, Qt.AlignmentFlag.AlignVCenter)
            row.addWidget(chk_swap_skill, 0, Qt.AlignmentFlag.AlignVCenter)
            row.addStretch(1)

            lay.addWidget(wrap)
            self._skill_edits.append(ed)
            self._slot_pri_combos.append(pri)
            self._slot_pri2_combos.append(pri2)
            self._slot_save2_btns.append(btn_save2)
            self._slot_swap_toggles.append(chk_swap)
            self._slot_skill_enabled_cbs.append(chk_skill)
            self._slot_swap_skill_enabled_cbs.append(chk_swap_skill)
            self._slot_skill_combos.append(cmb_skill1)
            self._swap_skill_combos.append(cmb_skill2)

        self._sync_slot_hdr_buttons()

    def _template_dir_resolved(self) -> Path:
        raw = self.ed_template.text().strip() or "templates"
        p = Path(raw)
        if not p.is_absolute():
            p = project_root() / p
        return p

    def _save_slot_template(self, slot_index: int, *, swap: bool = False) -> None:
        n = self.sp_slots.value()
        rects = slot_rects_for_capture(self._serialize_slot_rois_for_config(), self._roi_dict, n)
        if rects is None:
            QMessageBox.warning(
                self,
                "범위",
                "스킬바 전체 범위를 지정하거나 슬롯마다 [슬롯 영역]을 모두 지정한 뒤 저장하세요.",
            )
            return
        if slot_index < 0 or slot_index >= len(rects):
            return
        try:
            img = grab_bgr(rects[slot_index])
        except Exception as ex:  # noqa: BLE001
            QMessageBox.critical(self, "캡처", str(ex)); return
        out_dir = self._template_dir_resolved()
        out_dir.mkdir(parents=True, exist_ok=True)
        fname = (
            template_filename_swap(slot_index)
            if swap
            else template_filename_for_slot(slot_index)
        )
        out_path = out_dir / fname
        ok, buf = cv2.imencode(".png", img)
        if not ok:
            QMessageBox.critical(self, "저장", "PNG 인코딩 실패"); return
        buf.tofile(str(out_path))
        QMessageBox.information(self, "저장됨", str(out_path))

    # ── 슬롯-스킬 콤보박스 헬퍼 ──────────────────────────────────────────────

    def _populate_skill_combo(self, combo: QComboBox) -> None:
        """콤보박스에 현재 라이브러리 스킬 목록 채우기."""
        prev_id = combo.currentData() or ""
        combo.blockSignals(True)
        combo.clear()
        combo.addItem("(없음)", "")
        library = getattr(self, "_skill_lib_row_widgets", [])
        for w in library:
            name = w["name"].text().strip() or f"[{w['id'][:4]}]"
            combo.addItem(name, w["id"])
        self._set_combo_by_skill_id(combo, prev_id)
        combo.blockSignals(False)

    def _set_combo_by_skill_id(self, combo: QComboBox, skill_id: str) -> None:
        """콤보박스를 skill_id에 해당하는 항목으로 설정."""
        for idx in range(combo.count()):
            if combo.itemData(idx) == skill_id:
                combo.setCurrentIndex(idx)
                return
        combo.setCurrentIndex(0)

    def _refresh_slot_skill_combos(self) -> None:
        """라이브러리 변경 시 슬롯 탭의 모든 콤보박스 갱신."""
        for combo in getattr(self, "_slot_skill_combos", []):
            self._populate_skill_combo(combo)
        for combo in getattr(self, "_swap_skill_combos", []):
            self._populate_skill_combo(combo)

    def _collect_slot_skill_ids(self) -> tuple[list[str], list[str]]:
        """슬롯 콤보박스에서 (slot_skill_ids, swap_slot_skill_ids) 수집."""
        s1 = [c.currentData() or "" for c in getattr(self, "_slot_skill_combos", [])]
        s2 = [c.currentData() or "" for c in getattr(self, "_swap_skill_combos", [])]
        return s1, s2

    def _gather(self) -> AppConfig:
        self._flush_pending_slot_rebuild()
        keys = self._collect_keys_from_ui()
        n = self.sp_slots.value()
        while len(keys) < n:
            keys.append("2")
        return AppConfig(
            monitor_width=self._cfg.monitor_width,
            monitor_height=self._cfg.monitor_height,
            mc_width=self._cfg.mc_width,
            mc_height=self._cfg.mc_height,
            template_dir=self.ed_template.text().strip() or "templates",
            swap_key=self.ed_swap.text().strip().lower() or "f",
            skill_bar_roi=dict(self._roi_dict) if self._roi_dict else None,
            slot_count=n, skill_keys=keys[:n],
            slot_rois=self._serialize_slot_rois_for_config(),
            match_threshold=self.dbl_threshold.value(),
            slot_timeout_sec=self.dbl_timeout.value(),
            poll_interval_ms=self.sp_poll.value(),
            post_press_delay_ms=self.sp_after.value(),
            slot_gap_ms=self.sp_slot_gap.value(),
            run_hotkey=self.ed_run_hotkey.text().strip(),
            auto_swap_enabled=self._chk_auto_run.isChecked(),
            swap_delay_ms=self.sp_swap_delay.value(),
            slot_priorities=normalize_slot_priorities(
                self._collect_priorities_from_ui(), n
            ),
            slot_skill_enabled=normalize_slot_skill_enabled(
                [cb.isChecked() for cb in self._slot_skill_enabled_cbs], n
            ),
            slot_swap_skill_enabled=normalize_slot_swap_skill_enabled(
                [cb.isChecked() for cb in self._slot_swap_skill_enabled_cbs], n
            ),
            slot_swap_enabled=normalize_slot_swap_enabled(
                [cb.isChecked() for cb in self._slot_swap_toggles], n
            ),
            slot_swap_priorities=normalize_slot_priorities(
                [cb.value() for cb in self._slot_pri2_combos],
                n,
            ),
            skill_infos=self._cfg.skill_infos,
            cycle_mode_enabled=bool(
                getattr(self, "_chk_cycle", None) and self._chk_cycle.isChecked()
            ),
            dummy_mode_enabled=False,
            skill_library=(
                self._collect_skill_library()
                if hasattr(self, "_skill_lib_row_widgets")
                else self._cfg.skill_library
            ),
            slot_skill_ids=self._collect_slot_skill_ids()[0],
            swap_slot_skill_ids=self._collect_slot_skill_ids()[1],
            global_speed_pct=(
                self._dbl_global_speed.value()
                if hasattr(self, "_dbl_global_speed") else 0.0
            ),
            last_rotation=list(getattr(self, "_last_placement", [])),
        )

    def _save(self) -> None:
        cfg = self._gather()
        save_config(cfg)
        self._cfg = cfg
        self._roi_dict = dict(cfg.skill_bar_roi) if cfg.skill_bar_roi else None
        self._slot_roi_list = MainWindow._slot_roi_list_from_cfg(cfg)
        self.lbl_roi.setText(self._roi_status_text())
        self._refresh_roi_mode_label()
        self._apply_hotkey(cfg.run_hotkey)
        p = default_config_path()
        QMessageBox.information(self, "저장됨", f"설정을 저장했습니다.\n{p}")

    def _reload(self) -> None:
        self._cfg = load_config()
        c = self._cfg
        self.ed_template.setText(c.template_dir)
        self.ed_swap.setText(c.swap_key)
        self.sp_swap_delay.setValue(c.swap_delay_ms)
        self._roi_dict = dict(c.skill_bar_roi) if c.skill_bar_roi else None
        self.lbl_roi.setText(self._roi_status_text())
        self._slot_roi_list = MainWindow._slot_roi_list_from_cfg(c)
        self.sp_slots.blockSignals(True)
        self.sp_slots.setValue(c.slot_count)
        self.sp_slots.blockSignals(False)
        self.ed_run_hotkey.setText(c.run_hotkey or "")
        self.sp_slot_gap.setValue(c.slot_gap_ms)
        self.dbl_threshold.setValue(c.match_threshold)
        self.dbl_timeout.setValue(c.slot_timeout_sec)
        self.sp_poll.setValue(c.poll_interval_ms)
        self.sp_after.setValue(c.post_press_delay_ms)
        self._slot_rebuild_timer.stop()
        self._rebuild_slot_rows()
        for i, ed in enumerate(self._skill_edits):
            if i < len(c.skill_keys):
                ed.setText(c.skill_keys[i])
        # 증분 방식에서는 기존 행 값을 명시적으로 config로 덮어씀
        for i, cb in enumerate(self._slot_pri_combos):
            p = c.slot_priorities[i] if i < len(c.slot_priorities) else 0
            cb.setValue(int(p))
        for i, cb in enumerate(self._slot_pri2_combos):
            p = c.slot_swap_priorities[i] if i < len(c.slot_swap_priorities) else 0
            cb.setValue(int(p))
        for i, cb in enumerate(self._slot_swap_toggles):
            cb.setChecked(c.slot_swap_enabled[i] if i < len(c.slot_swap_enabled) else False)
        for i, cb in enumerate(self._slot_skill_enabled_cbs):
            cb.setChecked(c.slot_skill_enabled[i] if i < len(c.slot_skill_enabled) else True)
        for i, cb in enumerate(self._slot_swap_skill_enabled_cbs):
            cb.setChecked(c.slot_swap_skill_enabled[i] if i < len(c.slot_swap_skill_enabled) else True)
        self._refresh_preset_grid()
        self._refresh_roi_mode_label()
        self._chk_auto_run.setChecked(c.auto_swap_enabled)
        if hasattr(self, "_chk_cycle"):
            self._chk_cycle.setChecked(c.cycle_mode_enabled)
        self._sync_run_button_label()
        # 스킬 속도 일괄설정 + 딜사이클 rotation 복원
        if hasattr(self, "_dbl_global_speed"):
            self._dbl_global_speed.setValue(c.global_speed_pct)
        self._last_placement = list(c.last_rotation)
        if hasattr(self, "_btn_apply_placement"):
            self._btn_apply_placement.setEnabled(bool(self._last_placement))
        # 스킬 라이브러리 재로드
        if hasattr(self, "_skill_lib_row_widgets"):
            self._load_skill_lib_rows()
            self._refresh_slot_skill_combos()
        # 슬롯-스킬 ID 복원
        for slot_i, combo in enumerate(getattr(self, "_slot_skill_combos", [])):
            sid = c.slot_skill_ids[slot_i] if slot_i < len(c.slot_skill_ids) else ""
            self._set_combo_by_skill_id(combo, sid)
        for slot_i, combo in enumerate(getattr(self, "_swap_skill_combos", [])):
            sid = c.swap_slot_skill_ids[slot_i] if slot_i < len(c.swap_slot_skill_ids) else ""
            self._set_combo_by_skill_id(combo, sid)

    def _browse_template_dir(self) -> None:
        start = Path(self.ed_template.text().strip() or ".")
        if not start.is_dir():
            start = Path.home()
        d = QFileDialog.getExistingDirectory(self, "템플릿 폴더 선택", str(start))
        if d:
            self.ed_template.setText(d)

    def _append_log(self, line: str) -> None:
        cur = self.log_lbl.text()
        lines = (cur + "\n" + line).strip().split("\n")
        self.log_lbl.setText("\n".join(lines[-10:]))

    def _run_cycle(self, *, from_hotkey: bool = False) -> None:
        if self._worker and self._worker.isRunning():
            self._stop_cycle()
            return

        cycle_mode = getattr(self, "_chk_cycle", None) and self._chk_cycle.isChecked()

        rotation_summary_text = ""
        if cycle_mode:
            from src.core.skill_info import (
                compute_rotation,
                normalize_skill_infos,
                rotation_summary,
            )
            cfg_pre = self._gather()
            # 라이브러리 전체 스킬로 딜사이클 계산
            raw_lib = cfg_pre.skill_library or cfg_pre.skill_infos
            infos = normalize_skill_infos(raw_lib, len(raw_lib))
            rotation = compute_rotation(infos, cfg_pre.slot_gap_ms / 1000.0)
            if not rotation:
                msg = "딜사이클에 포함된 슬롯이 없습니다.\n스킬 정보 탭에서 쿨타임 > 0 인 슬롯을 설정하세요."
                if from_hotkey:
                    self._ensure_macro_page_front()
                    self._switch_page(4)
                    self._append_log(f"[실행 키] {msg.splitlines()[0]}")
                else:
                    QMessageBox.warning(self, "딜사이클", msg)
                return
            rotation_summary_text = rotation_summary(infos, rotation)

        w = self._build_base_worker()
        if w is None:
            if from_hotkey:
                self._ensure_macro_page_front()
                self._switch_page(4)
                self._append_log("[실행 키] 스킬바 범위 또는 슬롯 영역을 먼저 설정하세요.")
            return

        w.cycle_mode = bool(cycle_mode)
        w.dummy_mode = False
        self._worker = w
        self.btn_run.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.log_lbl.setText("")
        if rotation_summary_text and hasattr(self, "_lbl_cycle_rotation"):
            self._lbl_cycle_rotation.setText(rotation_summary_text)
        if self._spinner is not None:
            self._spinner.start()
        self._ensure_macro_page_front()
        self._switch_page(4)
        self._worker.start()

    def _stop_cycle(self) -> None:
        if self._worker and self._worker.isRunning():
            self._worker.request_stop()
        if self._spinner is not None:
            self._spinner.stop()

    def _on_worker_finished(self) -> None:
        self.btn_run.setEnabled(True)
        self.btn_stop.setEnabled(False)
        if self._spinner is not None:
            self._spinner.stop()
        self._sync_run_button_label()

    def _build_base_worker(self) -> "CycleWorker | None":
        """공통 CycleWorker 설정 후 반환. 범위 미설정 시 None."""
        cfg = self._gather()
        rects = slot_rects_for_capture(cfg.slot_rois, cfg.skill_bar_roi, cfg.slot_count)
        if rects is None:
            QMessageBox.warning(
                self, "범위",
                "스킬바 전체 범위 또는 슬롯별 [슬롯 영역] 전체가 필요합니다.\n"
                "캡처 설정·스킬 슬롯 탭에서 범위를 지정한 뒤 [저장] 하세요."
            )
            return None
        w = CycleWorker(self)
        w.roi_dict = cfg.skill_bar_roi
        w.slot_rects = list(rects)
        w.slot_count = cfg.slot_count
        w.slot_gap_ms = cfg.slot_gap_ms
        w.skill_keys = list(cfg.skill_keys)
        w.template_dir = cfg.template_path(project_root())
        w.threshold = cfg.match_threshold
        w.slot_timeout_sec = cfg.slot_timeout_sec
        w.poll_interval_ms = cfg.poll_interval_ms
        w.post_press_delay_ms = cfg.post_press_delay_ms
        w.swap_key = cfg.swap_key
        w.auto_swap = cfg.auto_swap_enabled
        w.slot_swap_enabled = list(cfg.slot_swap_enabled)
        w.swap_delay_ms = cfg.swap_delay_ms
        w.slot_priorities = list(cfg.slot_priorities)
        w.slot_skill_enabled = list(cfg.slot_skill_enabled)
        w.slot_swap_skill_enabled = list(cfg.slot_swap_skill_enabled)
        w.slot_swap_priorities = list(cfg.slot_swap_priorities)
        # 슬롯별 유효 스킬 정보: 라이브러리+슬롯 ID로 구성
        library = cfg.skill_library or []
        lib_by_id = {str(d.get("id", "")): d for d in library}
        effective: list[dict] = []
        for slot_i in range(cfg.slot_count):
            sid = cfg.slot_skill_ids[slot_i] if slot_i < len(cfg.slot_skill_ids) else ""
            skill = lib_by_id.get(sid) if sid else None
            effective.append(skill or {})
        w.skill_infos_data = effective
        # 바2(스왑) 스킬 정보
        swap_effective: list[dict] = []
        for slot_i in range(cfg.slot_count):
            sid = cfg.swap_slot_skill_ids[slot_i] if slot_i < len(cfg.swap_slot_skill_ids) else ""
            skill = lib_by_id.get(sid) if sid else None
            swap_effective.append(skill or {})
        w.swap_skill_infos_data = swap_effective
        w.log.connect(self._append_log)
        w.finished_ok.connect(self._on_worker_finished)
        return w

def run() -> None:
    from PyQt6.QtCore import QCoreApplication, Qt as QtCore

    from src.ui.app_fonts import load_app_fonts

    QApplication.setHighDpiScaleFactorRoundingPolicy(
        QtCore.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    try:
        QCoreApplication.setAttribute(
            QtCore.ApplicationAttribute.AA_DontCreateNativeWidgetSiblings, True
        )
    except Exception:
        pass

    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyle("Fusion")

    _ico = yasu_logo_path()
    if _ico is not None:
        app.setWindowIcon(QIcon(str(_ico)))

    fam = load_app_fonts()
    base = QFont(app.font())
    if fam:
        base.setFamily(fam)
    base.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
    base.setStyleStrategy(
        QFont.StyleStrategy.PreferAntialias | QFont.StyleStrategy.PreferQuality
    )
    app.setFont(base)

    # 위젯 생성 전에 스타일 적용 → QComboBox 드롭다운 컨테이너 재생성 방지
    app.setStyleSheet(DARK_QSS)

    # 스플래시 → InitWorker(파일 초기화) → 메인 창
    _saved_theme = QSettings("Yasu2947", "DokkaebiSkillMacro").value("theme", "dark", type=str)
    splash = SplashScreen(is_dark=(_saved_theme == "dark"))
    splash.show()
    app.processEvents()

    _init_worker = _InitWorker()
    _init_worker.status.connect(splash.set_status)
    _init_worker.update_found.connect(splash.on_update_found)
    _init_worker.ready.connect(splash.on_init_ready)
    _init_worker.start()

    w = MainWindow()
    _init_worker.update_found.connect(w.on_update_found)
    splash.done.connect(w.show)
    QTimer.singleShot(50, splash.start)

    raise SystemExit(app.exec())
