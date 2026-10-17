# Datasheet: the document set

What the assistant answers from, where it came from, and what was deliberately left out. Follows the questions in Gebru et al., *Datasheets for Datasets* (2021), cut down to the ones that apply to a retrieval corpus.

## What it is

| Source | Documents | Passages | Last updated, oldest to newest |
|---|---|---|---|
| Procurement Act 2023 guidance (Cabinet Office) | 49 | 1,063 | 15 April 2026 to 17 August 2026 |
| Procurement policy notes for the Act | 44 | 845 | 13 February 2025 to 5 August 2026 |
| Tender notices from Find a Tender | 167 | 368 | 1 to 30 September 2026 |
| **Total** | **260** | **2,276** | |

The guidance and policy notes are the HTML versions published on GOV.UK. The 49 guidance documents sit in four publications (plan, define, procure, manage); the 44 policy note documents sit in 24 policy notes, several of which have a guide or FAQ alongside the note itself.

The notices are every tender-stage notice that Find a Tender's OCDS API reported as updated between 1 and 30 September 2026. They cover all sectors, not only IT: the sample was chosen for its personal data, not its subject.

## Why it was assembled

To answer a small supplier's questions about public procurement rules and live tenders. See [the brief](../01-brief.md).

## How it was collected

`scripts/extract.py` downloads it: guidance and policy notes from the GOV.UK Content API, notices from Find a Tender's OCDS release packages. `corpus/manifest.json` records every document's id, title, last-updated date and a SHA-256 checksum of its content. Downloading again reports any document added, removed or changed since the manifest was written. A second download on the day of the build matched it exactly.

## What was left out, and why

| Left out | Why |
|---|---|
| Policy notes for the Public Contract Regulations 2015 | They apply to procurements started before 24 February 2025. Mixing them in would let the assistant answer with the old rules |
| Policy notes marked out of date | Superseded (N8) |
| PDF and ODT attachments | Copies of the HTML documents |
| Welsh Government guidance | Wales publishes its own guidance for devolved Welsh authorities; it isn't in the Cabinet Office collection |
| Contact points, addresses and attached documents in notices | Personal data, which the licence doesn't cover (see below) |
| Contract award and other later-stage notices | The supplier's questions are about opportunities still open |

## Licence

All three sources are Crown copyright, published under the [Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/), which allows reuse with attribution. The licence states that it doesn't cover personal data in the information. That's why the contact details in tender notices are never read into passages, and why a guardrail masks any personal data left in the free text.

Attribution: Contains public sector information licensed under the Open Government Licence v3.0.

## Personal data

| Where | What | What happens to it |
|---|---|---|
| Notice contact points | Names, emails, phone and fax numbers of public servants | Never read: notices are rendered from an allowlist of fields |
| Notice descriptions and other free text | Occasionally names or contact details | Masked by regular expressions, then by the ingest guardrail |
| Guidance and policy notes | Team mailboxes, the odd named official | Masked the same way |

The raw downloads stay on the build machine, outside git, and are deleted at the end of the project. `scripts/check_pii.py` searches every passage and every audit log row for every contact value in the raw notices; the result is in [03-results.md](../03-results.md).

## Known limits

- It's a snapshot. Guidance changes; the manifest shows the date of every document, and answers show the date of every passage they cite.
- One document can contradict another when one is newer. The Utilities Contracts guidance (April 2026) still lists the 2024 threshold for a utilities works contract, £5,372,609; PPN 023 sets it at £5,193,000 from 1 January 2026. One of the evaluation questions checks which the assistant uses.
- Tables are flattened into rows of text, which keeps the figures but loses some layout.
- September's notices have mostly closed by now. They're there to answer questions about real notices, not to find open opportunities.
