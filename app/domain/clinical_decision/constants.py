"""Version identifiers for clinical decision evaluation (distinct from rule/source versions)."""

# Engine implementation identity (NoOp in Phase 0B.2).
NOOP_ENGINE_VERSION = "noop_clinical_decision_v1"

# No specialty module loaded.
SPECIALTY_MODULE_VERSION_NONE = "none"

# Policy profile placeholders when no active profile is bound.
POLICY_PROFILE_ID_NONE = "none"
POLICY_PROFILE_VERSION_NONE = "0.0.0"

# Rule catalog manifest hash when no production rule pack is active.
RULE_SET_MANIFEST_HASH_EMPTY = "empty"

# Context contract version for forward-compatible snapshots.
ENCOUNTER_EVALUATION_CONTEXT_VERSION = "encounter_eval_context_v1"
