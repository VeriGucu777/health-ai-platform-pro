"""Regression: production DI wiring for risk assessment services."""

from unittest.mock import MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_diabetes_risk_assessment_service,
    get_heart_disease_risk_assessment_service,
    get_stroke_risk_assessment_service,
)
from app.application.models.rule_based_diabetes_risk_model_v1 import RuleBasedDiabetesRiskModelV1
from app.application.models.rule_based_heart_disease_risk_model_v1 import (
    RuleBasedHeartDiseaseRiskModelV1,
)
from app.application.models.rule_based_stroke_risk_model_v1 import RuleBasedStrokeRiskModelV1
from app.application.services.diabetes_risk_assessment_service import DiabetesRiskAssessmentService
from app.application.services.heart_disease_risk_assessment_service import (
    HeartDiseaseRiskAssessmentService,
)
from app.application.services.stroke_risk_assessment_service import StrokeRiskAssessmentService
from app.infrastructure.repositories.risk_assessment_history_repository import (
    SQLAlchemyRiskAssessmentHistoryRepository,
)


@pytest.fixture
def mock_db_session() -> MagicMock:
    return MagicMock(spec=AsyncSession)


def test_diabetes_risk_service_production_di_wiring(mock_db_session: MagicMock) -> None:
    service = get_diabetes_risk_assessment_service(mock_db_session)
    assert isinstance(service, DiabetesRiskAssessmentService)
    assert isinstance(service._risk_model, RuleBasedDiabetesRiskModelV1)
    assert hasattr(service._risk_model, "assess")
    assert isinstance(service._history, SQLAlchemyRiskAssessmentHistoryRepository)
    assert service._history is not service._risk_model


def test_heart_disease_risk_service_production_di_wiring(mock_db_session: MagicMock) -> None:
    service = get_heart_disease_risk_assessment_service(mock_db_session)
    assert isinstance(service, HeartDiseaseRiskAssessmentService)
    assert isinstance(service._risk_model, RuleBasedHeartDiseaseRiskModelV1)
    assert hasattr(service._risk_model, "assess")
    assert isinstance(service._history, SQLAlchemyRiskAssessmentHistoryRepository)
    assert service._history is not service._risk_model


def test_stroke_risk_service_production_di_wiring(mock_db_session: MagicMock) -> None:
    service = get_stroke_risk_assessment_service(mock_db_session)
    assert isinstance(service, StrokeRiskAssessmentService)
    assert isinstance(service._risk_model, RuleBasedStrokeRiskModelV1)
    assert hasattr(service._risk_model, "assess")
    assert isinstance(service._history, SQLAlchemyRiskAssessmentHistoryRepository)
    assert service._history is not service._risk_model
