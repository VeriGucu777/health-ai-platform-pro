"""Build patient health summary PDF documents."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.application.dtos.patient_health_report import PatientHealthReportContextDTO
from app.application.reports.pdf_fonts import PDF_FONT_NAME, ensure_pdf_unicode_font_registered
from app.core.reference_ranges import REPORT_STATISTICS_METRICS

MAX_TREND_ROWS = 10

METRIC_LABELS_TR = {
    "blood_glucose": "Kan Şekeri",
    "systolic_pressure": "Sistolik Tansiyon",
    "diastolic_pressure": "Diyastolik Tansiyon",
    "heart_rate": "Nabız",
    "weight_kg": "Kilo",
}

TREND_LABELS_TR = {
    "increasing": "Artış",
    "decreasing": "Azalış",
    "stable": "Stabil",
    "insufficient_data": "Yetersiz veri",
}

RANGE_LABELS_TR = {
    "within_reference_range": "Referans aralığında",
    "below_reference_range": "Referans altı",
    "above_reference_range": "Referans üstü",
    "not_applicable": "Uygulanamaz",
}


def build_patient_health_pdf(context: PatientHealthReportContextDTO) -> bytes:
    """Render the patient health report PDF and return raw bytes."""
    font_name = ensure_pdf_unicode_font_registered()
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title="Patient Health Report",
    )

    styles = _build_styles(font_name)
    story: list = []

    story.append(Paragraph("Health AI Platform Pro", styles["title"]))
    story.append(Paragraph("Hasta Sağlık Raporu", styles["heading"]))
    story.append(
        Paragraph(
            f"Oluşturulma Tarihi (UTC): {_format_datetime(context.generated_at)}",
            styles["body"],
        )
    )
    story.append(Spacer(1, 0.4 * cm))

    story.extend(_patient_section(context, styles))
    story.extend(_period_section(context, styles))
    story.extend(_medical_records_section(context, styles))
    story.extend(_measurement_summary_section(context, styles))
    story.extend(_statistics_section(context, styles))
    story.extend(_trends_section(context, styles))
    story.extend(_insights_section(context, styles))
    story.extend(_alerts_section(context, styles))
    story.extend(_recommendations_section(context, styles))
    story.extend(_disclaimer_section(context, styles))

    doc.build(story)
    return buffer.getvalue()


def _build_styles(font_name: str) -> dict[str, ParagraphStyle]:
    return {
        "title": ParagraphStyle(
            "title",
            fontName=font_name,
            fontSize=16,
            leading=20,
            spaceAfter=6,
        ),
        "heading": ParagraphStyle(
            "heading",
            fontName=font_name,
            fontSize=13,
            leading=16,
            spaceBefore=10,
            spaceAfter=6,
            textColor=colors.HexColor("#1F2937"),
        ),
        "body": ParagraphStyle(
            "body",
            fontName=font_name,
            fontSize=10,
            leading=14,
            spaceAfter=4,
        ),
        "small": ParagraphStyle(
            "small",
            fontName=font_name,
            fontSize=9,
            leading=12,
            spaceAfter=3,
            textColor=colors.HexColor("#374151"),
        ),
        "disclaimer": ParagraphStyle(
            "disclaimer",
            fontName=font_name,
            fontSize=9,
            leading=12,
            spaceAfter=6,
            textColor=colors.HexColor("#4B5563"),
        ),
    }


def _patient_section(
    context: PatientHealthReportContextDTO,
    styles: dict[str, ParagraphStyle],
) -> list:
    patient = context.patient
    full_name = f"{patient.first_name} {patient.last_name}"
    lines = [
        Paragraph("Hasta Bilgileri", styles["heading"]),
        Paragraph(f"Ad Soyad: {_escape(full_name)}", styles["body"]),
        Paragraph(f"Doğum Tarihi: {patient.date_of_birth.isoformat()}", styles["body"]),
        Paragraph(f"Cinsiyet: {_escape(patient.gender)}", styles["body"]),
        Paragraph(f"Telefon: {_escape(patient.phone or '-')}", styles["body"]),
        Paragraph(
            f"Durum: {'Aktif' if patient.is_active else 'Pasif'}",
            styles["body"],
        ),
    ]
    if patient.notes:
        lines.append(Paragraph(f"Notlar: {_escape(patient.notes)}", styles["body"]))
    lines.append(Spacer(1, 0.2 * cm))
    return lines


def _period_section(
    context: PatientHealthReportContextDTO,
    styles: dict[str, ParagraphStyle],
) -> list:
    return [
        Paragraph("Rapor Dönemi", styles["heading"]),
        Paragraph(
            f"Başlangıç (UTC): {_format_datetime(context.date_from)}",
            styles["body"],
        ),
        Paragraph(
            f"Bitiş (UTC): {_format_datetime(context.date_to)}",
            styles["body"],
        ),
        Spacer(1, 0.2 * cm),
    ]


def _medical_records_section(
    context: PatientHealthReportContextDTO,
    styles: dict[str, ParagraphStyle],
) -> list:
    lines = [Paragraph("Tıbbi Kayıt Özeti", styles["heading"])]
    if not context.medical_records:
        lines.append(
            Paragraph("Seçilen dönemde tıbbi kayıt bulunmamaktadır.", styles["body"])
        )
        lines.append(Spacer(1, 0.2 * cm))
        return lines

    if context.medical_records_truncated:
        lines.append(
            Paragraph(
                "Bu raporda en yeni 100 tıbbi kayıt gösterilmektedir. "
                f"Seçilen dönemde toplam {context.medical_records_total_in_range} kayıt "
                "bulunmaktadır.",
                styles["small"],
            )
        )

    table_data = [["Tarih", "Tür", "Başlık", "Doktor", "Hastane"]]
    for record in context.medical_records:
        table_data.append(
            [
                _format_datetime(record.record_date),
                _escape(record.record_type),
                _escape(record.title),
                _escape(record.doctor_name or "-"),
                _escape(record.hospital_name or "-"),
            ]
        )

    table = Table(table_data, repeatRows=1, colWidths=[3.2 * cm, 2.4 * cm, 4.5 * cm, 3.2 * cm, 3.2 * cm])
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), PDF_FONT_NAME),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E5E7EB")),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    lines.extend([table, Spacer(1, 0.2 * cm)])
    return lines


def _measurement_summary_section(
    context: PatientHealthReportContextDTO,
    styles: dict[str, ParagraphStyle],
) -> list:
    return [
        Paragraph("Sağlık Ölçümü Özeti", styles["heading"]),
        Paragraph(
            f"Seçilen dönemdeki toplam ölçüm sayısı: "
            f"{context.measurement_summary.total_measurement_count}",
            styles["body"],
        ),
        Spacer(1, 0.2 * cm),
    ]


def _statistics_section(
    context: PatientHealthReportContextDTO,
    styles: dict[str, ParagraphStyle],
) -> list:
    lines = [Paragraph("Temel Metrik İstatistikleri", styles["heading"])]
    stats_by_metric = {
        item.metric: item for item in context.measurement_summary.overall
    }

    table_data = [["Metrik", "Adet", "Ort.", "Min", "Max", "Trend", "Referans"]]
    for metric in REPORT_STATISTICS_METRICS:
        item = stats_by_metric.get(metric)
        if item is None:
            continue
        table_data.append(
            [
                METRIC_LABELS_TR.get(metric, metric),
                str(item.measurement_count),
                _format_decimal(item.average),
                _format_decimal(item.minimum),
                _format_decimal(item.maximum),
                TREND_LABELS_TR.get(item.trend_direction, item.trend_direction),
                RANGE_LABELS_TR.get(item.target_range_status, item.target_range_status),
            ]
        )

    if len(table_data) == 1:
        lines.append(
            Paragraph("Seçilen dönemde rapor metrikleri için veri bulunmamaktadır.", styles["body"])
        )
        lines.append(Spacer(1, 0.2 * cm))
        return lines

    table = Table(
        table_data,
        repeatRows=1,
        colWidths=[3.2 * cm, 1.4 * cm, 1.8 * cm, 1.8 * cm, 1.8 * cm, 2.2 * cm, 3.2 * cm],
    )
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), PDF_FONT_NAME),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E5E7EB")),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
            ]
        )
    )
    lines.extend([table, Spacer(1, 0.2 * cm)])
    return lines


def _trends_section(
    context: PatientHealthReportContextDTO,
    styles: dict[str, ParagraphStyle],
) -> list:
    lines = [Paragraph("Haftalık Sağlık Ölçümü Trendleri", styles["heading"])]
    periods = context.measurement_trends.periods[-MAX_TREND_ROWS:]
    if not periods:
        lines.append(Paragraph("Seçilen dönemde haftalık trend verisi bulunmamaktadır.", styles["body"]))
        lines.append(Spacer(1, 0.2 * cm))
        return lines

    table_data = [["Hafta Başlangıcı", "Metrik", "Adet", "Ortalama"]]
    for period in periods:
        metrics_by_name = {item.metric: item for item in period.metrics}
        for metric in REPORT_STATISTICS_METRICS:
            item = metrics_by_name.get(metric)
            if item is None or item.measurement_count == 0:
                continue
            table_data.append(
                [
                    _format_datetime(period.period_start),
                    METRIC_LABELS_TR.get(metric, metric),
                    str(item.measurement_count),
                    _format_decimal(item.average),
                ]
            )

    if len(table_data) == 1:
        lines.append(Paragraph("Seçilen dönemde haftalık trend verisi bulunmamaktadır.", styles["body"]))
        lines.append(Spacer(1, 0.2 * cm))
        return lines

    table = Table(table_data, repeatRows=1, colWidths=[3.5 * cm, 3.5 * cm, 1.5 * cm, 2.5 * cm])
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), PDF_FONT_NAME),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E5E7EB")),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
            ]
        )
    )
    lines.extend([table, Spacer(1, 0.2 * cm)])
    return lines


def _insights_section(
    context: PatientHealthReportContextDTO,
    styles: dict[str, ParagraphStyle],
) -> list:
    lines = [
        Paragraph("Klinik İçgörüler", styles["heading"]),
        Paragraph(
            f"Genel durum: {_escape(context.clinical_insights.overall_status)}",
            styles["body"],
        ),
    ]
    for insight in context.clinical_insights.insights:
        metric_label = METRIC_LABELS_TR.get(insight.metric, insight.metric)
        lines.append(
            Paragraph(
                f"{_escape(metric_label)} | {_escape(insight.severity)} | "
                f"Son: {_format_decimal(insight.latest_value)} | "
                f"Ort: {_format_decimal(insight.average_value)}",
                styles["small"],
            )
        )
        lines.append(Paragraph(_escape(insight.message), styles["small"]))
    lines.append(Spacer(1, 0.2 * cm))
    return lines


def _alerts_section(
    context: PatientHealthReportContextDTO,
    styles: dict[str, ParagraphStyle],
) -> list:
    lines = [Paragraph("Uyarılar", styles["heading"])]
    if not context.clinical_insights.alerts:
        lines.append(Paragraph("Seçilen dönemde uyarı bulunmamaktadır.", styles["body"]))
        lines.append(Spacer(1, 0.2 * cm))
        return lines

    for alert in context.clinical_insights.alerts:
        metric_label = METRIC_LABELS_TR.get(alert.metric, alert.metric)
        lines.append(
            Paragraph(
                f"{_escape(metric_label)} ({_escape(alert.severity)}): {_escape(alert.message)}",
                styles["small"],
            )
        )
    lines.append(Spacer(1, 0.2 * cm))
    return lines


def _recommendations_section(
    context: PatientHealthReportContextDTO,
    styles: dict[str, ParagraphStyle],
) -> list:
    lines = [Paragraph("Takip Önerileri", styles["heading"])]
    if not context.clinical_insights.recommendations:
        lines.append(Paragraph("Takip önerisi bulunmamaktadır.", styles["body"]))
        lines.append(Spacer(1, 0.2 * cm))
        return lines

    for recommendation in context.clinical_insights.recommendations:
        lines.append(Paragraph(_escape(recommendation.message), styles["small"]))
    lines.append(Spacer(1, 0.2 * cm))
    return lines


def _disclaimer_section(
    context: PatientHealthReportContextDTO,
    styles: dict[str, ParagraphStyle],
) -> list:
    return [
        Paragraph("Tıbbi Sorumluluk Reddi", styles["heading"]),
        Paragraph(_escape(context.insights_disclaimer), styles["disclaimer"]),
        Paragraph(_escape(context.report_disclaimer), styles["disclaimer"]),
    ]


def _format_datetime(value: datetime) -> str:
    from datetime import UTC

    if value.tzinfo is None:
        return value.isoformat(sep=" ", timespec="seconds") + " UTC"
    return value.astimezone(UTC).isoformat(sep=" ", timespec="seconds").replace("+00:00", " UTC")


def _format_decimal(value: Decimal | None) -> str:
    if value is None:
        return "-"
    return format(value, "f").rstrip("0").rstrip(".") or "0"


def _escape(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
