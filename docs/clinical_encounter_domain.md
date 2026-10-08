# Clinical Encounter Domain (Phase 1B)

## Bounded context

**Clinical Encounter** models an in-clinic session: documentation captured during a visit and (later) input to the Clinical Decision Engine. It is separate from:

- **Patient** — longitudinal identity
- **Retrospective Clinical Summary / Risk History** — hub analytics
- **Clinical Decision / Clinical Knowledge** — rule evaluation and catalogs

## Aggregate root

`ClinicalEncounter` owns lifecycle and coordinates child documentation. Child entities reference `encounter_id` only (no denormalized patient/org on domain children; persistence may add DB guards later).

## Lifecycle

| Status | Meaning |
|--------|---------|
| `draft` | Created, not yet documenting |
| `active` | Documentation and copilot evaluation allowed |
| `finalized` | Terminal; immutable clinical input history |
| `cancelled` | Terminal; abandoned session |

Explicit methods: `activate`, `finalize`, `cancel`. No generic status setter.

**Cancelled ≠ soft delete:** `is_active` / `deleted_at` are separate retention concepts.

## Domain vs non-domain

| In domain (Phase 1B) | Outside domain |
|----------------------|----------------|
| State transitions, version field | PatientAccessPolicy enforcement |
| Child field validation | One active encounter per patient/org (DB/repository) |
| `assert_mutable()` | Appointment/patient/org consistency checks |
| Repository **port** | ORM, API, engine mapper |

## Engine mapping (future)

Application mapper will produce `EncounterEvaluationContext` using **machine keys only** (`complaint_key`, `finding_key`, `question_key`, `answer_code`). Fields such as `clinician_display_text` and `clinician_note` are PHI-capable UI text and must not flow into rule evaluation automatically. Text question responses expose `is_engine_evaluable() == False`.

## PHI

Domain types use `repr=False` on PHI-capable fields. No logging in this module.

## Final summary

`EncounterFinalSummary` is the clinician-finalized visit summary (immutable value object). It is **not** the retrospective **Clinical Summary** product under analytics.

## Corrections

Finalized encounters are not silently edited. Future addendum/amendment workflows are application/Phase 2+ concerns.
