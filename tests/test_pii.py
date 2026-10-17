from rag.pii import digits, mask


def test_masks_emails_and_uk_phone_numbers():
    text, counts = mask("Call 01632 960001 or +44 20 7946 0958, or email someone.name@example.gov.uk.")
    assert "{EMAIL}" in text and text.count("{PHONE}") == 2
    assert "960001" not in text and "@" not in text
    assert counts == {"EMAIL": 1, "PHONE": 2}


def test_leaves_money_dates_and_references_alone():
    for s in ("£5,193,000", "GBP 51,700,000", "24 February 2025", "section 54(3)", "PPN 023", "2026-10-06T12:00:00"):
        assert mask(s) == (s, {})


def test_digits():
    assert digits("+44 (0)20 7946-0958") == "440207946" + "0958"
