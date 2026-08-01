# The High-End Wingmen — Hörbuch-Produktion

Vollständige, **kostenfreie** Hörbuch-Pipeline für das Production Pack V2.
Kein ElevenLabs, kein API-Key, kein Zeichenkontingent.

Aus den 33 erzählfertigen Kapitel-Skripten entstehen 33 gemasterte MP3s und
eine M4B-Datei mit Kapitelmarken — mit **vier Stimmen**, getrennt nach Sprache
und Funktion.

```
python build.py
```

---

## Die Besetzung

| Rolle | Was sie spricht | Stimme (offline) | Stimme (Edge) |
|---|---|---|---|
| `narrator_de` | deutscher Erzähltext, Kapitelansagen | `de_DE-thorsten-high` — männlich, ruhig, warm | `de-DE-FlorianMultilingualNeural` |
| `voice_de` | zitierte deutsche Feldzeilen | `de_DE-pavoque-low` — männlich, anderes Timbre | `de-DE-SeraphinaMultilingualNeural` |
| `narrator_en` | englische Erzählpassagen | `en_US-lessac-high` — weiblich, klar | `en-US-AvaMultilingualNeural` |
| `voice_en` | zitierte englische Feldzeilen | `en_US-ryan-high` — männlich, US | `en-US-AndrewMultilingualNeural` |

Jede Sprache hat also eine eigene Erzählstimme, und die gesprochenen Beispiel-
Lines heben sich in beiden Sprachen nochmal von der Erzählung ab. Alles steht
in `config/voices.yaml`; ein Stimmentausch ist eine Zeile. Alternativen sind
dort auskommentiert aufgelistet (u. a. `thorsten_emotional` mit acht Emotionen,
weibliche deutsche Stimmen, britisches Englisch).

Der Voice Brief aus dem Pack wollte *eine* Stimme für alles. Die Vorgabe
„pro Sprache eine andere Stimme“ geht vor — wer den Brief exakt umsetzen will,
setzt in `voices.yaml` einfach überall dasselbe Modell ein.

---

## Zwei Backends

### A) `piper` — offline, unbegrenzt (Standard)

Läuft komplett lokal auf der CPU, kein Konto, kein Limit, keine Internet-
verbindung nötig (nach dem einmaligen Modell-Download, ca. 400 MB).
Modelle: Piper-Stimmen, geladen über die
[sherpa-onnx-Releases](https://github.com/k2-fsa/sherpa-onnx/releases/tag/tts-models).

```
python build.py                    # kompletter Durchlauf
python build.py --only 4,16        # einzelne Kapitel neu
```

Tempo: ca. 4-fach Echtzeit auf vier Kernen — die ~1,8 h Hörbuch brauchen
knapp 30 Minuten.

### B) `edge` — Microsoft-Neural-Stimmen, kostenlos ohne Konto

Klanglich das Beste, was ohne Bezahlung erreichbar ist: dieselben Neural-
Stimmen, die Azure verkauft, über den offenen Endpunkt von Edge —
**ohne API-Key, ohne Registrierung, ohne Zeichenkontingent**.

```
pip install edge-tts
python build.py --backend edge
```

Die vier besetzten Stimmen sind `Multilingual`-Modelle: sie sprechen Deutsch
**und** Englisch nativ, ein Sprachwechsel mitten im Absatz klingt sauber.

Einziger Haken: Es braucht eine Verbindung zu `speech.platform.bing.com`.
Hinter restriktiven Firmenproxys oder in CI-Containern ist der Host oft
gesperrt — dann bleibt Backend A.

Stimmenliste: `edge-tts --list-voices | grep Multilingual`

---

## Warum kein ElevenLabs — und was sonst reicht

Das Hörbuch hat **rund 95.000 Zeichen**. Damit passt es in praktisch jedes
kostenlose Monatskontingent:

| Dienst | Kosten | Kontingent | Reicht für das Buch? |
|---|---|---|---|
| **edge-tts** | 0 € | unbegrenzt, kein Konto | ja, beliebig oft |
| **Piper (lokal)** | 0 € | unbegrenzt, offline | ja, beliebig oft |
| Azure Speech, Gratis-Stufe F0 | 0 € | 500.000 Zeichen/Monat Neural | ja, gut 5× |
| Google Cloud TTS, Gratis-Stufe | 0 € | monatliches Freikontingent je Stimmklasse | in der Regel ja |
| Amazon Polly, Free Tier | 0 € | Freikontingent in den ersten 12 Monaten | in der Regel ja |
| ElevenLabs Free | 0 € | ~10.000 Zeichen/Monat | nein, ~10 % eines Durchlaufs |

Die Kontingente der Cloud-Anbieter ändern sich; die Zahlen oben sind der
Stand bei Erstellung und vor dem Anlegen eines Kontos zu prüfen. Azures F0
und der Edge-Endpunkt liefern dieselbe Stimmfamilie — der Umweg über ein
Azure-Konto lohnt nur, wenn du SSML-Feinsteuerung brauchst.

**Empfehlung:** `--backend edge`. Kein Konto, kein Limit, beste Qualität.
Wenn der Endpunkt gesperrt ist: Standard-Backend, das ist ohnehin schon
gerendert.

---

## Was die Pipeline mit dem Text macht

`src/script_pack.py` baut aus den Kapitel-Skripten ein Sprechskript
(`out/script.json`) und trifft dabei die Entscheidungen, die ein Regisseur
sonst im Studio trifft:

* **Zitierte Zeilen herauslösen.** Alles in „…“ wird zur Feldstimme, der
  Rest bleibt Erzählung.
* **Sprache je Absatz bestimmen.** Sprachwechsel nur bei ausreichend langen
  Sätzen; kurze Fragmente erben die Sprache des Vorgängers, damit die Stimme
  nicht bei jedem Zwischentitel springt. Umlaute und Funktionswörter
  überstimmen die statistische Erkennung — das Buch ist anglizismenhaltiges
  Deutsch, da liegt reine Statistik zu oft daneben.
* **Rahmen bleibt deutsch.** „Kapitel 18. Wingman and Friend Management.“
  spricht der deutsche Erzähler, auch wenn der Titel englisch ist.
* **Trägersätze ausdünnen.** „Die Line lautet:“ steht 45× im Buch, oft
  direkt hintereinander. Bei unmittelbarer Wiederholung entfällt der
  Trägersatz — die zweite Stimme markiert die Zeile ohnehin.
  Abschaltbar über `trim_repeated_carriers: false`.
* **Aussprache-Lexikon anwenden.** Das `.pls` aus `04_Pronunciation` wird als
  Textersetzung übernommen (`Cold Read` → `Cold Ried`, `KPI` → `K P I`, …).
* **Vorlesbar machen.** Prozentzeichen, Pfeile, Zahlenbereiche, „2+“,
  Abkürzungen und die Scorecard-Rubriken („0: … 1: … 2: …“ →
  „Null Punkte: … Ein Punkt: … Zwei Punkte: …“).
* **Pausen setzen.** Vor Kapiteln, vor und nach Feldzeilen, nach Absätzen —
  Werte in `config/voices.yaml`.

## Mastering

`src/master.py` normalisiert jedes Kapitel in zwei Durchgängen auf
**−18 LUFS / −3 dBTP** (der übliche Hörbuch-Zielwert, u. a. ACX-konform),
filtert Rumpeln unter 65 Hz, schreibt MP3s mit ID3-Tags und Cover und baut
daraus ein M4B mit Kapitelmarken.

---

## Ergebnis

```
out/
  script.json                            Sprechskript, vollständig aufgelöst
  mp3/01_Operating_Profile.mp3 …         33 gemasterte Kapitel
  The_High-End_Wingmen_Hoerbuch.m4b      alles in einem, mit Kapitelmarken
  00_Stimmenprobe.mp3                    Besetzungsprobe
```

## Struktur

```
build.py                 Orchestrierung
config/voices.yaml       Besetzung, Pausen, Mastering-Ziele
src/script_pack.py       Kapitel-Skripte -> Sprechskript
src/normalize.py         Textaufbereitung für TTS
src/tts_piper.py         Backend A (offline)
src/tts_edge.py          Backend B (Edge Neural)
src/master.py            Normalisierung, MP3, M4B
src/extract.py           HTML -> Rohstruktur (Fallback ohne Pack)
src/script.py            Rohstruktur -> Sprechskript (Fallback)
quelle/                  Production Pack V2 und Original-HTML
```

## Installation

```
pip install -r requirements.txt
sudo apt install ffmpeg        # bzw. brew install ffmpeg
python build.py
```

## Lizenzen

Piper-Stimmen stehen unter MIT bzw. CC-BY-Lizenzen (Details im `MODEL_CARD`
jedes Modellordners); die Thorsten-Stimmen stammen aus dem
Thorsten-Voice-Datensatz (CC0). `edge-tts` spricht einen öffentlichen
Microsoft-Endpunkt an — für private Nutzung unproblematisch, für eine
kommerzielle Veröffentlichung des Hörbuchs ist die Azure-Variante mit
regulärem Konto der saubere Weg.
