"""Unit tests for rule-based diabetes risk model v1."""

from decimal import Decimal

from app.application.models.rule_based_diabetes_risk_model_v1 import (
    FORBIDDEN_RECOMMENDATION_TERMS,
    RuleBasedDiabetesRiskModelV1,
)
from app.core.reference_ranges import DIABETES_RISK_DISCLAIMER
from app.domain.interfaces.diabetes_risk_model import DiabetesRiskFeatureVector


def _features(**overrides) -> DiabetesRiskFeatureVector:
    base = {
        "age_years": 35,
        "gender": "male",
        "measurement_count": 1,
        "latest_fasting_glucose": Decimal("95"),
        "latest_non_fasting_glucose": None,
        "average_systolic_pressure": Decimal("115"),
        "structured_medical_record_types": (),
    }
    base.update(overrides)
    return DiabetesRiskFeatureVector(**base)


def test_model_version_is_rule_based_v1() -> None:
    model = RuleBasedDiabetesRiskModelV1()
    assert model.model_version == "rule_based_v1"


def test_insufficient_data_when_glucose_missing() -> None:
    result = RuleBasedDiabetesRiskModelV1().assess(
        _features(
            latest_fasting_glucose=None,
            latest_non_fasting_glucose=None,
            measurement_count=0,
        )
    )

    assert result.assessment_status == "insufficient_data"
    assert result.risk_level is None
    assert result.score is None
    assert result.probability is None


def test_low_risk_for_normal_fasting_glucose() -> None:
    result = RuleBasedDiabetesRiskModelV1().assess(_features(latest_fasting_glucose=Decimal("92")))

    assert result.assessment_status == "completed"
    assert result.risk_level == "low"
    assert result.score is not None
    assert result.score < 34


def test_moderate_risk_for_warning_range_fasting_glucose() -> None:
    result = RuleBasedDiabetesRiskModelV1().assess(_features(latest_fasting_glucose=Decimal("110")))

    assert result.assessment_status == "completed"
    assert result.risk_level == "moderate"
    assert result.score is not None
    assert 34 <= result.score < 67


def test_elevated_risk_for_high_glucose_and_older_age() -> None:
    result = RuleBasedDiabetesRiskModelV1().assess(
        _features(
            age_years=62,
            latest_fasting_glucose=Decimal("130"),
            average_systolic_pressure=Decimal("132"),
        )
    )

    assert result.assessment_status == "completed"
    assert result.risk_level == "elevated"
    assert result.score is not None
    assert result.score >= 67


def test_contributing_factors_are_traceable_to_inputs() -> None:
    result = RuleBasedDiabetesRiskModelV1().assess(
        _features(structured_medical_record_types=("lab_result",))
    )

    sources = {factor.source for factor in result.contributing_factors}
    assert "health_measurement" in sources
    assert "patient" in sources
    assert "medical_record" in sources


def test_recommendations_avoid_prescriptive_language() -> None:
    result = RuleBasedDiabetesRiskModelV1().assess(_features(latest_fasting_glucose=Decimal("130")))

    for recommendation in result.recommendations:
        lowered = recommendation.message.lower()
        assert not any(term in lowered for term in FORBIDDEN_RECOMMENDATION_TERMS)


def test_mandatory_disclaimer_constant_present() -> None:
    assert "not a medical diagnosis" in DIABETES_RISK_DISCLAIMER
    assert "medication or treatment advice" in DIABETES_RISK_DISCLAIMER
