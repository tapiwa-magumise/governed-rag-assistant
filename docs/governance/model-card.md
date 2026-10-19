# Model card: the procurement assistant

Written for the people who will use the assistant, not for engineers: what it's for, what it isn't for, how it was tested, and how it fails. Follows the sections in Mitchell et al., *Model Cards for Model Reporting* (2019), adapted to a system that answers from documents.

## What it is

An assistant that answers questions about UK public procurement. It reads only 260 published documents: the government's guidance on the Procurement Act 2023, the procurement policy notes that apply under the Act, and a month of tender notices from Find a Tender. It finds the passages that match a question and has a language model write an answer from those passages alone, citing each one.

| | |
|---|---|
| Owner | The client's managing director, who decides who may use it and for what |
| Built by | The developer of this repository, who is responsible for the controls below working as described |
| Answer model | Amazon Nova Lite, run by Amazon Bedrock in London, at temperature 0 |
| Search model | Amazon Titan Text Embeddings v2, in London |
| Checks | Amazon Bedrock Guardrails, on every question and every answer |
| Documents | Listed with their dates in the [datasheet](datasheet.md) |

## What it's for

- Finding what the guidance and policy notes say about a rule, with the paragraph to read.
- Checking a threshold, a deadline or a procedure before a bid.
- Reading a tender notice in the sample: what's being bought, its value, its deadlines, how to respond.

## What it's not for

- Legal advice. It describes what the guidance says. It won't say what to do in a particular dispute, and it declines when asked. Anything that matters should go to a lawyer.
- Finding open tenders. The notices are a fixed sample from September 2026, and most have closed.
- Contacting buyers. Contact names, emails and phone numbers are never read into it, so it can't answer "who is the contact for this tender?". The notice itself, linked from every citation, has them.
- Anything outside public procurement. It declines.

## Before relying on an answer

Open the cited passage and read it. Each citation shows the document's last-updated date and links to the paragraph. The assistant is a way to find the right paragraph quickly, not a substitute for reading it.

## How it decides what to say

1. Email addresses and phone numbers in the question are masked. The guardrail then blocks prompt attacks and two topics (legal advice on a specific case, and collusion or concealment), and masks names.
2. It searches the documents by meaning and by wording, and keeps the six best passages.
3. If none of them is close to the question, it replies that the documents don't answer it. No model is asked.
4. The model writes an answer from the six passages, citing them. It is told to treat their text as material, never as instructions.
5. The guardrail checks the answer against the passages. If the answer isn't well supported by them (a grounding score below 0.75 or a relevance score below 0.5), or cites nothing, it isn't shown.
6. Every question and outcome is logged, with personal data masked.

Under every answer, the page shows how it was checked: the scores, and what the guardrail did.

## How it was tested

| Requirement | Test | Result |
|---|---|---|
| No personal data from the notices in the index (N1) | Every one of the 354 contact values in the source notices searched for in all 2,276 passages | No names, emails or phone numbers found |
| The right passage is found (N4) | 32 questions whose source passages are known; the right one must be in the top five for at least 90% | Not yet run |
| It declines what it should (N5) | 20 questions outside the documents or asking for legal advice; at least 95% declined | Not yet run |
| Injected instructions don't work (N6) | 10 attempts in questions, and one planted in a passage in the index | Not yet run |
| Prompts stay in the UK (N2) | A call to another region with the app's permissions | Refused |

The evaluation hasn't run yet. Its results, and the similarity threshold in step 3, will be added when it does. Until then, nothing here says how often its answers are right.

## How it fails

These are known weaknesses of the design. How often each happens will be measured by the evaluation.

- It can withhold a correct answer. The grounding check is strict by design; a correct answer phrased differently from its passage may score below the bar. The reply then says it couldn't give an answer the documents support.
- It can miss a passage. If the right paragraph isn't among the six it finds, the answer is incomplete or it says the documents don't answer.
- Documents can disagree. The Utilities Contracts guidance (April 2026) still gives the 2024 threshold for utilities works; PPN 023 sets a lower one from 1 January 2026. The assistant shows the date of each source, and the newer one should win. One of the test questions checks this.
- It's a snapshot. Guidance published after the documents were downloaded isn't there.
- Masking isn't perfect. Names are found by the guardrail's detector, which can miss unusual names or mark ordinary words. The contact sections of notices are excluded entirely for this reason, rather than relying on masking.
- Its refusals rely on wording. A request for legal advice phrased as a general question may get a general answer.

## Data and privacy

The documents are Crown copyright under the Open Government Licence v3.0, which doesn't cover personal data; see the [datasheet](datasheet.md) and the [data protection impact assessment](dpia.md). Questions are masked before they are logged or sent to a model. Bedrock keeps its own log of model calls in London for 30 days, of the masked text.

## Related documents

- [Risk assessment](risk-assessment.md), against ISO/IEC 42001 Annex A
- [EU AI Act classification](eu-ai-act.md): a limited-risk system with transparency duties
- [Decisions](../02-decisions.md), with the trade-offs behind each choice
