import json
from pathlib import Path

from rag.chunk import MAX_CHARS, _split, govuk_passages, notice_passages, notice_text

FIX = Path(__file__).parent / "fixtures"


def test_guidance_passages_keep_heading_path_and_anchor():
    ps = govuk_passages(json.loads((FIX / "guidance.json").read_text()), "guidance")
    standstill = next(p for p in ps if "eight working days" in p.text)
    assert standstill.section.startswith("Standstill")
    assert standstill.url.endswith("#standstill")
    assert standstill.updated.startswith("2026-08-17")


def test_short_sections_join_their_neighbour():
    ps = govuk_passages(json.loads((FIX / "guidance.json").read_text()), "guidance")
    # The one-line Exceptions list joins the Standstill section it belongs to.
    standstill = next(p for p in ps if "eight working days" in p.text)
    assert "user choice contracts" in standstill.text


def test_tables_keep_their_rows():
    ps = govuk_passages(json.loads((FIX / "guidance.json").read_text()), "guidance")
    assert any("Works | £5,193,000" in p.text for p in ps)


def test_long_text_splits_under_the_limit():
    text = "\n".join(f"Paragraph {i}. " + "word " * 60 for i in range(40))
    pieces = _split(text)
    assert len(pieces) > 1
    assert all(len(p) <= MAX_CHARS + 400 for p in pieces)
    assert "".join(pieces).replace("\n", "") == text.replace("\n", "")


def test_notice_text_never_reads_contact_points_or_addresses():
    release = json.loads((FIX / "notice.json").read_text())
    text = notice_text(release)
    for value in ("Alex Placeholder", "alex.placeholder@example.org", "1632 960001", "Fictional Street", "ZZ1 1ZZ"):
        assert value not in text
    for value in ("Cloud hosting services", "Example Borough Council", "GBP 250,000", "2026-10-20"):
        assert value in text


def test_notice_passages_link_to_find_a_tender():
    (p,) = notice_passages(json.loads((FIX / "notice.json").read_text()))
    assert p.url == "https://www.find-tender.service.gov.uk/Notice/000001-2026"
    assert p.source == "notice"
