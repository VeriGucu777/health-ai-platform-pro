# Technical Synthetic Evaluation Scenarios (Phase 2H)

**Status:** Engineering fixtures only · **Not** clinical validation · **Not** clinical golden cases

## Purpose

Neutral synthetic encounter scenarios support:

- deterministic `EncounterEvaluationContext` assembly
- semantic `input_snapshot_id` (`sha256:…`) stability and sensitivity tests
- vocabulary identity on snapshot metadata
- input-side provenance replay (rebuild → same semantic id)
- mutation isolation and ordering contracts

They do **not** assert medical correctness, diagnosis, risk, or guideline compliance.

## Location

- Factory library: `tests/support/clinical_decision_scenarios.py`
- Tests: `tests/unit/clinical_decision/test_technical_synthetic_evaluation_scenarios.py`

No production application modules contain scenario data.

## Naming

Scenario IDs use neutral technical labels:

- `scenario_001` … `scenario_005`
- No disease labels (`acs_case`, `mi_case`, `high_risk_case`, etc.)

## Scenario dimensions

| ID | Intent |
|----|--------|
| `scenario_001` | Minimal structured cardiology input (baseline) |
| `scenario_002` | Same semantics, different encounter id/version/timestamps |
| `scenario_003` | One structured field change → hash must change |
| `scenario_004` | PHI-only documentation change → hash unchanged |
| `scenario_005` | HealthMeasurement input order → canonical vitals order stable |

Additional fixtures: unknown vocabulary key (fail-closed), free-text-only complaint (excluded), duplicate structured keys, historical context flags.

## Assembly mode

Scenarios assemble with **`VocabularyEligibilityMode.DEMO`** because cardiology vocabulary terms are `approved_demo`. Production mode must continue to reject those terms (regression test included).

## Independence from clinical sources

Fixture assembly does **not** depend on AHA/ESC source metadata, license gates, or rule catalogs. No guideline-derived semantics.

## Provenance replay (technical)

Pipeline under test:

```text
SyntheticEncounterScenario → assemble_encounter_evaluation_context_with_snapshot
  → EncounterEvaluationContext + EvaluationContextSnapshotMetadata
```

Re-running assembly on an equivalent fixture must yield the same **semantic** `input_snapshot_id`. This is **input provenance replay**, not clinical outcome validation.

Future full evaluation provenance may also include `rule_manifest_hash`, engine version, and policy profile — not asserted in Phase 2H.

## Snapshot envelope

Metadata includes: `input_snapshot_id`, `context_schema_version`, `encounter_id`, `encounter_version`, `specialty_key`, optional vocabulary identity.

Must **not** include: rule manifests, diagnosis, probability, or recommendations.

## Known DTO gaps (unchanged in 2H)

Finding numeric/unit and onset on decision DTO, numeric question responses, etc. — see encounter assembly docs. Fixtures avoid unsupported fields for hash expectations.

## Future: clinical golden set

| Technical synthetic fixtures (2H) | Clinical golden set (later) |
|-----------------------------------|-----------------------------|
| Neutral keys, no clinical truth | Cardiologist-reviewed |
| No source section refs | Verified `section_ref` / recommendations |
| No expected alerts/differential | Structured expectation types (post-review) |
| Engineering replay tests | Safety FN/FP drills |

Transition requires: reviewer, review date, scope, version, limitations, and dual gates (license + clinical) per chest-pain governance docs.

## Related

- [`docs/encounter_evaluation_context_assembly.md`](encounter_evaluation_context_assembly.md)
- [`docs/evaluation_context_snapshot.md`](evaluation_context_snapshot.md)
- [`docs/cardiology_chest_pain_rule_pack_design.md`](cardiology_chest_pain_rule_pack_design.md) §34 (dual gates)
