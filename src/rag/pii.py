"""The deterministic first layer of personal data masking. The ingest guardrail runs after it and catches names.

Every email address is masked, including team mailboxes in the guidance: telling a person's address from a
team's isn't reliable, and an answer can link to the source page instead.
"""
import re

EMAIL = re.compile(r"[\w.+'-]+@[\w-]+(?:\.[\w-]+)+")
# UK numbers: +44 or 0, then 9 or 10 more digits in groups. Amounts like 2,500,000 never match: they use commas.
PHONE = re.compile(r"(?<![\w£$€.,])(?:\+44\s?(?:\(0\)\s?)?|\(?0)\d{2,4}\)?[\s-]?\d{3,4}[\s-]?\d{3,4}(?![\w,.]\d)")


def mask(text: str) -> tuple[str, dict[str, int]]:
    counts = {}
    text, counts["EMAIL"] = EMAIL.subn("{EMAIL}", text)
    text, counts["PHONE"] = PHONE.subn("{PHONE}", text)
    return text, {k: v for k, v in counts.items() if v}


def digits(s: str) -> str:
    return re.sub(r"\D", "", s)
