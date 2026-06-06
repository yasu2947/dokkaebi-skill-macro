"""
PyInstaller / EXE 진입점.
루트에 두어 import 경로가 프로젝트(exe 폴더) 기준으로 유지됩니다.
"""
from __future__ import annotations

import os
import sys


def _suppress_console() -> None:
    """Windows GUI exe 환경에서 콘솔 창이 뜨지 않도록 처리."""
    if sys.platform != "win32":
        return
    # OpenCV: 내부 초기화 로그/서브프로세스 억제
    os.environ.setdefault("OPENCV_LOG_LEVEL", "SILENT")
    os.environ.setdefault("OPENCV_IO_ENABLE_OPENEXR", "0")
    os.environ.setdefault("OPENCV_VIDEOIO_DEBUG", "0")
    # mss: DirectX/GDI 초기화 관련 경고 억제
    os.environ.setdefault("MSS_DEBUG", "0")

    # PyInstaller onefile: 부트로더가 이미 콘솔 없이 실행하지만
    # ctypes 로 한번 더 콘솔 윈도우를 명시적으로 숨김
    try:
        import ctypes
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 0)  # SW_HIDE
    except Exception:  # noqa: BLE001
        pass


def main() -> None:
    _suppress_console()
    from src.ui.main_window import run
    run()


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    main()
