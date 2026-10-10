# Cardiology Controlled Vocabulary (Phase 2A)

## Purpose

This catalog defines **stable machine keys** for structured cardiology documentation and future Clinical Copilot inputs. It answers:

> Which clinical concept maps to which stable identifier?

It does **not** answer:

> If this finding is present, what diagnosis or action applies?

That separation is intentional:

| Layer | Responsibility |
|--------|----------------|
| **Vocabulary** | Structured input terminology |
| **Clinical rule** | Source-linked interpretation logic |
| **Engine** | Evaluation orchestration |
| **Output** | Clinician-facing decision support (future) |

## Location

- Manifest: `clinical_knowledge/vocabularies/cardiology/cardiology_v1.0.0.yaml`
- JSON Schema: `clinical_knowledge/schemas/controlled_vocabulary_manifest.schema.json`
- Registry port: `ClinicalVocabularyRegistry` (read-only, filesystem-backed)

Vocabulary files live under `clinical_knowledge/` for shared validation tooling but are **not** clinical rules and must not be edited alongside rule YAML as if they were rules.

## Key naming convention

Format:

```text
card.{category}.{snake_case_term}
```

Rules:

- lowercase ASCII
- `snake_case`
- language-neutral (never Turkish/English display text as keys)
- stable across releases; use deprecation + `replacement_key` instead of silent renames

Categories: `complaint`, `finding`, `question`, `answer_code`, `vital`, `unit`, `onset`.

## Versioning

- Manifest field: `vocabulary_version` (semver, e.g. `1.0.0`)
- Persisted encounter data, audit replay, and future engine snapshots should record vocabulary version + manifest hash.

## Lifecycle statuses

Term `status`:

- `draft`, `review_pending`, `approved_demo`, `approved_prod`, `deprecated`, `retired`

`engine_safe` is **true** only when `status == approved_prod` **and** `clinical_review_status == clinically_approved`.

Current pilot terms are `approved_demo` with `proposed_by_product` — **not** doctor-approved for production engine use.

## Clinical review

Fields support future governance:

- `clinical_review_status` per term
- manifest-level `manifest_clinical_review_status`

Do not mark items `clinically_approved` without an actual cardiologist review record.

## Negation invariant

Use the same concept key with domain `negated=true` on complaints/findings.

Do **not** create separate keys such as `card.finding.no_chest_pain`.

No NLP, fuzzy matching, or LLM mapping from free text to keys in this phase.

## Synonyms

Optional `synonyms.en` / `synonyms.tr` are human reference only (UI search / authoring). They are **not** auto-applied to encounter text.

## Localization

- Machine keys are language-neutral.
- `labels.en` / `labels.tr` provide display strings for future UI.
- `display_key` is an i18n hook for frontend integration (not wired in Phase 2A).

## Units and vitals

Vital keys (e.g. `card.vital.systolic_blood_pressure`) reference unit keys (e.g. `card.unit.mm_hg`) via `default_unit_key`.

No normal ranges, thresholds, or interpretation are encoded.

## Deprecation

Never silently delete keys. Set:

- `status: deprecated`
- `replacement_key: card....`

Historical encounters remain valid.

## Manifest hash

SHA-256 over canonical JSON (`controlled_vocab:v1:{id}:{version}:...`) with terms sorted by `key`. See `vocabulary_manifest_hash()`.

## Validation

```powershell
python scripts/validate_clinical_vocabulary.py
pytest tests/unit/clinical_vocabulary -v
```

## Pilot scope disclaimer

The initial cardiology set is **minimal** (35 terms in v1.0.0) for MVP scaffolding. It is **not** clinically complete.

## Open questions for cardiologist review

- Which complaints belong in the first selectable list for Turkish cardiology practice?
- Which history/risk factors should be structured vs free text in pilot?
- Which question keys match the first-visit workflow (without implying triage priority)?
- Which vitals are mandatory for the pilot clinic?
- Preferred clinician-facing Turkish labels vs internal `display_key` mapping?
- Are onset codes (`acute`, `subacute`, `chronic`, `unknown`) sufficient for pilot documentation?

## Copyright / external coding systems

No SNOMED CT, LOINC, or ICD bulk imports. Optional future fields: `external_system`, `external_code` (currently unused).

## Not in Phase 2A

- Engine evaluate wiring
- Encounter API validation against vocabulary
- Frontend dropdowns from vocabulary
- Database persistence
- NLP / LLM terminology inference
