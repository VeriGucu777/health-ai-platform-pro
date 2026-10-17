# Clinical Source Permission Tracker (Cardiology Pilots)

**Phase H2** · Operational tracking only · **Does not change** catalog `license_status` fields until written permission exists.

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
| request_status | **SUBMITTED / PENDING** (operational, off-repo) |
| request_date | **TO_RECORD** (off-repo) |
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
| notes | No ESC license **on file** in repo. Scope: **ACS 2023 only**. Correction DOI **10.1093/eurheartj/ehad870**. Draft: [`permission_requests/esc_ai_cds_license_request.md`](permission_requests/esc_ai_cds_license_request.md). **Does not cover** `guideline:esc:htn:2024`. |

---

## Tracker — ESC Hypertension 2024 (Pilot #1)

| Field | Value |
|-------|--------|
| `source_id` | `guideline:esc:htn:2024` |
| organization | ESC / OUP (*European Heart Journal*) |
| document_title | 2024 ESC Guidelines for the **management** of elevated blood pressure and hypertension |
| official DOI | [10.1093/eurheartj/ehae178](https://doi.org/10.1093/eurheartj/ehae178) |
| intended_product_use | Hypertension Pilot #1 CDS — missing-info / review domains (future deterministic rules) |
| intended_AI_CDS_use | ESC AI/CDS licensing path — deterministic rules, not LLM training |
| commercial_intent | Potential commercial SaaS (TO_CONFIRM with legal) |
| requested_material_scope | Selected HTN sections/recommendation IDs; metadata only |
| guideline_text_ingestion_requested | **NO** |
| rule_derivation_requested | **YES** (if permitted) |
| permission_channel | ESC licensing form (AI/CDS); OUP for non-AI reproduction |
| request_status | **APPLICATION SUBMITTED — RESPONSE PENDING** |
| permission_requested | **YES** |
| permission_granted | **NO / PENDING** |
| content_ingestion_allowed (product) | **NO** (catalog: **false**) |
| production_clinical_rule_allowed | **NO** |
| approved_prod_activation | **BLOCKED** |
| request_date | **Not recorded in repo** (operational tracking off-repo) |
| response_date | — |
| permission_reference | — |
| legal_review_status | **PENDING_INTERNAL** |
| notes | Catalog metadata present; `license_status` remains **`permission_required`** until written terms. Corrigenda: **ehaf031**, **ehaf659** — verify before rule refs. Template: [`permission_requests/esc_hypertension_ai_cds_license_request.md`](permission_requests/esc_hypertension_ai_cds_license_request.md). **Separate** from ACS submission. Submission date/status reflects operational tracking supplied by the project owner. Written permission has not yet been received. |

---

## Tracker — AHA/ACC Hypertension 2025

| Field | Value |
|-------|--------|
| `source_id` | `guideline:aha-acc:hypertension:2025` (**proposed** — not in catalog H2) |
| organization | AHA / ACC (+ collaborator societies listed on guideline) |
| document_title | 2025 AHA/ACC/... Guideline for the Prevention, Detection, Evaluation, and Management of High Blood Pressure in Adults |
| official DOI (primary) | [10.1016/j.jacc.2025.05.007](https://doi.org/10.1016/j.jacc.2025.05.007) |
| intended_product_use | Secondary / comparison HTN evidence for Pilot #1 (dual-provenance policy TBD) |
| intended_AI_CDS_use | **UNKNOWN** — confirm with AHA/ACC / publisher |
| commercial_intent | Potential commercial SaaS (TO_CONFIRM) |
| guideline_text_ingestion_requested | **NO** |
| rule_derivation_requested | **YES** (if permitted) |
| permission_channel | AHA/ACC / publisher permissions |
| request_status | **APPLICATION SUBMITTED — RESPONSE PENDING** |
| permission_requested | **YES** |
| permission_granted | **NO / PENDING** |
| written_permission_received | **NO** |
| response | **PENDING** |
| content_ingestion_allowed (product) | **NO** (default-deny; no catalog YAML until licensed) |
| production_clinical_rule_allowed | **NO** |
| approved_prod_activation | **BLOCKED** |
| production_clinical_rule_count | **0** |
| request_date | **Not recorded in repo** (tracked by project owner; submission date not recorded in repository) |
| response_date | — |
| legal_review_status | **PENDING_INTERNAL** |
| notes | Replaces **2017** ACC/AHA HTN guideline per publisher. Default-deny: AI/commercial **unknown**, ingestion **false**. Draft: [`permission_requests/aha_acc_hypertension_permission_request.md`](permission_requests/aha_acc_hypertension_permission_request.md). **Separate permission track** from ESC HTN 2024 and from AHA/ACC chest pain 2021. **Application submission does not constitute permission or license grant.** Submission status reflects operational tracking supplied by the project owner. Written permission has not yet been received. |

---

## Tracker — TKD Hypertension Consensus 2025 (national)

| Field | Value |
|-------|--------|
| `source_id` | `guideline:tkd:hypertension-consensus:2025` (**proposed** — not in catalog H2) |
| organization | Türk Kardiyoloji Derneği |
| document_title | Türk Hipertansiyon Uzlaşı Raporu 2025 |
| official URL | [tkd.org.tr](https://tkd.org.tr/hipertansiyon-calisma-grubu/sayfa/turk-hipertansiyon-uzlasi-raporu-2025) |
| AI/CDS / commercial | **UNKNOWN** |
| content ingestion | **false** (default) |
| request_status | **NOT_SUBMITTED** |
| notes | National alignment candidate; **not** a substitute for ESC/AHA permission. No unofficial PDF mirrors. |

---

## Decision log

| Date | Source | Event | Gate impact |
|------|--------|-------|-------------|
| 2026-10-15 | H2 verification | Official **ESC 2024 HTN** (DOI ehae178) and **ACC/AHA 2025 HTN** (DOI j.jacc.2025.05.007) identities verified; TKD **2025 uzlaşı** page verified. | Metadata docs updated; **catalog YAML unchanged** |
| 2026-10 (operational) | `guideline:esc:acs:2023` | External ESC licensing inquiry **SUBMITTED / PENDING** (off-repo). Scope: **2023 ACS only** — **does not cover** HTN 2024. | ACS gate **CLOSED** until permission on file |
| 2026-10 (operational) | `guideline:esc:htn:2024` | ESC **2024 Hypertension** AI/CDS inquiry **APPLICATION SUBMITTED — RESPONSE PENDING** (off-repo). **Not** a license grant. | HTN license gate **CLOSED** until written permission; catalog YAML unchanged |
| 2026-10 (operational) | `guideline:aha-acc:hypertension:2025` (proposed) | ACC/AHA **2025 Hypertension** permission inquiry **APPLICATION SUBMITTED — RESPONSE PENDING** (off-repo). **Not** a license grant. **Separate** from ESC HTN track. | ACC/AHA HTN gate **CLOSED**; no catalog YAML; ingestion **false**; `approved_prod` **BLOCKED** |
| 2026-10 | Product | Cardiologist **product-direction** for HTN Pilot #1 — **not** rule/license approval. | Does not open license or production rule gates |
| — | AHA chest pain | **NOT_SUBMITTED** | License gate **CLOSED** |

---

## Related

- [`chest_pain_governance_status.md`](chest_pain_governance_status.md)
- [`chest_pain_verified_source_references.md`](chest_pain_verified_source_references.md)
- [`chest_pain_source_license_matrix.md`](chest_pain_source_license_matrix.md)
