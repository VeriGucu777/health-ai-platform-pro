"""Unit tests for rule-based heart disease risk model v1."""

from decimal import Decimal

from app.application.models.rule_based_heart_disease_risk_model_v1 import (
    FORBIDDEN_RECOMMENDATION_TERMS,
    RuleBasedHeartDiseaseRiskModelV1,
)
from app.core.reference_ranges import HEART_DISEASE_RISK_DISCLAIMER
from app.domain.interfaces.heart_disease_risk_model import HeartDiseaseRiskFeatureVector


def _features(**overrides) -> HeartDiseaseRiskFeatureVector:
    base = {
        "age_years": 35,
        "gender": "male",
        "measurement_count": 1,
        "average_systolic_pressure": Decimal("115"),
        "average_diastolic_pressure": Decimal("75"),
        "average_heart_rate": Decimal("72"),
        "structured_medical_record_types": (),
        "cardiovascular_history_record_types": (),
    }
    base.update(overrides)
    return HeartDiseaseRiskFeatureVector(**base)


def test_model_version_is_heart_rule_based_v1() -> None:
    assert RuleBasedHeartDiseaseRiskModelV1().model_version == "heart_rule_based_v1"


def test_insufficient_data_without_blood_pressure() -> None:
    result = RuleBasedHeartDiseaseRiskModelV1().assess(
        _features(average_systolic_pressure=None, average_diastolic_pressure=None)
    )

    assert result.assessment_status == "insufficient_data"
    assert result.score is None
    assert result.probability is None


def test_low_risk_for_normal_blood_pressure() -> None:
    result = RuleBasedHeartDiseaseRiskModelV1().assess(
        _features(
            average_systolic_pressure=Decimal("110"),
            average_diastolic_pressure=Decimal("70"),
            average_heart_rate=Decimal("68"),
        )
    )

    assert result.assessment_status == "completed"
    assert result.risk_level == "low"


def test_moderate_risk_for_elevated_systolic_pressure() -> None:
    result = RuleBasedHeartDiseaseRiskModelV1().assess(
        _features(
            average_systolic_pressure=Decimal("130"),
            average_diastolic_pressure=Decimal("82"),
        )
    )

    assert result.assessment_status == "completed"
    assert result.risk_level == "moderate"


def test_elevated_risk_for_high_blood_pressure_and_older_age() -> None:
    result = RuleBasedHeartDiseaseRiskModelV1().assess(
        _features(
            age_years=66,
            average_systolic_pressure=Decimal("145"),
            average_diastolic_pressure=Decimal("92"),
            average_heart_rate=Decimal("105"),
        )
    )

    assert result.assessment_status == "completed"
    assert result.risk_level == "elevated"


def test_mandatory_disclaimer_constant_present() -> None:
    assert "not a medical diagnosis" in HEART_DISEASE_RISK_DISCLAIMER
    assert "medication or treatment advice" in HEART_DISEASE_RISK_DISCLAIMER


def test_recommendations_avoid_prescriptive_language() -> None:
    result = RuleBasedHeartDiseaseRiskModelV1().assess(
        _features(average_systolic_pressure=Decimal("145"), average_diastolic_pressure=Decimal("92"))
    )

    for recommendation in result.recommendations:
        lowered = recommendation.message.lower()
        assert not any(term in lowered for term in FORBIDDEN_RECOMMENDATION_TERMS)
