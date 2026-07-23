"""Rule-based diabetes risk model v1."""

from __future__ import annotations

from decimal import Decimal

from app.application.analytics.diabetes_risk_assessment import detect_missing_inputs, has_minimum_required_inputs
from app.core.reference_ranges import (
    DIABETES_RISK_ELEVATED_SCORE_MIN,
    DIABETES_RISK_MODERATE_SCORE_MIN,
    FASTING_GLUCOSE_THRESHOLDS,
    GENERIC_GLUCOSE_THRESHOLDS,
    SYSTOLIC_PRESSURE_THRESHOLDS,
)
from app.domain.interfaces.diabetes_risk_model import (
    ContributingFactorItem,
    DiabetesRiskFeatureVector,
    DiabetesRiskModelPort,
    DiabetesRiskModelResult,
    DiabetesRiskRecommendationItem,
    MissingInputItem,
    RiskLevel,
)

MODEL_VERSION = "rule_based_v1"

FORBIDDEN_RECOMMENDATION_TERMS = (
    "prescribe",
    "medication",
    "dosage",
    "diagnosis",
    "diabetic",
    "non-diabetic",
    "insulin dose",
    "start taking",
)


class RuleBasedDiabetesRiskModelV1(DiabetesRiskModelPort):
    """Deterministic, explainable diabetes risk scoring for v1."""

    @property
    def model_version(self) -> str:
        return MODEL_VERSION

    def assess(self, features: DiabetesRiskFeatureVector) -> DiabetesRiskModelResult:
        missing_inputs = tuple(detect_missing_inputs(features))

        if not has_minimum_required_inputs(features):
            return DiabetesRiskModelResult(
                assessment_status="insufficient_data",
                risk_level=None,
                score=None,
                probability=None,
                contributing_factors=(),
                missing_inputs=missing_inputs,
                recommendations=(
                    DiabetesRiskRecommendationItem(
                        category="tracking",
                        message=(
                            "Add blood glucose measurements, preferably with fasting context, "
                            "to enable an informational diabetes risk assessment."
                        ),
                        related_metrics=("blood_glucose",),
                    ),
                ),
            )

        factors: list[ContributingFactorItem] = []
        score = 0.0

        age_points, age_factor = self._evaluate_age(features.age_years)
        score += age_points
        if age_factor is not None:
            factors.append(age_factor)

        glucose_points, glucose_factor = self._evaluate_glucose(features)
        score += glucose_points
        if glucose_factor is not None:
            factors.append(glucose_factor)

        bp_points, bp_factor = self._evaluate_blood_pressure(features.average_systolic_pressure)
        score += bp_points
        if bp_factor is not None:
            factors.append(bp_factor)

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

        return DiabetesRiskModelResult(
            assessment_status="completed",
            risk_level=risk_level,
            score=score,
            probability=None,
            contributing_factors=tuple(factors),
            missing_inputs=missing_inputs,
            recommendations=recommendations,
        )

    def _evaluate_age(self, age_years: int) -> tuple[float, ContributingFactorItem | None]:
        if age_years >= 60:
            return 20.0, ContributingFactorItem(
                factor="age",
                status="present",
                severity="warning",
                weight=0.20,
                message=(
                    f"Patient age ({age_years} years) is a demographic factor associated with "
                    "higher informational diabetes risk in population models."
                ),
                source="patient",
            )
        if age_years >= 45:
            return 10.0, ContributingFactorItem(
                factor="age",
                status="present",
                severity="info",
                weight=0.10,
                message=(
                    f"Patient age ({age_years} years) is a demographic factor commonly included "
                    "in informational diabetes risk models."
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

    def _evaluate_glucose(
        self,
        features: DiabetesRiskFeatureVector,
    ) -> tuple[float, ContributingFactorItem | None]:
        if features.latest_fasting_glucose is not None:
            value = features.latest_fasting_glucose
            thresholds = FASTING_GLUCOSE_THRESHOLDS
            context_label = "fasting"
        elif features.latest_non_fasting_glucose is not None:
            value = features.latest_non_fasting_glucose
            thresholds = GENERIC_GLUCOSE_THRESHOLDS
            context_label = "non-fasting"
        else:
            return 0.0, None

        severity, status, points = self._classify_glucose(value, thresholds)
        return points, ContributingFactorItem(
            factor="blood_glucose",
            status=status,
            severity=severity,
            weight=0.45,
            message=(
                f"Latest {context_label} blood glucose ({value} mg/dL) is {status.replace('_', ' ')} "
                "based on informational reference thresholds."
            ),
            source="health_measurement",
        )

    def _classify_glucose(
        self,
        value: Decimal,
        thresholds,
    ) -> tuple[str, str, float]:
        if value >= thresholds.urgent_high_above:
            return "urgent", "above_reference_range", 55.0
        if value > thresholds.warning_high_above:
            return "warning", "above_reference_range", 35.0
        if value < thresholds.warning_low_below:
            return "warning", "below_reference_range", 15.0
        return "normal", "within_reference_range", 0.0

    def _evaluate_blood_pressure(
        self,
        average_systolic: Decimal | None,
    ) -> tuple[float, ContributingFactorItem | None]:
        if average_systolic is None:
            return 0.0, None

        thresholds = SYSTOLIC_PRESSURE_THRESHOLDS
        if average_systolic >= thresholds.urgent_high_above:
            severity = "urgent"
            status = "above_reference_range"
            points = 20.0
        elif average_systolic > thresholds.warning_high_above:
            severity = "warning"
            status = "above_reference_range"
            points = 12.0
        else:
            severity = "normal"
            status = "within_reference_range"
            points = 0.0

        return points, ContributingFactorItem(
            factor="systolic_blood_pressure",
            status=status,
            severity=severity,
            weight=0.15,
            message=(
                f"Average systolic blood pressure ({average_systolic} mmHg) is {status.replace('_', ' ')} "
                "based on informational reference thresholds."
            ),
            source="health_measurement",
        )

    def _map_score_to_risk_level(self, score: float) -> RiskLevel:
        if score >= DIABETES_RISK_ELEVATED_SCORE_MIN:
            return "elevated"
        if score >= DIABETES_RISK_MODERATE_SCORE_MIN:
            return "moderate"
        return "low"

    def _build_recommendations(
        self,
        risk_level: RiskLevel,
        features: DiabetesRiskFeatureVector,
    ) -> tuple[DiabetesRiskRecommendationItem, ...]:
        recommendations: list[DiabetesRiskRecommendationItem] = [
            DiabetesRiskRecommendationItem(
                category="monitoring",
                message=(
                    "Continue recording blood glucose measurements with context labels such as "
                    "fasting or post_meal to support ongoing informational tracking."
                ),
                related_metrics=("blood_glucose",),
            )
        ]

        if risk_level in {"moderate", "elevated"}:
            recommendations.append(
                DiabetesRiskRecommendationItem(
                    category="follow_up",
                    message=(
                        "Consider discussing these informational risk results with a qualified "
                        "healthcare professional for clinical evaluation."
                    ),
                    related_metrics=("blood_glucose", "systolic_pressure"),
                )
            )

        if features.latest_fasting_glucose is None and features.latest_non_fasting_glucose is not None:
            recommendations.append(
                DiabetesRiskRecommendationItem(
                    category="tracking",
                    message=(
                        "Add fasting blood glucose measurements when possible to improve the "
                        "interpretability of future informational assessments."
                    ),
                    related_metrics=("blood_glucose",),
                )
            )

        for recommendation in recommendations:
            lowered = recommendation.message.lower()
            if any(term in lowered for term in FORBIDDEN_RECOMMENDATION_TERMS):
                raise ValueError("Recommendation contains disallowed prescriptive language.")

        return tuple(recommendations)
