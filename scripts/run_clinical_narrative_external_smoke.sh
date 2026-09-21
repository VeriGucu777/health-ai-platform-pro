#!/usr/bin/env bash
# Live external clinical narrative smoke (synthetic evidence only — no real PHI).
set -euo pipefail

cd "$(dirname "$0")/.."

if [[ "${CLINICAL_NARRATIVE_LIVE_SMOKE:-}" != "1" ]]; then
  echo "Set CLINICAL_NARRATIVE_LIVE_SMOKE=1 to run live external provider smoke." >&2
  exit 2
fi

for var in CLINICAL_NARRATIVE_EXTERNAL_BASE_URL CLINICAL_NARRATIVE_EXTERNAL_API_KEY CLINICAL_NARRATIVE_EXTERNAL_MODEL; do
  if [[ -z "${!var:-}" ]]; then
    echo "Missing required env: ${var}" >&2
    exit 2
  fi
done

export CLINICAL_NARRATIVE_PROVIDER=external
pytest tests/integration/narrative/test_external_narrative_live_smoke.py -v -m external_narrative_live
