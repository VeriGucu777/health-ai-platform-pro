# Hypertension Pilot — Governance Status Dashboard

**Last updated:** 2026-10-16 (ESC HTN operational permission docs) · **Pilot priority:** **PRIMARY (#1)**

## Clinician governance (separate from license)

| Status | Value |
|--------|--------|
| Product-direction review | **RECEIVED** ([`reviews/cardiology_hypertension_direction_review_2026-10.md`](reviews/cardiology_hypertension_direction_review_2026-10.md)) |
| Clinical rule review | **NOT STARTED** |
| Rule / threshold / treatment approval | **NONE** |
| Vocabulary clinical approval | **NOT STARTED** (`approved_demo` only in catalog) |

## Dual gates (clinical rules)

| Gate | Status | Notes |
|------|--------|--------|
| **A — License / AI-CDS** | **CLOSED** | ESC HTN metadata: `permission_required`; ingestion **false** |
| **B — Clinical review** | **CLOSED** | Direction ≠ rule sign-off |

**Lifecycle ceiling for rules:** `source_linked` (no production rules).

## Artifact status

| Item | Status |
|------|--------|
| Pilot design doc | [`cardiology_hypertension_pilot_design.md`](cardiology_hypertension_pilot_design.md) `v0.1.0-design` |
| Source metadata | **VERIFIED_METADATA (H2)** — ESC HTN 2024 in catalog; ACC/AHA 2025 + TKD 2025 documented in matrix (**not** in catalog yet) |
| Source verification doc | [`hypertension_source_license_matrix.md`](hypertension_source_license_matrix.md) |
| Section-level verified refs (HTN) | **NOT STARTED** — all recommendation anchors **TO_VERIFY** |
| Permission drafts | ESC HTN: **APPLICATION SUBMITTED — RESPONSE PENDING**; ACC/AHA HTN (**NOT SUBMITTED**) |
| Clinical rules | **0** |
| Rule YAML | **0** |
| Active production rules | **0** |

## Source & permission (operational notes)

| Source | Catalog | Permission (operational) |
|--------|---------|---------------------------|
| `guideline:esc:htn:2024` | `permission_required`, ingestion **false** | **APPLICATION SUBMITTED — RESPONSE PENDING** — permission **not granted**; catalog unchanged; draft pack [`permission_requests/esc_hypertension_ai_cds_license_request.md`](permission_requests/esc_hypertension_ai_cds_license_request.md) |
| `guideline:esc:acs:2023` | Chest-pain / deferred pilot | **SUBMITTED / PENDING** (ACS only — **does not cover HTN**) |
| ACC/AHA HTN **2025** | **Not in catalog** (proposed `guideline:aha-acc:hypertension:2025`) | **NOT_SUBMITTED** — verified official source H2 |
| TKD Hipertansiyon Uzlaşı **2025** | **Not in catalog** | **UNKNOWN** license — national candidate only |

Update operational permission in [`clinical_source_permission_tracker.md`](clinical_source_permission_tracker.md) decision log when responses arrive. **Do not** change catalog YAML without written terms.

**ESC HTN 2024 operational note:** Permission requested **YES**; permission granted **NO / PENDING**; `content_ingestion_allowed` **NO**; production clinical rules / `approved_prod` **BLOCKED** until written ESC response. Submission date/status reflects operational tracking supplied by the project owner. Written permission has not yet been received.

## Product requirements captured

| Requirement | Status |
|-------------|--------|
| Alert-fatigue control | **DOCUMENTED** (no engine) |
| Existing internal record reuse | **DOCUMENTED** |
| Medication interactions | **FUTURE MODULE** — no drug DB |
| No autonomous diagnosis | **DOCUMENTED** |

## Go / no-go (hypertension rules)

**NO-GO** until license + clinician rule review + verified references + tests (same stack as chest-pain governance).

## Related

| Document | Role |
|----------|------|
| [`chest_pain_governance_status.md`](chest_pain_governance_status.md) | Deferred pilot #2 |
| [`hypertension_clinician_followup_questions.md`](hypertension_clinician_followup_questions.md) | Follow-up workshop |
| [`hypertension_vocabulary_review.md`](hypertension_vocabulary_review.md) | H1 vocabulary plan |
| [`hypertension_source_license_matrix.md`](hypertension_source_license_matrix.md) | H2 source/license matrix |
