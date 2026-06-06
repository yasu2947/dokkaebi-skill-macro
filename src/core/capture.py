"""화면 캡처 (mss → OpenCV BGR)."""
from __future__ import annotations

import mss
import numpy as np

from src.core.regions import Rect


def grab_bgr(rect: Rect, sct=None) -> np.ndarray:
    """지정 영역을 BGR uint8 이미지로 캡처.

    sct: 재사용할 mss.mss() 인스턴스.
         None이면 임시 컨텍스트를 생성한다.
         매 호출마다 새 컨텍스트를 만들면 Windows GDI DC 초기화가
         반복되어 콘솔 플래시가 발생하므로 워커에서는 반드시 하나의 sct를 재사용할 것.
    """
    if sct is not None:
        raw = sct.grab(rect.as_mss_dict())
        return np.asarray(raw)[:, :, :3].copy()
    with mss.mss() as _sct:
        raw = _sct.grab(rect.as_mss_dict())
        return np.asarray(raw)[:, :, :3].copy()
