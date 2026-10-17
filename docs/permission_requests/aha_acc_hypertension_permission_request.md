# DRAFT — AHA/ACC Hypertension Guideline Permission Inquiry (2025)

**Operational status:** **APPLICATION SUBMITTED — RESPONSE PENDING** · Applicant/contact fields below remain **TO_FILL** · **Not legal advice**

| Governance field | Value |
|------------------|--------|
| Permission requested | **YES** |
| Permission granted | **NO / PENDING** |
| Written permission received | **NO** |
| Response | **PENDING** |
| Request / submission date (repo) | **Not recorded in repository** |
| Content ingestion allowed | **NO** |
| Production rule activation (`approved_prod`) | **BLOCKED** |
| Production clinical rule count | **0** |

**Application submission does not constitute permission or license grant.** Separate permission track from ESC HTN 2024 and from AHA/ACC chest pain 2021. Tracker: [`../clinical_source_permission_tracker.md`](../clinical_source_permission_tracker.md).

## Project

**Health AI Platform Pro** — Cardiology Clinical Copilot (clinician-facing CDS) · **Pilot #1: Hypertension**

## Applicant

| Field | Value |
|-------|--------|
| Applicant type | **TO_FILL** |
| Legal entity | **TO_FILL** |
| Contact | **TO_FILL** |

## Requested source (verified official — H2)

**2025 AHA/ACC/AANP/AAPA/ABC/ACCP/ACPM/AGS/AMA/ASPC/NMA/PCNA/SGIM Guideline for the Prevention, Detection, Evaluation, and Management of High Blood Pressure in Adults**

| Field | Value |
|-------|--------|
| Primary DOI (JACC) | [10.1016/j.jacc.2025.05.007](https://doi.org/10.1016/j.jacc.2025.05.007) |
| Hypertension DOI | [10.1161/HYP.0000000000000249](https://doi.org/10.1161/HYP.0000000000000249) |
| Circulation DOI | [10.1161/CIR.0000000000001356](https://doi.org/10.1161/CIR.0000000000001356) |
| Replaces | 2017 ACC/AHA hypertension guideline (retired per publisher statement) |

**Proposed catalog `source_id` (not added in H2):** `guideline:aha-acc:hypertension:2025`

## Intended use (draft language for permissions form)

- **Audience:** Licensed healthcare professionals only  
- **Purpose:** Clinical **decision support** — structured documentation, missing-information prompts, review-domain completeness (future source-linked deterministic rules)  
- **Not:** Autonomous diagnosis, treatment orders, or AHA/ACC **endorsement**  
- **Material use:** Selected concepts may inform **human-authored** deterministic rules; **no** full article reproduction; **no** guideline PDF hosting  
- **AI / CDS:** Request clarity on machine-readable derived logic and SaaS deployment  
- **Provenance:** Store official section/recommendation **references**; display independently written CDS text with citation  

**Default-deny until permission:** `license_status=permission_required`, AI/commercial **unknown**, ingestion **false**.

## Questions for AHA/ACC / publisher permissions

1. Permissions path for **clinician-facing CDS** using selected 2025 HTN guideline content (comparison / secondary provenance alongside ESC if permitted).
2. Separate licence for **structured deterministic rules** vs short quotations.
3. **Commercial SaaS** to healthcare organizations — terms and fees.
4. Use of **recommendation identifiers** and class/level metadata without storing full recommendation text.
5. Whether ACC/AHA grants **AI/CDS** rights or refers to publisher (Elsevier) for certain uses.
6. Relationship to **2017** guideline — confirm 2025 as sole current document for new CDS.

## Message draft (email)

**Subject:** Permission inquiry — Clinical decision support use of 2025 AHA/ACC Hypertension Guideline

**Body (draft):**

Dear AHA/ACC Permissions,

We are building a clinician-only decision support tool for hypertension encounters (documentation completeness and review reminders, not autonomous diagnosis). We seek permission guidance for the smallest use of the **2025 AHA/ACC Hypertension Guideline** (DOI 10.1016/j.jacc.2025.05.007) suitable for source-linked deterministic rules and citation metadata, without hosting full guideline text or training LLMs on the article.

[Applicant details TO_FILL]

Thank you,

[Signature TO_FILL]

## Related

- Chest pain draft (separate): [`aha_acc_guideline_permission_request.md`](aha_acc_guideline_permission_request.md)  
- Matrix: [`../hypertension_source_license_matrix.md`](../hypertension_source_license_matrix.md)
