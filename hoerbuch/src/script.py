"""book.json -> script.json

Zerlegt jeden Block in sprachreine Segmente, weist Rolle und Stimme zu und
setzt die Pausen. Ergebnis ist ein flaches, komplett aufgeloestes Sprechskript.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml
from lingua import Language, LanguageDetectorBuilder

sys.path.insert(0, str(Path(__file__).parent))
from normalize import normalize, sentences  # noqa: E402

DETECTOR = (
    LanguageDetectorBuilder.from_languages(Language.GERMAN, Language.ENGLISH)
    .with_preloaded_language_models()
    .build()
)

LINE_KINDS = {"line"}
TITLE_KINDS = {"title", "subtitle", "chapter", "heading", "subheading", "kicker"}

# Begriffe, die im Dokument als deutsche Fachsprache verwendet werden und
# einen Satz nicht nach Englisch kippen duerfen.
JARGON = {
    "opener", "openers", "opening", "set", "sets", "hook", "close", "closing",
    "state", "move", "line", "lines", "game", "wing", "wingman", "target",
    "location", "venue", "check", "exit", "peak", "kiss", "call", "callback",
    "push", "pull", "frame", "vibe", "vibes", "flow", "rule", "cold", "read",
    "group", "solo", "warm", "up", "same", "night", "tier", "safety", "position",
    "drill", "scenario", "logistics", "follow", "escalation", "transition",
}

MIN_WORDS_FOR_SWITCH = 4
MIN_CONFIDENCE = 0.72

# Funktionswoerter, die es im jeweils anderen Sprachraum praktisch nicht gibt.
# Das Dokument ist stark anglizismenhaltiges Deutsch - lingua allein kippt
# solche Saetze zu oft ins Englische.
DE_MARKERS = {
    "und", "nicht", "bei", "dann", "wenn", "oder", "mit", "fuer", "für", "ein",
    "eine", "einen", "einer", "der", "die", "das", "dem", "den", "du", "dich",
    "dir", "sie", "ihr", "ist", "sind", "wird", "werden", "kein", "keine",
    "nach", "vor", "auf", "aus", "zum", "zur", "als", "auch", "noch", "nur",
    "mehr", "sehr", "ohne", "ueber", "über", "unter", "zwischen", "sofort",
    "kurz", "klar", "gut", "statt", "immer", "jede", "jeder", "jedes", "man",
    "sich", "ich", "wir", "was", "wie", "warum", "damit", "weil", "aber",
}
EN_MARKERS = {
    "the", "and", "you", "your", "with", "for", "not", "she", "her", "they",
    "this", "that", "is", "are", "was", "were", "will", "would", "can", "one",
    "two", "then", "when", "if", "of", "to", "in", "on", "at", "it", "do",
    "does", "have", "has", "but", "or", "about", "into", "without", "keep",
}


def _marker_bias(text: str) -> tuple[int, int]:
    words = [w.strip(".,;:!?").lower() for w in text.split()]
    de = sum(1 for w in words if w in DE_MARKERS)
    en = sum(1 for w in words if w in EN_MARKERS)
    if any(ch in text for ch in "äöüßÄÖÜ"):
        de += 2
    return de, en


def detect(text: str, fallback: str) -> str:
    words = [w for w in text.replace(".", " ").split() if w.isalpha()]
    if len(words) < MIN_WORDS_FOR_SWITCH:
        return fallback
    if all(w.lower() in JARGON for w in words):
        return fallback

    de_hits, en_hits = _marker_bias(text)
    if de_hits and de_hits > en_hits:
        return "de"
    if en_hits and en_hits > de_hits + 1:
        return "en"

    values = DETECTOR.compute_language_confidence_values(text)
    if not values:
        return fallback
    top = values[0]
    if top.value < MIN_CONFIDENCE:
        return fallback
    return "de" if top.language == Language.GERMAN else "en"


def block_language(text: str, fallback: str) -> str:
    de_hits, en_hits = _marker_bias(text)
    if de_hits > en_hits:
        return "de"
    if en_hits > de_hits:
        return "en"
    lang = DETECTOR.detect_language_of(text)
    if lang is None:
        return fallback
    return "de" if lang == Language.GERMAN else "en"


def part_languages(book: list[dict]) -> dict[str, str]:
    """Dominante Sprache je Kapitel/Sektion aus den laengeren Fliesstextbloecken.

    Kurze Struktur-Labels ("Lines", "Sequence", "Setup") erben diese Sprache,
    damit die Stimme nicht bei jedem Einwort-Zwischentitel wechselt.
    """
    tally: dict[str, list[int]] = {}
    for block in book:
        if block["kind"] not in {"para", "item", "line", "pair"}:
            continue
        text = block["text"]
        if len(text.split()) < 8:
            continue
        key = block.get("part_id") or block.get("part") or ""
        lang = block.get("lang_hint") or block_language(text, "de")
        counts = tally.setdefault(key, [0, 0])
        counts[0 if lang == "de" else 1] += 1
    return {k: ("de" if v[0] >= v[1] else "en") for k, v in tally.items()}


def build(book_path: str, cfg_path: str, out_path: str) -> None:
    book = json.loads(Path(book_path).read_text(encoding="utf-8"))
    cfg = yaml.safe_load(Path(cfg_path).read_text(encoding="utf-8"))
    pauses = cfg["pauses"]
    pauses_before = cfg.get("pauses_before", {})

    segments: list[dict] = []
    chapters: list[dict] = []
    doc_lang = "de"

    for block in book:
        kind = block["kind"]
        raw = block["text"]
        if not raw.strip():
            continue

        if kind == "chapter":
            chapters.append({"title": raw, "part_id": block.get("part_id", ""),
                             "first_segment": len(segments)})

        hint = block.get("lang_hint") or ""
        base_lang = hint or block_language(raw, doc_lang)
        role_kind = "voice" if kind in LINE_KINDS else "narrator"

        # Sprachreine Laeufe bilden
        runs: list[tuple[str, list[str]]] = []
        for sent in sentences(raw):
            lang = hint or detect(sent, base_lang)
            if runs and runs[-1][0] == lang:
                runs[-1][1].append(sent)
            else:
                runs.append((lang, [sent]))

        for idx, (lang, sents) in enumerate(runs):
            text = normalize(" ".join(sents), lang)
            if not text or text == ".":
                continue
            first, last = idx == 0, idx == len(runs) - 1
            segments.append({
                "id": len(segments),
                "role": f"{role_kind}_{lang}",
                "lang": lang,
                "kind": kind,
                "part": block.get("part", ""),
                "part_id": block.get("part_id", ""),
                "text": text,
                "pause_before": pauses_before.get(kind, 0) if first else 0,
                "pause_after": pauses.get(kind, 300) if last else 120,
            })
        doc_lang = base_lang

    out = {"chapters": chapters, "segments": segments}
    Path(out_path).write_text(json.dumps(out, ensure_ascii=False, indent=1),
                              encoding="utf-8")

    from collections import Counter
    roles = Counter(s["role"] for s in segments)
    words = sum(len(s["text"].split()) for s in segments)
    print(f"{len(segments)} Segmente, {words} Woerter, {len(chapters)} Kapitel")
    for role, n in roles.most_common():
        w = sum(len(s["text"].split()) for s in segments if s["role"] == role)
        print(f"  {role:14} {n:5} Segmente  {w:6} Woerter")


if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2], sys.argv[3])
