"""PNG → ICO 변환 유틸. build_exe.ps1 에서 호출됩니다."""
from __future__ import annotations

import sys
from pathlib import Path


def convert(png_path: str, ico_path: str) -> None:
    from PIL import Image

    img = Image.open(png_path).convert("RGBA")
    sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    imgs = [img.resize(s, Image.LANCZOS) for s in sizes]
    imgs[0].save(ico_path, format="ICO", sizes=sizes, append_images=imgs[1:])
    print(f"ICO 생성: {ico_path}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: png_to_ico.py <src.png> <dst.ico>", file=sys.stderr)
        sys.exit(1)
    convert(sys.argv[1], sys.argv[2])
