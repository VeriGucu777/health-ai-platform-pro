# Clinical Decision Engine (Phase 0B.2)

## Clinical Knowledge ≠ Clinical Decision Engine

| Layer | Role |
|-------|------|
| **Clinical Knowledge** | Source metadata, rule YAML, license gates, validation (`clinical_knowledge/`) |
| **Clinical Decision Engine** | Runs **approved** rules against structured encounter input; produces decision-support outputs |

The engine **does not**:

- Read guideline PDFs or ingest copyrighted text
- Call LLM or RAG
- Issue diagnoses, prescriptions, or treatment orders
- Access the database, HTTP APIs, or the filesystem
- Write audit records (identifiers are carried on results for a future recorder)

## Version fields (do not conflate)

| Field | Meaning |
|-------|---------|
| `engine_version` | Engine implementation (e.g. `noop_clinical_decision_v1`) |
| `specialty_module_version` | Specialty rule module (e.g. cardiology pack); `none` for NoOp |
| `policy_profile_id` / `policy_profile_version` | Deployment-approved guideline conflict policy |
| `rule_version` | Per-rule semver in the knowledge catalog |
| `rule_set_manifest_hash` | Hash of loaded rule manifest; `empty` when no active pack |

## NoOp engine

`NoOpClinicalDecisionEngine` returns `evaluation_status=no_applicable_rules` with empty output arrays. It is **not** registered in FastAPI or `app.main` until a later phase.

## Outputs (MVP)

Only: differential **considerations**, suggested questions, missing information, safety alerts — all via i18n keys, with provenance for rule-derived items in future phases.

No probability, diagnosis confidence, medication, or reimbursement fields.
