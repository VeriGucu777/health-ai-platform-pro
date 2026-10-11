# Cardiology Chest Pain Pilot Rule-Pack — Design & Clinical Review Plan (Phase 2B)

**Status:** PROPOSED / UNREVIEWED (no cardiologist sign-off)  
**Design version (not a rule manifest):** `cardiology-chest-pain-v0.1.0-design`  
**Repository main at design time:** `e88d702` (controlled vocabulary foundation)  
**Scope:** Documentation and governance only — **zero executable clinical rules**

---

## 1. Purpose and boundaries

### First pilot use case

A patient presents with **chest pain** (`card.complaint.chest_pain`). During an encounter, clinicians record structured complaints, findings, vitals, and question responses. A **future** Clinical Copilot may surface:

| Future output channel | Role |
|----------------------|------|
| Clinical considerations (differential support) | Structured inputs may support *consideration* of condition categories |
| Missing information | Important structured data not yet captured |
| Suggested questions | Clinically relevant questions not yet asked |
| Safety alerts | Combinations that may warrant increased clinician attention |

**Phase 2B defines rule families, inputs, governance, and review gates — not medical outputs.**

### Critical limits (Phase 2B)

- No disease ranking, thresholds, scores (HEART/TIMI/GRACE/Wells), troponin/ECG logic, treatment, medication, disposition, or NBQ/red-flag **runtime** behavior.
- No `ClinicalDecisionEngine` wiring, evaluate API, Copilot UI, DB, migrations, vocabulary edits, or rule YAML.

### Safety language (product + clinical)

| Avoid | Prefer |
|-------|--------|
| Diagnostic engine, autonomous diagnosis, diagnosis confirmer | Clinical decision **support** |
| “Patient has X”, “Diagnosis is X” | “Değerlendirmede dikkate alınabilir.” / “Consideration for clinician review.” |
| “X probability 78%” | Ordinal priority or explicit non-probability bands (after validation) |

Final clinical decisions remain with the licensed clinician.

---

## 2. Layering (unchanged from Phase 2A)

```text
VOCABULARY  → stable keys (structured input)
RULE        → source-linked, deterministic interpretation (future)
ENGINE      → orchestration, policy merge, provenance
OUTPUT      → considerations, missing info, questions, alerts (future)
```

Rule families below are **design templates** only (e.g. `chest_pain_missing_characterization`), not YAML rules.

---

## 3. Existing vocabulary — chest pain workflow relevance

Source: `clinical_knowledge/vocabularies/cardiology/cardiology_v1.0.0.yaml` (v1.0.0, 35 terms, all `approved_demo` / `proposed_by_product`).

### Directly relevant to chest pain documentation (keys only; no clinical significance assigned)

| Key | Category | Notes |
|-----|----------|--------|
| `card.complaint.chest_pain` | complaint | Primary pilot chief complaint |
| `card.question.chest_pain_on_exertion` | question | yes/no/unknown |
| `card.question.chest_pain_duration` | question | **Schema note:** duration question currently allows yes/no/unknown only — likely needs future answer model review (see gaps) |
| `card.complaint.dyspnea` | complaint | Associated symptom candidate |
| `card.question.dyspnea_on_exertion` | question | |
| `card.complaint.palpitations` | complaint | Associated symptom candidate |
| `card.complaint.syncope` | complaint | Associated symptom candidate |
| `card.question.syncope_with_exertion` | question | |
| `card.complaint.dizziness` | complaint | Associated symptom candidate |
| `card.finding.exertional_symptoms` | finding | History/finding overlap with exertional questions — dedup strategy needed in review |
| `card.finding.smoking_history` | finding | Risk context |
| `card.finding.diabetes_history` | finding | Risk context |
| `card.finding.hypertension_history` | finding | Risk context |
| `card.finding.family_cardiovascular_history` | finding | Risk context |
| `card.vital.systolic_blood_pressure` | vital | + `card.unit.mm_hg` |
| `card.vital.diastolic_blood_pressure` | vital | + `card.unit.mm_hg` |
| `card.vital.heart_rate` | vital | + `card.unit.beats_per_minute` |
| `card.vital.oxygen_saturation` | vital | + `card.unit.percent` |
| `card.onset.acute` … `card.onset.unknown` | onset | Attach via encounter finding `onset_code` (documentation) |
| `card.answer_code.yes` / `no` / `unknown` | answer_code | Canonical ternary for questions |

### Present but lower priority for **first** chest-pain pack scope (still in catalog)

Orthopnea, PND, irregular pulse, lower extremity edema, peripheral edema complaint, fatigue, palpitations_duration question — may matter in expanded packs; cardiologist to prioritize.

---

## 4. Vocabulary gap analysis (review candidates only — **do not add in 2B**)

Classification: **A** likely useful structured concept · **B** needs cardiologist confirmation · **C** likely out of first MVP · **D** overlaps existing vocabulary

| Concept area | Class | Notes |
|--------------|-------|--------|
| Pain location | B | No key today |
| Radiation | B | |
| Character/quality | B | |
| Onset timing (structured) | D/B | `card.onset.*` exists; may be insufficient for rules |
| Duration (numeric + unit) | B | Question `chest_pain_duration` vs yes/no answers mismatch |
| Severity (ordinal) | B | |
| Exertional relation | D | `card.question.chest_pain_on_exertion`, `card.finding.exertional_symptoms` |
| Positional relation | B | |
| Pleuritic relation | B | |
| Reproducibility (palpation) | B | |
| Associated dyspnea | D | complaint + question keys exist |
| Diaphoresis/sweating | B | |
| Nausea/vomiting | B | |
| Syncope/presyncope | D | complaint + question |
| Palpitations | D | complaint |
| Known cardiovascular disease | B | |
| Prior PCI/CABG/stent | B | |
| Thromboembolic risk context | C/B | Often PE workup — scope boundary |
| Recent immobilization/procedure | C/B | |
| Fever/infectious symptoms | C | |
| Trauma context | C | |

**New terms added in Phase 2B:** 0

---

## 5. Rule family model (future `rule_type` alignment)

Maps to existing `clinical_rule.schema.json` enums where applicable.

| Family | Future `rule_type` | Purpose | Output class (domain) |
|--------|-------------------|---------|------------------------|
| Differential support | `differential_support` | Input pattern may support a **consideration** | `DifferentialCandidateOutput` |
| Differential against | `differential_against` | Input pattern may reduce support | opposing_evidence on candidates |
| Missing information | `missing_information` | Required structured element absent | `MissingInformationOutput` |
| Suggested question | `next_best_question` | Question should be asked | `SuggestedQuestionOutput` |
| Safety alert | `safety_alert` / `red_flag` | Heightened attention | `SafetyAlertOutput` |
| Workflow guard | `workflow_guard` | e.g. minimum-information gate | `missing_information` / status |
| Medication/reimbursement | `medication_safety`, etc. | **Out of chest-pain pack v1** | separate modules |

### Conceptual template examples (not rules)

- `chest_pain_missing_characterization` — detects absent characterization fields (keys TBD by cardiologist).
- `chest_pain_unanswered_core_question` — question key not present in `question_responses`.
- `chest_pain_insufficient_data_for_consideration` — gate before emitting differential support.

No triggers, no condition keys, no thresholds.

---

## 6. Condition / differential concepts — architecture recommendation

**Recommendation: B — separate `CardiologyDifferentialConceptRegistry` (future), not vocabulary category.**

| Option | Verdict |
|--------|---------|
| A. Vocabulary category | Reject for diseases — vocabulary is **input** terminology, not interpretive disease ontology |
| B. Separate condition registry | **Preferred** — `condition_key`, display_key, status, clinical_review_status, source_refs, specialty |
| C. Embedded only in rules | Reject — duplicates condition metadata across rules |

Rules reference `condition_key` from the registry; vocabulary keys remain findings/complaints/questions/vitals.

---

## 7. Chest pain workflow stages (evaluation pipeline design)

Order is **architectural**, not clinical priority:

1. **Presentation characterization** — chief complaint present; onset codes if recorded  
2. **Associated symptoms** — linked complaints/findings/questions  
3. **History / risk context** — structured history findings  
4. **Vital / observed finding context** — vitals + clinician findings  
5. **Missing information detection** — before strong considerations  
6. **Safety screening** — parallel channel, not suppressed by ranking  
7. **Differential support generation** — only if minimum-information gate passes (fields TBD by cardiologist)

Engine should run stages **deterministically** with provenance per emitted artifact.

---

## 8. Input completeness model

| State | Meaning | Rule consumption |
|-------|---------|------------------|
| Not asked | No question response / no finding slot filled | `missing_information` candidate |
| Asked — negative | `answer_code` = `card.answer_code.no` or finding with `negated=true` | Explicit negative evidence |
| Asked — positive | yes or finding present, not negated | Positive evidence |
| Unknown | `card.answer_code.unknown` | **Neither** positive nor negative — do not treat as “no” |
| Unavailable | e.g. vital not measured | Distinct from unknown where modeled |

**Invariants**

- `missing response` ≠ `negative response`  
- `unknown` ≠ `no`  
- Negation uses **same key** + `negated=true` — never `card.finding.no_chest_pain`

---

## 9. Temporal model

Current onset codes: `card.onset.acute`, `subacute`, `chronic`, `unknown` — sufficient for **documentation** only in v1.0.0.

**Review candidates (no medical time thresholds):**

- Duration numeric + unit (separate from yes/no duration question)  
- Relation to exertion/meals/position (structured codes)  
- “Constant vs intermittent” (structured)

Do not encode ACS/time-to-treatment windows in rules without guideline + cardiologist approval.

---

## 10. Numeric predicate model (future)

Operators only (no clinical numbers in Phase 2B):

`eq`, `neq`, `gt`, `gte`, `lt`, `lte`, `between`, `exists`, `not_exists`

Apply to `VitalObservationInput.value_numeric` and future structured measurements — **after** cardiologist defines which vitals matter, not default thresholds.

---

## 11. Combination logic (future)

Declarative boolean composition:

- `ALL`, `ANY`, `NOT` over predicate nodes  
- Clinically neutral examples only in tests: `finding.a`, `finding.b`

No real chest-pain trigger combinations in design docs or fixtures.

---

## 12. Rule output prohibitions (future schema policy)

Future `output_definition` must **not** include autonomous actions:

`diagnosis_confirmed`, `prescribe`, `order_medication`, `discharge`, `admit`, `send_to_icu`, test orders, referral mandates.

Allowed output channels remain: consideration, question, missing info, alert.

---

## 13. Scoring and differential display safety

Existing model: `relative_priority_score` float 0–1 on `DifferentialCandidateOutput` — **must not be presented as probability** without independent validation.

| Strategy | MVP recommendation |
|----------|-------------------|
| A. Weighted evidence | Defer until weights clinically signed off |
| B. **Ordinal priority only** | **Preferred for first demo** — use `rank` + bands |
| C. Evidence count | Supplementary display only |
| D. Expert priority bands | Good for UI (“higher attention” vs numeric %) |

**Differential ranking (pre-validation):** Prefer **C — unranked or weakly grouped considerations** (e.g. “considerations for review”) OR **B — high/medium/low relevance bands** without numeric probability. Avoid numeric ranking that implies calibrated likelihood.

---

## 14. Explanation and provenance

Reuse `ClinicalDecisionProvenance` and existing catalog provenance:

- `rule_id`, `rule_version`, `source_refs`, `guideline_refs` (section_ref, recommendation_id — **no full guideline text**)
- `policy_profile_id`, `rule_set_manifest_hash`, `input_snapshot_id`, `triggered_by`
- Per output: `supporting_evidence[]`, `opposing_evidence[]`, `rationale_key`, `explanation_key` → **deterministic i18n templates** (TR/EN), not LLM free text

---

## 15. Source requirements

### Existing ESC HTN source

`guideline:esc:htn:2024` (`clinical_knowledge/sources/guideline_esc_htn_2024.yaml`) is **hypertension** metadata.

**NOT SUFFICIENT FOR CHEST PAIN RULE PACK** — do not cite as chest-pain evidence because it shares “ESC”.

### Source requirement matrix (defaults: UNKNOWN / deny ingestion until verified)

| Clinical area | Source type needed | Candidate org (TO VERIFY EXTERNALLY) | License status | AI/commercial use | Ingestion allowed | Review status |
|---------------|-------------------|--------------------------------------|----------------|---------------------|-------------------|---------------|
| Acute chest pain / ACS assessment | Society guideline | ESC, AHA/ACC, etc. | UNKNOWN | UNKNOWN | NO until cleared | UNREVIEWED |
| Stable chest pain / outpatient cardiology | Society / national | ESC, Turkish Cardiology Assoc. if applicable | UNKNOWN | UNKNOWN | NO | UNREVIEWED |
| Pulmonary embolism (if in scope) | Society guideline | ESC, ACCP, etc. | UNKNOWN | UNKNOWN | NO | UNREVIEWED |
| Aortic syndromes (if in scope) | Society guideline | ESC, AHA | UNKNOWN | UNKNOWN | NO | UNREVIEWED |
| Emergency triage context (if in scope) | Emergency guideline | IFEM, national ED protocols | UNKNOWN | UNKNOWN | NO | UNREVIEWED |
| Vital sign documentation | Standards / device | LOINC (mapping only, no bulk) | UNKNOWN | N/A | NO bulk | UNREVIEWED |
| ECG interpretation | Society statement | ESC/AHA | UNKNOWN | UNKNOWN | NO raw ECG AI in v1 | UNREVIEWED |

**License verification required:** YES before any `source_linked` → `license_cleared` promotion.

### Source acquisition process (future)

1. Identify official source  
2. Verify publication/version/date  
3. Verify license / redistribution / AI use  
4. Register metadata in `clinical_knowledge/sources/`  
5. Clinician selects recommendation areas  
6. Product translates to **deterministic rule proposal** (IDs + refs only)  
7. Clinician review  
8. Technical validation (schema, tests)  
9. `approved_demo`  
10. `approved_prod` (later)

**Copyright:** Rule YAML stores `source_id`, `section_ref`, `recommendation_id` — never full guideline paragraphs.

---

## 16. Rule lifecycle — first chest pain pack

Proposed lifecycle (aligned with `clinical_knowledge/README.md`):

`draft` → `source_linked` → `license_cleared` → `clinical_review` → `approved_demo` → `approved_prod`

**Maximum ceiling before cardiologist review:** **`license_cleared`** at most for internal engineering fixtures; prefer **`draft`** or **`source_linked`** until clinical review completes.  
**Never** `approved_demo` / `approved_prod` / `clinically_approved` without documented cardiologist review.

Pack design version SemVer: **`cardiology-chest-pain-v0.1.0-design`** (0.x = pre-implementation design); implementation manifest might become `cardiology-chest-pain-v1.0.0` after review.

---

## 17. Conflict resolution

When rules disagree on the same `condition_key`:

- Preserve **both** supporting and opposing evidence  
- Deterministic merge policy (ordered rule_id, policy profile weights on **ordinal** priority only)  
- Explanation surfaces conflict — never hide opposing evidence  
- Safety alerts independent of differential merge

---

## 18. Output channel precedence (future UI)

Recommended Copilot panel order:

1. **Safety alerts** (separate channel; never demoted by differential ranking)  
2. **Missing information** (prefer “insufficient structured information” over confident considerations)  
3. **Suggested questions** (bounded list)  
4. **Clinical considerations** (non-probability wording)

No “diagnosis probability” UI.

---

## 19. Minimum information gate (structure only)

Future concept: `minimum_information_gate`

```yaml
# Illustrative shape only — NOT implemented
gate_id: chest_pain_mvp_gate_v0
required_all: []      # keys TBD by cardiologist
required_any: []      # keys TBD by cardiologist
clinical_review_status: unrevised
```

Engine: if gate fails → emit missing_information / workflow_guard; **suppress or attenuate** differential_support rules (policy-defined).

---

## 20. Suggested question controls (technical)

- Max questions per evaluation (configurable policy cap)  
- Do not suggest keys already in `question_responses`  
- Do not repeat dismissed questions without new encounter version  
- Allowlist per pack — only vocabulary `question` keys approved for pack  
- No clinical branching tree in Phase 2B

---

## 21. Encounter integration mapping

| Source entity | Maps to `EncounterEvaluationContext` | Gap |
|---------------|----------------------------------------|-----|
| `EncounterComplaint` | `chief_complaints[]` (`complaint_key`, `negated`) | Application mapper must set `ClinicalInputSource` |
| `EncounterFinding` | `findings[]` (`finding_key`, `negated`, optional `value_code`, onset) | Onset code vocabulary alignment |
| `EncounterQuestionResponse` | `question_responses[]` | Ensure answer_code vocabulary validation (future) |
| HealthMeasurement / vitals | `vitals[]` | **Gap:** encounter UI vs HealthMeasurement — see below |
| Historical bundle | `historical_context` flags only in v1 slice | Full history consumption deferred |

No implementation in Phase 2B.

---

## 22. Vital mapping recommendation

**Recommendation: A primary — encounter-linked measurements mapped into `VitalObservationInput` with vocabulary `vital_key` + unit keys; B — optional numeric finding values only when explicitly modeled.**

Precedence policy (future):

1. Most recent encounter-scoped vital measurement with valid unit  
2. Explicit `EncounterFinding` numeric only if schema extends — avoid duplicate semantics  
3. Do not merge unrelated HealthMeasurement streams without source tagging

No clinical thresholds in mapping layer.

---

## 23. Historical data scope (MVP)

**Strict MVP:** active encounter structured inputs + optional `historical_context` boolean flags only.

Defer: automated consumption of diagnoses, labs, ECG PDFs, imaging narratives for **first** chest-pain pack.

---

## 24. Labs / ECG / imaging boundaries

| Modality | First pack scope |
|----------|------------------|
| ECG | Structured interpretation fields only (future vocabulary) — **NO** raw ECG AI |
| Labs | Structured result keys (future) — **NO** troponin thresholds in design |
| Imaging | Structured report metadata — **NO** DICOM / imaging AI |
| Free text | **NO** NLP mapping to rules in deterministic v1 |

---

## 25. Out-of-scope modules (documented boundaries)

| Module | Relation to chest-pain pack |
|--------|----------------------------|
| `MedicationSafetyModule` | Separate future module |
| `AllergyInteractionModule` | Separate |
| `ReimbursementModule` | Separate (SGK later) |
| e-Nabız / SGK | Dependency boundary only — **no** integration design in 2B |
| Multi-clinician ward round (“visite”) | Future collaboration use case — no encounter ownership change now |

---

## 26. Test strategy (future implementation)

| Class | Intent |
|-------|--------|
| A. Rule schema validation | JSON Schema + business rules |
| B. Source reference validation | source_id exists, license_cleared |
| C. License gate | block `approved_prod` without clearance |
| D–G. Fixtures | positive / negative / missing / contradictory — **neutral keys only** |
| H. Provenance | rule_id, manifest hash present |
| I. Deterministic ordering | stable sort keys |
| J. Locale-independent rules | keys stable; templates localized |
| K. TR/EN templates | no mixed locale in rule files |
| L. No PHI in logs | audit metadata only |
| M. No probability language | lint rule output templates |

---

## 27. Synthetic scenario test pack (future format)

```yaml
scenario_id: SYN-CHEST-001
input_context: { ... EncounterEvaluationContext-shaped neutral fixture ... }
expected_triggered_rule_ids: []
expected_absent_rule_ids: []
expected_output_types: [missing_information]
review_status: proposed
```

No real clinical values; no real patient narratives.

---

## 28. Clinical golden set (later)

Cardiologist-reviewed synthetic cases:

- structured inputs  
- expected consideration **types** (not medical truth until signed)  
- expected missing info / questions / alerts  
- reviewer id, review date  

No real patient data.

---

## 29. Metrics plan (pre-production)

- Rule precision vs expert review  
- Alert usefulness / false-positive burden  
- Missed critical scenario drills (synthetic)  
- Question suggestion usefulness  
- Inter-rater agreement where feasible  

No medical validation claims in Phase 2B.

---

## 30. Human override (future)

Clinician actions on outputs: **acknowledge**, **dismiss**, **not applicable** — stored as encounter-level overlay; **does not mutate** rule YAML or catalog.

---

## 31. Clinician review matrix

| Item | Review required |
|------|-----------------|
| Complaint characterization fields | YES |
| Associated symptom fields | YES |
| Mandatory history fields | YES |
| Mandatory vital fields | YES |
| Candidate differential concepts (registry) | YES |
| Missing-information logic | YES |
| Suggested-question logic | YES |
| Safety alert logic | YES |
| Rule conflict resolution policy | YES |
| Output wording (TR/EN templates) | YES |
| Relative priority / band strategy | YES |
| Minimum-data gate fields | YES |
| Vocabulary gap candidates | YES |
| Purely technical ordering/cache/replay | Engineering |

All clinical decisions: **UNREVIEWED** / **PROPOSED** until cardiologist workshop.

---

## 32. Cardiologist review sheet (≤15 questions)

1. First presentation scope: ED only, outpatient only, or both for pilot?  
2. Minimum chief complaint set: is `card.complaint.chest_pain` alone sufficient entry?  
3. Which associated complaints must be structured vs free text in v1?  
4. Which history findings are mandatory before any “consideration” output?  
5. Which vitals are mandatory vs optional at first documentation pass?  
6. Is current onset code set sufficient, or do we need duration numeric + unit first?  
7. How should `chest_pain_duration` be answered (yes/no vs structured duration)?  
8. Which question keys belong in the first-visit workflow (max count)?  
9. Safety alert philosophy: few high-specificity alerts vs broader reminders (alert fatigue)?  
10. Should differential considerations be **unranked**, **banded**, or **ordinal rank** in demo UI?  
11. Acceptable TR wording examples for considerations and alerts?  
12. Which condition categories may appear in v1 consideration list (names only — no logic)?  
13. Minimum-data gate: required questions/findings before considerations?  
14. Overlap: exertional finding vs exertional questions — canonical representation?  
15. Pilot boundary: explicitly exclude PE/aortic/GERD/etc. from v1 pack or include as labeled “out of scope for v1”?

---

## 33. Product / engineering open questions

1. Copilot result ordering — fixed channel order vs collapsible sections?  
2. Re-evaluation trigger: on each save vs explicit “Refresh support”?  
3. Stale evaluation when encounter version increments?  
4. Audit events for evaluate vs dismiss vs acknowledge?  
5. Rule version replay on historical encounters — read-only snapshot?  
6. Cache strategy for manifest hash + policy profile?  
7. Performance budget for evaluate (p95 target)?  
8. CI: add `validate_clinical_vocabulary` alongside knowledge validate?  
9. When to add `CardiologyDifferentialConceptRegistry` port (2C vs 2D)?  
10. Encounter→context mapper location (application service vs specialty module)?

---

## 34. Phase 2B deliverables checklist

- [x] Chest pain pilot scope defined  
- [x] Rule families designed  
- [x] Vocabulary reuse + gap list  
- [x] Source / license matrix  
- [x] Review gates and lifecycle ceiling  
- [x] Test / golden-set / metrics plan  
- [x] No rule YAML, no code behavior change  

---

## 35. Related paths

| Path | Role |
|------|------|
| `docs/cardiology_controlled_vocabulary.md` | Vocabulary governance |
| `clinical_knowledge/rules/cardiology/chest_pain/README.md` | Inert pointer — no rules |
| `clinical_knowledge/README.md` | Catalog lifecycle |
| `app/domain/clinical_decision/models.py` | Output contracts |

---

*Document owner: product + engineering. Clinical authority: pending cardiologist review.*
