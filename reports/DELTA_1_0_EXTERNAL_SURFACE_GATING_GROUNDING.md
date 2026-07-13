# DELTA 1.0 External Surface Gating Grounding

Date: 2026-07-11
Status: PROPOSAL_ONLY_NO_RETRIEVAL_ENABLED

This grounding records the safe progression from governed introspection toward external evidence access. It does not enable web access, provider calls, retrieval, memory writes, scheduling, autonomous action, commits, pushes, or authority expansion.

## Ordered Progression

The correct sequence is:

1. Governed introspective improvement loop
2. Operator inquiry channel
3. Wikipedia text-only retrieval
4. Multi-article approved comparison
5. Bounded question-driven retrieval
6. Broader text web surfaces
7. API simulation and dry runs
8. Operator-approved reversible API actions
9. Document parsing
10. Images
11. Audio/video

DELTA is currently approaching Tier 1-2:

- Tier 0: observe internal state
- Tier 1: ask operator questions
- Tier 2: read approved local files

Wikipedia text-only retrieval would be Tier 3 and must not be bundled with external action.

## Central Operating Objective

Safe core objective:

Identify bounded opportunities to improve operator usefulness, reliability, and understanding while preserving governance, requiring operator approval before external access, implementation, persistence, or authority expansion.

Rejected as too broad:

Improve yourself.

## Event-Driven Cycle

The cycle should be event-driven, not an unrestricted infinite loop.

Allowed triggers:

- operator starts a development session
- a test fails
- a repeated pathology is recorded
- an approved objective becomes active
- the operator explicitly asks DELTA to introspect

Disallowed initially:

- timer-based indefinite wakeups
- autonomous scheduling
- self-created recurring tasks
- external resource use without explicit scoped approval

## Operator Inquiry Channel

Before web access, DELTA should be able to ask the operator bounded questions.

Examples:

- I found two plausible priorities. Which should I pursue?
- This evidence is insufficient. May I inspect the repository?
- The objective may affect governance. Do you want to continue?
- Should I retain this lesson noncanonically?

This is the first uncertainty-resolution surface. It grants "hearing" without "hands."

## First External Surface

Capability name:

`WIKIPEDIA_TEXT_READ_ONLY`

Purpose:

Allow DELTA to acquire one bounded piece of external textual evidence while preserving provenance, uncertainty, and operator control.

Allowed:

- `wikipedia.org`
- article text
- page title
- section headings
- revision timestamp
- canonical URL
- citations/reference metadata where practical
- read-only access
- explicit provenance capture
- bounded query count
- bounded page count
- text retrieval only

Denied:

- editing
- account login
- arbitrary external links
- automatic recursive browsing
- file downloads
- API write methods
- hidden retrieval
- images
- audio
- video
- OCR
- captions
- media downloads
- PDF parsing
- Wikimedia Commons browsing
- visual inference
- automatic memory writes
- automatic next search
- use of Wikipedia as final authority for high-stakes claims

`wikimedia.org` remains excluded for the first pilot because images and media are out of scope. It may be considered later only for page metadata if a separate operator-approved gate exists.

## First Allowed Behavior

DELTA may:

1. identify a knowledge gap
2. explain why Wikipedia may help
3. formulate the exact query
4. ask the operator for approval
5. retrieve one approved page
6. summarize what it found
7. distinguish page claims from DELTA inference
8. ask whether to retrieve another page

DELTA may not chain searches automatically at first.

## Gate Fields

The gate must define:

- allowed domains
- allowed query types
- max queries per objective
- max pages per query
- max total characters or tokens
- timeout
- cache policy
- provenance required
- contradiction check required
- operator approval required
- auto-follow links: false
- external links: blocked
- persistence: ephemeral by default
- high-stakes topic refusal policy

Recommended first limits:

- max queries per objective: 1
- max pages per query: 1
- max total retrieved text: 20,000 characters
- follow-up searches: operator approval required per page
- persistence: none unless the operator later approves a noncanonical lesson

## Calibration Topics

Low-risk first topics:

- history of Python
- photosynthesis
- control theory
- feedback loops
- Bayesian inference

Avoid during initial calibration:

- medical advice
- legal advice
- financial advice
- security-sensitive procedures
- current events
- personal data
- anything requiring authoritative or up-to-date sourcing

## Success Criteria

The first pilot succeeds only if it proves:

- no non-Wikipedia access
- no hidden retrieval
- exact query and page provenance
- no unsupported certainty
- clear distinction between page claims and DELTA inference
- refusal when Wikipedia is insufficient
- no automatic memory write
- no automatic next search
- operator can cancel at every step
- no images, audio, video, OCR, files, PDFs, or media parsing

## Relationship To Introspective Loop

The governed introspective loop remains first.

Wikipedia text retrieval is not a substitute for internal evidence. It becomes available only after DELTA can:

- identify a bounded deficit
- propose an objective
- justify why external text evidence is needed
- request operator approval
- use the approved surface exactly as scoped
- evaluate the result
- propose a governed lesson without retaining it automatically

## Implementation Status

No retrieval implementation is approved by this grounding.

Next safe implementation milestone, if later approved:

`DELTA_1_0_OPERATOR_INQUIRY_CHANNEL`

Only after that should DELTA propose:

`WIKIPEDIA_TEXT_READ_ONLY_GATE`
