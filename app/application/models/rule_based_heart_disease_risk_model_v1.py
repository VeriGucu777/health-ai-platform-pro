"""Rule-based heart disease risk model v1."""

from __future__ import annotations

from decimal import Decimal

from app.application.analytics.heart_disease_risk_assessment import (
    detect_missing_inputs,
    has_minimum_required_inputs,
)
from app.core.reference_ranges import (
    DIASTOLIC_PRESSURE_THRESHOLDS,
    RESTING_HEART_RATE_THRESHOLDS,
    RISK_ELEVATED_SCORE_MIN,
    RISK_MODERATE_SCORE_MIN,
    SYSTOLIC_PRESSURE_THRESHOLDS,
)
from app.domain.interfaces.heart_disease_risk_model import (
    ContributingFactorItem,
    HeartDiseaseRiskFeatureVector,
    HeartDiseaseRiskModelPort,
    HeartDiseaseRiskModelResult,
    HeartDiseaseRiskRecommendationItem,
    RiskLevel,
)

MODEL_VERSION = "heart_rule_based_v1"

FORBIDDEN_RECOMMENDATION_TERMS = (
    "prescribe",
    "medication",
    "dosage",
    "diagnosis",
    "heart attack",
    "start taking",
    "statin",
)


class RuleBasedHeartDiseaseRiskModelV1(HeartDiseaseRiskModelPort):
    """Deterministic, explainable heart disease risk scoring for v1."""

    @property
    def model_version(self) -> str:
        return MODEL_VERSION

    def assess(self, features: HeartDiseaseRiskFeatureVector) -> HeartDiseaseRiskModelResult:
        missing_inputs = tuple(detect_missing_inputs(features))

        if not has_minimum_required_inputs(features):
            return HeartDiseaseRiskModelResult(
                assessment_status="insufficient_data",
                risk_level=None,
                score=None,
                probability=None,
                contributing_factors=(),
                missing_inputs=missing_inputs,
                recommendations=(
                    HeartDiseaseRiskRecommendationItem(
                        category="tracking",
                        message=(
                            "Add paired blood pressure measurements and heart rate readings "
                            "to enable an informational heart disease risk assessment."
                        ),
                        related_metrics=("systolic_pressure", "diastolic_pressure", "heart_rate"),
                    ),
                ),
            )

        factors: list[ContributingFactorItem] = []
        score = 0.0

        age_points, age_factor = self._evaluate_age(features.age_years)
        score += age_points
        factors.append(age_factor)

        gender_points, gender_factor = self._evaluate_gender(features.gender, features.age_years)
        score += gender_points
        factors.append(gender_factor)

        systolic_points, systolic_factor = self._evaluate_systolic(features.average_systolic_pressure)
        score += systolic_points
        factors.append(systolic_factor)

        diastolic_points, diastolic_factor = self._evaluate_diastolic(
            features.average_diastolic_pressure
        )
        score += diastolic_points
        factors.append(diastolic_factor)

        if features.average_heart_rate is not None:
            heart_rate_points, heart_rate_factor = self._evaluate_heart_rate(features.average_heart_rate)
            score += heart_rate_points
            factors.append(heart_rate_factor)

        for record_type in features.cardiovascular_history_record_types:
            score += 10.0
            factors.append(
                ContributingFactorItem(
                    factor=f"structured_cardiovascular_history_{record_type}",
                    status="present",
                    severity="info",
                    weight=0.10,
                    message=(
                        f"A structured cardiovascular history record with record_type '{record_type}' "
                        "is present in the selected date range."
                    ),
                    source="medical_record",
                )
            )

        for record_type in features.structured_medical_record_types:
            factors.append(
                ContributingFactorItem(
                    factor=f"structured_medical_record_{record_type}",
                    status="present",
                    severity="info",
                    weight=0.05,
                    message=(
                        f"A structured medical record with record_type '{record_type}' "
                        "is present in the selected date range."
                    ),
                    source="medical_record",
                )
            )

        score = min(round(score, 1), 100.0)
        risk_level = self._map_score_to_risk_level(score)
        recommendations = self._build_recommendations(risk_level, features)

        return HeartDiseaseRiskModelResult(
            assessment_status="completed",
            risk_level=risk_level,
            score=score,
            probability=None,
            contributing_factors=tuple(factors),
            missing_inputs=missing_inputs,
            recommendations=recommendations,
        )

    def _evaluate_age(self, age_years: int) -> tuple[float, ContributingFactorItem]:
        if age_years >= 65:
            return 20.0, ContributingFactorItem(
                factor="age",
                status="present",
                severity="warning",
                weight=0.20,
                message=(
                    f"Patient age ({age_years} years) is a demographic factor associated with "
                    "higher informational cardiovascular risk in population models."
                ),
                source="patient",
            )
        if age_years >= 55:
            return 12.0, ContributingFactorItem(
                factor="age",
                status="present",
                severity="info",
                weight=0.12,
                message=(
                    f"Patient age ({age_years} years) is a demographic factor commonly included "
                    "in informational heart disease risk models."
                ),
                source="patient",
            )
        return 0.0, ContributingFactorItem(
            factor="age",
            status="present",
            severity="normal",
            weight=0.05,
            message=f"Patient age ({age_years} years) is recorded and included as context.",
            source="patient",
        )

    def _evaluate_gender(self, gender: str, age_years: int) -> tuple[float, ContributingFactorItem]:
        normalized = gender.strip().lower()
        if normalized == "male" and age_years >= 45:
            return 5.0, ContributingFactorItem(
                factor="gender",
                status="present",
                severity="info",
                weight=0.05,
                message=(
                    "Recorded gender (male) and age are included as demographic context in "
                    "informational cardiovascular risk models."
                ),
                source="patient",
            )
        return 0.0, ContributingFactorItem(
            factor="gender",
            status="present",
            severity="normal",
            weight=0.05,
            message=f"Recorded gender ({gender}) is included as demographic context.",
            source="patient",
        )

    def _evaluate_systolic(self, value: Decimal) -> tuple[float, ContributingFactorItem]:
        thresholds = SYSTOLIC_PRESSURE_THRESHOLDS
        if value >= thresholds.urgent_high_above:
            points, severity, status = 35.0, "urgent", "above_reference_range"
        elif value > thresholds.warning_high_above:
            points, severity, status = 22.0, "warning", "above_reference_range"
        else:
            points, severity, status = 0.0, "normal", "within_reference_range"

        return points, ContributingFactorItem(
            factor="systolic_blood_pressure",
            status=status,
            severity=severity,
            weight=0.30,
            message=(
                f"Average systolic blood pressure ({value} mmHg) is {status.replace('_', ' ')} "
                "based on informational reference thresholds."
            ),
            source="health_measurement",
        )

    def _evaluate_diastolic(self, value: Decimal) -> tuple[float, ContributingFactorItem]:
        thresholds = DIASTOLIC_PRESSURE_THRESHOLDS
        if value >= thresholds.urgent_high_above:
            points, severity, status = 25.0, "urgent", "above_reference_range"
        elif value > thresholds.warning_high_above:
            points, severity, status = 15.0, "warning", "above_reference_range"
        else:
            points, severity, status = 0.0, "normal", "within_reference_range"

        return points, ContributingFactorItem(
            factor="diastolic_blood_pressure",
            status=status,
            severity=severity,
            weight=0.20,
            message=(
                f"Average diastolic blood pressure ({value} mmHg) is {status.replace('_', ' ')} "
                "based on informational reference thresholds."
            ),
            source="health_measurement",
        )

    def _evaluate_heart_rate(self, value: Decimal) -> tuple[float, ContributingFactorItem]:
        thresholds = RESTING_HEART_RATE_THRESHOLDS
        if value >= thresholds.urgent_high_above:
            points, severity, status = 15.0, "urgent", "above_reference_range"
        elif value > thresholds.warning_high_above:
            points, severity, status = 8.0, "warning", "above_reference_range"
        else:
            points, severity, status = 0.0, "normal", "within_reference_range"

        return points, ContributingFactorItem(
            factor="heart_rate",
            status=status,
            severity=severity,
            weight=0.10,
            message=(
                f"Average resting heart rate ({value} bpm) is {status.replace('_', ' ')} "
                "based on informational reference thresholds."
            ),
            source="health_measurement",
        )

    def _map_score_to_risk_level(self, score: float) -> RiskLevel:
        if score >= RISK_ELEVATED_SCORE_MIN:
            return "elevated"
        if score >= RISK_MODERATE_SCORE_MIN:
            return "moderate"
        return "low"

    def _build_recommendations(
        self,
        risk_level: RiskLevel,
        features: HeartDiseaseRiskFeatureVector,
    ) -> tuple[HeartDiseaseRiskRecommendationItem, ...]:
        recommendations: list[HeartDiseaseRiskRecommendationItem] = [
            HeartDiseaseRiskRecommendationItem(
                category="monitoring",
                message=(
                    "Continue recording paired blood pressure readings and heart rate measurements "
                    "to support ongoing informational cardiovascular tracking."
                ),
                related_metrics=("systolic_pressure", "diastolic_pressure", "heart_rate"),
            )
        ]

        if risk_level in {"moderate", "elevated"}:
            recommendations.append(
                HeartDiseaseRiskRecommendationItem(
                    category="follow_up",
                    message=(
                        "Consider discussing these informational heart disease risk results with "
                        "a qualified healthcare professional for clinical evaluation."
                    ),
                    related_metrics=("systolic_pressure", "diastolic_pressure", "heart_rate"),
                )
            )

        if features.average_heart_rate is None:
            recommendations.append(
                HeartDiseaseRiskRecommendationItem(
                    category="tracking",
                    message="Add resting heart rate measurements to improve future assessment context.",
                    related_metrics=("heart_rate",),
                )
            )

        for recommendation in recommendations:
            lowered = recommendation.message.lower()
            if any(term in lowered for term in FORBIDDEN_RECOMMENDATION_TERMS):
                raise ValueError("Recommendation contains disallowed prescriptive language.")

        return tuple(recommendations)
