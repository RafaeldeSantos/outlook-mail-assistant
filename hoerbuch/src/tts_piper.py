"""Offline-Synthese mit Piper-Stimmen ueber sherpa-onnx.

Vollstaendig kostenlos, ohne Konto, ohne Kontingent und ohne Netzzugriff -
die Modelle werden einmal geladen und liegen danach lokal.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tarfile
import urllib.request
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import soundfile as sf
import soxr
import yaml

ROOT = Path(__file__).resolve().parent.parent
MODEL_DIR = ROOT / "models"

_ENGINES: dict[str, object] = {}
_CFG: dict | None = None


# --------------------------------------------------------------- Modelle ----

def ensure_model(name: str, base_url: str) -> Path:
    target = MODEL_DIR / name
    if target.is_dir() and any(target.glob("*.onnx")):
        return target
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    archive = MODEL_DIR / f"{name}.tar.bz2"
    url = f"{base_url}/{name}.tar.bz2"
    print(f"  lade {name} ...", flush=True)
    urllib.request.urlretrieve(url, archive)
    with tarfile.open(archive, "r:bz2") as tar:
        tar.extractall(MODEL_DIR)
    archive.unlink()
    return target


def engine(role: str, cfg: dict):
    if role in _ENGINES:
        return _ENGINES[role]
    import sherpa_onnx

    spec = cfg["piper"]["cast"][role]
    folder = ensure_model(spec["model"], cfg["piper"]["base_url"])
    onnx = next(folder.glob("*.onnx"))
    tts_cfg = sherpa_onnx.OfflineTtsConfig(
        model=sherpa_onnx.OfflineTtsModelConfig(
            vits=sherpa_onnx.OfflineTtsVitsModelConfig(
                model=str(onnx),
                tokens=str(folder / "tokens.txt"),
                data_dir=str(folder / "espeak-ng-data"),
                length_scale=1.0 / float(spec.get("speed", 1.0)),
                # noise_scale steuert die Variation in Klangfarbe und Melodie,
                # noise_scale_w die Variation der Lautlaengen - zusammen der
                # Unterschied zwischen "abgelesen" und "erzaehlt".
                # Piper-Standard: 0.667 / 0.8
                noise_scale=float(spec.get("expressiveness", 0.667)),
                noise_scale_w=float(spec.get("rhythm_variation", 0.8)),
            ),
            num_threads=int(os.environ.get("TTS_THREADS", "2")),
            provider="cpu",
        ),
        max_num_sentences=1,
    )
    _ENGINES[role] = (sherpa_onnx.OfflineTts(tts_cfg), spec)
    return _ENGINES[role]


# ------------------------------------------------------------- Synthese -----

def say(text: str, role: str, cfg: dict, target_sr: int) -> np.ndarray:
    tts, spec = engine(role, cfg)
    audio = tts.generate(text, sid=int(spec.get("speaker", 0)),
                         speed=float(spec.get("speed", 1.0)))
    samples = np.asarray(audio.samples, dtype=np.float32)
    if samples.size == 0:
        return np.zeros(0, dtype=np.float32)
    if audio.sample_rate != target_sr:
        samples = soxr.resample(samples, audio.sample_rate, target_sr, quality="VHQ")
    gain = float(spec.get("gain_db", 0.0))
    if gain:
        samples = samples * (10.0 ** (gain / 20.0))
    return samples.astype(np.float32)


def silence(ms: int, sr: int) -> np.ndarray:
    return np.zeros(int(sr * ms / 1000.0), dtype=np.float32)


def render_chapter(args) -> tuple[int, str, float]:
    number, title, segments, cfg_path, out_dir = args
    cfg = yaml.safe_load(Path(cfg_path).read_text(encoding="utf-8"))
    sr = int(cfg["piper"]["sample_rate"])

    existing = Path(out_dir) / f"{number:02d}.wav"
    if os.environ.get("TTS_SKIP_EXISTING") and existing.exists():
        info = sf.info(existing)
        print(f"  Kapitel {number:02d} vorhanden: {title}", flush=True)
        return number, str(existing), info.frames / info.samplerate

    pieces: list[np.ndarray] = [silence(500, sr)]
    for seg in segments:
        if seg["pause_before"]:
            pieces.append(silence(seg["pause_before"], sr))
        try:
            pieces.append(say(seg["text"], seg["role"], cfg, sr))
        except Exception as exc:  # eine kaputte Zeile darf das Kapitel nicht kippen
            print(f"  ! Segment {seg['id']} ({seg['role']}): {exc}", flush=True)
            continue
        pieces.append(silence(seg["pause_after"], sr))
    pieces.append(silence(900, sr))

    audio = np.concatenate(pieces)
    peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    if peak > 0.99:
        audio = audio * (0.99 / peak)

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{number:02d}.wav"
    sf.write(path, audio, sr, subtype="PCM_16")
    duration = len(audio) / sr
    print(f"  Kapitel {number:02d} fertig: {title} ({duration/60:.1f} min)", flush=True)
    return number, str(path), duration


def main(script_path: str, cfg_path: str, out_dir: str, workers: int = 3,
         only: set[int] | None = None) -> None:
    script = json.loads(Path(script_path).read_text(encoding="utf-8"))
    cfg = yaml.safe_load(Path(cfg_path).read_text(encoding="utf-8"))

    print("Modelle pruefen ...")
    for role in cfg["piper"]["cast"]:
        ensure_model(cfg["piper"]["cast"][role]["model"], cfg["piper"]["base_url"])

    by_chapter: dict[int, list[dict]] = {}
    for seg in script["segments"]:
        by_chapter.setdefault(seg["chapter"], []).append(seg)

    jobs = []
    for chapter in script["chapters"]:
        n = chapter["number"]
        if only and n not in only:
            continue
        jobs.append((n, chapter["title"], by_chapter.get(n, []), cfg_path, out_dir))

    print(f"Synthese: {len(jobs)} Kapitel auf {workers} Prozessen")
    results = []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for res in pool.map(render_chapter, jobs):
            results.append(res)

    total = sum(r[2] for r in results)
    print(f"Gesamt: {total/60:.1f} Minuten Rohaudio")


if __name__ == "__main__":
    only = None
    if len(sys.argv) > 5:
        only = {int(x) for x in sys.argv[5].split(",")}
    main(sys.argv[1], sys.argv[2], sys.argv[3],
         int(sys.argv[4]) if len(sys.argv) > 4 else 3, only)
