"""
PyInstaller / EXE 진입점.
루트에 두어 import 경로가 프로젝트(exe 폴더) 기준으로 유지됩니다.
"""
from __future__ import annotations


def main() -> None:
    from src.ui.main_window import run

    run()


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    main()
