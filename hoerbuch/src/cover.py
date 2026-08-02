"""Typografisches Cover fuer das Hoerbuch erzeugen.

    python src/cover.py "The Selective Operator" "Rafael Edition" out/cover.jpg
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SIZE = 1400
GOLD = (215, 194, 156)
WHITE = (238, 240, 244)
MUTED = (150, 160, 175)


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    for name in ("DejaVuSerif", "DejaVuSans"):
        pfad = Path(f"/usr/share/fonts/truetype/dejavu/{name}"
                    f"{'-Bold' if bold else ''}.ttf")
        if pfad.exists():
            return ImageFont.truetype(str(pfad), size)
    return ImageFont.load_default()


def gesperrt(text: str, abstand: int = 1) -> str:
    return (" " * abstand).join(text)


def build(titel: str, edition: str, ziel: Path,
          kicker: str = "HIGH-END NIGHTGAME SYSTEM",
          fuss: str = "HÖRBUCH · DEUTSCH UND ENGLISCH",
          zusatz: str = "") -> None:
    img = Image.new("RGB", (SIZE, SIZE))
    d = ImageDraw.Draw(img)
    for y in range(SIZE):
        t = y / SIZE
        d.line([(0, y), (SIZE, y)],
               fill=(int(9 + t * 22), int(17 + t * 24), int(31 + t * 30)))

    def zentriert(text: str, f: ImageFont.FreeTypeFont, y: int, fill) -> None:
        breite = d.textbbox((0, 0), text, font=f)[2]
        d.text(((SIZE - breite) // 2, y), text, font=f, fill=fill)

    worte = titel.upper().split()
    gross = font(112, True)
    zentriert(gesperrt(kicker), font(26), 190, GOLD)
    y = 300
    for i, wort in enumerate(worte):
        zentriert(wort, gross, y, GOLD if i == len(worte) - 1 else WHITE)
        y += 120
    d.line([(SIZE // 2 - 90, y + 40), (SIZE // 2 + 90, y + 40)], fill=GOLD, width=4)
    zentriert(edition, font(40), y + 85, WHITE)
    zentriert(gesperrt(fuss, 0), font(30, True), 1090, MUTED)
    if zusatz:
        zentriert(gesperrt(zusatz, 0), font(24), 1150, MUTED)
    d.rectangle([55, 55, SIZE - 55, SIZE - 55], outline=(60, 72, 92), width=2)

    ziel.parent.mkdir(parents=True, exist_ok=True)
    img.save(ziel, "JPEG", quality=92)
    print(f"Cover: {ziel} ({ziel.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2], Path(sys.argv[3]),
          zusatz=sys.argv[4] if len(sys.argv) > 4 else "")
