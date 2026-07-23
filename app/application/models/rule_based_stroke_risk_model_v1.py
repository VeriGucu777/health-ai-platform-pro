"""Rule-based stroke risk model v1."""

from __future__ import annotations

from decimal import Decimal

from app.application.analytics.stroke_risk_assessment import detect_missing_inputs, has_minimum_required_inputs
from app.core.reference_ranges import (
    DIASTOLIC_PRESSURE_THRESHOLDS,
    FASTING_GLUCOSE_THRESHOLDS,
    GENERIC_GLUCOSE_THRESHOLDS,
    RISK_ELEVATED_SCORE_MIN,
    RISK_MODERATE_SCORE_MIN,
    SYSTOLIC_PRESSURE_THRESHOLDS,
)
from app.domain.interfaces.stroke_risk_model import (
    ContributingFactorItem,
    RiskLevel,
    StrokeRiskFeatureVector,
    StrokeRiskModelPort,
    StrokeRiskModelResult,
    StrokeRiskRecommendationItem,
)

MODEL_VERSION = "stroke_rule_based_v1"

FORBIDDEN_RECOMMENDATION_TERMS = (
    "prescribe",
    "medication",
    "dosage",
    "diagnosis",
    "stroke confirmed",
    "start taking",
    "blood thinner",
)


class RuleBasedStrokeRiskModelV1(StrokeRiskModelPort):
    """Deterministic, explainable stroke risk scoring for v1."""

    @property
    def model_version(self) -> str:
        return MODEL_VERSION

    def assess(self, features: StrokeRiskFeatureVector) -> StrokeRiskModelResult:
        missing_inputs = tuple(detect_missing_inputs(features))

        if not has_minimum_required_inputs(features):
            return StrokeRiskModelResult(
                assessment_status="insufficient_data",
                risk_level=None,
                score=None,
                probability=None,
                contributing_factors=(),
                missing_inputs=missing_inputs,
                recommendations=(
                    StrokeRiskRecommendationItem(
                        category="tracking",
                        message=(
                            "Add blood pressure and blood glucose measurements to enable an "
                            "informational stroke risk assessment."
                        ),
                        related_metrics=("systolic_pressure", "blood_glucose"),
                    ),
                ),
            )

        factors: list[ContributingFactorItem] = []
        score = 0.0

        age_points, age_factor = self._evaluate_age(features.age_years)
        score += age_points
        factors.append(age_factor)

        systolic_points, systolic_factor = self._evaluate_systolic(features.average_systolic_pressure)
        score += systolic_points
        factors.append(systolic_factor)

        if features.average_diastolic_pressure is not None:
            diastolic_points, diastolic_factor = self._evaluate_diastolic(
                features.average_diastolic_pressure
            )
            score += diastolic_points
            factors.append(diastolic_factor)

        glucose_points, glucose_factor = self._evaluate_glucose(features)
        score += glucose_points
        factors.append(glucose_factor)

        for record_type in features.stroke_history_record_types:
            score += 15.0
            factors.append(
                ContributingFactorItem(
                    factor=f"structured_stroke_history_{record_type}",
                    status="present",
                    severity="warning",
                    weight=0.15,
                    message=(
                        f"A structured stroke or TIA history record with record_type '{record_type}' "
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

        return StrokeRiskModelResult(
            assessment_status="completed",
            risk_level=risk_level,
            score=score,
            probability=None,
            contributing_factors=tuple(factors),
            missing_inputs=missing_inputs,
            recommendations=recommendations,
        )

    def _evaluate_age(self, age_years: int) -> tuple[float, ContributingFactorItem]:
        if age_years >= 70:
            return 22.0, ContributingFactorItem(
                factor="age",
                status="present",
                severity="warning",
                weight=0.22,
                message=(
                    f"Patient age ({age_years} years) is a demographic factor associated with "
                    "higher informational stroke risk in population models."
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
                    "in informational stroke risk models."
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

    def _evaluate_systolic(self, value: Decimal) -> tuple[float, ContributingFactorItem]:
        thresholds = SYSTOLIC_PRESSURE_THRESHOLDS
        if value >= thresholds.urgent_high_above:
            points, severity, status = 30.0, "urgent", "above_reference_range"
        elif value > thresholds.warning_high_above:
            points, severity, status = 18.0, "warning", "above_reference_range"
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
            points, severity, status = 18.0, "urgent", "above_reference_range"
        elif value > thresholds.warning_high_above:
            points, severity, status = 10.0, "warning", "above_reference_range"
        else:
            points, severity, status = 0.0, "normal", "within_reference_range"

        return points, ContributingFactorItem(
            factor="diastolic_blood_pressure",
            status=status,
            severity=severity,
            weight=0.15,
            message=(
                f"Average diastolic blood pressure ({value} mmHg) is {status.replace('_', ' ')} "
                "based on informational reference thresholds."
            ),
            source="health_measurement",
        )

    def _evaluate_glucose(self, features: StrokeRiskFeatureVector) -> tuple[float, ContributingFactorItem]:
        if features.latest_fasting_glucose is not None:
            value = features.latest_fasting_glucose
            thresholds = FASTING_GLUCOSE_THRESHOLDS
            context_label = "fasting"
        elif features.latest_non_fasting_glucose is not None:
            value = features.latest_non_fasting_glucose
            thresholds = GENERIC_GLUCOSE_THRESHOLDS
            context_label = "non-fasting"
        else:
            raise ValueError("Glucose evaluation requires at least one glucose reading.")

        if value >= thresholds.urgent_high_above:
            points, severity, status = 28.0, "urgent", "above_reference_range"
        elif value > thresholds.warning_high_above:
            points, severity, status = 16.0, "warning", "above_reference_range"
        else:
            points, severity, status = 0.0, "normal", "within_reference_range"

        return points, ContributingFactorItem(
            factor="blood_glucose",
            status=status,
            severity=severity,
            weight=0.25,
            message=(
                f"Latest {context_label} blood glucose ({value} mg/dL) is {status.replace('_', ' ')} "
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
        features: StrokeRiskFeatureVector,
    ) -> tuple[StrokeRiskRecommendationItem, ...]:
        recommendations: list[StrokeRiskRecommendationItem] = [
            StrokeRiskRecommendationItem(
                category="monitoring",
                message=(
                    "Continue recording blood pressure and blood glucose measurements to support "
                    "ongoing informational stroke risk tracking."
                ),
                related_metrics=("systolic_pressure", "diastolic_pressure", "blood_glucose"),
            )
        ]

        if risk_level in {"moderate", "elevated"}:
            recommendations.append(
                StrokeRiskRecommendationItem(
                    category="follow_up",
                    message=(
                        "Consider discussing these informational stroke risk results with a qualified "
                        "healthcare professional for clinical evaluation."
                    ),
                    related_metrics=("systolic_pressure", "blood_glucose"),
                )
            )

        if features.latest_fasting_glucose is None and features.latest_non_fasting_glucose is not None:
            recommendations.append(
                StrokeRiskRecommendationItem(
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
