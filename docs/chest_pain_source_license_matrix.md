# Chest Pain Pilot — Clinical Source & License Matrix (Phase 2F)

**Status:** Metadata-only verification · **No guideline body ingestion** · **No clinical rules**

Verified at catalog review: **2026-10-12** (product/legal review pending for commercial AI/CDS use).

## Usage policy (default deny)

| Allowed now | Not allowed now |
|-------------|-----------------|
| Source metadata in git | Full guideline text in repo |
| `source_id`, title, official URL | PDF storage / embedding |
| Future `section_ref` / `recommendation_id` if lawfully recorded | RAG / vector ingestion of copyrighted text |
| Citation to official publisher pages | Copying recommendation tables or long quotes |
| | Production CDS rules without license + clinical gates |

**License approval ≠ clinical approval.** Both gates remain independent before `approved_prod`.

## Source role separation (chest pain pilot)

| Source | Pilot role | Not interchangeable with |
|--------|------------|---------------------------|
| `guideline:aha-acc:chest-pain:2021` | Chest pain **evaluation / diagnostic workflow** framing | ACS management-only guidance |
| `guideline:esc:acs:2023` | **ACS-specific** evaluation/management evidence | Generic chest pain workup |
| `guideline:esc:htn:2024` | Hypertension only | Chest pain (do not cite as chest-pain evidence) |

## Matrix

| source_id | organization | document (year) | pilot role | official verified | license_status | commercial_use | AI/CDS use | content ingestion | permission path | clinical review |
|-----------|--------------|-----------------|------------|-------------------|----------------|----------------|------------|-------------------|-----------------|-----------------|
| `guideline:aha-acc:chest-pain:2021` | AHA/ACC (+ collaborating societies) | Evaluation & Diagnosis of Chest Pain (2021) | Primary chest-pain framing | Yes — [Circulation DOI](https://www.ahajournals.org/doi/10.1161/CIR.0000000000001029) | `permission_required` | `unknown` | `unknown` | **false** | Elsevier/ACC/AHA permissions workflow | `not_reviewed` |
| `guideline:esc:acs:2023` | ESC | ACS management (2023) | ACS-specific evidence | Yes — [ESC ACS hub](https://www.escardio.org/guidelines/clinical-practice-guidelines/all-esc-practice-guidelines/acute-coronary-syndromes/) · EHJ DOI 10.1093/eurheartj/ehad191 | `permission_required` | `permission_required` | `permission_required` | **false** | ESC formal licensing (AI/LLM/CDS/EHR/commercial); OUP permissions | `not_reviewed` |
| `guideline:esc:htn:2024` | ESC | Hypertension (2024) | **Out of chest-pain pack** (HTN) | Yes — ESC hypertension guideline page | `permission_required` | `permission_required` | `permission_required` | **false** | Same ESC licensing framework | `not_reviewed` |

## Web verification notes (official sources)

### AHA/ACC 2021 chest pain

- Joint ACC/AHA clinical practice guideline; published **2021** (Circulation **2021-10-28**; JACC co-publication).
- Copyright **AHA/ACC**; reproduction/modification requires publisher permission (see JACC permissions block on official PDF landing page).
- **No verified** commercial AI/CDS license → default deny for ingestion and automated rule encoding.

### ESC (ACS 2023, HTN 2024, and other ESC guidelines)

- ESC guideline page published **2023-08-25** (ACS); European Heart Journal **2023-10-07** (ACS).
- ESC/OUP copyright: personal/educational use only unless permission granted; reproduction and commercial deployment require authorization.
- ESC maintains a **formal licensing path** for **AI model / LLM development**, **clinical decision support (CDS)**, **EHR integration**, and **operational/commercial deployment** — granted terms may permit uses that are denied without a license.
- **This project:** **no ESC license obtained** → metadata uses `permission_required` (deny today; **not** “prohibited under all circumstances”).
- Catalog fields `ai_usage_status` / `commercial_usage_status` = `permission_required` express **licensable, default-deny** — distinct from `prohibited` (absolute bar) and from `licensed` / `allowed` after a signed grant.

### Turkish / national sources (Phase 2F search)

| Candidate | Result |
|-----------|--------|
| TKD guideline index | Lists **Turkish summaries** of ESC/AHA guidelines (e.g. 2021 chest pain, 2023 ACS); **not** a separate license-cleared national chest-pain guideline record for this repo |
| Sağlık Bakanlığı / 112 protocols | Legacy clinical protocol PDFs exist; **license/use for commercial AI not verified** — **not added** to catalog |
| TKD “KAH Vizyon” / algorithm documents | Operational algorithms referenced in summaries; **official standalone license for product ingestion not verified** — document only in this matrix |

**Turkish official source added to catalog:** **NO** (pending legal review of any national document).

## Future rule authoring gate (design)

Before production rule YAML:

1. `source_id` metadata present and `last_license_reviewed_at` current  
2. `license_status` permits intended use (ingestion + AI/CDS if applicable)  
3. `source_linked` + `clinical_review` completed  
4. No `approved_prod` without cardiologist approval  

**Phase 2G:** Rule-family → source roles and dual-gate checklist: [`docs/cardiology_chest_pain_rule_pack_design.md`](cardiology_chest_pain_rule_pack_design.md) §34.  
**Phase 2I:** Official section-level citation anchors: [`docs/chest_pain_verified_source_references.md`](chest_pain_verified_source_references.md). Lifecycle ceiling remains **`source_linked`** only.

## Schema (Phase 2F + pre-commit ESC semantics fix)

- `license_status` already included `permission_required`.
- **Additive enum values:** `ai_usage_status` and `commercial_usage_status` now allow `permission_required` so ESC **licensable / default-deny** is not mislabeled as `prohibited`.
- License gates treat `ai_usage_status=permission_required` as ingestion denial until clearance (operational deny unchanged).
- Optional future fields (`license_source_url`, `doi`) still **not added**.

## Active clinical rules

**Production active rules: 0** — no executable rule YAML added under `clinical_knowledge/rules/`.
