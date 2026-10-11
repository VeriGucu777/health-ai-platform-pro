# Encounter → EncounterEvaluationContext Assembly (Phase 2C)

## Purpose

Read-only, deterministic mapping from `ClinicalEncounterAggregate` (plus optional encounter-scoped `HealthMeasurement` rows and pre-built `EncounterHistoricalContext`) into `EncounterEvaluationContext` for future clinical decision evaluation.

**No rule execution**, no `evaluate()`, no Copilot API/UI.

Implementation: `app/application/clinical_decision/encounter_context_mapper.py`

## Source → target

| Encounter source | Evaluation context field | Notes |
|------------------|-------------------------|--------|
| Active `EncounterComplaint` with `complaint_key` | `chief_complaints[]` | Display-only complaints excluded |
| Active `EncounterFinding` | `findings[]` | `finding_type` not duplicated on context DTO |
| Active evaluable `EncounterQuestionResponse` | `question_responses[]` | TEXT/NUMBER excluded |
| Active `HealthMeasurement` (caller-supplied) | `vitals[]` | BP + HR fields only today |
| Pre-built bundle helper output | `historical_context` | Use `encounter_historical_context_from_bundle` upstream |
| `EncounterFinalSummary` | **Excluded** | Clinician-authored; not engine evidence |

## Exclusions (PHI / non-engine-safe)

Never mapped into evaluation context:

- `clinician_display_text` (complaints)
- `clinician_note` (questions, final summary)
- Final summary section text
- Patient name, email, phone, address (not on context contract)

## Active-only filter

Children with `is_active=false` or `deleted_at` set are skipped (fail-safe filter).

## Encounter status

Mapper does **not** block on `EncounterStatus`. Callers may restrict to `active` for live Copilot later; **finalized** replay/audit may still assemble context. **Cancelled** encounters are not special-cased here.

## Ordering (deterministic)

| Collection | Sort key |
|------------|----------|
| Complaints | `sequence_no`, then `id` |
| Findings | `sequence_no`, then `id` |
| Question responses | `sequence_no`, then `id` |
| Vitals (from measurements) | `measured_at`, then measurement `id` |

Duplicate keys are **not** deduplicated; negated and positive entries may coexist.

## Vitals

- **Source:** encounter-linked `HealthMeasurement` passed into the request — not SQL inside the mapper.
- **Fields mapped:** systolic/diastolic pressure, heart rate → `card.vital.*` keys.
- **Not mapped:** SpO2 (no field on `HealthMeasurement` yet), weight, glucose, etc.
- **Precedence:** all observations preserved in sort order (no averaging).
- **Units:** literal `mmHg` / `bpm` on context; no unit conversion.
- **Finding numerics:** `EncounterFinding.value_numeric` is **not** copied into vitals (avoid duplicate vital channels).

## Vocabulary validation

Optional `ClinicalVocabularyRegistry` port (no filesystem/YAML in mapper).

| Policy | Behavior |
|--------|----------|
| `validate_vocabulary_keys=True` + registry | Fail-closed: unknown or wrong-category key → `UnknownClinicalVocabularyKeyError` |
| Missing `complaint_key` (display text only) | Valid documentation; **excluded** from structured complaints (assembly continues) |
| `VocabularyEligibilityMode.DEMO` | Allows `approved_demo` / `approved_prod` terms (not clinically approved) |
| `VocabularyEligibilityMode.PRODUCTION` | Requires `engine_safe` on term (`approved_prod` + clinically approved) |

Current pilot vocabulary is **demo-only**; production mode will reject all v1.0.0 terms until review promotes them.

## Contract gaps (unchanged in 2C)

`EncounterEvaluationContext` does not include:

- `encounter_version`, `vocabulary_version`, `vocabulary_manifest_hash` (future provenance extension)
- `is_primary` on complaints
- `finding_type`, `onset_code`, finding `value_numeric` / `unit`
- `answer_numeric` on question responses (NUMBER-type encounter responses are not engine-mapped in Phase 2C)
- `VitalObservationInput.value_numeric` as **float** per existing contract (int/Decimal sources converted; no clinical unit conversion)

Numeric finding/answer values remain on the aggregate only until a backward-compatible DTO extension is approved. These gaps are **known and non-blocking** for Phase 2C mapper correctness.

## Historical context

Pass `EncounterHistoricalContext` built via `encounter_historical_context_from_bundle` — mapper does not read `MedicalRecord` narrative text.

## Negation

Same vocabulary key with `negated=true` on complaints/findings; no separate `no_*` keys.

## Unknown vs missing vs negative

- No response → absent from `question_responses` (missing, not negative)
- `answer_code=no` → explicit negative
- `answer_code=unknown` → explicit unknown (not treated as `no`)

Boolean answers are stored on the encounter as `yes` / `no` / `unknown`. Vocabulary validation resolves these to `card.answer_code.*` keys; the evaluation context keeps the encounter-native short codes.

## Related

- [Clinical Decision Engine](clinical_decision_engine.md)
- [Cardiology chest pain rule pack design (Phase 2B)](cardiology_chest_pain_rule_pack_design.md)
