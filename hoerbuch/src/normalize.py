"""Text-Normalisierung fuer TTS (deutsch + englisch).

Ziel: alles entfernen oder ersetzen, was eine Sprachsynthese ueber
Sonderzeichen, Abkuerzungen oder Layout-Reste stolpern laesst.
"""

from __future__ import annotations

import re

QUOTES = {
    "„": "", "“": "", "”": "", "‟": "",
    "«": "", "»": "", "‹": "", "›": "",
    "‘": "'", "’": "'", "‚": "", '"': "",
    "–": " - ", "—": " - ", "−": "-",
    "…": ".", " ": " ", "­": "",
    "→": " -> ", "➔": " -> ", "➜": " -> ",
    "✓": "", "✗": "", "•": ". ",
}

ABBR_DE = [
    (r"\bz\.\s?B\.", "zum Beispiel"),
    (r"\bd\.\s?h\.", "das heisst"),
    (r"\bu\.\s?a\.", "unter anderem"),
    (r"\bbzw\.", "beziehungsweise"),
    (r"\busw\.", "und so weiter"),
    (r"\bggf\.", "gegebenenfalls"),
    (r"\binkl\.", "inklusive"),
    (r"\bexkl\.", "exklusive"),
    (r"\bca\.", "circa"),
    (r"\bevtl\.", "eventuell"),
    (r"\bmax\.", "maximal"),
    (r"\bmin\.", "mindestens"),
    (r"\bNr\.", "Nummer"),
    (r"\bStk\.", "Stueck"),
    (r"\bMin\b\.?", "Minuten"),
    (r"\bvs\.", "gegen"),
]

ABBR_EN = [
    (r"\be\.\s?g\.", "for example"),
    (r"\bi\.\s?e\.", "that is"),
    (r"\betc\.", "et cetera"),
    (r"\bvs\.", "versus"),
    (r"\bapprox\.", "approximately"),
    (r"\bmin\b\.", "minutes"),
]

WORDS = {
    "de": {"pct": " Prozent", "amp": " und ", "arrow": ", dann ", "range": " bis ",
           "ratio": " zu ", "slash": ", "},
    "en": {"pct": " percent", "amp": " and ", "arrow": ", then ", "range": " to ",
           "ratio": " to ", "slash": ", "},
}


def normalize(text: str, lang: str = "de") -> str:
    t = text
    for src, dst in QUOTES.items():
        t = t.replace(src, dst)

    w = WORDS.get(lang, WORDS["de"])
    for pat, rep in (ABBR_DE if lang == "de" else ABBR_EN):
        t = re.sub(pat, rep, t, flags=re.IGNORECASE)

    # Pfeile als Ablaufkette
    t = re.sub(r"\s*(->|=>)\s*", w["arrow"], t)

    # Prozent
    t = re.sub(r"(\d)\s*%", r"\1" + w["pct"], t)
    t = t.replace("%", w["pct"])

    # Verhaeltnisse und Zahlenbereiche
    t = re.sub(r"(\d+)\s*/\s*(\d+)", r"\1" + w["ratio"] + r"\2", t)
    t = re.sub(r"(\d+)\s*[-–]\s*(\d+)", r"\1" + w["range"] + r"\2", t)

    # Wort/Wort -> Aufzaehlung (nicht bei URLs)
    t = re.sub(r"(?<=[A-Za-zÀ-ſ])\s*/\s*(?=[A-Za-zÀ-ſ])", w["slash"], t)

    t = t.replace("&", w["amp"])
    # "2+" heisst "zwei plus", " + " heisst "und"
    t = re.sub(r"(\d)\s*\+", r"\1 plus", t)
    t = re.sub(r"\s\+\s", w["amp"], t)
    t = t.replace("+", w["amp"])

    # Uhrzeiten / Ziffernketten mit Bindestrich: 5-2-1 -> 5, 2, 1
    t = re.sub(r"\b(\d)-(\d)-(\d)\b", r"\1, \2, \3", t)

    # Aufraeumen
    t = re.sub(r"[\[\]\(\)\{\}<>|*_#~^]", " ", t)
    t = re.sub(r"\s+([,.;:!?])", r"\1", t)
    t = re.sub(r"([,;:])\1+", r"\1", t)
    t = re.sub(r"\.{2,}", ".", t)
    t = re.sub(r"\s{2,}", " ", t).strip()
    t = re.sub(r"^[\s,;:.\-]+", "", t)

    if t and t[-1] not in ".!?:":
        t += "."
    return t


SENT_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-ZÄÖÜ„\"'‘])")


def sentences(text: str) -> list[str]:
    """Konservative Satztrennung - Abkuerzungen sind vorher schon aufgeloest."""
    parts = [p.strip() for p in SENT_SPLIT.split(text) if p.strip()]
    return parts or ([text] if text.strip() else [])
