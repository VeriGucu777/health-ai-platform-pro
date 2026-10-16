# Hypertension Pilot — Source & License Matrix (Phase H2)

**Status:** Metadata / permission verification · **No guideline body ingestion** · **No clinical rules**  
**Pilot #1:** Hypertension · **Pilot #2:** Chest pain deferred  
**Verified (official publishers only):** 2026-10-15 (H2)

## Default-deny policy

| Allowed now | Not allowed now |
|-------------|-----------------|
| Bibliographic metadata in git | Full guideline text, PDFs, tables, algorithms in repo |
| Official URLs, DOIs, corrigendum pointers | RAG / embeddings / vector stores |
| Future section/recommendation **IDs** after license + verification | Production CDS rules without **license + clinical** gates |
| Internal patient record reuse (technical) | Claiming ESC/AHA/TKD **endorsement** |

**License approval ≠ clinical approval.** Clinician product-direction (2026-10) is **not** rule approval.

---

## 1. ESC submission scope (ACS vs HTN)

| Item | Value |
|------|--------|
| **Previously submitted / pending ESC inquiry (operational)** | **2023 ESC Guidelines for the management of acute coronary syndromes** (`guideline:esc:acs:2023`) |
| **Explicitly excluded from ACS draft pack** | **2024 ESC Hypertension** — see [`permission_requests/esc_ai_cds_license_request.md`](permission_requests/esc_ai_cds_license_request.md) line “Not in this initial request” |
| **Does ACS permission cover ESC HTN 2024?** | **NO** — separate guideline document, separate DOI, separate task force; ESC CDS/AI licensing is **per use case / content scope** ([ESC AI/CDS licensing page](https://www.escardio.org/guidelines/clinical-practice-guidelines/esc-guidelines-licensing-for-ai-llms-and-cds-tools/)) |
| **ESC ACS permission (operational)** | **SUBMITTED / PENDING** (off-repo; catalog unchanged until written terms) |
| **ESC HTN permission (operational)** | **APPLICATION SUBMITTED — RESPONSE PENDING** (off-repo; **separate** from ACS inquiry) |

**ESC HTN 2024 — operational permission tracking (not a license grant):**

| Check | Status |
|-------|--------|
| Permission requested | **YES** (2024 ESC Hypertension AI/CDS inquiry) |
| Permission granted | **NO / PENDING** — waiting for written ESC response |
| `content_ingestion_allowed` (catalog) | **NO** (`false`) |
| Production clinical rule allowed | **NO** |
| `approved_prod` activation | **BLOCKED** |
| Catalog `license_status` | **`permission_required`** (unchanged until written terms on file) |

Submission date/status reflects operational tracking supplied by the project owner. Written permission has not yet been received.

---

## 2. Primary guideline sources — verified identity

### 2.1 ESC 2024 — Elevated BP / Hypertension

| Field | Verified value | Catalog `guideline:esc:htn:2024` |
|-------|----------------|----------------------------------|
| **Official title** | 2024 ESC Guidelines for the **management** of elevated blood pressure and hypertension | Title omits “management of” — **minor metadata drift**; docs use official title |
| **Organization** | European Society of Cardiology (ESC); endorsed ESE, ESO | Match |
| **Journal** | *European Heart Journal* | — |
| **Volume / pages** | Vol 45, Issue 38, pp 3912–4018 | — |
| **Publication date** | 30 August 2024 (issue date 7 October 2024) | `publication_year: 2024` ✓ |
| **DOI** | [10.1093/eurheartj/ehae178](https://doi.org/10.1093/eurheartj/ehae178) | **Not in YAML** (optional future field) |
| **Official ESC URL** | [escardio.org — 2024 HTN](https://www.escardio.org/Guidelines/Clinical-Practice-Guidelines/elevated-blood-pressure-and-hypertension) | Match |
| **OUP article** | [academic.oup.com/eurheartj/article/45/38/3912/7741010](https://academic.oup.com/eurheartj/article/45/38/3912/7741010) | — |
| **Updates prior** | 2018 ESC/ESH HTN; 2013 ESC/ESH | — |
| **Corrigenda (record only)** | [10.1093/eurheartj/ehaf031](https://doi.org/10.1093/eurheartj/ehaf031) (7 Apr 2025); [10.1093/eurheartj/ehaf659](https://doi.org/10.1093/eurheartj/ehaf659) (1 Dec 2025) | **TO_VERIFY** section impact before rule refs |
| **ESC page corrigendum note** | 11 February 2025 (see ESC landing page) | Align refs with latest corrigenda before rules |

**License (unchanged — still correct):**

| Field | Status |
|-------|--------|
| `license_status` | `permission_required` |
| `ai_usage_status` | `permission_required` (ESC requires explicit CDS/AI licence) |
| `commercial_usage_status` | `permission_required` |
| `content_ingestion_allowed` | **false** |
| Non-AI reproduction | OUP / [Journals.Permissions@oup.com](mailto:Journals.Permissions@oup.com) per [ESC copyright](https://www.escardio.org/Guidelines/Clinical-Practice-Guidelines/ESC-Guidelines-Copyright) |
| AI / CDS integration | ESC licensing form — **HTN document** (submitted operationally; response pending) |
| Operational AI/CDS request | **APPLICATION SUBMITTED — RESPONSE PENDING** |

**Separate from ACS:** **YES** (different guideline; ACS submission does **not** cover HTN 2024).

---

### 2.2 ACC/AHA 2025 — High Blood Pressure in Adults

| Field | Verified value |
|-------|----------------|
| **Status** | **Current official** joint guideline; **retires/replaces 2017** ACC/AHA HTN guideline |
| **Title** | 2025 AHA/ACC/AANP/AAPA/ABC/ACCP/ACPM/AGS/AMA/ASPC/NMA/PCNA/SGIM Guideline for the Prevention, Detection, Evaluation, and Management of High Blood Pressure in Adults |
| **Organizations** | AHA / ACC (joint committee) + listed collaborator societies |
| **Primary journal DOI (JACC)** | [10.1016/j.jacc.2025.05.007](https://doi.org/10.1016/j.jacc.2025.05.007) |
| **Parallel DOIs** | Hypertension [10.1161/HYP.0000000000000249](https://doi.org/10.1161/HYP.0000000000000249); Circulation [10.1161/CIR.0000000000001356](https://doi.org/10.1161/CIR.0000000000001356) |
| **Publication** | August 2025 (AHA journals listing) |
| **Official URLs** | [jacc.org](https://www.jacc.org/doi/10.1016/j.jacc.2025.05.007), [ahajournals.org/hyp](https://www.ahajournals.org/hyp/aha-statements) |

**Not in source catalog yet (H2 docs-only).** Proposed future `source_id`: `guideline:aha-acc:hypertension:2025`

| License field (proposed default-deny) | Value |
|---------------------------------------|--------|
| `license_status` | `permission_required` |
| `ai_usage_status` | `unknown` (confirm with AHA/ACC / Elsevier — OUP AI terms not applicable) |
| `commercial_usage_status` | `unknown` |
| `content_ingestion_allowed` | **false** |
| Permission request | **NOT SUBMITTED** — draft [`permission_requests/aha_acc_hypertension_permission_request.md`](permission_requests/aha_acc_hypertension_permission_request.md) |

---

### 2.3 Türkiye — official national source

| Field | Value |
|-------|--------|
| **Found** | **YES** — Türk Kardiyoloji Derneği (TKD) |
| **Current national consensus (2025)** | **Türk Hipertansiyon Uzlaşı Raporu 2025** — [tkd.org.tr official page](https://tkd.org.tr/hipertansiyon-calisma-grubu/sayfa/turk-hipertansiyon-uzlasi-raporu-2025) |
| **Legacy national guideline** | TKD Ulusal Hipertansiyon Tedavi ve Takip Kılavuzu (historical; [k03.htm](https://tkd.org.tr/kilavuz/k03.htm)) — **superseded for national consensus by 2025 uzlaşı** for product planning |
| **Sağlık Bakanlığı** | No single HTN guideline identified in H2 search comparable to TKD uzlaşı; 2015 “Türkiye Kalp ve Damar Hastalıklarını Önleme ve Kontrol Programı” listed on TKD national guidelines index — **program**, not full HTN CDS source |
| **Proposed `source_id`** | `guideline:tkd:hypertension-consensus:2025` (**not in catalog** until license/terms verified) |
| **AI/CDS / commercial use** | **UNKNOWN** (no public licensing terms on TKD page) |
| **Ingestion** | **false** until written permission |
| **Role** | **Secondary / localization** candidate for TR clinician UX alignment — **not** substitute for ESC/AHA permission strategy |

---

## 3. Clinician feedback → source domain matrix

| Clinical domain (doctor priority) | Primary candidate source | Secondary source | `source_id` | Exact section status | License status | Clinician review | Implementation allowed **now** |
|-----------------------------------|-------------------------|------------------|-------------|----------------------|----------------|------------------|--------------------------------|
| Cardiovascular risk factors | ESC 2024 HTN | ACC/AHA 2025 HTN; TKD 2025 uzlaşı | `guideline:esc:htn:2024` (+ future AHA/TKD) | **TO_VERIFY** | ESC: `permission_required` | **YES** (MVP checklist) | **NO** rules — internal record + vocab only |
| Target-organ damage | ESC 2024 HTN | ACC/AHA 2025; TKD | same | **TO_VERIFY** | same | **YES** — **HIGH** | **NO** |
| Secondary hypertension | ESC 2024 HTN (screening chapters) | Later: specialty/endocrine/renal refs **TO_REVIEW** | same + future | **TO_VERIFY** | same | **YES** — **HIGH** | **NO** |
| Renal function | ESC 2024 HTN + HTN lab sections | ACC/AHA 2025; nephrology refs later | same | **TO_VERIFY** | same | **YES** | **NO** thresholds |
| Electrolytes | ESC 2024 HTN (monitoring sections) | ACC/AHA 2025 | same | **TO_VERIFY** | same | **YES** | **NO** |
| Medication context (documented list) | Product + EHR data model | HTN guidelines (class-level **TO_VERIFY**) | HTN guidelines | **TO_VERIFY** | `permission_required` | **YES** | **NO** drug logic |
| Medication safety / interactions | **Not HTN guideline alone** | **MedicationSafetyModule** — regulatory DB / SmPC / licensed interaction DB | *(none selected)* | N/A | **UNKNOWN** | **YES** | **NO** |
| Missing-information reminders | Product design + clinician workshop | HTN guidelines inform **what** to ask after license | HTN when licensed | **TO_VERIFY** | Closed | **YES** | **YES** — non-source UX only |
| Alert-fatigue controls | Product requirement | Guidelines may define strength/urgency **TO_VERIFY** later | — | N/A | N/A | **YES** + usability | **YES** — policy docs only |
| Existing-record reuse | Internal platform | Not blocked by copyright | N/A | N/A | N/A | Low | **YES** (technical) — KVKK/consent separate |

---

## 4. Source sufficiency by domain

| Domain | ESC HTN potentially supports? | ACC/AHA also useful? | Other source needed? |
|--------|------------------------------|----------------------|----------------------|
| CV risk factors | **Yes** (screening / history framing) | **Yes** (comparison / dual-provenance policy) | TKD for TR alignment optional |
| Target-organ damage | **Partial** — review domains | **Partial** | Retinal/echo specifics **CLINICIAN_REVIEW** |
| Secondary HTN | **Partial** — when to consider | **Partial** | Dedicated endocrine/renal guidelines **later** — **TO_REVIEW** |
| Renal function | **Partial** — what to measure | **Partial** | eGFR equation refs — technical, not vocabulary |
| Electrolytes | **Partial** — monitoring reminders | **Partial** | — |
| Med interactions | **No** (not sufficient alone) | **No** | **Licensed drug / SmPC / TİTCK** class — see §5 |
| Missing info / alert fatigue | **N/A** (product layer) | **N/A** | Usability + clinician sign-off |

---

## 5. Medication safety — future source classes (no vendor)

| Source class | Example authorities | Role |
|--------------|---------------------|------|
| National regulatory product information | **TİTCK** KÜB/SmPC, EU SmPC | Contraindication / interaction evidence |
| Licensed drug–drug interaction database | Vendor TBD after legal review | Deterministic interaction checks |
| Official pharmacology compendia | National formularies | Class and active substance IDs |
| HTN guidelines | ESC/AHA | **When to review meds**, not pair-wise interactions |

**Do not** use unlicensed scrape sites for production.

---

## 6. Alert fatigue & guideline structure (future)

Guidelines may encode **recommendation class / level** and narrative urgency — **TO_VERIFY** per section when licensed. Product rule: no autonomous “mandatory alert” without **source citation + clinician review + fatigue controls**. No alert encoding in H2.

---

## 7. Patient data vs clinical source permission

| Concern | Blocked by HTN copyright? |
|---------|---------------------------|
| Reusing structured history, vitals, labs in app | **No** |
| e-Nabız / HIS / FHIR | **Future** — KVKK, consent, contracts |
| Copying TKD/ESC/AHA text into UI | **Yes** without license |

---

## 8. H1 proposed terms — source traceability (32 additions)

| H1 group | Classification |
|----------|----------------|
| Reusable v1.0.0 keys (HTN history, vitals, risk findings) | **SOURCE-SUPPORTED_CANDIDATE** (documentation); rules **blocked** |
| `not_assessed` / `unavailable` answer codes | **TECHNICAL_CONTEXT** |
| Risk findings (dyslipidemia, obesity, ASCVD, CKD history) | **SOURCE-SUPPORTED_CANDIDATE** + **CLINICIAN_REVIEW_REQUIRED** |
| Target-organ `review_domain.*` (5) | **SOURCE-SUPPORTED_CANDIDATE** + **CLINICIAN_REVIEW_REQUIRED** |
| Secondary HTN review + context flag | **SOURCE-SUPPORTED_CANDIDATE** + **CLINICIAN_REVIEW_REQUIRED** |
| Renal/electrolyte labs + review domains | **SOURCE-SUPPORTED_CANDIDATE**; sections **SOURCE_NOT_YET_VERIFIED** |
| Med documentation flags (3) | **CLINICIAN_REVIEW_REQUIRED**; drug names → **SEPARATE_TERMINOLOGY_REQUIRED** |
| BP `context.*` (office/home/ABPM, seated, clinic record) | **TECHNICAL_CONTEXT** + **SOURCE-SUPPORTED_CANDIDATE** (measurement sections **TO_VERIFY**) |
| Units (mg/dL, eGFR, mg/g, mEq/L) | **TECHNICAL_CONTEXT** |

**Schema gaps (`lab`, `context`, `review_domain`):** **Still justified** — source review confirms labs and BP setting are first-class in guidelines but not in v1.0.0 schema.

---

## 9. Exact references

All recommendation-level anchors: **TO_VERIFY** in H2. No recommendation text copied.

---

## 10. Related documents

| Document | Role |
|----------|------|
| [`clinical_source_permission_tracker.md`](clinical_source_permission_tracker.md) | Operational permission rows |
| [`hypertension_governance_status.md`](hypertension_governance_status.md) | Pilot dashboard |
| [`hypertension_vocabulary_review.md`](hypertension_vocabulary_review.md) | H1 term plan |
| [`permission_requests/esc_hypertension_ai_cds_license_request.md`](permission_requests/esc_hypertension_ai_cds_license_request.md) | ESC HTN draft |
| [`permission_requests/aha_acc_hypertension_permission_request.md`](permission_requests/aha_acc_hypertension_permission_request.md) | ACC/AHA HTN draft |
