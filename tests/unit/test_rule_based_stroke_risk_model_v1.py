"""Unit tests for rule-based stroke risk model v1."""

from decimal import Decimal

from app.application.models.rule_based_stroke_risk_model_v1 import (
    FORBIDDEN_RECOMMENDATION_TERMS,
    RuleBasedStrokeRiskModelV1,
)
from app.core.reference_ranges import STROKE_RISK_DISCLAIMER
from app.domain.interfaces.stroke_risk_model import StrokeRiskFeatureVector


def _features(**overrides) -> StrokeRiskFeatureVector:
    base = {
        "age_years": 35,
        "gender": "male",
        "measurement_count": 1,
        "average_systolic_pressure": Decimal("115"),
        "average_diastolic_pressure": Decimal("75"),
        "latest_fasting_glucose": Decimal("95"),
        "latest_non_fasting_glucose": None,
        "structured_medical_record_types": (),
        "stroke_history_record_types": (),
    }
    base.update(overrides)
    return StrokeRiskFeatureVector(**base)


def test_model_version_is_stroke_rule_based_v1() -> None:
    assert RuleBasedStrokeRiskModelV1().model_version == "stroke_rule_based_v1"


def test_insufficient_data_without_glucose() -> None:
    result = RuleBasedStrokeRiskModelV1().assess(
        _features(latest_fasting_glucose=None, latest_non_fasting_glucose=None)
    )

    assert result.assessment_status == "insufficient_data"
    assert result.score is None
    assert result.probability is None


def test_low_risk_for_normal_inputs() -> None:
    result = RuleBasedStrokeRiskModelV1().assess(_features())

    assert result.assessment_status == "completed"
    assert result.risk_level == "low"


def test_moderate_risk_for_warning_glucose_and_pressure() -> None:
    result = RuleBasedStrokeRiskModelV1().assess(
        _features(
            latest_fasting_glucose=Decimal("110"),
            average_systolic_pressure=Decimal("128"),
        )
    )

    assert result.assessment_status == "completed"
    assert result.risk_level == "moderate"


def test_elevated_risk_for_high_glucose_older_age_and_stroke_history() -> None:
    result = RuleBasedStrokeRiskModelV1().assess(
        _features(
            age_years=72,
            latest_fasting_glucose=Decimal("130"),
            average_systolic_pressure=Decimal("145"),
            average_diastolic_pressure=Decimal("92"),
            stroke_history_record_types=("stroke_history",),
        )
    )

    assert result.assessment_status == "completed"
    assert result.risk_level == "elevated"


def test_mandatory_disclaimer_constant_present() -> None:
    assert "not a medical diagnosis" in STROKE_RISK_DISCLAIMER
    assert "medication or treatment advice" in STROKE_RISK_DISCLAIMER


def test_recommendations_avoid_prescriptive_language() -> None:
    result = RuleBasedStrokeRiskModelV1().assess(
        _features(latest_fasting_glucose=Decimal("130"), average_systolic_pressure=Decimal("145"))
    )

    for recommendation in result.recommendations:
        lowered = recommendation.message.lower()
        assert not any(term in lowered for term in FORBIDDEN_RECOMMENDATION_TERMS)
