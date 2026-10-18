# Risk assessment

The risks of the procurement assistant to the client, the people named in the documents and the client's bids, with the controls in place and the evidence for each. Mapped to the controls in Annex A of ISO/IEC 42001:2023 (AI management systems).

The Annex A control titles below are taken from two published summaries of the standard that agree with each other ([TCSA](https://www.tcsa.in/frameworks/iso-42001/controls), [RiskProfs](https://riskprofs.com/iso-42001-annex-a-controls-list/)); the standard's own text wasn't consulted. This is a portfolio project, so it shows how the controls apply to one system, not a certified management system.

## Risk register

Likelihood and impact are rated low, medium or high, before and after the controls.

| # | Risk | Before | Controls | After | Evidence |
|---|---|---|---|---|---|
| R1 | A confident wrong answer leads the client to misjudge a rule and lose a bid or breach the Act | High | Answers only from cited passages; grounding check blocks unsupported answers; fixed "don't know" reply; every passage dated; model card says to check the source | Medium | N3 and the golden set in [03-results.md](../03-results.md) |
| R2 | It answers from out-of-date guidance | Medium | Superseded policy notes excluded; manifest with dates and checksums; dates shown on every citation | Low | N8, datasheet |
| R3 | Personal data from tender notices reaches the index, a model, the log or an answer | Medium | Allowlist rendering; regex and guardrail masking; masked questions; invocation log of masked prompts only | Low | N1 check over every passage and log row |
| R4 | A prompt injection, in a question or planted in a document, makes it break its rules | Medium | Prompt attack filter; passages framed as material, not instructions; grounding check; planted-injection test | Low | N6, injection and planted sets |
| R5 | It's used for legal advice on a specific dispute | Medium | Denied topic in the guardrail; model told to describe guidance, not advise; model card | Low | N5, out-of-scope set |
| R6 | It helps conceal a conflict of interest or coordinate bids | Low | Denied topic in the guardrail | Low | N5, out-of-scope set |
| R7 | Prompts or documents leave the UK | Medium | Models invoked only in eu-west-2 through tagged profiles; IAM deny outside London; Amazon's own models, no cross-region routing | Low | N2: a call to eu-west-1 refused in testing |
| R8 | Costs run away | Low | Budget alarm on Bedrock; cost per question logged; no model call when retrieval is weak | Low | N10 |
| R9 | Users trust it more than its tested accuracy warrants | Medium | Model card in plain English; evaluation results on the page; "how this answer was checked" under every answer | Medium | Model card, web page |
| R10 | A guardrail or model update changes behaviour unnoticed | Low | Numbered guardrail versions; evaluation workflow re-runs every set | Low | Decisions, CI |

## Statement of applicability (ISO/IEC 42001 Annex A)

"Applies" means the control is relevant to this system. Where it doesn't apply, the reason is given. Several controls concern the organisation running the system rather than the system itself; for those, the column says what the client would need.

| Control | Applies | How it's met, or why not |
|---|---|---|
| A.2.2 AI policy | Client | The client needs a short AI use policy; the model card's "intended use" is a starting point |
| A.2.3 Alignment with other organisational policies | Client | Aligns with the client's data protection policy via the DPIA |
| A.2.4 Review of the AI policy | Client | Review when the use changes; see "if the use changed" in the EU AI Act assessment |
| A.3.2 AI roles and responsibilities | Yes | Model card names the owner (the managing director) and the builder's responsibilities |
| A.3.3 Reporting of concerns | Yes | The audit log id under each answer lets a user report a specific answer |
| A.4.2 Resource documentation | Yes | Decisions document: models, store, guardrails, infrastructure |
| A.4.3 Data resources | Yes | Datasheet |
| A.4.4 Tooling resources | Yes | `requirements.txt` pinned; Terraform provider pinned |
| A.4.5 System and computing resources | Yes | Terraform; local Postgres; quotas recorded in the build log |
| A.4.6 Human resources | Client | Staff using it need the model card briefing (AI literacy) |
| A.5.2 AI system impact assessment process | Yes | This document and the DPIA |
| A.5.3 Documentation of AI system impact assessments | Yes | Kept in the repository with the code |
| A.5.4 Assessing impact on individuals or groups | Yes | DPIA for the people named in notices; R1 and R9 for users |
| A.5.5 Assessing societal impacts | Limited | One supplier's internal tool; no effect on how contracts are awarded. Reassess if used by a contracting authority |
| A.6.1.2 Objectives for responsible development | Yes | The brief's requirements F1 to F4 and N1 to N10 |
| A.6.1.3 Processes for responsible design and development | Yes | Requirements first, decisions recorded, build log of every problem |
| A.6.2.2 AI system requirements and specification | Yes | The brief |
| A.6.2.3 Documentation of design and development | Yes | Decisions and build log |
| A.6.2.4 Verification and validation | Yes | Offline tests, live guardrail tests, four evaluation sets, the N1 check |
| A.6.2.5 AI system deployment | Limited | Runs locally for the client; no public deployment |
| A.6.2.6 Operation and monitoring | Yes | Audit log, Bedrock invocation log, budget alarm |
| A.6.2.7 Technical documentation | Yes | README, decisions |
| A.6.2.8 Recording of event logs | Yes | Audit log of every question and answer, masked; invocation log for 30 days |
| A.7.2 Data for development and enhancement | Yes | The corpus is the only data; no model is trained or fine-tuned |
| A.7.3 Acquisition of data | Yes | Public APIs, Open Government Licence; datasheet |
| A.7.4 Quality of data | Yes | Official sources only; superseded notes excluded; chunking tested |
| A.7.5 Provenance of data | Yes | Manifest with ids, dates, checksums; every citation links to its source |
| A.7.6 Data preparation | Yes | Chunking and masking, both documented and tested |
| A.8.2 System documentation and information for users | Yes | Model card; the page's "how this answer was checked" |
| A.8.3 External reporting | Limited | The repository is public; no regulator reporting applies |
| A.8.4 Communication of incidents | Client | The client would tell affected people if personal data were exposed; DPIA |
| A.8.5 Information for interested parties | Yes | AI disclosure on the page and `generated_by` on every answer (EU AI Act Article 50) |
| A.9.2 Processes for responsible use | Client | The model card's "check the source before relying on an answer" |
| A.9.3 Objectives for responsible use | Client | Faster answers to rule questions; not decisions |
| A.9.4 Intended use of the AI system | Yes | Model card |
| A.10.2 Allocating responsibilities | Yes | AWS (infrastructure, Nova as provider of the model), the builder (system), the client (use) |
| A.10.3 Suppliers | Yes | AWS: London region; zero data retention tested and refused by the models, so each model's own retention terms apply; decisions document |
| A.10.4 Customers | Client | The client's staff are the users; no external customers |
