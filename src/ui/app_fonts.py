"""contents/font/ 에 넣은 TTF·OTF를 Qt에 등록."""
from __future__ import annotations

from PyQt6.QtGui import QFontDatabase

from src.core.paths import app_font_dir


def load_app_fonts() -> str | None:
    """
    font 디렉터리의 *.ttf / *.otf 를 모두 등록하고,
    QSS·setFont 에 쓸 패밀리 이름 하나를 반환한다. 실패 시 None.
    """
    d = app_font_dir()
    if d is None:
        return None
    paths = sorted(d.glob("*.ttf")) + sorted(d.glob("*.otf"))
    if not paths:
        return None
    families: set[str] = set()
    for path in paths:
        fid = QFontDatabase.addApplicationFont(str(path))
        if fid < 0:
            continue
        families |= set(QFontDatabase.applicationFontFamilies(fid))
    if not families:
        return None
    for name in ("Noto Sans KR", "Noto Sans CJK KR", "Noto Sans"):
        if name in families:
            return name
    return next(iter(sorted(families)), None)
