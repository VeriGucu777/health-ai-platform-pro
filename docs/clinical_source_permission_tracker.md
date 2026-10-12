# Clinical Source Permission Tracker (Chest Pain Pilot)

**Phase 2J** · Operational tracking only · **Does not change** catalog `license_status` fields until written permission exists.

## Intended product use (reference)

Health AI Platform Pro — **clinician-facing clinical decision support (CDS)** for cardiology encounters. Planned approach: **deterministic, source-linked structured rules** with provenance — **not** autonomous diagnosis, **not** prescription automation, **not** consumer self-diagnosis. The licensed clinician retains final judgment.

Potential future use of third-party guideline material (subject to permission):

- Derive **selected** recommendations into machine-readable rules (no full-text corpus)
- Store `source_id`, section/recommendation **identifiers** for audit
- Display **independently written** CDS wording (TR/EN)
- **No** full guideline reproduction, PDF redistribution, or public guideline database
- **No** LLM/RAG training on guideline body (not requested unless product direction changes)

**Nothing below is licensed today.**

---

## Tracker — AHA/ACC Chest Pain 2021

| Field | Value |
|-------|--------|
| `source_id` | `guideline:aha-acc:chest-pain:2021` |
| organization | AHA / ACC (joint guideline) |
| document_title | 2021 AHA/ACC/ASE/CHEST/SAEM/SCCT/SCMR Guideline for the Evaluation and Diagnosis of Chest Pain |
| intended_product_use | Clinician-facing CDS; structured encounter documentation support; future deterministic rules |
| intended_AI_CDS_use | Structured rule evaluation in product (not LLM training on guideline text) |
| commercial_intent | Potential commercial SaaS for healthcare organizations (TO_CONFIRM with legal) |
| requested_material_scope | Selected sections/recommendations only; metadata + identifiers; no full article |
| guideline_text_ingestion_requested | **NO** (repo policy: metadata only) |
| rule_derivation_requested | **YES** (if permitted — manual curation into deterministic rules) |
| display/reproduction_requested | Independent CDS strings + citation to official source; no bulk reproduction |
| permission_channel | AHA/ACC / Elsevier permissions (see draft request doc) |
| request_status | **NOT_SUBMITTED** |
| request_date | — |
| response_date | — |
| permission_reference | — |
| license_term | — |
| expiration_date | — |
| financial_terms | — |
| restrictions | — |
| allowed_use | — |
| prohibited_use | — |
| renewal_required | — |
| legal_review_status | **PENDING_INTERNAL** |
| notes | Catalog: `license_status=permission_required`, AI/commercial **unknown**, ingestion **false**. Draft: [`permission_requests/aha_acc_guideline_permission_request.md`](permission_requests/aha_acc_guideline_permission_request.md) |

---

## Tracker — ESC ACS 2023

| Field | Value |
|-------|--------|
| `source_id` | `guideline:esc:acs:2023` |
| organization | European Society of Cardiology (ESC) / OUP |
| document_title | 2023 ESC Guidelines for the management of acute coronary syndromes |
| intended_product_use | ACS-scoped secondary CDS evidence for chest-pain pilot (not generic chest pain primary) |
| intended_AI_CDS_use | Deterministic CDS rules; ESC formal AI/LLM/CDS licensing path |
| commercial_intent | Potential commercial SaaS (TO_CONFIRM with legal) |
| requested_material_scope | Selected ACS sections/recommendation IDs; smallest scope for deterministic rules |
| guideline_text_ingestion_requested | **NO** |
| rule_derivation_requested | **YES** (if permitted) |
| display/reproduction_requested | Independent CDS wording + provenance; no table/algorithm copy |
| permission_channel | ESC / Oxford University Press permissions |
| request_status | **NOT_SUBMITTED** |
| request_date | — |
| response_date | — |
| permission_reference | — |
| license_term | — |
| expiration_date | — |
| financial_terms | — |
| restrictions | — |
| allowed_use | — |
| prohibited_use | — |
| renewal_required | — |
| legal_review_status | **PENDING_INTERNAL** |
| notes | No ESC license on file. Correction DOI **10.1093/eurheartj/ehad870** — review before citing biomarker algorithm sections. Draft: [`permission_requests/esc_ai_cds_license_request.md`](permission_requests/esc_ai_cds_license_request.md). **ESC HTN 2024 not bundled** in initial request. |

---

## Out of scope (chest-pain pack)

| `source_id` | Note |
|-------------|------|
| `guideline:esc:htn:2024` | Hypertension module only; separate permission track if HTN pack proceeds |

---

## Decision log

| Date | Source | Event | Gate impact |
|------|--------|-------|-------------|
| — | — | *(no submissions yet)* | License gate **CLOSED** |

---

## Related

- [`chest_pain_governance_status.md`](chest_pain_governance_status.md)
- [`chest_pain_verified_source_references.md`](chest_pain_verified_source_references.md)
- [`chest_pain_source_license_matrix.md`](chest_pain_source_license_matrix.md)
