"""Stroke risk assessment application service."""

from datetime import datetime
from uuid import UUID

from app.application.analytics.risk_assessment_common import (
    filter_measurements_by_window,
    filter_medical_records_by_window,
    resolve_assessment_window,
)
from app.application.analytics.stroke_risk_assessment import build_feature_vector
from app.application.dtos.health_measurement_insights import HealthRecommendationDTO
from app.application.dtos.stroke_risk_assessment import (
    ContributingFactorDTO,
    MissingInputDTO,
    StrokeRiskAssessmentDTO,
)
from app.application.models.rule_based_stroke_risk_model_v1 import RuleBasedStrokeRiskModelV1
from app.application.services.base import BaseService
from app.core.exceptions import NotFoundError, ValidationError
from app.core.reference_ranges import MAX_ANALYTICS_DATE_RANGE_DAYS
from app.domain.interfaces.health_measurement_repository import HealthMeasurementRepository
from app.domain.interfaces.medical_record_repository import MedicalRecordRepository
from app.domain.interfaces.patient_repository import PatientRepository
from app.domain.interfaces.stroke_risk_model import StrokeRiskModelPort


class StrokeRiskAssessmentService(BaseService):
    """On-demand stroke risk assessments scoped to one owned patient."""

    def __init__(
        self,
        patient_repository: PatientRepository,
        health_measurement_repository: HealthMeasurementRepository,
        medical_record_repository: MedicalRecordRepository,
        risk_model: StrokeRiskModelPort | None = None,
    ) -> None:
        self._patients = patient_repository
        self._health_measurements = health_measurement_repository
        self._medical_records = medical_record_repository
        self._risk_model = risk_model or RuleBasedStrokeRiskModelV1()

    async def assess_stroke_risk(
        self,
        owner_id: UUID,
        *,
        patient_id: UUID,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> StrokeRiskAssessmentDTO:
        patient = await self._patients.get_by_id_and_owner(patient_id, owner_id)
        if patient is None:
            raise NotFoundError("Patient not found")

        window = resolve_assessment_window(date_from, date_to)
        self._validate_date_range(window.date_from, window.date_to)

        measurements = await self._health_measurements.list_by_owner_for_analytics(
            owner_id,
            patient_id=patient_id,
            date_from=window.date_from,
            date_to=window.date_to,
        )
        measurements = filter_measurements_by_window(measurements, window)

        medical_records = await self._medical_records.list_by_owner(
            owner_id,
            offset=0,
            limit=100,
            patient_id=patient_id,
        )
        medical_records = filter_medical_records_by_window(medical_records, window)

        features = build_feature_vector(patient, measurements, medical_records, window)
        model_result = self._risk_model.assess(features)

        return StrokeRiskAssessmentDTO(
            patient_id=patient_id,
            date_from=window.date_from,
            date_to=window.date_to,
            model_version=self._risk_model.model_version,
            assessment_status=model_result.assessment_status,
            risk_level=model_result.risk_level,
            score=model_result.score,
            probability=model_result.probability,
            contributing_factors=[
                ContributingFactorDTO(**factor.__dict__)
                for factor in model_result.contributing_factors
            ],
            missing_inputs=[
                MissingInputDTO(**item.__dict__) for item in model_result.missing_inputs
            ],
            recommendations=[
                HealthRecommendationDTO(
                    category=item.category,
                    message=item.message,
                    related_metrics=list(item.related_metrics),
                )
                for item in model_result.recommendations
            ],
        )

    def _validate_date_range(self, date_from: datetime, date_to: datetime) -> None:
        if date_from > date_to:
            raise ValidationError("date_from must be before or equal to date_to")

        if (date_to - date_from).days > MAX_ANALYTICS_DATE_RANGE_DAYS:
            raise ValidationError("Date range cannot exceed 366 days")
