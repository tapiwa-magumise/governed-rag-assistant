"""N1: no personal data from the tender notices in the passages or the audit log.

Collects every contact name, email, phone and fax number from the raw notices, then searches every stored passage
and every audit log row for them. Phone numbers are compared by their last nine digits, so spacing or a +44 prefix can't hide a match.
Contact "names" that are a team or a role ("Procurement Team") aren't personal data and are counted separately.
Prints counts only: the values themselves are never printed.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from rag.db import connect
from rag.pii import digits

ROLE_WORDS = re.compile(r"\b(team|department|dept|procurement|commercial|contracts?|office|services?|unit|council|"
                        r"board|trust|authority|admin|enquiries|tenders?|purchasing|finance|estates|nhs|ltd|limited)\b",
                        re.IGNORECASE)


# A phone-shaped run: digits joined only by spaces, dashes, dots or brackets. Joining every digit in a text
# would line up amounts, dates and checksums into false nine-digit matches.
PHONE_RUN = re.compile(r"\+?\d[\d\s().-]{7,}\d")


def phone_runs(text: str) -> set[str]:
    return {d[-9:] for m in PHONE_RUN.finditer(text) if len(d := digits(m.group())) >= 9}


def contacts() -> dict[str, set[str]]:
    found = {"name": set(), "role_name": set(), "email": set(), "phone": set()}
    for f in (ROOT / "data" / "raw" / "notices").glob("*.json"):
        release = json.loads(f.read_text())
        for party in release.get("parties", []):
            for cp in [party.get("contactPoint", {}), *party.get("additionalContactPoints", [])]:
                if name := (cp.get("name") or "").strip():
                    (found["role_name"] if ROLE_WORDS.search(name) else found["name"]).add(name.lower())
                if email := (cp.get("email") or "").strip():
                    found["email"].add(email.lower())
                for key in ("telephone", "faxNumber"):
                    if len(d := digits(cp.get(key) or "")) >= 9:
                        found["phone"].add(d[-9:])  # the last nine digits survive any +44 / 0 prefix
    return found


def main() -> None:
    c = contacts()
    with connect() as conn:
        texts = [r[0] for r in conn.execute("SELECT title || ' ' || section || ' ' || text FROM passage")]
        audit = [r[0] for r in conn.execute("SELECT coalesce(question, '') || ' ' || coalesce(answer, '') FROM audit_log")]
    report = {}
    for label, corpus in (("passages", texts), ("audit_log", audit)):
        low = [t.lower() for t in corpus]
        dig = [phone_runs(t) for t in corpus]
        report[label] = {
            "rows": len(corpus),
            "personal_names_found": sum(any(n in t for t in low) for n in c["name"]),
            "emails_found": sum(any(e in t for t in low) for e in c["email"]),
            "phone_numbers_found": sum(any(p in runs for runs in dig) for p in c["phone"]),
            "role_names_found": sum(any(n in t for t in low) for n in c["role_name"]),
        }
    checked = {k: len(v) for k, v in c.items()}
    print(json.dumps({"contact_values_checked": checked, **report}, indent=1))
    failed = any(report[s][k] for s in report for k in ("personal_names_found", "emails_found", "phone_numbers_found"))
    print("N1 FAIL" if failed else "N1 pass: no contact name, email or phone number found")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
