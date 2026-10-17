# Brief: a procurement assistant that can show its working

*The client is fictional. The documents are real: the UK government's guidance on the Procurement Act 2023, its current procurement policy notes, and a sample of live tender notices from Find a Tender, all published under the Open Government Licence v3.0.*

## Background

A small UK IT supplier wants to start bidding for public-sector contracts. The Procurement Act 2023 replaced the old regulations for procurements started from 24 February 2025, and the rules now sit across nearly a hundred guidance documents and two dozen policy notes. Nobody in the company has time to read them all, and the managing director asks the same questions every week: what counts as a conflict of interest, when a supplier can be excluded, what the thresholds are this year, what a particular tender actually asks for.

They want an assistant that answers those questions from the official documents. Two things worry them more than the answers themselves. A wrong answer that sounds confident could cost them a bid or put them in breach. And tender notices contain the names, phone numbers and email addresses of real public servants, which they must not copy into another system without a reason.

## Documents

| Source | What | How many |
|---|---|---|
| [Procurement Act 2023 guidance](https://www.gov.uk/government/collections/procurement-act-2023-guidance-documents) | The Cabinet Office's guidance, in four phases: plan, define, procure, manage | HTML documents in the four phase publications |
| [Procurement policy notes](https://www.gov.uk/government/collections/procurement-policy-notes) | The notes that apply to procurements under the Act. Notes for the 2015 regulations and notes marked out of date are left out | The "Procurement Act 2023 PPNs" group |
| [Find a Tender](https://www.find-tender.service.gov.uk/) | Live tender notices, from its OCDS API | A dated sample, fixed when the corpus is built |

All three are Crown copyright under the [Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/). The licence does not cover personal data in the information, so the contact details in tender notices can't be republished on the strength of it.

## What it must do

| # | Requirement |
|---|---|
| F1 | Answer questions about the Act's guidance and the current policy notes, citing the passages the answer comes from, with each document's last-updated date |
| F2 | Answer questions about a tender notice in the sample: what's being bought, its value, deadlines, how to respond |
| F3 | Say it doesn't know when the documents don't answer the question, instead of guessing |
| F4 | Decline to give legal advice on a specific case, and decline questions that have nothing to do with procurement |

## How it will be judged

Each of these is measured and the result recorded in `docs/03-results.md`.

| # | Requirement |
|---|---|
| N1 | No personal data from the tender notices is stored, embedded, logged or sent to a model. Checked against every contact field in the source notices |
| N2 | Documents, prompts and answers stay in the UK: every model call goes to eu-west-2, and the app's permissions allow nothing else |
| N3 | Every answer cites at least one passage, and a grounding check confirms the passages support it. Answers that fail it aren't shown |
| N4 | For a hand-written set of questions with known source passages, the right passage is in the top five retrieved for at least 90% of them |
| N5 | At least 95% of out-of-scope questions and legal-advice requests are declined |
| N6 | None of a set of prompt-injection attempts, in questions or planted in a document, makes it break these rules |
| N7 | Every question and answer is logged with the passages used, the model, what the guardrail did, tokens and cost, with no personal data in the log |
| N8 | Only current documents are used: superseded notes are excluded, and the corpus can be rebuilt to a known date |
| N9 | No long-lived AWS keys, including in CI |
| N10 | Under $10 of AWS spend, and everything in AWS deleted at the end |

## Governance documents

The client's board will ask whether this is safe to use. The project ships the documents an AI governance review would ask for:

- a model card: what the system does, what it's for and not for, how it was tested, its known failure modes
- a datasheet for the document set: where it came from, its licence, what was excluded and why
- a risk assessment against the controls in ISO/IEC 42001 Annex A
- its classification under the EU AI Act and what that requires
- a data protection impact assessment under UK GDPR, for the contact details in tender notices

## Scope

**In:** the corpus and its rebuild, personal data masking, retrieval, answers with citations, guardrails, the audit log, the evaluation sets and their results, a small web page, the governance documents, Terraform for the AWS parts, CI.

**Out:** live updates as new notices are published, user accounts, hosting it for the public, and anything that needs a lawyer. The assistant points to guidance; it doesn't replace legal advice, and the model card says so.
