#!/usr/bin/env python3
"""Hoerbuch-Produktion in einem Befehl.

    python build.py                 # Skript + Synthese + Mastering (Backend aus voices.yaml)
    python build.py --backend edge  # mit den Edge-Neural-Stimmen rendern
    python build.py --only 4,16     # nur einzelne Kapitel neu bauen
    python build.py --step script   # nur das Sprechskript neu erzeugen
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
CFG_DEFAULT = ROOT / "config" / "voices.yaml"
OUT_DEFAULT = ROOT / "out"
PACK = ROOT / "quelle" / "pack"


STEPS = ("script", "tts", "master")


def sh(args: list[str]) -> None:
    print(f"\n$ {' '.join(str(a) for a in args)}", flush=True)
    proc = subprocess.run([sys.executable, *[str(a) for a in args]])
    if proc.returncode != 0:
        sys.exit(proc.returncode)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", choices=("piper", "edge"),
                    help="ueberschreibt backend aus voices.yaml")
    ap.add_argument("--only", help="Kapitelnummern, z. B. 4,16,30")
    ap.add_argument("--step", choices=STEPS, action="append",
                    help="nur diese Schritte ausfuehren (mehrfach nutzbar)")
    ap.add_argument("--workers", type=int, default=4,
                    help="Prozesse fuer die Offline-Synthese")
    ap.add_argument("--pack", default=str(PACK),
                    help="Quellordner mit Kapitel-Skripten (siehe src/laden.py)")
    ap.add_argument("--config", default=str(CFG_DEFAULT),
                    help="Konfiguration mit Besetzung, Pausen und Mastering-Zielen")
    ap.add_argument("--out", default=str(OUT_DEFAULT), help="Ausgabeordner")
    args = ap.parse_args()
    pack = Path(args.pack)
    CFG = Path(args.config)
    OUT = Path(args.out)

    cfg = yaml.safe_load(CFG.read_text(encoding="utf-8"))
    backend = args.backend or cfg.get("backend", "piper")
    steps = args.step or list(STEPS)
    OUT.mkdir(parents=True, exist_ok=True)

    if "script" in steps:
        sh([SRC / "script_pack.py", pack, CFG, OUT / "script.json"])

    if "tts" in steps:
        if backend == "edge":
            cmd = [SRC / "tts_edge.py", OUT / "script.json", CFG, OUT / "wav"]
            if args.only:
                cmd.append(args.only)
        else:
            cmd = [SRC / "tts_piper.py", OUT / "script.json", CFG, OUT / "wav",
                   args.workers]
            if args.only:
                cmd.append(args.only)
        sh(cmd)

    if "master" in steps:
        cover = next((c for c in (pack / "cover.jpg", PACK / "06_Cover" / "cover.jpg")
                      if c.exists()), None)
        sh([SRC / "master.py", OUT / "script.json", CFG, OUT / "wav", OUT,
            cover or ""])

    print("\nFertig. Ergebnisse in", OUT)


if __name__ == "__main__":
    main()
