#!/usr/bin/env python3
"""Deutsche Neural-Stimmen durchhoeren - kostenlos, ohne Konto, ohne Key.

Rendert denselben Text mit allen verfuegbaren deutschen Maennerstimmen von
Microsoft Edge und legt pro Stimme eine MP3 ab. Das ist die Klasse Stimme,
die in YouTube-Videos als "KI-Sprecher" laeuft - die lokalen Piper-Modelle
kommen da klanglich nicht hin.

    pip install edge-tts
    python stimmenprobe_edge.py

Braucht eine Verbindung zu speech.platform.bing.com. Hinter Firmenproxys oder
in abgeschotteten Containern ist der Host oft gesperrt.

Alle Stimmen auflisten:  edge-tts --list-voices
Nur deutsche:            edge-tts --list-voices | grep de-
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

OUT = Path("out/stimmenprobe_edge")

TEXT = (
    "Macht wird nicht verliehen. Sie wird genommen, still und ohne Ankündigung. "
    "Wer wartet, bis man ihn ruft, hat die Entscheidung längst an jemand anderen "
    "abgegeben. Beobachte, wer im Raum spricht. Und beobachte, wer zuhört. "
    "Und jetzt ein Satz auf Englisch: Power is never given, it is taken."
)

# Ein ruhiger, dunkler Erzaehlton entsteht aus langsamerem Tempo und
# abgesenkter Tonhoehe - dieselbe Stimme klingt damit deutlich anders.
STIMMEN = [
    # (Stimme, Tempo, Tonhoehe, Notiz)
    ("de-DE-ConradNeural",              "-8%",  "-6Hz",  "Klassiker, sachlich-dunkel"),
    ("de-DE-ConradNeural",              "-15%", "-15Hz", "derselbe, deutlich tiefer und langsamer"),
    ("de-DE-KillianNeural",             "-8%",  "-6Hz",  "juenger, wacher"),
    ("de-DE-FlorianMultilingualNeural", "-8%",  "-6Hz",  "warm, spricht auch Englisch nativ"),
    ("de-DE-FlorianMultilingualNeural", "-15%", "-12Hz", "derselbe, tiefer und langsamer"),
    ("de-DE-BerndNeural",               "-8%",  "-6Hz",  "reifer"),
    ("de-DE-ChristophNeural",           "-8%",  "-6Hz",  "nuechtern"),
    ("de-DE-KasperNeural",              "-8%",  "-6Hz",  "trocken"),
    ("de-AT-JonasNeural",               "-8%",  "-6Hz",  "oesterreichisch"),
    ("de-CH-JanNeural",                 "-8%",  "-6Hz",  "schweizerisch"),
]


async def verfuegbare_stimmen() -> set[str]:
    import edge_tts
    return {v["ShortName"] for v in await edge_tts.list_voices()}


async def main() -> None:
    try:
        import edge_tts  # noqa: F401
    except ImportError:
        sys.exit("Bitte zuerst installieren:  pip install edge-tts")

    import edge_tts

    try:
        vorhanden = await verfuegbare_stimmen()
    except Exception as exc:
        sys.exit(f"Kein Zugriff auf den Edge-Endpunkt: {exc}\n"
                 f"Hinter einem Proxy ist speech.platform.bing.com oft gesperrt.")

    OUT.mkdir(parents=True, exist_ok=True)
    deutsch = sorted(v for v in vorhanden if v.startswith(("de-DE", "de-AT", "de-CH")))
    print(f"{len(vorhanden)} Stimmen erreichbar, davon {len(deutsch)} deutsche:")
    print("  " + ", ".join(deutsch) + "\n")

    nummer = 0
    for stimme, tempo, pitch, notiz in STIMMEN:
        if stimme not in vorhanden:
            print(f"  uebersprungen (nicht mehr verfuegbar): {stimme}")
            continue
        nummer += 1
        kurz = stimme.split("-")[-1].replace("Neural", "")
        ziel = OUT / f"{nummer:02d}_{kurz}_{tempo.replace('%','').replace('-','minus')}.mp3"
        try:
            await edge_tts.Communicate(TEXT, stimme, rate=tempo, pitch=pitch).save(str(ziel))
            print(f"  {ziel.name:<34} {stimme:<34} {notiz}")
        except Exception as exc:
            print(f"  Fehler bei {stimme}: {exc}")

    print(f"\n{nummer} Proben in {OUT.resolve()}")
    print("Die beste Stimme dann in config/voices.yaml unter edge.cast eintragen und")
    print("das Hoerbuch damit rendern:  python build.py --backend edge")


if __name__ == "__main__":
    asyncio.run(main())
