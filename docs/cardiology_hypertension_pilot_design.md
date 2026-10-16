# Cardiology Hypertension Pilot — Design (Phase 3A)

**Design version:** `cardiology-hypertension-v0.1.0-design`  
**Status:** PROPOSED / **product direction received** — **no clinical rule approval**  
**Pilot priority:** **#1 (PRIMARY)** · Chest pain: **#2 deferred** (see [`chest_pain_governance_status.md`](chest_pain_governance_status.md))

## Purpose

Clinician-facing **hypertension decision-support** pilot: help clinicians notice **missing structured information** and important **review domains** — **not** autonomous diagnosis, staging, or treatment.

## System goal (from cardiologist direction)

Support the licensed clinician to:

- Reduce overlooked **cardiovascular risk factors**  
- Remind about **target-organ damage** evaluation gaps  
- Support **secondary hypertension** workup thinking (structured review only)  
- Remind about **renal function** and **electrolytes**  
- **Future:** medication **interaction** awareness (separate module)  
- Integrate with **existing patient records**  
- Avoid **alert fatigue**

## Core product domains (no rules in 3A)

| ID | Domain | Phase 3A scope |
|----|--------|----------------|
| A | Blood pressure documentation | Workflow + data-model review |
| B | Cardiovascular risk-factor review | Structured presence / missing / not_assessed |
| C | Target-organ damage review | Domain checklist design only |
| D | Secondary hypertension review | Module boundary — **no algorithm** |
| E | Renal function review | Lab observation concepts — **no thresholds** |
| F | Electrolyte review | Lab observation concepts — **no thresholds** |
| G | Medication context | Structured list / class placeholders |
| H | Medication-interaction safety | **FUTURE** `MedicationSafetyModule` |
| I | Missing-information support | Primary MVP candidate output |
| J | Alert-fatigue control | Product requirement — no engine |
| K | Existing-record integration | Internal records yes; e-Nabız/HIS later |

## Recommended first MVP outputs

**Recommendation:** Ship **missing_information** + **documentation_reminder** + **review_domain_status** (checklist completeness) **before** differential, autonomous safety alerts, or medication recommendations.

| Output class | First MVP | Later |
|--------------|-----------|--------|
| `missing_information` | **YES** | |
| `documentation_reminder` | **YES** | |
| `review_domain_status` | **YES** (neutral completeness) | |
| Structured clinical summary (non-diagnostic) | Optional | |
| `safety_alert` / red-flag automation | **NO** initially | After review + license |
| Diagnosis / staging | **NO** | |
| Treatment / medication recommendation | **NO** | |
| Probability / risk scores as diagnosis | **NO** | |

## Vocabulary reconciliation (`cardiology_v1.0.0.yaml`)

**No vocabulary edits in Phase 3A.**

| Key | Category | Disposition |
|-----|----------|-------------|
| `card.finding.hypertension_history` | finding | **REUSABLE** |
| `card.finding.diabetes_history` | finding | **REUSABLE** |
| `card.finding.smoking_history` | finding | **REUSABLE** |
| `card.finding.family_cardiovascular_history` | finding | **REUSABLE** |
| `card.vital.systolic_blood_pressure` | vital | **REUSABLE** |
| `card.vital.diastolic_blood_pressure` | vital | **REUSABLE** |
| `card.vital.heart_rate` | vital | **REUSABLE** (adjacent context) |
| `card.unit.mm_hg` | unit | **REUSABLE** |
| Obesity/BMI, dyslipidemia, CKD stage, creatinine, eGFR, Na/K labs, meds | — | **MISSING** |
| Target-organ domains (retinal, LVH, etc.) | — | **MISSING** / **NEEDS_CLINICIAN_REVIEW** |
| Secondary HTN causes (e.g. renal artery, pheo) | — | **NEEDS_CLINICIAN_REVIEW** — high risk |
| Home BP vs office BP | — | **MISSING** |
| Medication class / active med list | — | **MISSING** |
| Chest-pain-specific complaints/questions | complaint/question | **OUT_OF_SCOPE** for HTN MVP (may remain in catalog) |

## Vocabulary gap candidates (do not add in 3A)

- **Risk:** obesity/BMI, dyslipidemia, prior ASCVD, CKD, sleep apnea placeholder  
- **Target-organ:** cardiac, renal, neurologic, vascular, retinal review flags  
- **Secondary HTN:** structured “review performed / not assessed” placeholders only  
- **Renal:** creatinine, eGFR, albuminuria/UACR concepts (after source + review)  
- **Electrolytes:** sodium, potassium  
- **Meds:** active medications, antihypertensive class, OTC/NSAID context  

## BP data model review (technical)

**Current:** `HealthMeasurement` has `systolic_pressure`, `diastolic_pressure`, `measured_at`, `patient_id`, `owner_id`; encounter assembly maps to `VitalObservationInput` (integer → float) sorted by `(measured_at, id)`.

| Capability | Current | Gap |
|------------|---------|-----|
| Multiple BP readings per encounter | **YES** (multiple rows) | No encounter_id on measurement in domain entity — linkage via application layer |
| Timestamp | **YES** (`measured_at`) | |
| Repeat order | **Partial** — deterministic sort on assembly | Position (supine/standing) **not modeled** |
| Measurement source (office/home/ABPM) | **NO** dedicated field | **GAP** |
| Device metadata | **NO** | **GAP** |
| Ambulatory BP series | **NO** | **GAP** — future profile or stream |
| Decision DTO numeric finding/unit | **Limited** (Phase 2C notes) | Labs may not map cleanly yet |

## Risk-factor review model (future)

Structured ternary+ per factor:

| State | Meaning |
|-------|---------|
| `present` | Documented positive |
| `absent` | Documented negative |
| `unknown` | Asked, unknown |
| `not_assessed` | Not yet evaluated |

**Invariant:** `not_assessed` ≠ `absent`.

## Target-organ damage model (future)

Review **domains** only — **CLINICIAN_REVIEW_REQUIRED** for all:

| Domain | Future fields (conceptual) |
|--------|----------------------------|
| Cardiac | evidence present / missing / not_assessed |
| Renal | same |
| Neurologic | same |
| Vascular | same |
| Retinal | same |

No diagnostic rules (e.g. LVH criteria) in design phase.

## Secondary hypertension — `SecondaryHypertensionReviewModule` (future)

- Structured context + missing-information prompts  
- **NOT** autonomous secondary HTN diagnosis  
- **REQUIRES DEDICATED CLINICAL REVIEW** before any demo rule  

## Renal & electrolytes (future)

Laboratory observation concept: value, unit, date, source — **no clinical interpretation**, no eGFR staging thresholds in 3A.

Link: [`evaluation_context_snapshot`](evaluation_context_snapshot.md) / mapper — finding `value_numeric` / `unit` not fully on decision DTO (Phase 2C gap).

## Medication safety boundary

**`MedicationSafetyModule`** (future): interaction_warning, contraindication_warning, monitoring_reminder — requires **licensed drug database** or verified regulatory source (SmPC, national formulary). **No vendor, no DB, no rules in 3A.**

## Source strategy (metadata only)

| Priority | Candidate | Catalog status |
|----------|-----------|----------------|
| Primary | **2024 ESC** hypertension (`guideline:esc:htn:2024`) | Registered; license **closed** |
| Secondary | **ACC/AHA** current HTN guideline (e.g. 2025 cited in planning) | **TO_VERIFY_CURRENT_OFFICIAL_SOURCE** — no YAML until verified |
| National | Official Turkish source if verified | **Not in catalog** |

Rule gate remains **closed** until permission + section/recommendation verification (HTN section refs **not** done in 2I).

## License strategy

- **ESC ACS 2023:** external request reported **SUBMITTED / PENDING** — scope likely **ACS-only** per draft pack; **do not assume HTN coverage**.  
- **ESC HTN 2024:** **APPLICATION SUBMITTED — RESPONSE PENDING** (separate from ACS). Permission requested **YES**; permission granted **NO / PENDING**; `content_ingestion_allowed` **NO**; production clinical rules / `approved_prod` **BLOCKED** until written ESC response. Catalog YAML **`permission_required`** unchanged until written terms on file. Submission date/status reflects operational tracking supplied by the project owner. Written permission has not yet been received.  
- Catalog YAML **unchanged** in 3A (no `licensed` promotion without written permission).

## Alert-fatigue requirements (formal)

- No repeated identical alerts for unchanged state  
- No alert when data already documented or explicitly `not_assessed` per policy  
- Distinguish **reminder** vs **safety alert** (severity later)  
- Future: acknowledge / dismiss with audit trail  
- Default to **fewer, higher-value** prompts in MVP  

## Existing-record integration

| Scope | Phase 3A |
|-------|----------|
| Internal patient history, prior measurements, meds (when modeled) | **YES** — design intent |
| e-Nabız, hospital HIS, FHIR | **Future** — not implemented |

Reuse structured history to avoid re-asking answered questions (aligns with encounter mapper dedup patterns).

## Clinician workflow (high level)

1. Open patient  
2. Start cardiology encounter (HTN context)  
3. Record BP measurement(s)  
4. Record complaints / context  
5. Pull existing structured history  
6. Risk-factor completeness review  
7. Target-organ review completeness  
8. Secondary-HTN review completeness  
9. Renal / electrolyte data availability  
10. Medication context (when available)  
11. Missing-information summary  
12. **Clinician decides** — system does not diagnose or treat  

## Chest pain pilot status

**DEFERRED_SECONDARY_PILOT (#2)** — all Phase 2F–2J artifacts retained (AHA/ESC ACS metadata, references, governance).

## Implementation roadmap (documentation only)

| Phase | Focus |
|-------|--------|
| **H1** | Hypertension vocabulary review / gap sign-off with cardiologist |
| **H2** | HTN source identity + license verification (ESC HTN + ACC/AHA verify) |
| **H3** | Encounter / measurement data-model gaps (BP context, labs on DTO) |
| **H4** | Clinician-reviewed **synthetic** HTN scenarios (not golden clinical truth yet) |
| **H5** | Missing-information deterministic rules (post gates) |
| **H6** | Alert-fatigue controls in engine/UI policy |
| **H7** | Target-organ + secondary HTN review modules |
| **H8** | Medication safety module + licensed data |

## Related documents

| Path | Role |
|------|------|
| [`hypertension_governance_status.md`](hypertension_governance_status.md) | Dashboard |
| [`hypertension_clinician_followup_questions.md`](hypertension_clinician_followup_questions.md) | Follow-up |
| [`cardiology_chest_pain_rule_pack_design.md`](cardiology_chest_pain_rule_pack_design.md) | Deferred pilot #2 |
