"""Split the corpus into passages for retrieval.

Guidance is split at its own headings, so each passage keeps its place in the document and a link to the
heading's anchor on GOV.UK. Tender notices are rendered from an allowlist of fields: contact points,
addresses and documents are never read, so the personal data they hold can't reach a passage.
"""
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from bs4 import BeautifulSoup, Tag

MAX_CHARS = 1800  # about 400 tokens: long enough to hold a rule and its exceptions, short enough to cite
MIN_CHARS = 300   # shorter sections are joined to a neighbour under the same top heading


@dataclass
class Passage:
    id: str
    source: str            # guidance, ppn or notice
    doc_id: str
    title: str             # the document's title
    section: str           # heading path within the document, e.g. "Exclusions > Discretionary grounds"
    url: str
    updated: str
    text: str
    meta: dict = field(default_factory=dict)

    def embed_text(self) -> str:
        """What gets embedded: the passage with its document and section, so a search for the topic finds it."""
        return f"{self.title}\n{self.section}\n\n{self.text}" if self.section else f"{self.title}\n\n{self.text}"


def _clean(s: str) -> str:
    return re.sub(r"[ \t ]+", " ", re.sub(r"\n\s*\n+", "\n", s)).strip()


def _block_text(el: Tag) -> str:
    if el.name == "table":
        rows = [" | ".join(_clean(c.get_text(" ")) for c in tr.find_all(["th", "td"])) for tr in el.find_all("tr")]
        return "\n".join(r for r in rows if r.strip(" |"))
    if el.name in ("ul", "ol"):
        return "\n".join("- " + _clean(li.get_text(" ")) for li in el.find_all("li", recursive=False))
    return _clean(el.get_text(" "))


def _split(text: str) -> list[str]:
    """Split a long section at paragraph boundaries, then sentences, keeping each piece under MAX_CHARS."""
    if len(text) <= MAX_CHARS:
        return [text]
    pieces, current = [], ""
    for para in text.split("\n"):
        units = [para] if len(para) <= MAX_CHARS else re.split(r"(?<=[.;:])\s+", para)
        for unit in units:
            if current and len(current) + len(unit) + 1 > MAX_CHARS:
                pieces.append(current)
                current = ""
            current = f"{current}\n{unit}" if current else unit
    if current:
        pieces.append(current)
    if len(pieces) > 1 and len(pieces[-1]) < MIN_CHARS:  # a short tail reads better with what came before it
        pieces[-2:] = [pieces[-2] + "\n" + pieces[-1]]
    return pieces


def govuk_passages(doc: dict, source: str) -> list[Passage]:
    body = BeautifulSoup(doc["details"].get("body", ""), "html.parser")
    root = body.find("div", class_="govspeak") or body
    sections: list[tuple[list[str], str | None, list[str]]] = [([], None, [])]  # (heading path, anchor, blocks)
    path: list[tuple[int, str]] = []
    for el in root.find_all(["h2", "h3", "h4", "h5", "p", "ul", "ol", "table", "blockquote"]):
        if el.find_parent(["ul", "ol", "table", "blockquote"]):
            continue  # nested inside a block that's rendered whole
        if el.name in ("h2", "h3", "h4", "h5"):
            level = int(el.name[1])
            path = [(lvl, t) for lvl, t in path if lvl < level] + [(level, _clean(el.get_text(" ")))]
            sections.append(([t for _, t in path], el.get("id"), []))
        else:
            text = _block_text(el)
            if text:
                sections[-1][2].append(text)

    merged: list[tuple[list[str], str | None, str]] = []
    for heads, anchor, blocks in sections:
        text = "\n".join(blocks)
        if not text:
            continue
        prev = merged[-1] if merged else None
        if prev and (len(prev[2]) < MIN_CHARS or len(text) < MIN_CHARS) and heads[:1] == prev[0][:1]:
            merged[-1] = (prev[0], prev[1], prev[2] + "\n" + (" > ".join(heads[len(prev[0]):]) + "\n" if heads else "") + text)
        else:
            merged.append((heads, anchor, text))

    url = "https://www.gov.uk" + doc["base_path"]
    out = []
    for i, (heads, anchor, text) in enumerate(merged):
        for j, piece in enumerate(_split(text)):
            out.append(Passage(id=f"{doc['base_path']}#{i}.{j}", source=source, doc_id=doc["base_path"],
                               title=doc["title"], section=" > ".join(heads),
                               url=f"{url}#{anchor}" if anchor else url, updated=doc.get("public_updated_at", ""),
                               text=piece))
    return out


def _money(v: dict | None) -> str:
    if not v or "amount" not in v:
        return ""
    return f"{v.get('currency', '')} {v['amount']:,.0f}".strip()


def notice_text(release: dict) -> str:
    """A tender notice as text, from named fields only. Contact points, addresses and documents are never read."""
    t = release["tender"]
    buyer = release.get("buyer", {}).get("name", "")
    lines = [f"Tender notice: {t.get('title', '')}", f"Buyer: {buyer}"]
    if t.get("description"):
        lines.append(f"Description: {t['description']}")
    if c := t.get("classification"):
        lines.append(f"Main classification: {c.get('description', '')} ({c.get('scheme', '')} {c.get('id', '')})")
    for label, key in (("Category", "mainProcurementCategory"), ("Procedure", "procurementMethodDetails"),
                       ("How to respond", "submissionMethodDetails")):
        if t.get(key):
            lines.append(f"{label}: {t[key]}")
    if v := _money(t.get("value")):
        lines.append(f"Estimated value: {v}")
    if end := t.get("tenderPeriod", {}).get("endDate"):
        lines.append(f"Deadline for tenders: {end}")
    if end := t.get("enquiryPeriod", {}).get("endDate"):
        lines.append(f"Deadline for clarification questions: {end}")
    for lot in t.get("lots", []):
        lot_line = f"Lot {lot.get('id', '')}: {lot.get('title', '')}".rstrip(": ")
        if lot.get("description"):
            lot_line += f". {lot['description']}"
        if v := _money(lot.get("value")):
            lot_line += f" Value: {v}."
        lines.append(lot_line)
    sel = t.get("selectionCriteria", {})
    for crit in sel.get("criteria", []):
        if crit.get("description"):
            lines.append(f"Selection criterion: {crit['description']}")
    return _clean("\n".join(lines))


def notice_passages(release: dict) -> list[Passage]:
    text = notice_text(release)
    ocid = release["ocid"]
    url = f"https://www.find-tender.service.gov.uk/Notice/{release['id']}"
    return [Passage(id=f"{release['id']}#{j}", source="notice", doc_id=release["id"], title=release["tender"].get("title", ""),
                    section="", url=url, updated=release.get("date", ""), text=piece, meta={"ocid": ocid})
            for j, piece in enumerate(_split(text))]


def corpus_passages(raw: Path, manifest: Path) -> list[Passage]:
    docs = json.loads(manifest.read_text())["documents"]
    out = []
    for d in docs:
        if d["source"] == "notice":
            out += notice_passages(json.loads((raw / "notices" / (d["id"].replace("/", "_") + ".json")).read_text()))
        else:
            f = raw / "govuk" / (d["id"].strip("/").replace("/", "__") + ".json")
            out += govuk_passages(json.loads(f.read_text()), d["source"])
    return out
