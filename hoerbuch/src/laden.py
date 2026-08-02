"""Beliebiges Quelldokument -> Kapitel-Textdateien im Format des Production Packs.

Damit laesst sich jede Vorlage (HTML, DOCX, PDF, Markdown, TXT) mit derselben
Pipeline vertonen wie das Pack: ein Ordner mit 'NN_Titel.txt' plus manifest.json,
den script_pack.py direkt liest.

    python src/laden.py meine_version.docx out/quelle_eigen

Kapitelgrenzen werden erkannt an
  * HTML   : <h1> bzw. <section class="chapter">
  * DOCX   : Absatzformat 'Heading 1' / 'Ueberschrift 1'
  * MD     : '# '
  * PDF/TXT: Zeilen der Form 'Kapitel 3', 'Chapter 3', '3. Titel' oder
             komplett grossgeschriebene Kurzzeilen
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

KAPITEL_RE = re.compile(
    r"^\s*(?:kapitel|chapter|teil|part)\s+(\d{1,2})\b[.:\s-]*(.*)$", re.IGNORECASE)
NUMMER_RE = re.compile(r"^\s*(\d{1,2})[.)]\s+(\S.{2,80})$")


def aus_html(path: Path) -> list[tuple[str, list[str]]]:
    sys.path.insert(0, str(Path(__file__).parent))
    from extract import Extractor

    blocks = Extractor(path.read_text(encoding="utf-8")).run()
    kapitel: list[tuple[str, list[str]]] = []
    for b in blocks:
        if b.kind in ("chapter", "title") or not kapitel:
            titel = b.text if b.kind in ("chapter", "title") else "Einleitung"
            kapitel.append((titel, []))
            if b.kind in ("chapter", "title"):
                continue
        text = b.text
        if b.kind == "line":
            text = f"„{text.rstrip('.')}“"
        kapitel[-1][1].append(text)
    return kapitel


def aus_docx(path: Path) -> list[tuple[str, list[str]]]:
    from docx import Document  # python-docx

    kapitel: list[tuple[str, list[str]]] = []
    for p in Document(str(path)).paragraphs:
        text = p.text.strip()
        if not text:
            continue
        stil = (p.style.name or "").lower()
        if stil.startswith(("heading 1", "überschrift 1", "ueberschrift 1", "title")):
            kapitel.append((text, []))
        else:
            if not kapitel:
                kapitel.append(("Einleitung", []))
            kapitel[-1][1].append(text)
    return kapitel


def aus_pdf(path: Path) -> list[tuple[str, list[str]]]:
    from pypdf import PdfReader

    text = "\n".join(page.extract_text() or "" for page in PdfReader(str(path)).pages)
    return aus_text(text)


def aus_text(text: str) -> list[tuple[str, list[str]]]:
    kapitel: list[tuple[str, list[str]]] = []
    for absatz in re.split(r"\n\s*\n", text):
        absatz = re.sub(r"[ \t]+", " ", absatz).strip()
        if not absatz:
            continue
        erste = absatz.split("\n", 1)[0].strip()
        ist_titel = (
            erste.startswith("# ")
            or KAPITEL_RE.match(erste)
            or NUMMER_RE.match(erste)
            or (len(erste) < 70 and erste == erste.upper() and any(c.isalpha() for c in erste))
        )
        if ist_titel and len(absatz.splitlines()) == 1:
            kapitel.append((erste.lstrip("# ").strip(), []))
        else:
            if not kapitel:
                kapitel.append(("Einleitung", []))
            kapitel[-1][1].append(absatz.replace("\n", " "))
    return kapitel


def sauber(name: str) -> str:
    name = re.sub(r"[^\w\s-]", "", name, flags=re.UNICODE).strip()
    return re.sub(r"\s+", "_", name)[:60] or "Kapitel"


def main(quelle: str, ziel: str) -> None:
    src = Path(quelle)
    suffix = src.suffix.lower()
    if suffix in (".html", ".htm"):
        kapitel = aus_html(src)
    elif suffix == ".docx":
        kapitel = aus_docx(src)
    elif suffix == ".pdf":
        kapitel = aus_pdf(src)
    else:
        kapitel = aus_text(src.read_text(encoding="utf-8", errors="replace"))

    kapitel = [(t, abs_) for t, abs_ in kapitel if abs_]
    if not kapitel:
        sys.exit("Keine Kapitel erkannt - bitte Ueberschriften pruefen.")

    out = Path(ziel)
    (out / "02_Chapter_Scripts").mkdir(parents=True, exist_ok=True)
    tracks = []
    for i, (titel, absaetze) in enumerate(kapitel, 1):
        datei = f"{i:02d}_{sauber(titel)}.txt"
        inhalt = f"Kapitel {i}. {titel}.\n\n" + "\n\n".join(absaetze) + "\n"
        (out / "02_Chapter_Scripts" / datei).write_text(inhalt, encoding="utf-8")
        tracks.append({"track": i, "code": f"{i:02d}", "title": titel,
                       "file": datei, "characters": len(inhalt)})

    (out / "manifest.json").write_text(
        json.dumps({"title": src.stem.replace("_", " "), "version": "1",
                    "tracks": tracks,
                    "total_characters": sum(t["characters"] for t in tracks)},
                   ensure_ascii=False, indent=1), encoding="utf-8")

    gesamt = sum(t["characters"] for t in tracks)
    print(f"{len(tracks)} Kapitel, {gesamt} Zeichen -> {out}")
    print(f"geschaetzte Laufzeit: {gesamt / 900 / 60:.1f} Stunden")
    for t in tracks:
        print(f"  {t['code']}  {t['characters']:>6} Zeichen  {t['title'][:60]}")
    print(f"\nWeiter mit:  python build.py --pack {out}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "out/quelle_eigen")
