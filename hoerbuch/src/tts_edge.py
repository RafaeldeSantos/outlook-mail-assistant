"""Synthese mit den Neural-Stimmen von Microsoft Edge (edge-tts).

Kostenlos, ohne Konto, ohne API-Key und ohne Zeichenkontingent. Klanglich
deutlich naeher an einer Studioproduktion als die Offline-Modelle.

Die vier besetzten Stimmen sind "Multilingual"-Modelle: sie sprechen Deutsch
und Englisch nativ, ein Sprachwechsel mitten im Kapitel klingt also sauber.

Voraussetzung: erreichbares speech.platform.bing.com. In abgeschotteten
Umgebungen (Firmenproxy, CI-Container) faellt der Aufruf durch - dann bleibt
tts_piper.py als vollstaendig lokale Alternative.
"""

from __future__ import annotations

import asyncio
import json
import sys
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf
import soxr
import yaml

CONCURRENCY = 4


def ssml_escape(text: str) -> str:
    return (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


async def synth_segment(seg: dict, cast: dict, tmpdir: Path, sem: asyncio.Semaphore):
    import edge_tts

    spec = cast[seg["role"]]
    path = tmpdir / f"{seg['id']:06d}.mp3"
    async with sem:
        for attempt in range(4):
            try:
                comm = edge_tts.Communicate(
                    ssml_escape(seg["text"]),
                    spec["model"],
                    rate=spec.get("rate", "+0%"),
                    pitch=spec.get("pitch", "+0Hz"),
                )
                await comm.save(str(path))
                if path.exists() and path.stat().st_size > 500:
                    return seg["id"], path
            except Exception as exc:
                if attempt == 3:
                    print(f"  ! Segment {seg['id']}: {exc}", flush=True)
                    return seg["id"], None
                await asyncio.sleep(1.5 * (attempt + 1))
    return seg["id"], None


def load_audio(path: Path, target_sr: int) -> np.ndarray:
    data, sr = sf.read(path, dtype="float32", always_2d=False)
    if data.ndim > 1:
        data = data.mean(axis=1)
    if sr != target_sr:
        data = soxr.resample(data, sr, target_sr, quality="VHQ")
    return data.astype(np.float32)


def silence(ms: int, sr: int) -> np.ndarray:
    return np.zeros(int(sr * ms / 1000.0), dtype=np.float32)


async def render_chapter(number: int, title: str, segments: list[dict],
                         cast: dict, sr: int, out_dir: Path) -> float:
    sem = asyncio.Semaphore(CONCURRENCY)
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        results = {
            sid: path
            for sid, path in await asyncio.gather(
                *(synth_segment(s, cast, tmpdir, sem) for s in segments))
        }

        pieces = [silence(500, sr)]
        for seg in segments:
            if seg["pause_before"]:
                pieces.append(silence(seg["pause_before"], sr))
            path = results.get(seg["id"])
            if path:
                pieces.append(load_audio(path, sr))
            pieces.append(silence(seg["pause_after"], sr))
        pieces.append(silence(900, sr))

    audio = np.concatenate(pieces)
    peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    if peak > 0.99:
        audio *= 0.99 / peak
    out_dir.mkdir(parents=True, exist_ok=True)
    sf.write(out_dir / f"{number:02d}.wav", audio, sr, subtype="PCM_16")
    dur = len(audio) / sr
    print(f"  Kapitel {number:02d} fertig: {title} ({dur/60:.1f} min)", flush=True)
    return dur


async def run(script_path: str, cfg_path: str, out_dir: str,
              only: set[int] | None = None) -> None:
    script = json.loads(Path(script_path).read_text(encoding="utf-8"))
    cfg = yaml.safe_load(Path(cfg_path).read_text(encoding="utf-8"))
    cast = cfg["edge"]["cast"]
    sr = int(cfg["edge"]["sample_rate"])

    by_chapter: dict[int, list[dict]] = {}
    for seg in script["segments"]:
        by_chapter.setdefault(seg["chapter"], []).append(seg)

    total = 0.0
    for chapter in script["chapters"]:
        n = chapter["number"]
        if only and n not in only:
            continue
        total += await render_chapter(n, chapter["title"], by_chapter.get(n, []),
                                      cast, sr, Path(out_dir))
    print(f"Gesamt: {total/60:.1f} Minuten Rohaudio")


if __name__ == "__main__":
    only = {int(x) for x in sys.argv[4].split(",")} if len(sys.argv) > 4 else None
    asyncio.run(run(sys.argv[1], sys.argv[2], sys.argv[3], only))
