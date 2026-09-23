"""Localized copy for patient health PDF reports and insight messages."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Literal

ReportLocale = Literal["en", "tr"]

SUPPORTED_REPORT_LOCALES: frozenset[str] = frozenset({"en", "tr"})

# Patient notes excluded from PDF (technical/demo markers only — not clinical content).
INTERNAL_PATIENT_NOTE_PREFIXES: tuple[str, ...] = (
    "seed:",
    "demo-fixture:",
    "internal-test:",
)


def parse_report_locale(value: str | None) -> ReportLocale:
    if value is None:
        return "en"
    normalized = value.strip().lower()
    if normalized in SUPPORTED_REPORT_LOCALES:
        return normalized  # type: ignore[return-value]
    return "en"


def _primary_accept_language_tag(accept_language: str | None) -> str | None:
    if not accept_language or not accept_language.strip():
        return None
    first_range = accept_language.split(",")[0].strip()
    if not first_range:
        return None
    return first_range.split(";")[0].strip().lower()


def resolve_report_locale(
    query_locale: str | None,
    accept_language: str | None = None,
) -> ReportLocale:
    """Resolve PDF locale from explicit query param, else Accept-Language, else English."""
    if query_locale is not None and query_locale.strip():
        return parse_report_locale(query_locale)
    primary = _primary_accept_language_tag(accept_language)
    if primary:
        if primary == "tr" or primary.startswith("tr-"):
            return "tr"
        if primary == "en" or primary.startswith("en-"):
            return "en"
    return "en"


REPORT_LOCALE_RESPONSE_HEADER = "X-Report-Locale"


def patient_notes_for_report(notes: str | None) -> str | None:
    """Return notes for PDF, or None when the value is an internal/demo marker only."""
    if notes is None:
        return None
    stripped = notes.strip()
    if not stripped:
        return None
    lowered = stripped.lower()
    if any(lowered.startswith(prefix) for prefix in INTERNAL_PATIENT_NOTE_PREFIXES):
        return None
    return stripped


@dataclass(frozen=True)
class ReportCopy:
    locale: ReportLocale
    document_title: str
    platform_name: str
    report_title: str
    generated_at_label: str
    patient_section_title: str
    full_name_label: str
    date_of_birth_label: str
    gender_label: str
    phone_label: str
    status_label: str
    notes_label: str
    active_label: str
    inactive_label: str
    period_section_title: str
    period_from_label: str
    period_to_label: str
    medical_records_title: str
    no_medical_records: str
    medical_records_truncated: str
    measurement_summary_title: str
    measurement_count_label: str
    statistics_title: str
    no_statistics: str
    trends_title: str
    no_trends: str
    insights_title: str
    overall_status_heading: str
    latest_label: str
    average_label: str
    alerts_title: str
    no_alerts: str
    recommendations_title: str
    no_recommendations: str
    disclaimer_title: str
    table_date: str
    table_type: str
    table_title: str
    table_doctor: str
    table_hospital: str
    table_metric: str
    table_count: str
    table_avg: str
    table_min: str
    table_max: str
    table_trend: str
    table_reference: str
    table_week_start: str
    insights_disclaimer: str
    report_disclaimer: str

    def metric_label(self, metric: str) -> str:
        return METRIC_LABELS[self.locale].get(metric, metric)

    def trend_label(self, trend: str) -> str:
        return TREND_LABELS[self.locale].get(trend, trend)

    def range_label(self, status: str) -> str:
        return RANGE_LABELS[self.locale].get(status, status)

    def gender_label_value(self, gender: str) -> str:
        return GENDER_LABELS[self.locale].get(gender.strip().lower(), gender)

    def severity_label(self, severity: str) -> str:
        return SEVERITY_LABELS[self.locale].get(severity, severity)

    def overall_status_label(self, status: str) -> str:
        return OVERALL_STATUS_LABELS[self.locale].get(status, status)

    def record_type_label(self, record_type: str) -> str:
        key = record_type.strip().lower().replace(" ", "_")
        return RECORD_TYPE_LABELS[self.locale].get(key, record_type)


METRIC_LABELS: dict[ReportLocale, dict[str, str]] = {
    "en": {
        "blood_glucose": "Blood glucose",
        "systolic_pressure": "Systolic blood pressure",
        "diastolic_pressure": "Diastolic blood pressure",
        "heart_rate": "Resting heart rate",
        "weight_kg": "Weight",
    },
    "tr": {
        "blood_glucose": "Kan şekeri",
        "systolic_pressure": "Sistolik tansiyon",
        "diastolic_pressure": "Diyastolik tansiyon",
        "heart_rate": "Dinlenme nabzı",
        "weight_kg": "Kilo",
    },
}

TREND_LABELS: dict[ReportLocale, dict[str, str]] = {
    "en": {
        "increasing": "Increasing",
        "decreasing": "Decreasing",
        "stable": "Stable",
        "insufficient_data": "Insufficient data",
    },
    "tr": {
        "increasing": "Artış",
        "decreasing": "Azalış",
        "stable": "Stabil",
        "insufficient_data": "Yetersiz veri",
    },
}

RANGE_LABELS: dict[ReportLocale, dict[str, str]] = {
    "en": {
        "within_reference_range": "Within reference range",
        "below_reference_range": "Below reference range",
        "above_reference_range": "Above reference range",
        "not_applicable": "Not applicable",
    },
    "tr": {
        "within_reference_range": "Referans aralığında",
        "below_reference_range": "Referans altı",
        "above_reference_range": "Referans üstü",
        "not_applicable": "Uygulanamaz",
    },
}

GENDER_LABELS: dict[ReportLocale, dict[str, str]] = {
    "en": {"male": "Male", "female": "Female", "other": "Other"},
    "tr": {"male": "Erkek", "female": "Kadın", "other": "Diğer"},
}

SEVERITY_LABELS: dict[ReportLocale, dict[str, str]] = {
    "en": {
        "normal": "Normal",
        "info": "Info",
        "warning": "Warning",
        "urgent": "Urgent",
    },
    "tr": {
        "normal": "Normal",
        "info": "Bilgi",
        "warning": "Uyarı",
        "urgent": "Acil",
    },
}

RECORD_TYPE_LABELS: dict[ReportLocale, dict[str, str]] = {
    "en": {
        "visit": "Visit",
        "lab": "Lab",
        "laboratory": "Laboratory",
        "imaging": "Imaging",
        "diagnosis": "Diagnosis",
        "prescription": "Prescription",
        "procedure": "Procedure",
        "other": "Other",
    },
    "tr": {
        "visit": "Muayene",
        "lab": "Laboratuvar",
        "laboratory": "Laboratuvar",
        "imaging": "Görüntüleme",
        "diagnosis": "Tanı",
        "prescription": "Reçete",
        "procedure": "İşlem",
        "other": "Diğer",
    },
}

OVERALL_STATUS_LABELS: dict[ReportLocale, dict[str, str]] = {
    "en": {
        "normal": "Normal",
        "info": "Info",
        "warning": "Warning",
        "urgent": "Urgent",
    },
    "tr": {
        "normal": "Normal",
        "info": "Bilgi",
        "warning": "Uyarı",
        "urgent": "Acil",
    },
}

_MONTHS_TR = (
    "Oca",
    "Şub",
    "Mar",
    "Nis",
    "May",
    "Haz",
    "Tem",
    "Ağu",
    "Eyl",
    "Eki",
    "Kas",
    "Ara",
)
_MONTHS_EN = (
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
)


def format_report_date(value: date, locale: ReportLocale) -> str:
    months = _MONTHS_TR if locale == "tr" else _MONTHS_EN
    month = months[value.month - 1]
    if locale == "tr":
        return f"{value.day} {month} {value.year}"
    return f"{month} {value.day}, {value.year}"


def format_report_datetime(value: datetime, locale: ReportLocale) -> str:
    if value.tzinfo is None:
        normalized = value.replace(tzinfo=UTC)
    else:
        normalized = value.astimezone(UTC)
    months = _MONTHS_TR if locale == "tr" else _MONTHS_EN
    month = months[normalized.month - 1]
    if locale == "tr":
        date_part = f"{normalized.day} {month} {normalized.year}"
    else:
        date_part = f"{month} {normalized.day}, {normalized.year}"
    return f"{date_part} {normalized.hour:02d}:{normalized.minute:02d} UTC"


def get_report_copy(locale: ReportLocale) -> ReportCopy:
    if locale == "tr":
        return ReportCopy(
            locale="tr",
            document_title="Hasta Sağlık Raporu",
            platform_name="Health AI Platform Pro",
            report_title="Hasta Sağlık Raporu",
            generated_at_label="Oluşturulma tarihi (UTC)",
            patient_section_title="Hasta bilgileri",
            full_name_label="Ad soyad",
            date_of_birth_label="Doğum tarihi",
            gender_label="Cinsiyet",
            phone_label="Telefon",
            status_label="Durum",
            notes_label="Notlar",
            active_label="Aktif",
            inactive_label="Pasif",
            period_section_title="Rapor dönemi",
            period_from_label="Başlangıç (UTC)",
            period_to_label="Bitiş (UTC)",
            medical_records_title="Tıbbi kayıt özeti",
            no_medical_records="Seçilen dönemde tıbbi kayıt bulunmamaktadır.",
            medical_records_truncated=(
                "Bu raporda en yeni {limit} tıbbi kayıt gösterilmektedir. "
                "Seçilen dönemde toplam {total} kayıt bulunmaktadır."
            ),
            measurement_summary_title="Sağlık ölçümü özeti",
            measurement_count_label="Seçilen dönemdeki toplam ölçüm sayısı",
            statistics_title="Temel metrik istatistikleri",
            no_statistics="Seçilen dönemde rapor metrikleri için veri bulunmamaktadır.",
            trends_title="Haftalık sağlık ölçümü trendleri",
            no_trends="Seçilen dönemde haftalık trend verisi bulunmamaktadır.",
            insights_title="Klinik içgörüler",
            overall_status_heading="Genel durum",
            latest_label="Son",
            average_label="Ort",
            alerts_title="Uyarılar",
            no_alerts="Seçilen dönemde uyarı bulunmamaktadır.",
            recommendations_title="Takip önerileri",
            no_recommendations="Takip önerisi bulunmamaktadır.",
            disclaimer_title="Tıbbi sorumluluk reddi",
            table_date="Tarih",
            table_type="Tür",
            table_title="Başlık",
            table_doctor="Doktor",
            table_hospital="Hastane",
            table_metric="Metrik",
            table_count="Adet",
            table_avg="Ort.",
            table_min="Min",
            table_max="Max",
            table_trend="Trend",
            table_reference="Referans",
            table_week_start="Hafta başlangıcı",
            insights_disclaimer=(
                "Klinik içgörüler ve sağlık uyarıları yalnızca bilgilendirme amaçlı "
                "izleme özetleridir. Tanı değildir ve nitelikli bir sağlık profesyonelinin "
                "değerlendirmesinin yerini almaz. Acil uyarılar, gecikmeden profesyonel "
                "değerlendirme düşünülmesi gerektiğini belirtir; acil durumu doğrulamaz. "
                "Ciddi belirtiler varsa yerel acil yardım yönergelerine uyun."
            ),
            report_disclaimer=(
                "Bu hasta sağlık raporu, kayıtlı verilerden üretilmiş bilgilendirme "
                "amaçlı bir özetdir. Tanı, tedavi önerisi, acil durum değerlendirmesi veya "
                "resmi klinik belge değildir. Tıbbi kararlar için her zaman nitelikli bir "
                "sağlık profesyoneline danışın."
            ),
        )

    return ReportCopy(
        locale="en",
        document_title="Patient Health Report",
        platform_name="Health AI Platform Pro",
        report_title="Patient Health Report",
        generated_at_label="Generated at (UTC)",
        patient_section_title="Patient information",
        full_name_label="Full name",
        date_of_birth_label="Date of birth",
        gender_label="Gender",
        phone_label="Phone",
        status_label="Status",
        notes_label="Notes",
        active_label="Active",
        inactive_label="Inactive",
        period_section_title="Report period",
        period_from_label="From (UTC)",
        period_to_label="To (UTC)",
        medical_records_title="Medical record summary",
        no_medical_records="No medical records were found in the selected date range.",
        medical_records_truncated=(
            "This report shows the most recent {limit} medical records. "
            "A total of {total} records exist in the selected date range."
        ),
        measurement_summary_title="Health measurement summary",
        measurement_count_label="Total measurements in the selected period",
        statistics_title="Core metric statistics",
        no_statistics="No report metrics are available for the selected date range.",
        trends_title="Weekly health measurement trends",
        no_trends="No weekly trend data is available for the selected date range.",
        insights_title="Clinical insights",
        overall_status_heading="Overall status",
        latest_label="Latest",
        average_label="Avg",
        alerts_title="Alerts",
        no_alerts="No alerts were found in the selected date range.",
        recommendations_title="Follow-up recommendations",
        no_recommendations="No follow-up recommendations are available.",
        disclaimer_title="Medical disclaimer",
        table_date="Date",
        table_type="Type",
        table_title="Title",
        table_doctor="Doctor",
        table_hospital="Hospital",
        table_metric="Metric",
        table_count="Count",
        table_avg="Avg",
        table_min="Min",
        table_max="Max",
        table_trend="Trend",
        table_reference="Reference",
        table_week_start="Week start",
        insights_disclaimer=(
            "Clinical insights and health alerts are informational tracking summaries only. "
            "They are not a diagnosis and do not replace evaluation by a qualified "
            "healthcare professional. Urgent alerts suggest that prompt professional "
            "evaluation should be considered; they do not confirm an emergency condition. "
            "If severe symptoms are present, follow local emergency guidance."
        ),
        report_disclaimer=(
            "This patient health report is an informational summary generated from recorded "
            "data. It is not a diagnosis, treatment recommendation, emergency assessment, "
            "or official clinical document. Always consult a qualified healthcare "
            "professional for medical decisions."
        ),
    )


@dataclass(frozen=True)
class InsightMessages:
    locale: ReportLocale

    def no_data_message(self, metric: str) -> str:
        label = METRIC_LABELS[self.locale].get(metric, metric.replace("_", " "))
        if self.locale == "tr":
            return f"Seçilen dönemde {label} ölçümü kaydedilmemiştir."
        return f"No {label} measurements were recorded in the selected date range."

    def empty_history_recommendation(self) -> str:
        if self.locale == "tr":
            return (
                "Anlamlı içgörüler için zaman içinde daha fazla sağlık ölçümü ekleyin."
            )
        return "Add more health measurements over time to generate meaningful insights."

    def metric_unavailable(self) -> str:
        if self.locale == "tr":
            return "Bu metrik için içgörü kullanılamıyor."
        return "Metric insight is not available."

    def status_phrase(self, status: str) -> str:
        mapping_en = {
            "within_reference_range": "within the informational reference range",
            "below_reference_range": "below the informational reference range",
            "above_reference_range": "above the informational reference range",
            "context_required": "recorded without sufficient measurement context",
            "insufficient_data": "not available for assessment",
            "stable_trend": "associated with a stable trend",
            "increasing_trend": "associated with an increasing trend",
            "decreasing_trend": "associated with a decreasing trend",
        }
        mapping_tr = {
            "within_reference_range": "bilgilendirme referans aralığı içinde",
            "below_reference_range": "bilgilendirme referans aralığının altında",
            "above_reference_range": "bilgilendirme referans aralığının üstünde",
            "context_required": "yeterli ölçüm bağlamı olmadan kaydedildi",
            "insufficient_data": "değerlendirme için uygun değil",
            "stable_trend": "stabil bir trend ile ilişkili",
            "increasing_trend": "artış trendi ile ilişkili",
            "decreasing_trend": "azalış trendi ile ilişkili",
        }
        mapping = mapping_tr if self.locale == "tr" else mapping_en
        return mapping.get(status, "available for review" if self.locale == "en" else "incelenebilir")

    def numeric_metric_message(
        self,
        *,
        metric_label: str,
        status: str,
        reference_description: str,
        urgent: bool,
    ) -> str:
        phrase = self.status_phrase(status)
        if self.locale == "tr":
            message = (
                f"En son {metric_label} ölçümü, yalnızca bilgilendirme amaçlı "
                f"{reference_description} referanslarına göre {phrase}. Bu bir tanı değildir."
            )
            if urgent:
                message += (
                    " Gecikmeden profesyonel değerlendirme düşünülmelidir. "
                    "Ciddi belirtiler varsa yerel acil yardım yönergelerine uyun."
                )
            return message
        message = (
            f"The latest {metric_label} reading is {phrase} "
            f"based on {reference_description} for informational tracking only. "
            "This is not a diagnosis."
        )
        if urgent:
            message += (
                " Prompt professional evaluation should be considered. "
                "If severe symptoms are present, follow local emergency guidance."
            )
        return message

    def glucose_context_message(
        self,
        *,
        value: Decimal,
        severity: str,
        status: str,
        context_label: str | None,
        context_missing: bool,
    ) -> str:
        base = self._glucose_value_message(value, severity, status, context_label)
        if not context_missing:
            return base
        if self.locale == "tr":
            return (
                "Kan şekeri, glikoz bağlamı kaydedilmediği için muhafazakâr genel yetişkin "
                "referans aralığı ile değerlendirildi. Açlık veya tokluk bağlamı kaydı "
                "daha anlamlı bir değerlendirme sağlar. "
                + base
            )
        return (
            "Blood glucose was evaluated using a conservative generic adult reference range "
            "because glucose context was not recorded. Recording fasting or post-meal context "
            "supports a more meaningful assessment. "
            + base
        )

    def _glucose_value_message(
        self,
        value: Decimal,
        severity: str,
        status: str,
        context_label: str | None,
    ) -> str:
        _ = value
        context_text = f"{context_label} " if context_label else ""
        phrase = self.status_phrase(status)
        if self.locale == "tr":
            ctx = {"fasting": "açlık", "post-meal": "tokluk"}.get(context_label or "", context_label or "")
            context_text_tr = f"{ctx} " if ctx else ""
            base = (
                f"En son {context_text_tr}kan şekeri ölçümü, yalnızca bilgilendirme amaçlı "
                f"genel yetişkin referans aralıklarına göre {phrase}. Bu bir tanı değildir."
            )
            if severity == "urgent":
                base += (
                    " Gecikmeden profesyonel değerlendirme düşünülmelidir. "
                    "Ciddi belirtiler varsa yerel acil yardım yönergelerine uyun."
                )
            return base
        base = (
            f"The latest {context_text}blood glucose reading is {phrase} "
            "using general adult reference ranges for informational tracking only. "
            "This is not a diagnosis."
        )
        if severity == "urgent":
            base += (
                " Prompt professional evaluation should be considered. "
                "If severe symptoms are present, follow local emergency guidance."
            )
        return base

    def weight_insufficient(self) -> str:
        if self.locale == "tr":
            return "Trendi anlamlı değerlendirmek için yeterli kilo ölçümü yok."
        return "Not enough weight measurements are available to assess trend meaningfully."

    def weight_stable(self) -> str:
        if self.locale == "tr":
            return (
                "Kilo ölçümleri seçilen dönemde görece stabildir. "
                "Bu trend özeti bilgilendirme amaçlıdır ve tıbbi bir durum göstermez."
            )
        return (
            "Weight readings appear relatively stable across the selected period. "
            "This trend summary is informational and does not indicate a medical condition."
        )

    def weight_moderate_change(self) -> str:
        if self.locale == "tr":
            return (
                "Kilo ölçümleri seçilen dönemde orta düzeyde değişim göstermektedir. "
                "Rutin takibe devam edin; önemli değişiklikleri gerekirse nitelikli bir "
                "sağlık profesyoneli ile paylaşın."
            )
        return (
            "Weight readings show a moderate change over the selected period. "
            "Continue routine tracking and discuss significant changes with a qualified "
            "healthcare professional if needed."
        )

    def weight_notable_change(self) -> str:
        if self.locale == "tr":
            return (
                "Kilo ölçümleri seçilen dönemde belirgin yüzde değişimi göstermektedir. "
                "Bu özet yalnızca bilgilendirme amaçlıdır; tanı veya acil durum göstermez."
            )
        return (
            "Weight readings show a notable percentage change over the selected period. "
            "This tracking summary is informational only and does not diagnose a condition "
            "or indicate an emergency."
        )

    def trend_suffix_increasing(self) -> str:
        if self.locale == "tr":
            return " Seçilen dönemde artış trendi görülmektedir."
        return " Readings show an increasing trend over the selected period."

    def trend_suffix_decreasing(self) -> str:
        if self.locale == "tr":
            return " Seçilen dönemde azalış trendi görülmektedir."
        return " Readings show a decreasing trend over the selected period."

    def alert_recommendation_urgent(self, metric_label: str) -> str:
        if self.locale == "tr":
            return (
                f"Son {metric_label} ölçümleri için gecikmeden profesyonel değerlendirme "
                "düşünülmelidir. Ciddi belirtiler varsa yerel acil yardım yönergelerine uyun."
            )
        return (
            f"Prompt professional evaluation should be considered for recent {metric_label} readings. "
            "If severe symptoms are present, follow local emergency guidance."
        )

    def alert_recommendation_warning(self, metric_label: str) -> str:
        if self.locale == "tr":
            return (
                f"Son {metric_label} ölçümlerini nitelikli bir sağlık profesyoneli ile "
                "paylaşmayı ve sürekli takip için ölçümleri tekrarlamayı değerlendirin."
            )
        return (
            f"Consider sharing recent {metric_label} readings with a qualified healthcare professional "
            "and repeat measurements as appropriate for ongoing tracking."
        )

    def reference_bp(self) -> str:
        if self.locale == "tr":
            return "genel yetişkin kan basıncı referans aralıkları"
        return "general adult blood pressure reference ranges"

    def reference_hr(self) -> str:
        if self.locale == "tr":
            return "dinlenme yetişkin nabız referans aralıkları"
        return "resting adult heart rate reference ranges"


def get_insight_messages(locale: ReportLocale) -> InsightMessages:
    return InsightMessages(locale=locale)
