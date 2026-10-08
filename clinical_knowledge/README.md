# Clinical Knowledge Catalog

Git-versioned **metadata and rule contracts** for AI Clinical Copilot. This is not patient data and must never contain PHI, secrets, or copyrighted full-text guideline bodies.

## Five-layer model

1. **SOURCE** — Registry metadata (guidelines, articles, etc.)
2. **RULE** — Clinician-structured, source-linked decision rules
3. **ENGINE** — Executes approved rules (not wired in Phase 0B.1)
4. **OUTPUT** — Differential / NBQ / alerts shown to clinicians
5. **CLINICIAN DECISION** — Overrides and final judgment (future encounter module)

## Metadata ≠ content

Files under `sources/` hold **bibliographic and license metadata only**. Do not paste guideline PDF text, NEJM/Harrison excerpts, or bulk PubMed content here.

## Default-deny licensing

Unless formally verified, sources use `license_status: unknown` and `content_ingestion_allowed: false`. Ingestion into embeddings, RAG corpora, or training sets requires explicit license clearance in the registry.

## Current pilot state (Phase 0B.1–0B.4)

- One metadata stub: **2024 ESC hypertension guideline** (`guideline:esc:htn:2024`)
- **No active clinical rules** under `rules/cardiology/` (zero `approved_prod`)
- Draft policy profile: `tr-cardiology-pilot-v1` (inactive, not a production-active profile)

## Validated filesystem catalog provider (Phase 0B.4)

Load pipeline (read-only, **fail-closed**):

1. Resolve repository `clinical_knowledge/` root (trusted paths only; no traversal outside root)
2. `DefaultRuleCatalogValidator` — schema, duplicates, license gates, cross-refs, prod approval metadata
3. On any validation issue → **no** production catalog view (no skip-warnings, no partial prod pack)
4. Load source and rule manifests (`yaml.safe_load` only; `.yaml` / `.yml` allowlist)
5. Build `ValidatedProductionRuleCatalog` with injectable `reference_at` for effective dates
6. Expose `RuleCatalogView` via `ValidatedFilesystemClinicalRuleCatalogProvider` (tests only — **not wired** to FastAPI or `app.main`)

**Production vs demo:** `list_active_production_rules(specialty)` returns only rules that pass strict `approved_prod` eligibility (status, clinical approval, verified source licenses, effective window). `approved_demo` and `draft` rules never appear in production lists.

**Manifest hash:** SHA-256 over a canonical JSON payload. Empty production set uses fixed sentinel `approved_prod_rules:v1:empty` (cross-platform; sorted rule order for non-empty sets).

**Filesystem safety:** Manifest paths must stay under `clinical_knowledge/`; symlink escapes are rejected when loading with `knowledge_root` checks.

## Validation

From repository root:

```powershell
python scripts/validate_clinical_knowledge.py
```

Or pytest:

```powershell
pytest tests/unit/clinical_knowledge -v
```

The validator checks JSON Schema, duplicate IDs, license invariants, cross-references, lifecycle constraints, and production approval metadata (via test fixtures).

## Future rule lifecycle (summary)

`draft` → `source_linked` → `license_cleared` → `clinical_review` → `approved_demo` → `approved_prod` → `deprecated` → `retired`

Only `approved_prod` rules may ship in production rule packs after clinical, technical, and license validation.
