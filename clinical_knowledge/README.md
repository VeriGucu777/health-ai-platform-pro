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

## Current pilot state (Phase 0B.1)

- One metadata stub: **2024 ESC hypertension guideline** (`guideline:esc:htn:2024`)
- **No active clinical rules** under `rules/cardiology/`
- Draft policy profile: `tr-cardiology-pilot-v1` (inactive, no rule set)

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
