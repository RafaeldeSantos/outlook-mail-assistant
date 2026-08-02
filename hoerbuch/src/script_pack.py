"""Production Pack (33 Kapitel-Skripte) -> script.json

Die Kapiteltexte sind bereits erzaehlfertig geschrieben. Hier passiert nur noch:

* Kapitel- und Absatzgrenzen erkennen
* zitierte Feldzeilen („...") aus dem Fliesstext herausloesen
* Sprache je Segment bestimmen (deutsch/englisch)
* Rolle und damit Stimme zuweisen
* Traegersaetze entdoppeln ("Die Line lautet:" 45x hintereinander)
* Aussprache-Lexikon anwenden
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import yaml
from lingua import Language, LanguageDetectorBuilder

sys.path.insert(0, str(Path(__file__).parent))
from normalize import normalize, sentences  # noqa: E402

# Strukturelle Marker: hier spricht immer der deutsche Erzaehler, auch wenn der
# Titel dahinter englisch ist ("Kapitel 18. Wingman and Friend Management.").
FRAME_RE = re.compile(
    r"^(Kapitel|Szenario|Drill|Script|Woche|Teil|Woche\s*\d+)\b", re.IGNORECASE
)

# Scorecard-Rubriken lesbar machen: "X. 0: A. 1: B. 2: C. Target: 2."
RUBRIC_RE = re.compile(
    r"^(?P<crit>.+?)\.\s*0:\s*(?P<a>.+?)\.\s*1:\s*(?P<b>.+?)\.\s*2:\s*(?P<c>.+?)\."
    r"\s*Target:\s*(?P<t>\d)\.?\s*$"
)


def expand_rubric(text: str) -> str:
    m = RUBRIC_RE.match(text.strip())
    if not m:
        return text
    return (
        f"{m['crit']}. Null Punkte: {m['a']}. Ein Punkt: {m['b']}. "
        f"Zwei Punkte: {m['c']}. Zielwert: {m['t']}."
    )

DETECTOR = (
    LanguageDetectorBuilder.from_languages(Language.GERMAN, Language.ENGLISH)
    .with_preloaded_language_models()
    .build()
)

# Zitierte Zeilen: deutsche, englische und gemischte Anfuehrungszeichen.
QUOTE_RE = re.compile(r'[„“”"“„]([^„“”"“„]{2,400}?)[“”"“”]')

# Traegersaetze vor einer Feldzeile.
# Labels, nach denen normaler Erzaehltext folgt.
CARRIERS = (
    r"Die Kernaussage|Der Einstieg|Der [UÜ]bergang oder Close|Die Interaktion|"
    r"Der Kontext|Kontext|Das Ziel|Ziel|Der Hauptfehler|Hauptfehler|"
    r"Die Korrektur oder der Exit|Saubere Korrektur oder Exit|Der Ablauf|Ablauf|"
    r"Abschnitt|Kategorie|Grundsatz|Mission|Erfolgsstandard|Debrief|Phase|"
    r"Woran du Interesse erkennst|Dein n[aä]chster Schritt|Messpunkt|Titel|"
    r"Situation|Am Ende der Woche notierst du"
)
# Labels, nach denen eine gesprochene Beispielzeile folgt - die bekommt die
# Feldstimme, auch wenn im Manuskript keine Anfuehrungszeichen stehen.
LINE_CARRIERS = (
    r"Die Line lautet|Eine m[oö]gliche Line(?: ist)?|M[oö]gliche Formulierungen|"
    r"Formulierung|N[aä]chster Baustein|Beispiel|Line"
)
ALL_CARRIERS = f"{CARRIERS}|{LINE_CARRIERS}"

CARRIER_RE = re.compile(rf"^(?:{ALL_CARRIERS})\s*[:.]?\s*$", re.IGNORECASE)

# Deutscher Traegersatz mit direkt anschliessendem - oft englischem - Inhalt.
# Ohne Trennung liest die englische Erzaehlstimme "Die Interaktion:" mit.
CARRIER_LEAD_RE = re.compile(rf"^({CARRIERS})\s*:\s*(?=\S)(.+)$", re.IGNORECASE | re.S)
LINE_LEAD_RE = re.compile(rf"^({LINE_CARRIERS})\s*[.:]\s*(?=\S)(.+)$",
                          re.IGNORECASE | re.S)

# Regieanweisung im Manuskript: soll gehoert, nicht gelesen werden.
REGIE_RE = re.compile(r"^(?:Pause|Kurze Pause|Beat)\.?$", re.IGNORECASE)
REGIE_PAUSE_MS = 900

DE_MARKERS = {
    "und", "nicht", "bei", "dann", "wenn", "oder", "mit", "für", "ein", "eine",
    "einen", "der", "die", "das", "dem", "den", "du", "dich", "dir", "sie",
    "ihr", "ist", "sind", "wird", "werden", "kein", "keine", "nach", "vor",
    "auf", "aus", "zum", "zur", "als", "auch", "noch", "nur", "mehr", "sehr",
    "ohne", "über", "unter", "sofort", "kurz", "klar", "statt", "immer", "man",
    "sich", "ich", "wir", "was", "wie", "warum", "damit", "weil", "aber", "euch",
    "ihre", "seine", "dass", "wenn", "durch", "gegen", "beim", "ins", "vom",
}
EN_MARKERS = {
    "the", "and", "you", "your", "with", "for", "not", "she", "her", "they",
    "this", "that", "is", "are", "was", "will", "would", "can", "then", "when",
    "if", "of", "to", "in", "on", "at", "it", "do", "does", "have", "has",
    "but", "or", "about", "into", "without", "keep", "come", "me", "my", "am",
}


def detect_lang(text: str, fallback: str = "de") -> str:
    words = [w.strip(".,;:!?-„“”\"'").lower() for w in text.split()]
    real = [w for w in words if w.isalpha()]
    de = sum(1 for w in real if w in DE_MARKERS)
    en = sum(1 for w in real if w in EN_MARKERS)
    if any(c in text for c in "äöüßÄÖÜ"):
        de += 2
    if de > en:
        return "de"
    if en > de:
        return "en"
    if len(real) < 3:
        return fallback
    lang = DETECTOR.detect_language_of(text)
    if lang is None:
        return fallback
    return "de" if lang == Language.GERMAN else "en"


MIN_WORDS_FOR_SWITCH = 5


def strong_signal(text: str) -> str | None:
    """Eindeutiger Sprachhinweis auch bei sehr kurzen Fragmenten."""
    words = [w.lower() for w in re.split(r"\W+", text, flags=re.UNICODE) if w.isalpha()]
    de = sum(1 for w in words if w in DE_MARKERS)
    en = sum(1 for w in words if w in EN_MARKERS)
    if any(c in text for c in "äöüßÄÖÜ") and not en:
        return "de"
    if de and not en:
        return "de"
    if en and not de:
        return "en"
    return None


def split_by_language(text: str, default: str = "de") -> list[tuple[str, str]]:
    """Absatz in sprachreine Laeufe zerlegen.

    Ein Sprachwechsel wird nur akzeptiert, wenn der Satz lang genug ist, um
    verlaesslich erkannt zu werden. Kurze Fragmente erben die Sprache des
    Vorgaengers - sonst springt die Stimme bei jedem Zwischentitel.
    """
    runs: list[list[str]] = []
    langs: list[str] = []
    current = default

    for sent in sentences(text):
        words = [w for w in re.split(r"\W+", sent, flags=re.UNICODE) if w.isalpha()]
        if len(words) >= MIN_WORDS_FOR_SWITCH:
            current = detect_lang(sent, current)
        else:
            current = strong_signal(sent) or current
        if runs and langs[-1] == current:
            runs[-1].append(sent)
        else:
            runs.append([sent])
            langs.append(current)

    # Zu kurze Laeufe in den Nachbarn zurueckfalten
    merged: list[tuple[str, list[str]]] = []
    for lang, group in zip(langs, runs):
        words = sum(len(g.split()) for g in group)
        decisive = strong_signal(" ".join(group)) == lang
        if merged and words < MIN_WORDS_FOR_SWITCH and not decisive:
            merged[-1][1].extend(group)
        else:
            merged.append((lang, list(group)))
    return [(lang, " ".join(group)) for lang, group in merged]


# Wortgrenze, die Bindestriche als Trenner behandelt: "Same-Night-Venue-Change"
# soll wortweise ersetzt werden, "Kissen" aber nicht auf "Kiss" anspringen.
LETTER = r"A-Za-zÄÖÜäöüß0-9"


MAX_SEGMENT_CHARS = 380


def split_long(text: str, limit: int = MAX_SEGMENT_CHARS) -> list[str]:
    """Ueberlange Absaetze an Satzgrenzen in vorlesbare Stuecke teilen."""
    if len(text) <= limit:
        return [text]
    stuecke, aktuell = [], ""
    for satz in sentences(text):
        if aktuell and len(aktuell) + len(satz) + 1 > limit:
            stuecke.append(aktuell)
            aktuell = satz
        else:
            aktuell = f"{aktuell} {satz}".strip()
    if aktuell:
        stuecke.append(aktuell)
    return stuecke


def apply_lexicon(text: str, lexicon: dict[str, str]) -> str:
    for grapheme, alias in lexicon.items():
        text = re.sub(rf"(?<![{LETTER}]){re.escape(grapheme)}(?![{LETTER}])",
                      alias, text)
    return text


def load_lexicon(pls_path: Path, json_path: Path | None = None) -> dict[str, str]:
    """Aussprache-Lexikon aus dem Pack (.pls) plus eigene deutsche Umschriften."""
    entries: list[tuple[str, str]] = []
    if pls_path.exists():
        raw = pls_path.read_text(encoding="utf-8")
        entries += [
            (g.strip(), a.strip())
            for g, a in re.findall(
                r"<grapheme>(.*?)</grapheme>\s*<alias>(.*?)</alias>", raw, flags=re.S)
        ]
    if json_path and json_path.exists():
        data = json.loads(json_path.read_text(encoding="utf-8"))
        entries += [(k, v) for k, v in data.items() if not k.startswith("_")]
    # laengste Graphemen zuerst, damit "Cold Reads" vor "Cold" greift
    return dict(sorted(entries, key=lambda kv: -len(kv[0])))


def split_paragraph(para: str) -> list[tuple[str, str]]:
    """Absatz -> [(kind, text)] mit kind in {narration, line}."""
    out: list[tuple[str, str]] = []
    pos = 0
    for m in QUOTE_RE.finditer(para):
        before = para[pos:m.start()].strip()
        if before:
            out.append(("narration", before))
        quote = m.group(1).strip()
        if quote:
            out.append(("line", quote))
        pos = m.end()
    tail = para[pos:].strip()
    if tail:
        out.append(("narration", tail))
    return out or [("narration", para.strip())]


def build(pack_dir: str, cfg_path: str, out_path: str) -> None:
    pack = Path(pack_dir)
    cfg = yaml.safe_load(Path(cfg_path).read_text(encoding="utf-8"))
    pauses = cfg["pauses"]
    pauses_before = cfg.get("pauses_before", {})
    trim_carriers = cfg.get("trim_repeated_carriers", True)

    lexicon = load_lexicon(
        pack / "04_Pronunciation" / "wingman_pronunciation_aliases.pls",
        Path(cfg_path).parent / "lexikon_de.json",
    )
    manifest = json.loads((pack / "manifest.json").read_text(encoding="utf-8"))

    segments: list[dict] = []
    chapters: list[dict] = []

    for track in manifest["tracks"]:
        path = pack / "02_Chapter_Scripts" / track["file"]
        text = path.read_text(encoding="utf-8")
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        if not paragraphs:
            continue

        chapters.append({
            "number": track["track"],
            "title": track["title"],
            "file": track["file"],
            "first_segment": len(segments),
        })

        last_carrier = None
        last_lang = "de"
        for p_idx, para in enumerate(paragraphs):
            parts = split_paragraph(para.replace("\n", " "))
            is_heading = p_idx == 0

            for kind, chunk in parts:
                chunk = re.sub(r"\s+", " ", chunk).strip()
                if not chunk:
                    continue

                if kind == "narration" and REGIE_RE.match(chunk.strip()):
                    # "Pause." nicht vorlesen, sondern die vorige Zeile
                    # entsprechend laenger stehen lassen.
                    if segments:
                        segments[-1]["pause_after"] = max(
                            segments[-1]["pause_after"], REGIE_PAUSE_MS)
                    continue

                if kind == "narration":
                    # Traegersatz vor einer Zeile ggf. weglassen
                    stripped = chunk.rstrip(" :.")
                    if trim_carriers and CARRIER_RE.match(chunk.strip()):
                        if stripped == last_carrier:
                            continue
                        last_carrier = stripped
                    else:
                        last_carrier = None
                    chunk = expand_rubric(chunk)

                block = "chapter" if is_heading else ("line" if kind == "line" else "para")

                # Traegersatz vom Inhalt trennen, damit "Die Interaktion:"
                # immer deutsch bleibt, auch wenn danach Englisch folgt.
                lead = None
                if kind == "narration" and not is_heading:
                    m = CARRIER_LEAD_RE.match(chunk)
                    if m:
                        lead, chunk = m.group(1).strip() + ":", m.group(2).strip()
                    else:
                        m = LINE_LEAD_RE.match(chunk)
                        if m:
                            # "Beispiel. Du gibst mir ..." - das Label bleibt
                            # Erzaehlung, der Rest wird zur gesprochenen Zeile.
                            lead = m.group(1).strip() + "."
                            chunk, kind, block = m.group(2).strip(), "line", "line"
                            if trim_carriers and lead.rstrip(".:") == last_carrier:
                                lead = None
                            else:
                                last_carrier = m.group(1).strip()

                if lead:
                    spoken_lead = normalize(apply_lexicon(lead, lexicon), "de")
                    segments.append({
                        "id": len(segments), "chapter": track["track"],
                        "chapter_title": track["title"], "role": "narrator_de",
                        "lang": "de", "kind": block, "text": spoken_lead,
                        "pause_before": pauses_before.get(block, 0),
                        "pause_after": 220,
                    })

                # Zitierte Zeilen bleiben ein Stueck; Erzaehltext wird in
                # sprachreine Laeufe zerlegt, damit gemischte Absaetze nicht
                # komplett in einer Sprache landen.
                if kind == "line":
                    runs = [(detect_lang(chunk), chunk)]
                elif is_heading or FRAME_RE.match(chunk) or CARRIER_RE.match(chunk):
                    # Kapitelansagen und blosse Label bleiben immer deutsch -
                    # sie sind der Rahmen des Buches, nicht sein Inhalt.
                    runs = [("de", chunk)]
                else:
                    # Jeder Absatz startet wieder auf Deutsch. Der Haupttext ist
                    # deutsch; wer die Sprache des Vorabsatzes erbt, zieht sonst
                    # nach einem englischen Block ganze deutsche Absaetze mit.
                    runs = split_by_language(chunk, "de")
                    last_lang = runs[-1][0] if runs else last_lang

                # Sehr lange Absaetze in hoerbare Haeppchen teilen, damit
                # zwischendurch Luft bleibt statt eines Dauerlaufs.
                runs = [(lang, teil)
                        for lang, run in runs
                        for teil in split_long(run)]

                for lang, run in runs:
                    role = ("voice" if kind == "line" else "narrator") + "_" + lang
                    spoken = apply_lexicon(run, lexicon) if lang == "de" else run
                    spoken = normalize(spoken, lang)
                    if not spoken or spoken == ".":
                        continue
                    segments.append({
                        "id": len(segments),
                        "chapter": track["track"],
                        "chapter_title": track["title"],
                        "role": role,
                        "lang": lang,
                        "kind": block,
                        "text": spoken,
                        "pause_before": pauses_before.get(block, 0),
                        "pause_after": pauses.get(block, 320),
                    })
                    is_heading = False

    Path(out_path).write_text(
        json.dumps({"chapters": chapters, "segments": segments},
                   ensure_ascii=False, indent=1),
        encoding="utf-8",
    )

    from collections import Counter
    roles = Counter(s["role"] for s in segments)
    chars = sum(len(s["text"]) for s in segments)
    print(f"{len(chapters)} Kapitel, {len(segments)} Segmente, {chars} Zeichen")
    for role, n in roles.most_common():
        c = sum(len(s["text"]) for s in segments if s["role"] == role)
        print(f"  {role:14} {n:5} Segmente  {c:7} Zeichen")


if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2], sys.argv[3])
