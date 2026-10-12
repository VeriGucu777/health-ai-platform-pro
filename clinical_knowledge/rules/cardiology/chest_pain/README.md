# Chest pain rule pack (design only — Phase 2B + 2G)

**No clinical rule YAML in this directory.** Active production rules: **zero**.

## Verified source linkage (Phase 2G)

| `source_id` | Role in chest-pain pack |
|-------------|-------------------------|
| `guideline:aha-acc:chest-pain:2021` | **Primary** — chest-pain evaluation / diagnostic workflow framing |
| `guideline:esc:acs:2023` | **Secondary (ACS-scoped)** — ACS-specific evidence; not generic chest pain |
| `guideline:esc:htn:2024` | **Out of scope** for this pack (hypertension module only) |

Registry metadata: `clinical_knowledge/sources/`. License matrix: [`docs/chest_pain_source_license_matrix.md`](../../../../docs/chest_pain_source_license_matrix.md).

## Dual gates (both must pass for clinical rules)

| Gate | Status | Meaning |
|------|--------|---------|
| **A — License / usage** | **CLOSED** | No AHA/ESC clearance for ingestion or AI/CDS rule encoding; default deny |
| **B — Clinical review** | **CLOSED** | No cardiologist review record |

License clearance does **not** imply clinical correctness. Clinical approval does **not** imply copyright/license clearance.

## Lifecycle ceiling (this pack)

Maximum status for any future rule in this pack until gates open: **`source_linked`** (catalog enum). Do not promote to `license_cleared`, `clinical_review`, `approved_demo`, or `approved_prod` without documented gate passage.

## Citations (future rules)

- `guideline_refs[].section_ref` must be **`TO_VERIFY`** until officially verified — do not invent section/table/recommendation IDs.
- See [`docs/cardiology_chest_pain_rule_pack_design.md`](../../../../docs/cardiology_chest_pain_rule_pack_design.md) §34 (Phase 2G) for rule-family → source matrix and review templates.

**Design version:** `cardiology-chest-pain-v0.1.1-design`

Do not add executable rule manifests here until clinical governance and licensing allow implementation.
