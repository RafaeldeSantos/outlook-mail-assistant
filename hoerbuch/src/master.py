"""Mastering und Auslieferung.

Pro Kapitel: EBU-R128-Normalisierung (zwei Durchgaenge), leichtes Hochpass-
Filter gegen Rumpeln, dann MP3 mit ID3-Tags und Cover.
Zum Schluss ein M4B mit Kapitelmarken fuer Hoerbuch-Player.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

FFMPEG = "ffmpeg"


def run(cmd: list[str]) -> str:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd[:6])} ... -> {proc.stderr[-1500:]}")
    return proc.stderr


def measure(path: Path, target: dict) -> dict:
    """Erster loudnorm-Durchgang: Messwerte holen."""
    stderr = run([
        FFMPEG, "-hide_banner", "-nostats", "-i", str(path),
        "-af", (f"loudnorm=I={target['lufs']}:TP={target['true_peak']}"
                f":LRA={target['lra']}:print_format=json"),
        "-f", "null", "-",
    ])
    match = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", stderr, re.S)
    if not match:
        return {}
    return json.loads(match.group(0))


def normalize_chapter(src: Path, dst: Path, target: dict, bitrate: str,
                      channels: int, tags: dict, cover: Path | None) -> None:
    stats = measure(src, target)
    loudnorm = (f"loudnorm=I={target['lufs']}:TP={target['true_peak']}"
                f":LRA={target['lra']}")
    if stats:
        loudnorm += (f":measured_I={stats['input_i']}"
                     f":measured_TP={stats['input_tp']}"
                     f":measured_LRA={stats['input_lra']}"
                     f":measured_thresh={stats['input_thresh']}"
                     f":offset={stats.get('target_offset', 0)}:linear=true")
    chain = f"highpass=f=65,{loudnorm}"

    cmd = [FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-i", str(src)]
    if cover:
        cmd += ["-i", str(cover)]
    cmd += ["-af", chain, "-ac", str(channels), "-ar", "44100",
            "-c:a", "libmp3lame", "-b:a", bitrate]
    if cover:
        cmd += ["-map", "0:a", "-map", "1:v", "-c:v", "copy", "-id3v2_version", "3",
                "-metadata:s:v", "title=Album cover",
                "-metadata:s:v", "comment=Cover (front)", "-disposition:v", "attached_pic"]
    for key, value in tags.items():
        cmd += ["-metadata", f"{key}={value}"]
    cmd += [str(dst)]
    run(cmd)


def duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True, text=True)
    return float(out.stdout.strip())


def build_m4b(chapter_files: list[tuple[int, str, Path]], out_path: Path,
              tags: dict, cover: Path | None) -> None:
    """Alle Kapitel zu einem M4B mit Kapitelmarken zusammenfuehren."""
    workdir = out_path.parent
    listfile = workdir / "_concat.txt"
    listfile.write_text(
        "\n".join(f"file '{p.resolve()}'" for _, _, p in chapter_files),
        encoding="utf-8")

    meta_lines = [";FFMETADATA1"]
    for key, value in tags.items():
        meta_lines.append(f"{key}={str(value).replace('=', ' ')}")
    start = 0.0
    for number, title, path in chapter_files:
        end = start + duration(path)
        meta_lines += [
            "[CHAPTER]", "TIMEBASE=1/1000",
            f"START={int(start * 1000)}", f"END={int(end * 1000)}",
            f"title={number:02d} - {title}",
        ]
        start = end
    metafile = workdir / "_chapters.txt"
    metafile.write_text("\n".join(meta_lines) + "\n", encoding="utf-8")

    cmd = [FFMPEG, "-hide_banner", "-loglevel", "error", "-y",
           "-f", "concat", "-safe", "0", "-i", str(listfile),
           "-i", str(metafile)]
    if cover:
        cmd += ["-i", str(cover)]
    cmd += ["-map_metadata", "1", "-map", "0:a"]
    if cover:
        cmd += ["-map", "2:v", "-c:v", "copy", "-disposition:v", "attached_pic"]
    cmd += ["-c:a", "aac", "-b:a", "80k", "-movflags", "+faststart", str(out_path)]
    run(cmd)
    listfile.unlink(missing_ok=True)
    metafile.unlink(missing_ok=True)


def safe(name: str) -> str:
    name = re.sub(r"[^\w\s-]", "", name, flags=re.UNICODE).strip()
    return re.sub(r"\s+", "_", name)


def main(script_path: str, cfg_path: str, wav_dir: str, out_dir: str,
         cover_path: str | None = None) -> None:
    script = json.loads(Path(script_path).read_text(encoding="utf-8"))
    cfg = yaml.safe_load(Path(cfg_path).read_text(encoding="utf-8"))
    m = cfg["mastering"]
    album = cfg.get("album", "The High-End Wingmen")
    artist = cfg.get("artist", "High-End Wingmen")

    wav_dir, out_dir = Path(wav_dir), Path(out_dir)
    mp3_dir = out_dir / "mp3"
    mp3_dir.mkdir(parents=True, exist_ok=True)
    cover = Path(cover_path) if cover_path and Path(cover_path).exists() else None

    produced: list[tuple[int, str, Path]] = []
    for chapter in script["chapters"]:
        n, title = chapter["number"], chapter["title"]
        src = wav_dir / f"{n:02d}.wav"
        if not src.exists():
            print(f"  uebersprungen (kein WAV): Kapitel {n:02d}")
            continue
        dst = mp3_dir / f"{n:02d}_{safe(title)}.mp3"
        normalize_chapter(
            src, dst, m, m["mp3_bitrate"], m["channels"],
            {"title": f"{n:02d} - {title}", "album": album, "artist": artist,
             "track": f"{n}/{len(script['chapters'])}", "genre": "Audiobook",
             "album_artist": artist},
            cover)
        produced.append((n, title, dst))
        print(f"  gemastert: {dst.name} ({duration(dst)/60:.1f} min)", flush=True)

    if produced:
        m4b = out_dir / f"{safe(album)}_Hoerbuch.m4b"
        build_m4b(produced, m4b,
                  {"title": album, "artist": artist, "album": album,
                   "genre": "Audiobook"}, cover)
        total = sum(duration(p) for _, _, p in produced)
        print(f"\nM4B: {m4b}  ({total/3600:.2f} h, {len(produced)} Kapitel)")


if __name__ == "__main__":
    main(*sys.argv[1:])
