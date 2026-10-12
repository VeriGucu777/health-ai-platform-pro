# Chest Pain Pilot — Verified Source References (Phase 2I)

**Status:** Bibliographic and **section-level** anchors only · **No** recommendation bodies · **No** rules · **No** ingestion

**Verified at:** 2026-10-12 (official publisher table-of-contents / identity checks)

## 1. Purpose

Provide **traceable citation anchors** for future rule authoring. A verified `section_ref` means the project identified an official document location — **not** that a rule is licensed, clinically valid, or approved for production.

## 2. Verification methodology

- Primary identity and section numbering from **official full-text landing pages**:
  - AHA Journals / Circulation: [DOI 10.1161/CIR.0000000000001029](https://www.ahajournals.org/doi/full/10.1161/CIR.0000000000001029)
  - Oxford Academic / European Heart Journal: [DOI 10.1093/eurheartj/ehad191](https://academic.oup.com/eurheartj/article/44/38/3720/7243210)
- ESC hub (metadata cross-check): [ESC ACS 2023 guideline page](https://www.escardio.org/guidelines/clinical-practice-guidelines/all-esc-practice-guidelines/acute-coronary-syndromes/)
- **Not used:** blogs, tertiary summaries, unofficial PDF mirrors, medical education sites.
- **Not copied:** paragraph text, recommendation bodies, tables, or algorithms.

### Verification status values

| Status | Meaning |
|--------|---------|
| `VERIFIED` | Official document identity or TOC section number/title confirmed |
| `TO_VERIFY` | Not yet confirmed to section/recommendation level |
| `NOT_APPLICABLE` | Out of scope for chest-pain pack |
| `CORRECTION_REVIEW_REQUIRED` | Official correction may affect this anchor; do not cite for rules until reviewed |

## 3. AHA bibliographic identity

| Field | Value |
|-------|--------|
| `source_id` | `guideline:aha-acc:chest-pain:2021` |
| Title | 2021 AHA/ACC/ASE/CHEST/SAEM/SCCT/SCMR Guideline for the Evaluation and Diagnosis of Chest Pain |
| Organizations | AHA / ACC (joint guideline) |
| Journal | *Circulation* |
| Citation | 2021;144(22):e368–e454 |
| DOI | [10.1161/CIR.0000000000001029](https://doi.org/10.1161/CIR.0000000000001029) |
| Publication | Online **28 October 2021**; print issue **30 November 2021** (publisher record) |
| Current status | Active full guideline on AHA Journals (not superseded in Phase 2I review) |

Registry metadata: `clinical_knowledge/sources/guideline_aha_acc_chest_pain_2021.yaml`

## 4. AHA verified section anchors (topic mapping)

Section numbers and titles from official Circulation table of contents. **`recommendation_ref`:** none extracted (Class/LOE tables not transcribed).

| topic_key | section_ref | section_title (official) | verification_status |
|-----------|-------------|--------------------------|---------------------|
| `initial_evaluation_framework` | `2` | Initial Evaluation | VERIFIED |
| `history_symptom_characterization` | `2.1` | History | VERIFIED |
| `defining_chest_pain` | `1.4.2` | Defining Chest Pain | VERIFIED |
| `physical_examination` | `2.2` | Physical Examination | VERIFIED |
| `initial_diagnostic_testing` | `2.3` | Diagnostic Testing | VERIFIED |
| `cardiac_testing_framework` | `3` | Cardiac Testing General Considerations | VERIFIED |
| `acute_chest_pain_pathways` | `4` | Choosing the Right Pathway With Patient-Centric Algorithms for Acute Chest Pain | VERIFIED |
| `acute_suspected_acs_pathway` | `4.1` | Patients With Acute Chest Pain and Suspected ACS (Not Including STEMI) | VERIFIED |
| `stable_chest_pain_evaluation` | `5` | Evaluation of Patients With Stable Chest Pain | VERIFIED |
| `structured_risk_pretest_probability` | `5.1.1` | Pretest Risk Probability to Guide Need for Stress and Anatomic Tests | VERIFIED |

**Future rule families:** may point to these anchors; **`recommendation_ref` remains `TO_VERIFY`** until a specific recommendation row is independently verified (no Class/LOE extraction in 2I).

### Example anchor record (docs convention)

```yaml
source_ref:
  source_id: guideline:aha-acc:chest-pain:2021
  section_ref: "2.1"
  section_title: History
  recommendation_ref: null
  verification_status: VERIFIED
  verified_at: "2026-10-12"
  verification_source_url: https://www.ahajournals.org/doi/full/10.1161/CIR.0000000000001029
```

## 5. ESC bibliographic identity

| Field | Value |
|-------|--------|
| `source_id` | `guideline:esc:acs:2023` |
| Title | 2023 ESC Guidelines for the management of acute coronary syndromes |
| Organization | European Society of Cardiology |
| Journal | *European Heart Journal* |
| Citation | 2023;44(38):3720–3826 |
| DOI | [10.1093/eurheartj/ehad191](https://doi.org/10.1093/eurheartj/ehad191) |
| Publication date | **7 October 2023** (EHJ issue date) |
| Current status | Active guideline; **correction published 2024** (see §7) |

Registry metadata: `clinical_knowledge/sources/guideline_esc_acs_2023.yaml`

## 6. ESC verified section anchors (topic mapping)

From official EHJ table of contents (Oxford Academic full-text page).

| topic_key | section_ref | section_title (official) | verification_status |
|-----------|-------------|--------------------------|---------------------|
| `triage_and_diagnosis` | `3` | Triage and diagnosis | VERIFIED |
| `suspected_acs_presentation` | `3.1.1` | Clinical presentation | VERIFIED |
| `history_and_examination` | `3.1.2` | History taking and physical examination | VERIFIED |
| `initial_ecg_assessment` | `3.2` | Diagnostic tools \| Electrocardiogram | VERIFIED |
| `nstemi_nste_acs_ecg` | `3.2.2` | Acute coronary syndrome without persistent ST-segment elevation (non-ST elevation acute coronary syndrome) | VERIFIED |
| `hs_cTn_biomarkers` | `3.3.1` | High-sensitivity cardiac troponins | VERIFIED |
| `esc_0h_1h_2h_algorithms` | `3.3.4.1` | European Society of Cardiology 0 h/1 h and 0 h/2 h algorithms | CORRECTION_REVIEW_REQUIRED |
| `non_invasive_imaging` | `3.4` | Diagnostic tools \| Non-invasive imaging | VERIFIED |
| `chest_pain_differential` | `3.5` | Differential diagnosis for acute chest pain | VERIFIED |
| `initial_measures_suspected_acs` | `4` | Initial measures for patients presenting with suspected acute coronary syndrome \| Initial treatment | VERIFIED |
| `prehospital_triage` | `4.1` | Pre-hospital logistics of care | VERIFIED |
| `emergency_initial_assessment` | `4.2.1` | Initial diagnosis and monitoring | VERIFIED |
| `invasive_strategy_selection` | `5.1` | Selection of invasive strategy and reperfusion therapy | VERIFIED |
| `nste_acs_invasive_timing` | `5.2.3.1` | Early vs. delayed invasive strategy for non-ST elevation acute coronary syndrome | VERIFIED |

**Recommendation tables:** TOC lists **Recommendation Table 1–17** (e.g. Table 1 — clinical and diagnostic tools for suspected ACS, p. 3738). **Identifiers are verified at table-title level only** — **`recommendation_ref` = `TO_VERIFY`** for rule encoding (no table body copied).

## 7. ESC correction handling

| Field | Value |
|-------|--------|
| Correction DOI | [10.1093/eurheartj/ehad870](https://doi.org/10.1093/eurheartj/ehad870) |
| Journal | *European Heart Journal* |
| Citation | 2024;45(13):1145 |
| Published | **1 April 2024** (publisher notice on EHJ full-text page for ehad191) |

**Publisher-stated correction scope (summary, not clinical interpretation):**

- Citation error in **§3.3.2.1** (references for NSTEMI likelihood vs troponin levels).
- **Table S4** (assay-specific hs-cTn cut-offs for 0 h/1 h and 0 h/2 h algorithms): manufacturer naming and selected cut-off values corrected.

### Impact on candidate anchors

| Anchor | correction_impact |
|--------|-------------------|
| `3.1.1`, `3.1.2`, `3.5`, `4`, `4.1`, `4.2.1`, `5.1`, `5.2.3.1` | **NO** — not listed in correction notice |
| `3.3.4.1` (ESC 0 h/1 h / 0 h/2 h algorithms) | **YES** — related to corrected algorithm/supplementary cut-off material |
| `3.3.1` + future troponin **threshold** use | **TO_REVIEW** — adjacent to corrected content; **no thresholds extracted in this repo** |
| Any future cite of **Table S4** or **§3.3.2.1** | **CORRECTION_REVIEW_REQUIRED** |

**Provenance design (future):** store base guideline DOI `ehad191` plus optional `correction_doi: ehad870` when a rule anchor touches biomarker/algorithm sections affected by the correction.

## 8. Unresolved `TO_VERIFY` references

| Area | Why still TO_VERIFY |
|------|---------------------|
| Specific **Class/LOE recommendation rows** (AHA & ESC) | Not extracted; no recommendation bodies in repo |
| **ESC Recommendation Table N** row IDs for rule YAML | Table titles verified; row-level mapping not done |
| **AHA Top 10 Take-Home Messages** as rule sources | Deliberately excluded from anchors (summary layer) |
| **Non–chest-pain pathways** (PE, aortic, GI in AHA §4.2–4.3) | Out of first MVP scope; sections exist but not mapped to pack |
| **Turkish national guidelines** | No verified catalog source (Phase 2F) |

## 9. Licensing status (unchanged by 2I)

| Source | License / usage | Ingestion |
|--------|-----------------|-----------|
| AHA chest pain 2021 | `permission_required`; AI/commercial **unknown** | **false** |
| ESC ACS 2023 | `permission_required`; AI/commercial **permission_required** | **false** |

Citation verification **does not** grant copyright, AI/CDS, or commercial rights.

## 10. Clinical review status

| Gate | Status |
|------|--------|
| License / usage (Gate A) | **CLOSED** |
| Cardiologist review (Gate B) | **CLOSED** — **PENDING** |
| Lifecycle ceiling for rules | **`source_linked`** only (no `license_cleared`, no `approved_demo` / `approved_prod`) |

## 11. Rule-authoring restrictions

Even where `section_ref` is **VERIFIED**:

- Do **not** encode triggers, thresholds, scores, or recommendation text without license clearance **and** cardiologist review.
- Do **not** treat section verification as clinical approval.
- Do **not** ingest guideline PDFs, vectors, or RAG corpora.
- For ESC biomarker/algorithm areas, consult **§7** before any production anchor.

## Related documents

- [`docs/chest_pain_source_license_matrix.md`](chest_pain_source_license_matrix.md)
- [`docs/cardiology_chest_pain_rule_pack_design.md`](cardiology_chest_pain_rule_pack_design.md) §34
- [`docs/technical_synthetic_evaluation_scenarios.md`](technical_synthetic_evaluation_scenarios.md)
