# API Inventory

Authoritative inventory of FastAPI routes in Health AI Platform Pro. Generated from the registered routers in `backend/app/api/v1/router.py` and `backend/app/main.py`.

**Last synchronized:** 2026-07-28  
**Base prefix:** `/api/v1` (configurable via `API_V1_PREFIX`)  
**Route totals:** 36 `/api/v1` handlers + 1 root handler = **37 HTTP routes**  
**OpenAPI paths (development):** 23 path templates (some expose multiple methods)

> **Note:** `GET /api/v1/metrics` is registered but excluded from OpenAPI (`include_in_schema=False`) and returns 404 unless `METRICS_ENABLED=true`.

## Root

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/` | No | Development: redirect to `/docs`. Production/staging: JSON service metadata with health links |

## Health & Observability

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/v1/health` | No | Liveness — process uptime and service metadata |
| GET | `/api/v1/ready` | No | Readiness — PostgreSQL connectivity probe (503 when DB unavailable) |
| GET | `/api/v1/metrics` | No | Prometheus metrics (404 when disabled) |

## Authentication

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/v1/auth/register` | No | Register account (`patient` or `doctor` only) |
| POST | `/api/v1/auth/login` | No | Obtain JWT access + refresh tokens |
| POST | `/api/v1/auth/refresh` | No | Refresh token pair |
| POST | `/api/v1/auth/logout` | No | Validate refresh token; client-side token discard |
| GET | `/api/v1/auth/me` | Yes | Current user profile |
| GET | `/api/v1/auth/admin/ping` | Yes (`system_admin`) | Role-guarded admin check |

## Patients

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/v1/patients` | Yes | Create patient for current user |
| GET | `/api/v1/patients` | Yes | List patients (paginated) |
| GET | `/api/v1/patients/{patient_id}` | Yes | Get patient |
| PATCH | `/api/v1/patients/{patient_id}` | Yes | Partial update |
| DELETE | `/api/v1/patients/{patient_id}` | Yes | Delete patient (204) |

## Patient Health Reports

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/v1/patients/{patient_id}/reports/health-summary.pdf` | Yes | Generate patient health summary PDF |

## Risk Assessments (Decision Support)

Rule-based v1 models — not ML inference. All responses include mandatory disclaimers.

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/v1/patients/{patient_id}/risk-assessments/diabetes` | Yes | Diabetes risk assessment |
| GET | `/api/v1/patients/{patient_id}/risk-assessments/heart-disease` | Yes | Heart disease risk assessment |
| GET | `/api/v1/patients/{patient_id}/risk-assessments/stroke` | Yes | Stroke risk assessment |

## Appointments

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/v1/appointments` | Yes | Create appointment |
| GET | `/api/v1/appointments` | Yes | List appointments (paginated, filterable) |
| GET | `/api/v1/appointments/{appointment_id}` | Yes | Get appointment |
| PATCH | `/api/v1/appointments/{appointment_id}` | Yes | Partial update |
| DELETE | `/api/v1/appointments/{appointment_id}` | Yes | Delete appointment (204) |

## Medical Records

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/v1/medical-records` | Yes | Create medical record |
| GET | `/api/v1/medical-records` | Yes | List records (paginated, filterable) |
| GET | `/api/v1/medical-records/{medical_record_id}` | Yes | Get record |
| PATCH | `/api/v1/medical-records/{medical_record_id}` | Yes | Partial update |
| DELETE | `/api/v1/medical-records/{medical_record_id}` | Yes | Delete record (204) |

## Health Measurements

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/v1/health-measurements` | Yes | Create measurement |
| GET | `/api/v1/health-measurements` | Yes | List measurements (paginated, filterable) |
| GET | `/api/v1/health-measurements/{health_measurement_id}` | Yes | Get measurement |
| PATCH | `/api/v1/health-measurements/{health_measurement_id}` | Yes | Partial update |
| DELETE | `/api/v1/health-measurements/{health_measurement_id}` | Yes | Delete measurement (204) |

## Health Measurement Analytics

Compute-only endpoints — no dedicated database tables.

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/v1/health-measurements/analytics/summary` | Yes | Overall statistics for a patient/date range |
| GET | `/api/v1/health-measurements/analytics/trends` | Yes | Period trends (daily/weekly/monthly) |
| GET | `/api/v1/health-measurements/analytics/insights` | Yes | Rule-based insights with severity and recommendations |

## Endpoint Modules

| # | Module file | Router tag |
|---|---|---|
| 1 | `app/api/v1/endpoints/health.py` | Health |
| 2 | `app/api/v1/endpoints/metrics.py` | Observability |
| 3 | `app/api/v1/endpoints/auth.py` | Authentication |
| 4 | `app/api/v1/endpoints/patients.py` | Patients |
| 5 | `app/api/v1/endpoints/patient_health_reports.py` | Patient Health Reports |
| 6 | `app/api/v1/endpoints/diabetes_risk_assessment.py` | Diabetes Risk Assessment |
| 7 | `app/api/v1/endpoints/heart_disease_risk_assessment.py` | Heart Disease Risk Assessment |
| 8 | `app/api/v1/endpoints/stroke_risk_assessment.py` | Stroke Risk Assessment |
| 9 | `app/api/v1/endpoints/appointments.py` | Appointments |
| 10 | `app/api/v1/endpoints/medical_records.py` | Medical Records |
| 11 | `app/api/v1/endpoints/health_measurements.py` | Health Measurements |
| 12 | `app/api/v1/endpoints/health_measurement_analytics.py` | Health Measurement Analytics |

## Verification

Route registration is verified by `backend/tests/api/test_routes.py`, which asserts all expected OpenAPI paths are present in development mode.
