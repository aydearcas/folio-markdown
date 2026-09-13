"""Encode the generated master as a Windows ICO; no artwork changes.

Development-only dependency: Pillow. The desktop app does not require Pillow
for icons. PNG resizing and multi-size ICO encoding happen during this build.
"""
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def main():
    source = ROOT / "folio" / "assets" / "folio.png"
    target = source.with_suffix(".ico")
    temporary = source.with_name("folio.build.ico")
    with Image.open(source) as image:
        image.convert("RGBA").save(temporary, format="ICO",
                                   sizes=[(n, n) for n in (16, 24, 32, 48, 64, 128, 256)])
    with Image.open(temporary) as image:
        assert image.ico.sizes() == {(n, n) for n in (16, 24, 32, 48, 64, 128, 256)}
        for size in image.ico.sizes():
            frame = image.ico.getimage(size)
            frame.load()
            assert frame.size == size
    temporary.replace(target)
    print(target)


if __name__ == "__main__":
    main()
