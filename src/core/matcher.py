"""템플릿 매칭 점수."""
from __future__ import annotations

import cv2
import numpy as np


def match_score(screen_bgr: np.ndarray, template_bgr: np.ndarray) -> float:
    """0~1 근처 점수 (TM_CCOEFF_NORMED). 크기가 같으면 단일 픽셀 점수와 동일."""
    if screen_bgr.size == 0 or template_bgr.size == 0:
        return 0.0
    sh, sw = screen_bgr.shape[:2]
    th, tw = template_bgr.shape[:2]
    if th > sh or tw > sw:
        return 0.0
    res = cv2.matchTemplate(screen_bgr, template_bgr, cv2.TM_CCOEFF_NORMED)
    _min_v, max_v, _min_loc, _max_loc = cv2.minMaxLoc(res)
    return float(max_v)
