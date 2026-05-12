"""화면 캡처 (mss → OpenCV BGR)."""
from __future__ import annotations

import mss
import numpy as np

from src.core.regions import Rect


def grab_bgr(rect: Rect) -> np.ndarray:
    """지정 영역을 BGR uint8 이미지로 캡처."""
    with mss.mss() as sct:
        raw = sct.grab(rect.as_mss_dict())
        # BGRA → BGR
        return np.asarray(raw)[:, :, :3].copy()
