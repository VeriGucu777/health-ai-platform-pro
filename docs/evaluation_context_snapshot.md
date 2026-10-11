# Evaluation Context Snapshot & Provenance (Phase 2D)

## Purpose

Answer (future): **“Which exact structured input produced this clinical decision output?”**

Phase 2D provides deterministic **semantic snapshot identity** for `EncounterEvaluationContext` — not rule execution, not Copilot, not DB persistence.

Implementation: `app/application/clinical_decision/evaluation_context_snapshot.py`

## What is hashed (semantic input)

Included in **semantic hash**:

- `specialty_key`, `locale`
- `patient_demographics` (`age_years`, `gender_key` only)
- Ordered `chief_complaints`, `findings`, `vitals`, `question_responses`
- `historical_context` boolean flags (if present)
- Per-item `recorded_at` / vital `measured_at` when set (ordering/context timing)

Excluded from **semantic hash**:

- `encounter_id`, `patient_id`, `organization_id`, `clinician_user_id`
- `created_at`, `input_snapshot_id`, assembly envelope timestamps
- `encounter_version` (metadata envelope only)
- Rule catalog / engine / policy identifiers
- All PHI free text (never on context contract)

## Algorithm

| Item | Value |
|------|--------|
| Schema identity | `encounter_evaluation_context_semantic:v1` |
| Hash prefix | `encounter_evaluation_context:v1:` |
| Digest | SHA-256 over UTF-8 canonical JSON |
| `input_snapshot_id` | `sha256:<hex>` |

Canonical JSON: sorted object keys, compact separators, ASCII, stable list order as stored on context.

## Encounter version policy

**Semantic hash:** structured clinical content only.  
**Metadata:** `encounter_version` on `EvaluationContextSnapshotMetadata`.

Same structured input after a benign encounter version bump → **same semantic hash**, different metadata version.

## Timestamp policy

- Vital/question/finding `recorded_at` **included** when present (meaningful ordering/context).
- Context `created_at` **excluded** (assembly envelope, not clinical content).

## Float normalization

Vital `value_numeric` is hashed as **stable decimal text** derived from `Decimal(repr(float))` — avoids platform JSON float noise. Not clinical rounding.

## Empty / null normalization

- Missing `historical_context` → JSON `null`
- Empty tuples → JSON `[]`
- Explicit `null` fields inside items preserved (`recorded_at`, `value_code`, etc.)

## Vocabulary identity (metadata)

Optional `VocabularySnapshotIdentity`:

- `vocabulary_id`, `vocabulary_version`, `manifest_hash`

Does **not** imply clinical approval. `approved_demo` remains demo semantics.

## Rule catalog separation

**Rule manifest hash is NOT part of input snapshot.**

Future evaluation provenance combines:

```text
input_snapshot_id
+ vocabulary_manifest_hash (optional)
+ rule_manifest_hash
+ engine_version
+ specialty_module_version
+ policy_profile_id
```

See `EvaluationProvenanceEnvelope` (design type, unwired).

## PHI boundary

Canonical hash input must never include display names, notes, addresses, or final summary text. Sentinel tests enforce marker absence.

## Fixtures

Neutral helpers: `tests/support/evaluation_context_fixtures.py`  
(Vocabulary keys only; no disease scenarios.)

## Related

- [Encounter evaluation context assembly](encounter_evaluation_context_assembly.md)
- [Clinical decision engine](clinical_decision_engine.md)

No medical validation claim — identity and replay scaffolding only.
