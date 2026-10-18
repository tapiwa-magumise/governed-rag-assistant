# Decisions

What was built, and why each choice was made. The requirements (F1 to F4, N1 to N10) are in [01-brief.md](01-brief.md).

## Tools

| Need | Choice | Why |
|---|---|---|
| Answer model | Amazon Nova Lite, on demand in eu-west-2 | Runs in London itself, so prompts never leave the UK (N2). Amazon's own model, billed normally, so the account's promotional credits apply. $0.000084 per 1,000 input tokens |
| Judge for the evaluations | Amazon Nova Pro, eu-west-2 | A stronger model to check the answers of a weaker one, and still in London |
| Embeddings | Titan Text Embeddings v2, 1,024 dimensions, eu-west-2 | In London, and cheap enough to rebuild the whole index for a few cents |
| Not chosen | Claude on Bedrock | In this account it's offered only through cross-region inference profiles, which can route requests outside the UK, and it's billed through AWS Marketplace, which promotional credits may not cover |
| Vector store | Postgres 17 with pgvector, in Docker | One database for the passages, the full-text index and the audit log. Free to run, and the same image runs in CI |
| Guardrails | Bedrock Guardrails, two of them | One masks personal data at ingest. The other checks questions and answers: prompt attacks, two denied topics, personal data, and whether an answer is grounded in its passages |
| API and page | FastAPI, serving one HTML page with no build step | A React app was planned; the finished page needs only four views and the current answer (build log) |
| Infrastructure | Terraform, local state | Everything in AWS is deleted at the end (N10), so there's no shared state to keep |

## The documents

Guidance and policy notes come from the GOV.UK Content API rather than scraped pages: it returns the HTML body with its update date, and the same request gives the same document. Only HTML attachments are used; the PDF and ODT attachments are copies of them. Policy notes are taken from the collection's "Procurement Act 2023 PPNs" group only, so notes for the 2015 regulations and notes marked out of date can't be retrieved (N8).

The tender notices are every tender-stage notice Find a Tender updated in September 2026. The manifest records each document's id, update date and a checksum of its content, and `scripts/extract.py` reports any difference when the corpus is downloaded again.

## Passages

Guidance is split at its own headings, and a passage keeps its heading path and the anchor of its heading, so a citation links to the right paragraph. Sections shorter than 300 characters are joined to a neighbour under the same top heading, and sections longer than 1,800 are split at paragraphs, then sentences. 1,800 characters is about 400 tokens: long enough for a rule and its exceptions, short enough that a citation points somewhere specific. Tables are kept as rows of cells separated by `|`, because the threshold tables are what people ask about.

Tender notices are rendered as text from named fields only: title, buyer, description, classification, value, deadlines, lots and selection criteria. Contact points, addresses and attached documents are never read.

## Personal data (N1)

Two layers, before anything is embedded or stored:

1. Regular expressions mask every email address and UK phone number. This includes team mailboxes in the guidance: telling a person's address from a team's isn't reliable, and an answer can link to the source page instead.
2. The ingest guardrail masks names, emails, phone numbers, National Insurance numbers and tax references in what's left.

Questions go through the same two layers before they're logged. A question the guardrail blocks comes back as the refusal message, not as masked text, so it's masked separately before it's stored.

Bedrock's own invocation log is switched on and kept for 30 days in CloudWatch. Prompts are masked before they reach the model, so that log holds no personal data either. Embedding calls aren't logged: the vectors add volume and no insight.

## Answering

Retrieval combines vector similarity with Postgres full-text search, fused by reciprocal rank. Vector search finds paraphrases; full-text search finds exact terms such as a notice number or "PPN 023". Six passages go to the model.

If even the best passage is a weak match, the question is treated as outside the documents and no model is called. The threshold was set from the evaluation runs; see [03-results.md](03-results.md).

The model is told to use only the passages, cite each statement, treat passage text as material rather than instructions, and reply with a fixed sentence when the passages don't answer. Its answer then goes back through the guardrail with the passages as the grounding source. An answer scoring below 0.75 for grounding or 0.5 for relevance isn't shown, and nor is an answer with no citation.

## Guardrail versions

The app uses a numbered guardrail version, so a change to the guardrail can't alter its behaviour unnoticed. Terraform takes a new version whenever a guardrail changes.
