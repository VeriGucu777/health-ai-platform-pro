# DRAFT — ESC AI / CDS License Inquiry (2023 ACS Guidelines)

**Status:** DRAFT · **NOT SUBMITTED** · **Not legal advice**

## Project

**Health AI Platform Pro** — Cardiology Clinical Copilot (clinician-facing CDS pilot)

## Applicant

| Field | Value |
|-------|--------|
| Applicant type | **TO_FILL** |
| Legal entity name | **TO_FILL** |
| Entity status | **TO_FILL** (individual / startup / company / research institution) |
| Country of deployment | **TO_FILL** (pilot: Turkey + EU considerations) |
| Contact | **TO_FILL** |

## Use case summary

We are building a **healthcare-professional-only** clinical decision **support** tool. It does **not** autonomously diagnose, prescribe, or replace clinician judgment. We plan **deterministic, auditable rules** linked to official guideline **identifiers** (section/recommendation refs), not a RAG/LLM system trained on full guideline text.

**Requested primary source:** 2023 ESC Guidelines for the management of acute coronary syndromes (DOI [10.1093/eurheartj/ehad191](https://doi.org/10.1093/eurheartj/ehad191)).

**Not in this initial request:** 2024 ESC Hypertension guideline (separate module if pursued later).

We are aware of the published correction ([10.1093/eurheartj/ehad870](https://doi.org/10.1093/eurheartj/ehad870)) and will align citations with the corrected document.

## Minimum scope requested (preferred)

We seek the **smallest** permission scope that supports:

- Manual curation of **selected** recommendations into structured, machine-readable clinical rules
- Storing **bibliographic provenance** (`source_id`, official section/recommendation identifiers — not full text)
- Displaying **independently authored** CDS messages in Turkish and English UI

We are **not** requesting (unless ESC advises otherwise for our use case):

- Full guideline text ingestion into a vector database
- LLM / generative AI **training** on guideline body
- Repository storage or redistribution of PDFs

## Specific questions for ESC / OUP licensing

Please advise whether a license could permit:

**A.** Manual extraction of **selected** guideline recommendations into deterministic, machine-readable clinical rules (human-authored rule YAML/metadata, not automated scraping).

**B.** Storing official **section** and **recommendation** identifiers as provenance in our product database/git catalog (metadata only).

**C.** Displaying **independently written** CDS messages that are derived from licensed rules (no reproduction of recommendation paragraph text).

**D.** **Commercial SaaS** deployment to hospitals/clinics (subscription B2B).

**E.** **Internal clinical pilot** deployment (limited sites, no public guideline redistribution).

**F.** **Updates** when guideline versions or corrections change — process for rule version alignment.

**G.** Use in **Turkish and English** clinician-facing interfaces (localized UI strings; not translation of full guideline).

**H.** Whether structured rule logic derived from licensed selections counts as a **derivative work** under your terms.

**I.** Whether storing **recommendation metadata** (class, level, short title if permitted) is allowed without storing full recommendation text.

**J.** Whether the license requires **annual renewal** or reporting of active deployments.

## Attachments (when submitting)

- Product one-pager (CDS, not diagnosis) — **TO_PREPARE**
- Data flow diagram (no patient PHI in guideline store) — **TO_PREPARE**
- [`../clinical_source_permission_tracker.md`](../clinical_source_permission_tracker.md) excerpt

## Message draft (email)

**Subject:** Licensing inquiry — Clinical Decision Support use of 2023 ESC ACS Guidelines

**Body (draft):**

Dear ESC / Oxford University Press Permissions,

We are developing Health AI Platform Pro, a clinician-facing clinical decision support pilot for cardiology. We do not offer autonomous diagnosis or consumer-facing medical advice.

We request information on licensing for **deterministic, source-linked clinical decision support** based on **selected** content from the *2023 ESC Guidelines for the management of acute coronary syndromes* (DOI 10.1093/eurheartj/ehad191). We do not plan to ingest full guideline text into LLM training or public redistribution. We would store official section/recommendation identifiers for audit and display independently written CDS messages in Turkish and English.

Could you advise on the appropriate license type, scope, and process for commercial SaaS and pilot deployment? We have attached a short intended-use summary and specific questions (A–J).

Regards,  
**TO_FILL**
