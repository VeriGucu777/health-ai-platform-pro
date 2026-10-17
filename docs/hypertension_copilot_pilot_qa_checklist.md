# Hypertension Clinical Copilot — Pilot QA Checklist (Technical)

Synthetic data only. No clinical rules active in pilot. Use PASS / FAIL / NOT TESTED for each item.

## A. Login

| Item | Result |
|------|--------|
| Clinician can sign in with valid credentials | NOT TESTED |
| Invalid credentials rejected | NOT TESTED |

## B. Patient access

| Item | Result |
|------|--------|
| Assigned clinician opens authorized patient | NOT TESTED |
| Unassigned or cross-org patient returns masked not-found | NOT TESTED |

## C. Encounter

| Item | Result |
|------|--------|
| Active cardiology encounter visible on patient | NOT TESTED |
| Encounter detail loads without error | NOT TESTED |

## D. Evaluate

| Item | Result |
|------|--------|
| Clinical Copilot panel visible on encounter detail | NOT TESTED |
| Disclaimer visible before evaluate | NOT TESTED |
| Evaluate action available on active encounter | NOT TESTED |
| Loading state shown during evaluate | NOT TESTED |
| Evaluate completes with HTTP success | NOT TESTED |

## E. Safe empty result

| Item | Result |
|------|--------|
| Neutral no-active-rules message shown after success | NOT TESTED |
| No diagnosis or treatment language in UI | NOT TESTED |
| Duplicate evaluate clicks blocked while in flight | NOT TESTED |

## F. Provenance

| Item | Result |
|------|--------|
| Response includes snapshot / provenance metadata (API or UI as designed) | NOT TESTED |
| `context_profile` is hypertension_v1 | NOT TESTED |

## G. Audit

| Item | Result |
|------|--------|
| Copilot evaluation requested audit recorded | NOT TESTED |
| Copilot evaluation succeeded audit recorded | NOT TESTED |

## H. Cross-org isolation

| Item | Result |
|------|--------|
| Other organization cannot evaluate foreign encounter (404 mask) | NOT TESTED |

## I. Finalized encounter

| Item | Result |
|------|--------|
| Finalized encounter: evaluate disabled or read-only per product rules | NOT TESTED |
| Write workspace read-only on finalized encounter | NOT TESTED |

## J. Error state

| Item | Result |
|------|--------|
| Evaluate failure shows generic safe message (no stack trace) | NOT TESTED |
| Retry possible after transient error | NOT TESTED |

## K. TR/EN UI

| Item | Result |
|------|--------|
| Turkish locale: copilot strings fully Turkish | NOT TESTED |
| English locale: copilot strings fully English | NOT TESTED |

## L. No clinical claims

| Item | Result |
|------|--------|
| No medication, staging, or treatment recommendations displayed | NOT TESTED |
| Disclaimer states decision-support only | NOT TESTED |

---

**Notes:** Automated backend pilot QA covers evaluate, provenance, audit, and zero production rules via pytest. Frontend panel behavior covered by component tests. Mark manual rows after staging walkthrough.
