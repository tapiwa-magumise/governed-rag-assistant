# EU AI Act classification

An assessment for the client's board, not legal advice. Checked against the Act as amended by Regulation (EU) 2026/1744 (the "Digital Omnibus on AI"), in force since 27 July 2026.

## Does the Act apply?

The client is a UK company using the assistant internally, on UK documents, for UK tenders. The Act reaches providers and deployers outside the EU only when they place a system on the EU market or the system's output is used in the EU (Article 2(1)). As built, neither is true, so the Act doesn't apply directly.

It's assessed anyway, for two reasons: clients and partners in the EU ask for it, and if the client later bids for EU work with the assistant's help, the output would be used in the EU.

## Classification

| Question | Answer | Why |
|---|---|---|
| Is it a prohibited practice (Article 5)? | No | It doesn't manipulate, exploit vulnerabilities, score people socially, or do biometric identification |
| Is it high-risk under Annex III? | No | It answers questions about published guidance and public notices. It doesn't decide anything about a person's access to work, education, credit, benefits or public services, and it doesn't support law enforcement, migration or justice. It doesn't award contracts: contracting authorities do that, and they don't use this system |
| Is it high-risk under Annex I (safety components of regulated products)? | No | It isn't part of a product |
| Is it a general-purpose AI model? | No | It *uses* one, Amazon Nova Lite. The obligations for general-purpose AI models fall on Amazon as their provider |
| Does it have transparency obligations (Article 50)? | Yes | It interacts directly with people and generates text |

So it's a limited-risk system: no conformity assessment, but transparency duties.

## What that requires, and how it's met

| Obligation | Applies from | How the system meets it |
|---|---|---|
| Tell people they're dealing with an AI system, unless it's obvious (Article 50(1)) | 2 August 2026, not deferred by the omnibus | The page says it's an AI assistant above the question box, and every answer is labelled as generated |
| Mark generated text as AI-generated in a machine-readable way (Article 50(2)) | 2 August 2026 for systems placed on the market from that date | Every API response carries `generated_by` with the model id. Answers are drawn from cited public documents, which keeps them close to the assistive-function exception, but the marking costs nothing so it's there regardless |
| AI literacy for staff who use it (Article 4) | 2 February 2025 | The model card is written for users, not engineers: what it's for, what it isn't, how it fails. A short briefing for the client's staff is listed in the risk assessment |

## Dates that moved

The omnibus deferred the high-risk obligations: to 2 December 2027 for Annex III systems and 2 August 2028 for Annex I. Neither affects this system. The Article 50 transparency duties kept their August 2026 date, with a grace period to 2 December 2026 only for machine-readable marking on systems already on the market before 2 August 2026.

## If the use changed

Two changes would need this reassessed before going ahead:

- Using it to screen or rank suppliers, or to make or recommend award decisions for a contracting authority. That moves it towards decisions about access to public services and contracts, and towards Annex III.
- Offering it to the public or to other companies. The client would become a provider placing it on the market, with Article 50 duties as a provider rather than a deployer.

## Sources

- [AI Act Explorer: Digital Omnibus on AI](https://artificialintelligenceact.eu/ai-act-explorer/digital-omnibus/), for the regulation number, entry into force and the new dates
- [Orrick, July 2026](https://www.orrick.com/en/Insights/2026/07/EU-AI-Act-Update-Digital-Omnibus-Finalizes-8-Compliance-Changes) and [Morgan Lewis, June 2026](https://www.morganlewis.com/pubs/2026/06/eu-approves-delays-and-other-amendments-to-certain-eu-ai-act-obligations-what-businesses-should-know), for the Article 50 timing
