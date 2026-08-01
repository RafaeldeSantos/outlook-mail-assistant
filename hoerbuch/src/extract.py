"""HTML -> strukturiertes Hoerbuch-Skript (book.json).

Der Extraktor laeuft das Dokument in Lesereihenfolge durch und erzeugt Bloecke
mit semantischem Typ. Tabellen, Karten-Grids und Prozess-Schritte werden in
hoerbare Saetze uebersetzt, reine Layout-/Workbook-Elemente werden verworfen.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, asdict, field
from pathlib import Path

from bs4 import BeautifulSoup, Tag, NavigableString

# Container, die nur Platz zum Selberschreiben sind - im Hoerbuch wertlos.
SKIP_CLASSES = {
    "write-lines",
    "number-boxes",
    "rep-grid",
    "library-controls",
    "toc-grid",
    "cover-bottom",
    "line-library",  # wird von line_library() gesondert aufbereitet
    "tag",           # Filter-Chips, kein Sprechtext
}
SKIP_TAGS = {"script", "style", "input", "select", "option", "nav", "svg"}

# Bloecke, deren Text als gesprochene Beispielzeile gilt (eigene Stimme).
LINE_CONTAINERS = {"blockquote", "script", "sheet-lines", "pocket"}


@dataclass
class Block:
    kind: str  # title|subtitle|chapter|heading|kicker|para|line|item|pair|note|quote
    text: str
    part: str = ""  # Kapitel-/Sektionstitel zur Gruppierung
    part_id: str = ""
    lang_hint: str = ""  # "de" / "en" aus Metadaten (line-cards)
    meta: dict = field(default_factory=dict)


def txt(node) -> str:
    """Text eines Knotens, inklusive <br> -> Satzgrenze."""
    if node is None:
        return ""
    if isinstance(node, NavigableString):
        return str(node)
    parts = []
    for child in node.children:
        if isinstance(child, NavigableString):
            parts.append(str(child))
        elif isinstance(child, Tag):
            if child.name in SKIP_TAGS:
                continue
            if child.name == "br":
                parts.append(". ")
            else:
                parts.append(txt(child))
    return re.sub(r"\s+", " ", "".join(parts)).strip()


def classes(el: Tag) -> set[str]:
    return set(el.get("class", []) or [])


def is_skipped(el: Tag) -> bool:
    return bool(classes(el) & SKIP_CLASSES) or el.name in SKIP_TAGS


def table_to_sentences(table: Tag) -> list[str]:
    """Tabelle -> hoerbare Zeilen: 'Spalte: Wert. Spalte: Wert.'"""
    heads = [txt(th) for th in table.select("thead th")] or [
        txt(th) for th in table.select("tr th")
    ]
    out = []
    for tr in table.select("tbody tr") or table.select("tr"):
        cells = [txt(td) for td in tr.find_all("td")]
        if not cells:
            continue
        if heads and len(heads) == len(cells):
            first, rest = cells[0], cells[1:]
            tail = "; ".join(
                f"{h}: {c}" for h, c in zip(heads[1:], rest) if c and c not in {"-", "--"}
            )
            out.append(f"{first}. {tail}." if tail else f"{first}.")
        else:
            out.append(". ".join(c for c in cells if c) + ".")
    return out


def pairs_from_grid(grid: Tag) -> list[tuple[str, str]]:
    """profile-grid / metric-grid / steps / stack / sheet-meta -> (Label, Wert)."""
    pairs = []
    for cell in grid.find_all("div", recursive=False):
        label = cell.find("span")
        value = cell.find(["b", "p", "h3"])
        lab = txt(label) if label else ""
        val = txt(value) if value else ""
        if not val:
            # steps: <b>1</b><span>Titel</span><p>Text</p>
            val = txt(cell)
            if lab and val.startswith(lab):
                val = val[len(lab):].strip(" .:-")
        if val:
            pairs.append((lab, val))
    return pairs


class Extractor:
    def __init__(self, html: str):
        self.soup = BeautifulSoup(html, "lxml")
        self.blocks: list[Block] = []
        self.part = ""
        self.part_id = ""

    def add(self, kind: str, text: str, **meta):
        text = text.strip()
        if not text or text in {"-", "--", "."}:
            return
        lang_hint = meta.pop("lang_hint", "")
        self.blocks.append(
            Block(kind=kind, text=text, part=self.part, part_id=self.part_id,
                  lang_hint=lang_hint, meta=meta)
        )

    # ---------------------------------------------------------------- sections

    def run(self) -> list[Block]:
        body = self.soup.body
        self.cover(body.find("section", class_="cover"))
        for sec in body.find_all("section"):
            cl = classes(sec)
            if "cover" in cl:
                continue
            if "front" in cl:
                self.front(sec)
            elif "chapter" in cl:
                self.chapter(sec)
            elif "scenario-page" in cl:
                self.sheet(sec, "Szenario")
            elif "drill-page" in cl:
                self.sheet(sec, "Drill")
            elif "work-page" in cl:
                self.sheet(sec, "Workpage")
            elif "quick-page" in cl:
                self.sheet(sec, "Quick Reference")
        self.line_library()
        return self.blocks

    def cover(self, sec: Tag | None):
        if not sec:
            return
        self.part, self.part_id = "Titel", "cover"
        h1 = sec.find("h1")
        self.add("title", txt(h1))
        for cls in ("eyebrow", "cover-sub", "version"):
            p = sec.find("p", class_=cls)
            if p:
                self.add("subtitle", txt(p))

    def front(self, sec: Tag):
        self.part, self.part_id = txt(sec.find("h1")) or "Vorwort", sec.get("id", "front")
        for el in sec.find_all(["h1", "h2", "p", "div"], recursive=False):
            if is_skipped(el):
                continue
            if el.name == "h1":
                self.add("chapter", txt(el))
            elif el.name == "h2":
                self.add("heading", txt(el))
            elif el.name == "p":
                self.add("para", txt(el))
            elif "notice" in classes(el):
                self.add("note", txt(el))
        # Inhaltsverzeichnis als gesprochene Kapitelliste
        toc = sec.find("div", class_="toc-grid")
        if toc:
            items = [txt(a) for a in toc.find_all("a")]
            if items:
                self.add("heading", "Inhalt")
                for it in items:
                    self.add("item", it)

    def chapter(self, sec: Tag):
        h1 = sec.find("h1")
        self.part = txt(h1)
        self.part_id = sec.get("id", "")
        kicker = sec.find("div", class_="chapter-kicker")
        if kicker:
            self.add("kicker", txt(kicker))
        self.add("chapter", self.part)
        sub = sec.find("p", class_="chapter-sub")
        if sub:
            self.add("subtitle", txt(sub))
        for el in sec.children:
            if not isinstance(el, Tag) or is_skipped(el):
                continue
            if el is h1 or el is kicker or el is sub:
                continue
            self.walk(el)

    def sheet(self, sec: Tag, label: str):
        h1 = sec.find("h1")
        self.part = txt(h1) or label
        self.part_id = sec.get("id", "")
        kicker = sec.find("div", class_="sheet-kicker")
        self.add("kicker", f"{label}. {txt(kicker)}" if kicker else label)
        self.add("chapter", self.part)
        for el in sec.children:
            if not isinstance(el, Tag) or is_skipped(el):
                continue
            if el is h1 or el is kicker:
                continue
            self.walk(el)

    def line_library(self):
        cards = self.soup.select("article.line-card")
        if not cards:
            return
        self.part, self.part_id = "Line Library", "line-library"
        self.add("chapter", "Line Library")
        self.add(
            "para",
            "Die folgenden Zeilen sind Rohmaterial. Sie funktionieren nur, "
            "wenn du sie in deinen eigenen Ton uebersetzt.",
        )
        current_cat = None
        for card in cards:
            tags = [txt(s) for s in card.select("span.tag")]
            cat = card.get("data-cat") or (tags[0] if tags else "")
            lang = "de"
            for t in tags:
                if t.upper() == "EN":
                    lang = "en"
            style = tags[2] if len(tags) > 2 else ""
            if cat != current_cat:
                current_cat = cat
                self.add("heading", cat)
            body = txt(card.find("p"))
            self.add("line", body, lang_hint=lang, style=style)

    # ------------------------------------------------------------------- walk

    def walk(self, el: Tag):
        if is_skipped(el):
            return
        cl = classes(el)
        name = el.name

        if name in ("h1",):
            self.add("chapter", txt(el))
            return
        if name == "h2":
            self.add("heading", txt(el))
            return
        if name == "h3":
            self.add("subheading", txt(el))
            return
        if name == "p":
            self.add("para", txt(el))
            return
        if name == "blockquote":
            self.add("line", txt(el))
            return
        if name == "table":
            for s in table_to_sentences(el):
                self.add("item", s)
            return
        if name in ("ol", "ul"):
            for li in el.find_all("li", recursive=False):
                self.add("item", txt(li))
            return
        if name == "pre":
            for part in re.split(r"\n\s*\n", el.get_text()):
                self.add("para", re.sub(r"\s+", " ", part).strip())
            return
        if name == "small":
            self.add("note", txt(el))
            return
        if name in ("b", "strong"):
            self.add("subheading", txt(el))
            return
        if name in ("span", "i", "em", "a"):
            self.add("para", txt(el))
            return

        # --- Container mit Sonderformat ------------------------------------
        if "sheet-lines" in cl or "pocket" in cl:
            for q in el.find_all(["blockquote", "p"]):
                self.add("line", txt(q))
            return
        if "script" in cl:
            label = el.find("b")
            body = el.find("p")
            if label:
                self.add("note", txt(label))
            self.add("line", txt(body) if body else txt(el))
            return
        if "route" in cl:
            steps = [txt(s) for s in el.find_all("span")]
            self.add("item", " - dann - ".join(s for s in steps if s))
            return
        if "tree" in cl:
            for cell in el.find_all("div", recursive=False):
                self.add("item", txt(cell))
            return
        if cl & {"profile-grid", "metric-grid", "steps", "stack", "sheet-meta",
                 "quick-body", "work-grid"}:
            for lab, val in pairs_from_grid(el):
                self.add("pair", f"{lab}: {val}" if lab else val, label=lab)
            return
        if cl & {"traffic", "check-grid", "two-col", "card-grid", "quote-grid",
                 "sheet-bottom", "table-wrap"}:
            for child in el.children:
                if isinstance(child, Tag):
                    self.walk(child)
            return
        if cl & {"callout", "warning", "thesis", "notice", "protocol", "play",
                 "card", "mistake", "exit", "drill-mission", "drill-success",
                 "work-mission", "green", "amber", "red", "branch", "archive-note",
                 "quick-footer"}:
            head = el.find(["h2", "h3", "b"])
            if head:
                self.add("subheading", txt(head))
            for p in el.find_all(["p", "li", "blockquote"]):
                kind = "line" if p.name == "blockquote" else "para"
                self.add(kind, txt(p))
            if not el.find(["p", "li", "blockquote"]):
                body = txt(el)
                if head and body.startswith(txt(head)):
                    body = body[len(txt(head)):].strip(" .:-")
                self.add("para", body)
            return
        if "sheet-note" in cl:
            self.add("note", txt(el))
            return

        # --- generischer Container ----------------------------------------
        children = [c for c in el.children if isinstance(c, Tag)]
        if children:
            for child in children:
                self.walk(child)
        else:
            self.add("para", txt(el))


def main(src: str, dst: str):
    html = Path(src).read_text(encoding="utf-8")
    blocks = Extractor(html).run()

    # Duplikate direkt hintereinander entfernen (Grids wiederholen Ueberschriften)
    cleaned: list[Block] = []
    for b in blocks:
        if cleaned and cleaned[-1].text == b.text and cleaned[-1].kind == b.kind:
            continue
        cleaned.append(b)

    Path(dst).write_text(
        json.dumps([asdict(b) for b in cleaned], ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    words = sum(len(b.text.split()) for b in cleaned)
    print(f"{len(cleaned)} Bloecke, {words} Woerter -> {dst}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
