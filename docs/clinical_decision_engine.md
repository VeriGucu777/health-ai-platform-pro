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

`NoOpClinicalDecisionEngine` returns `evaluation_status=no_applicable_rules` with empty output arrays. It does **not** resolve specialty modules or read a rule catalog. It is **not** registered in FastAPI or `app.main` until a later phase.

## Orchestrator (Phase 0B.3)

`ClinicalDecisionOrchestrator`:

1. Validates/resolves the specialty via `SpecialtyDecisionModuleRegistry`
2. Requires an available `RuleCatalogView` (validated `ClinicalRuleCatalog` port only)
3. Delegates to a specialty module (e.g. `CardiologyNoRuleSpecialtyModule`)
4. Wraps a `SpecialtyEvaluationSlice` into `ClinicalDecisionEvaluationResult`

**Empty approved_prod rules:** `evaluation_status=no_applicable_rules` (valid state; not `unavailable`).

**Unsupported specialty:** `UnsupportedSpecialtyError` (no silent fallback to cardiology or NoOp).

**Catalog unavailable/corrupt:** `ClinicalDecisionEngineUnavailableError`.

**Draft policy profiles** (e.g. `tr-cardiology-pilot-v1`) are **not** presented as production-active; orchestrator emits `policy_profile_id=none` until a profile is explicitly production-active.

**Zero-clinical-claim guarantee:** With zero `approved_prod` rules, specialty modules return empty slices — no fake differentials, questions, or alerts.

## Specialty module boundary

Specialty modules consume **rules** via `ClinicalRuleCatalog`, not guideline PDFs or source YAML paths. Cardiology pack stubs may later add hypertension / ACS / CCS rule groups without new orchestrator logic.

## Outputs (MVP)

Only: differential **considerations**, suggested questions, missing information, safety alerts — all via i18n keys, with provenance for rule-derived items in future phases.

No probability, diagnosis confidence, medication, or reimbursement fields.
