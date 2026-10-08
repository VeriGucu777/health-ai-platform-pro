"""Cardiology specialty stub tests."""

from __future__ import annotations

import ast
from pathlib import Path

from app.application.clinical_decision.specialty.cardiology_no_rule import CardiologyNoRuleSpecialtyModule
from app.domain.clinical_decision.constants import CARDIOLOGY_SPECIALTY_MODULE_STUB_VERSION
from app.domain.clinical_decision.models import EncounterEvaluationContext, PatientDemographicsInput
from app.domain.clinical_knowledge.enums import (
    ClinicalKnowledgeReviewStatus,
    ClinicalRuleSeverity,
    ClinicalRuleStatus,
    ClinicalRuleType,
)
from app.domain.clinical_knowledge.models import ClinicalRule, GuidelineRef
from datetime import UTC, datetime
from uuid import uuid4

from tests.support.memory_clinical_rule_catalog import MemoryClinicalRuleCatalog


def _context() -> EncounterEvaluationContext:
    return EncounterEvaluationContext(
        encounter_id=uuid4(),
        patient_id=uuid4(),
        organization_id=uuid4(),
        clinician_user_id=uuid4(),
        specialty_key="cardiology",
        locale="tr",
        patient_demographics=PatientDemographicsInput(),
        context_version="encounter_eval_context_v1",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


def test_cardiology_module_empty_catalog_zero_claims() -> None:
    module = CardiologyNoRuleSpecialtyModule()
    catalog = MemoryClinicalRuleCatalog()
    result = module.evaluate(_context(), catalog)
    assert result.differential_candidates == ()
    assert result.suggested_questions == ()
    assert result.missing_information == ()
    assert result.safety_alerts == ()


def test_cardiology_module_ignores_non_production_rules() -> None:
    draft_rule = ClinicalRule(
        rule_id="TEST-DRAFT-001",
        specialty_key="cardiology",
        topic_key="hypertension",
        rule_type=ClinicalRuleType.NEXT_BEST_QUESTION,
        status=ClinicalRuleStatus.DRAFT,
        rule_version="1.0.0",
        clinical_intent="test fixture",
        input_requirements=(),
        trigger_conditions={},
        exclusion_conditions={},
        output_definition={},
        severity=ClinicalRuleSeverity.INFO,
        priority=1,
        explanation_key="copilot.explanation.test",
        rationale_key="copilot.rationale.test",
        source_refs=("guideline:esc:htn:2024",),
        guideline_refs=(
            GuidelineRef(source_id="guideline:esc:htn:2024", section_ref="test"),
        ),
        evidence_refs=(),
        clinical_review_status=ClinicalKnowledgeReviewStatus.NOT_REVIEWED,
    )
    module = CardiologyNoRuleSpecialtyModule()
    catalog = MemoryClinicalRuleCatalog((draft_rule,))
    result = module.evaluate(_context(), catalog)
    assert result == module.evaluate(_context(), MemoryClinicalRuleCatalog())


def test_cardiology_module_metadata() -> None:
    module = CardiologyNoRuleSpecialtyModule()
    assert module.specialty_key == "cardiology"
    assert module.module_version == CARDIOLOGY_SPECIALTY_MODULE_STUB_VERSION


def test_cardiology_module_does_not_import_filesystem_knowledge() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    module_path = (
        repo_root / "app/application/clinical_decision/specialty/cardiology_no_rule.py"
    )
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    assert not any(
        mod.startswith("app.infrastructure.clinical_knowledge") for mod in imports
    )
