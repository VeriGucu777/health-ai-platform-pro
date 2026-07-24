"""Stroke risk assessment application service."""

from datetime import datetime
from uuid import UUID

from app.application.analytics.stroke_risk_assessment import build_feature_vector
from app.application.dtos.stroke_risk_assessment import StrokeRiskAssessmentDTO
from app.application.models.rule_based_stroke_risk_model_v1 import RuleBasedStrokeRiskModelV1
from app.application.services.base import BaseService
from app.application.services.risk_assessment_runner import run_risk_assessment
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
        return await run_risk_assessment(
            patients=self._patients,
            health_measurements=self._health_measurements,
            medical_records=self._medical_records,
            owner_id=owner_id,
            patient_id=patient_id,
            date_from=date_from,
            date_to=date_to,
            build_feature_vector=build_feature_vector,
            risk_model=self._risk_model,
            assessment_dto_class=StrokeRiskAssessmentDTO,
        )
