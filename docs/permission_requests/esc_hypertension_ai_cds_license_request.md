# DRAFT — ESC AI / CDS License Inquiry (2024 Hypertension Guidelines)

**Operational request status:** **APPLICATION SUBMITTED — RESPONSE PENDING** · **Not legal advice**

**Document role:** DRAFT template (applicant `TO_FILL` fields may remain for internal archive). Submission to ESC does **not** imply permission granted.

| Gate | Status |
|------|--------|
| Permission requested | **YES** |
| Permission granted | **NO / PENDING** |
| `content_ingestion_allowed` | **NO** |
| Production clinical rule / `approved_prod` | **NO / BLOCKED** |
| Waiting for | Written ESC response |

Submission date/status reflects operational tracking supplied by the project owner. Written permission has not yet been received.

## Project

**Health AI Platform Pro** — Cardiology Clinical Copilot (clinician-facing CDS pilot) · **Pilot #1: Hypertension**

## Applicant

| Field | Value |
|-------|--------|
| Applicant type | **TO_FILL** |
| Legal entity name | **TO_FILL** |
| Country of deployment | **TO_FILL** (pilot: Turkey + EU considerations) |
| Contact | **TO_FILL** |

## Relationship to prior ESC inquiry

| Prior submission | Scope |
|------------------|--------|
| **2023 ESC ACS** (`guideline:esc:acs:2023`) | Reported **SUBMITTED / PENDING** off-repo — see [`esc_ai_cds_license_request.md`](esc_ai_cds_license_request.md) |
| **This request** | **Separate** — **2024 ESC Hypertension** only |

**Do not assume** ACS permission covers this document.

## Requested primary source

**2024 ESC Guidelines for the management of elevated blood pressure and hypertension**

| Field | Value |
|-------|--------|
| DOI | [10.1093/eurheartj/ehae178](https://doi.org/10.1093/eurheartj/ehae178) |
| Official ESC page | [Elevated blood pressure and hypertension](https://www.escardio.org/Guidelines/Clinical-Practice-Guidelines/elevated-blood-pressure-and-hypertension) |
| Corrigenda | [10.1093/eurheartj/ehaf031](https://doi.org/10.1093/eurheartj/ehaf031); [10.1093/eurheartj/ehaf659](https://doi.org/10.1093/eurheartj/ehaf659) — align citations before rule authoring |

## Use case summary

Healthcare-professional-only **clinical decision support** — **not** autonomous diagnosis or prescribing. Planned **deterministic, auditable rules** linked to official **section/recommendation identifiers**, not LLM/RAG on full guideline text.

**Clinician-facing domains (product direction — not clinical approval):** CV risk factors, target-organ review reminders, secondary HTN review prompts, renal/electrolyte documentation gaps, medication list completeness — **no** drug interaction engine in initial scope.

## Minimum scope requested

- Manual curation of **selected** recommendations into structured rules (human-authored metadata)
- Store `source_id`, section/recommendation **identifiers** for audit (metadata only)
- Display **independently authored** CDS strings (Turkish + English UI)
- **Internal pilot** and possible future **commercial B2B SaaS** (subject to your tiers)

## Explicitly excluded from request

- LLM / generative AI **training** on guideline body
- Full-text **RAG** / vector ingestion
- PDF storage or **redistribution**
- Full guideline or table **reproduction**
- Patient-facing self-diagnosis

## Questions for ESC (CDS / AI licensing path)

Per [ESC Guidelines Licensing for AI, LLMs, and CDS Tools](https://www.escardio.org/guidelines/clinical-practice-guidelines/esc-guidelines-licensing-for-ai-llms-and-cds-tools/):

1. Minimum licence scope for **deterministic CDS** (missing-information / review checklists) derived from selected HTN recommendations.
2. Whether **commercial SaaS** to hospitals requires a distinct fee tier.
3. Whether **recommendation metadata** (class, level, short identifier) may be stored without storing recommendation paragraph text.
4. Process when **corrigenda** publish — rule version alignment.
5. Whether Turkish UI strings (independent wording) require separate translation rights from OUP.
6. Whether this licence can be **combined** with a future ACS licence or must remain separate.

## Message draft (email)

**Subject:** Licensing inquiry — Clinical Decision Support use of 2024 ESC Hypertension Guidelines

**Body (draft):**

Dear ESC Permissions,

We are developing a clinician-facing clinical decision support pilot focused on hypertension care documentation and missing-information support (not autonomous diagnosis). We request guidance and a licence for the smallest scope of **2024 ESC Guidelines for the management of elevated blood pressure and hypertension** (DOI 10.1093/eurheartj/ehae178) suitable for deterministic, source-linked rules and provenance metadata. We do not plan to ingest full guideline text into LLM/RAG systems or redistribute PDFs.

[Applicant details TO_FILL]

Thank you,

[Signature TO_FILL]

## Attachments (when submitting)

- Product one-pager (CDS boundaries) — **TO_PREPARE**
- [`../clinical_source_permission_tracker.md`](../clinical_source_permission_tracker.md) excerpt (HTN row)
