# Chest Pain Pilot — Governance Status Dashboard

**Last updated:** 2026-10-12 (Phase 2J) · **Auto-sync:** manual — update when permission or review events occur.

## Dual gates

| Gate | Status | Notes |
|------|--------|--------|
| **A — License / copyright / AI-CDS permission** | **CLOSED** | AHA & ESC: `permission_required`; no written license |
| **B — Cardiologist clinical review** | **CLOSED** | **PENDING** — no completed review record |

**License approval ≠ clinical approval.** Both required before executable clinical rules beyond `source_linked`.

**Lifecycle ceiling for rules:** `source_linked` (no `license_cleared`, no `approved_demo` / `approved_prod`).

## Artifact status

| Item | Status |
|------|--------|
| Source metadata (catalog) | **COMPLETE** |
| Section-level references | **VERIFIED (TOC)** — recommendation rows **TO_VERIFY** |
| AHA permission request | **NOT_SUBMITTED** |
| ESC license request | **NOT_SUBMITTED** |
| Cardiologist review pack | **READY** (workshop not held) |
| Cardiologist review record | **NONE** |
| Vocabulary production approval | **0** terms (`approved_demo` only) |
| Clinical rules | **0** |
| Rule YAML files | **0** |
| Active production rules | **0** |

## Source permission snapshot (catalog — unchanged by 2J docs)

| Source | `license_status` | AI/CDS | Commercial | Ingestion |
|--------|------------------|--------|------------|-----------|
| `guideline:aha-acc:chest-pain:2021` | `permission_required` | `unknown` | `unknown` | **false** |
| `guideline:esc:acs:2023` | `permission_required` | `permission_required` | `permission_required` | **false** |

Project holds: **NO** ESC license · **NO** verified AHA AI/CDS permission.

## Go / no-go — rule implementation

**NO-GO** while **any** of:

- Intended use **not permitted in writing** for the material scope needed  
- **Cardiologist review** not completed for the rule scope  
- **Exact** rule-level source reference not verified (section + recommendation row where applicable)  

**Future GO (demo rule authoring)** requires at minimum:

1. Source metadata verified  
2. Exact reference verified for each rule  
3. Intended use permitted for rule derivation + CDS display  
4. Clinician review completed with documented outcome  
5. Rule design reviewed against safety/wording feedback  

**Production (`approved_prod`)** requires additional validation beyond this checklist.

## Document index

| Document | Purpose |
|----------|---------|
| [`clinical_source_permission_tracker.md`](clinical_source_permission_tracker.md) | Permission fields & decision log |
| [`permission_requests/esc_ai_cds_license_request.md`](permission_requests/esc_ai_cds_license_request.md) | ESC draft |
| [`permission_requests/aha_acc_guideline_permission_request.md`](permission_requests/aha_acc_guideline_permission_request.md) | AHA draft |
| [`cardiology_chest_pain_clinician_review_pack.md`](cardiology_chest_pain_clinician_review_pack.md) | Workshop pack |
| [`reviews/cardiology_review_record_template.md`](reviews/cardiology_review_record_template.md) | Review record |
| [`chest_pain_verified_source_references.md`](chest_pain_verified_source_references.md) | Section anchors |
| [`cardiology_chest_pain_rule_pack_design.md`](cardiology_chest_pain_rule_pack_design.md) | Rule pack design |

## Outreach drafts

Email/message drafts live inside the permission request docs and the clinician review pack (workshop invitation). **Nothing sent** in Phase 2J.
