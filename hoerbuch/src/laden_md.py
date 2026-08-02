"""FULL_AUDIOBOOK_MANUSCRIPT.md -> Kapitelordner im Pack-Format.

Das Manuskript ist bereits erzaehlfertig: '# Track NN: Titel', Absaetze durch
Leerzeilen getrennt, '---' als Trenner. Hier wird nur zerlegt und ein
manifest.json geschrieben, das script_pack.py lesen kann.

    python src/laden_md.py FULL_AUDIOBOOK_MANUSCRIPT.md out/quelle_rafael
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

TRACK_RE = re.compile(r"^#\s*Track\s*(\d+)\s*:\s*(.+?)\s*$", re.MULTILINE)


def sauber(name: str) -> str:
    name = name.replace("&", "und")
    name = re.sub(r"[^\w\s-]", "", name, flags=re.UNICODE).strip()
    return re.sub(r"\s+", "_", name)[:60] or "Track"


def zerlege(text: str) -> list[tuple[int, str, list[str]]]:
    treffer = list(TRACK_RE.finditer(text))
    if not treffer:
        sys.exit("Keine '# Track NN: ...'-Ueberschriften gefunden.")

    tracks = []
    for i, m in enumerate(treffer):
        start = m.end()
        ende = treffer[i + 1].start() if i + 1 < len(treffer) else len(text)
        rumpf = text[start:ende]

        # Innerhalb der Szenario-Bloecke steht jede Angabe (Kontext, Ziel,
        # Ablauf, Hauptfehler ...) auf einer eigenen Zeile. Der Fliesstext ist
        # nirgends hart umbrochen, also ist jede Zeile eine eigene Sinneinheit
        # und bekommt eine eigene Pause.
        absaetze = []
        for roh in re.split(r"\n+", rumpf):
            # Trennlinien, Markdown-Reste und Produktionshinweise fliegen raus
            roh = re.sub(r"^\s*-{3,}\s*$", "", roh, flags=re.MULTILINE)
            roh = re.sub(r"^\s*#{1,6}\s*", "", roh, flags=re.MULTILINE)
            roh = re.sub(r"\*\*(.+?)\*\*", r"\1", roh)
            roh = re.sub(r"[ \t]+", " ", roh).strip()
            if roh:
                absaetze.append(roh)
        tracks.append((int(m.group(1)), m.group(2).strip(), absaetze))
    return tracks


def main(quelle: str, ziel: str) -> None:
    text = Path(quelle).read_text(encoding="utf-8")
    tracks = zerlege(text)

    out = Path(ziel)
    (out / "02_Chapter_Scripts").mkdir(parents=True, exist_ok=True)
    eintraege = []
    for nummer, titel, absaetze in tracks:
        # Erste Zeile des Manuskripts ist bereits die gesprochene Kapitelansage
        # ("Kapitel 1. Executive Profile.") - der Track-Titel selbst wird nicht
        # zusaetzlich vorgelesen, sonst steht die Ansage doppelt im Audio.
        inhalt = "\n\n".join(absaetze) + "\n"
        datei = f"{nummer:02d}_{sauber(titel)}.txt"
        (out / "02_Chapter_Scripts" / datei).write_text(inhalt, encoding="utf-8")
        eintraege.append({"track": nummer, "code": f"{nummer:02d}", "title": titel,
                          "file": datei, "characters": len(inhalt)})

    (out / "manifest.json").write_text(
        json.dumps({"title": "The Selective Operator - Rafael Edition",
                    "version": "1", "tracks": eintraege,
                    "total_characters": sum(e["characters"] for e in eintraege)},
                   ensure_ascii=False, indent=1), encoding="utf-8")

    gesamt = sum(e["characters"] for e in eintraege)
    print(f"{len(eintraege)} Tracks, {gesamt} Zeichen -> {out}")
    print(f"geschaetzte Laufzeit: {gesamt / 880 / 60:.1f} Stunden")
    leer = [e for e in eintraege if e["characters"] < 40]
    if leer:
        print("  ! fast leere Tracks:", ", ".join(e["code"] for e in leer))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "out/quelle_rafael")
