# Build log

Everything that went wrong or surprised me, in the order it happened, and what I did about it.

## The documents

### Python couldn't check GOV.UK's certificate

The first download failed with `CERTIFICATE_VERIFY_FAILED`. The python.org build of Python 3.13 on macOS doesn't use the system's certificates. The extract script now verifies against `certifi`'s bundle instead of switching verification off.

### The guidance is clean; the notices aren't

The guidance and policy notes contain almost no personal data, so masking them proves little. Tender notices from Find a Tender carry the name, phone number and email of a named buyer contact, and the Open Government Licence they're published under excludes personal data. So a month of notices joined the corpus: 167 tender-stage notices updated in September 2026. Contact points are left out of the text entirely, and the masking guardrail runs over everything else.

The raw notices stay out of git. The manifest records each notice's id, title and a checksum, enough to tell whether a rebuild used the same data, and nothing personal.

## AWS

### The personal data filter ignored questions

Bedrock Guardrails' personal data filter was set to mask names, emails and phone numbers. Tested with a synthetic contact line, it masked all three when the text was checked as model output, and did nothing when the same text was checked as input. The `ANONYMIZE` action applies to output unless input masking is switched on separately. Left like that, a question containing someone's details would have reached the audit log unmasked. Both guardrails now set input and output masking explicitly, and the test that found it is in `tests/test_aws.py`.

### Guardrail versions don't follow the guardrail

The app uses a numbered guardrail version, so its behaviour can't change under it. Terraform doesn't take a new version when the guardrail changes, so the fix above would have been ignored by the app. Each version is now replaced whenever its guardrail changes.

## Building the index

### One timeout lost the whole run

The first full build stopped near the end: an embedding response timed out while its body was being read. botocore retries a failed request, but not a body that stalls mid-read, and the indexer held every result in memory until the end, so one failure threw away about $0.40 of work. Embedding calls now retry on a read timeout, and each finished passage is cached to disk as soon as it's done, keyed by its content. A rerun picks up where the last one stopped and pays only for what's new.

### The free personal data filter wasn't free

AWS's price list shows the built-in personal data types at $0 per text unit. In practice the guardrail reported every unit as paid: $0.10 per 1,000 text units, each block rounded up to a whole 1,000 characters. That's still small for this corpus, but sending a passage's title, section and text as three blocks would have tripled the rounding, so each passage goes as one block with separators that are checked when it comes back.

### Sixty embeddings a minute

The build slowed to about 25 passages a minute. Single calls were quick, so I checked the account's Bedrock quotas: Titan Text Embeddings v2 allows 60 requests a minute here, and it embeds one text per request. Eight threads were hitting the limit, and the client's growing backoff made it slower than the limit itself. A shared rate limiter now spaces embedding calls at 57 a minute, and the full index takes about 40 minutes. The guardrail's limit, 25 requests a second, was never the problem.

The last stretch of the build ran at about 24 passages a minute, under half the limiter's rate, without errors. I didn't find the cause; the run finished at 2,276 passages and $0.36 for the 1,907 that weren't already cached.

## Settings that live outside the code

### Zero data retention

Bedrock now has an account setting for whether AWS keeps prompts and responses. London was on `inherit`, which leaves it to each model. I set it to `none` and made one small call to Titan, Nova Lite, Nova Pro and both guardrails straight away. All five worked, and I took that as a pass. It wasn't: the setting hadn't taken effect. Later, every call to Titan and both Nova models failed with `ValidationException: Operation not allowed`, which is how Bedrock refuses a model that needs data kept, while the guardrails carried on working. The setting is back to `inherit`, and each model's own retention terms apply. A test of a setting that propagates needs to wait for it.

### The budget depends on a variable

The budget's alert address is passed when Terraform runs, so it never sits in the public repository. The other side of that: running Terraform without the address would delete the budget. Every apply passes it.

## The web page

### From a React plan to one HTML file

The brief planned a small React page. Once the design settled, the page needed no state beyond the current answer and four views, so it became one HTML file that FastAPI serves next to the API, with no build step and no npm packages to keep current. It uses the system's own fonts, so nothing is loaded from elsewhere and no visitor's address goes to a font service.

### When Bedrock refuses

When Bedrock refused a model call, a question failed with a bare 500 error. The API now returns 503 with a plain message, and the page says nothing was answered. A question that fails this way isn't written to the audit log: masking names needs the guardrail, and the guardrail is part of what's failing. Storing the question unmasked would break N1, so the gap is accepted and recorded here.
