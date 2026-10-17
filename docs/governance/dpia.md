# Data protection impact assessment

For the personal data in the tender notices, under UK GDPR. Structured as the ICO's guidance on DPIAs suggests: describe the processing, assess necessity and proportionality, identify risks, and record the measures taken. Not legal advice.

## Is a DPIA required?

Probably not. Article 35 requires one where processing is likely to result in a high risk to individuals, and the ICO's screening criteria (large-scale processing of special category data, systematic monitoring, profiling, decisions with legal effects, and so on) don't apply here. It's done anyway because the brief asks what happens to these contact details, and the answer should be written down before the system runs, not after someone asks.

## The processing

| | |
|---|---|
| Whose data | Contact people named in public tender notices: usually procurement officers at public bodies |
| What data | Name, work email address, work phone and fax number, as published on Find a Tender |
| Where it comes from | Find a Tender's public OCDS API, published under the Open Government Licence v3.0, which excludes personal data from what it licenses |
| How much | 167 notices, with a named contact in a minority of them. Exact counts are in [03-results.md](../03-results.md) |
| What's done with it | Downloaded with each notice, then excluded from everything else. Contact points are never read into passages; regular expressions and a guardrail mask what's left in free text. Nothing personal is embedded, stored in the database, sent to a model or logged |
| Where it's held | The raw downloads stay on the build machine in `data/raw/`, outside git, and are deleted when the project ends |
| Who it's shared with | Nobody. AWS processes only masked text, in London. GitHub holds the code, the manifest (ids, titles and checksums) and evaluation results, none of which contain contact details |

Questions typed into the assistant are a second, smaller source: a user might include a name or a number. They're masked the same way before they're logged or sent to a model.

## Lawful basis

Legitimate interests (Article 6(1)(f)). The interest is reading public tender notices to decide whether to bid. The contact details themselves aren't needed for that purpose, which is why they're removed at the first step. The processing that remains (downloading the notice, then discarding the contact fields) is what anyone does when they open a notice on Find a Tender.

## Necessity and proportionality

| Principle | How it's met |
|---|---|
| Data minimisation | Contact points are excluded by design, not filtered afterwards. The assistant can't answer "who is the contact for this tender?", and the model card says so |
| Purpose limitation | The raw notices are used only to build the passages and to run the N1 check |
| Storage limitation | Raw files deleted at the end of the project; the database holds masked text only |
| Accuracy | Not applicable to discarded data |
| Security | Local disk, a database bound to localhost, no copies in git, IAM role restricted to London |
| Transparency | This document and the datasheet are public in the repository |

## Risks

| Risk | Likelihood | Severity | Measure | Residual |
|---|---|---|---|---|
| A contact detail slips through into a passage and is shown in an answer | Low | Low: the detail is already public on Find a Tender | Allowlist rendering, two masking layers, `scripts/check_pii.py` searches every passage for every contact value | Low |
| A user types someone's details into a question and they're logged | Medium | Low | Questions masked before logging, including questions the guardrail blocks; tested in `tests/test_answer.py` and `tests/test_aws.py` | Low |
| Raw notices are committed to git by mistake | Low | Medium: a public copy that's hard to withdraw | `data/` is in `.gitignore`; the manifest holds no personal fields | Low |
| A masking step stops working after a change | Low | Low | The live guardrail test and the N1 check run in the evaluation workflow | Low |

## Outcome

Low residual risk; no consultation with the ICO needed. Reviewed again if the system starts storing raw notices, keeps contact details for a purpose, or is offered to anyone outside the client.
