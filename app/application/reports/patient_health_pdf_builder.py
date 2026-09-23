"""Build patient health summary PDF documents."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.application.dtos.patient_health_report import PatientHealthReportContextDTO
from app.application.reports.pdf_fonts import PDF_FONT_NAME, ensure_pdf_unicode_font_registered
from app.application.reports.report_i18n import (
    ReportCopy,
    format_report_date,
    format_report_datetime,
    get_report_copy,
)
from app.core.reference_ranges import MAX_MEDICAL_RECORDS_IN_REPORT, REPORT_STATISTICS_METRICS

MAX_TREND_ROWS = 10


def build_patient_health_pdf(context: PatientHealthReportContextDTO) -> bytes:
    """Render the patient health report PDF and return raw bytes."""
    copy = get_report_copy(context.locale)
    font_name = ensure_pdf_unicode_font_registered()
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title=copy.document_title,
    )

    styles = _build_styles(font_name)
    story: list = []

    story.append(Paragraph(_escape(copy.platform_name), styles["title"]))
    story.append(Paragraph(_escape(copy.report_title), styles["heading"]))
    story.append(
        Paragraph(
            f"{_escape(copy.generated_at_label)}: "
            f"{_format_datetime(context.generated_at, context.locale)}",
            styles["body"],
        )
    )
    story.append(Spacer(1, 0.4 * cm))

    story.extend(_patient_section(context, styles, copy))
    story.extend(_period_section(context, styles, copy))
    story.extend(_medical_records_section(context, styles, copy))
    story.extend(_measurement_summary_section(context, styles, copy))
    story.extend(_statistics_section(context, styles, copy))
    story.extend(_trends_section(context, styles, copy))
    story.extend(_insights_section(context, styles, copy))
    story.extend(_alerts_section(context, styles, copy))
    story.extend(_recommendations_section(context, styles, copy))
    story.extend(_disclaimer_section(context, styles, copy))

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
    copy: ReportCopy,
) -> list:
    patient = context.patient
    full_name = f"{patient.first_name} {patient.last_name}"
    status = copy.active_label if patient.is_active else copy.inactive_label
    lines = [
        Paragraph(_escape(copy.patient_section_title), styles["heading"]),
        Paragraph(f"{_escape(copy.full_name_label)}: {_escape(full_name)}", styles["body"]),
        Paragraph(
            f"{_escape(copy.date_of_birth_label)}: "
            f"{format_report_date(patient.date_of_birth, context.locale)}",
            styles["body"],
        ),
        Paragraph(
            f"{_escape(copy.gender_label)}: "
            f"{_escape(copy.gender_label_value(patient.gender))}",
            styles["body"],
        ),
        Paragraph(f"{_escape(copy.phone_label)}: {_escape(patient.phone or '-')}", styles["body"]),
        Paragraph(f"{_escape(copy.status_label)}: {_escape(status)}", styles["body"]),
    ]
    if patient.notes:
        lines.append(
            Paragraph(f"{_escape(copy.notes_label)}: {_escape(patient.notes)}", styles["body"])
        )
    lines.append(Spacer(1, 0.2 * cm))
    return lines


def _period_section(
    context: PatientHealthReportContextDTO,
    styles: dict[str, ParagraphStyle],
    copy: ReportCopy,
) -> list:
    return [
        Paragraph(_escape(copy.period_section_title), styles["heading"]),
        Paragraph(
            f"{_escape(copy.period_from_label)}: "
            f"{_format_datetime(context.date_from, context.locale)}",
            styles["body"],
        ),
        Paragraph(
            f"{_escape(copy.period_to_label)}: "
            f"{_format_datetime(context.date_to, context.locale)}",
            styles["body"],
        ),
        Spacer(1, 0.2 * cm),
    ]


def _medical_records_section(
    context: PatientHealthReportContextDTO,
    styles: dict[str, ParagraphStyle],
    copy: ReportCopy,
) -> list:
    lines = [Paragraph(_escape(copy.medical_records_title), styles["heading"])]
    if not context.medical_records:
        lines.append(Paragraph(_escape(copy.no_medical_records), styles["body"]))
        lines.append(Spacer(1, 0.2 * cm))
        return lines

    if context.medical_records_truncated:
        lines.append(
            Paragraph(
                _escape(
                    copy.medical_records_truncated.format(
                        limit=MAX_MEDICAL_RECORDS_IN_REPORT,
                        total=context.medical_records_total_in_range,
                    )
                ),
                styles["small"],
            )
        )

    table_data = [
        [
            copy.table_date,
            copy.table_type,
            copy.table_title,
            copy.table_doctor,
            copy.table_hospital,
        ]
    ]
    for record in context.medical_records:
        table_data.append(
            [
                _format_datetime(record.record_date, context.locale),
                _escape(copy.record_type_label(record.record_type)),
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
    copy: ReportCopy,
) -> list:
    return [
        Paragraph(_escape(copy.measurement_summary_title), styles["heading"]),
        Paragraph(
            f"{_escape(copy.measurement_count_label)}: "
            f"{context.measurement_summary.total_measurement_count}",
            styles["body"],
        ),
        Spacer(1, 0.2 * cm),
    ]


def _statistics_section(
    context: PatientHealthReportContextDTO,
    styles: dict[str, ParagraphStyle],
    copy: ReportCopy,
) -> list:
    lines = [Paragraph(_escape(copy.statistics_title), styles["heading"])]
    stats_by_metric = {
        item.metric: item for item in context.measurement_summary.overall
    }

    table_data = [
        [
            copy.table_metric,
            copy.table_count,
            copy.table_avg,
            copy.table_min,
            copy.table_max,
            copy.table_trend,
            copy.table_reference,
        ]
    ]
    for metric in REPORT_STATISTICS_METRICS:
        item = stats_by_metric.get(metric)
        if item is None:
            continue
        table_data.append(
            [
                copy.metric_label(metric),
                str(item.measurement_count),
                _format_decimal(item.average),
                _format_decimal(item.minimum),
                _format_decimal(item.maximum),
                copy.trend_label(item.trend_direction),
                copy.range_label(item.target_range_status),
            ]
        )

    if len(table_data) == 1:
        lines.append(Paragraph(_escape(copy.no_statistics), styles["body"]))
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
    copy: ReportCopy,
) -> list:
    lines = [Paragraph(_escape(copy.trends_title), styles["heading"])]
    periods = context.measurement_trends.periods[-MAX_TREND_ROWS:]
    if not periods:
        lines.append(Paragraph(_escape(copy.no_trends), styles["body"]))
        lines.append(Spacer(1, 0.2 * cm))
        return lines

    table_data = [[copy.table_week_start, copy.table_metric, copy.table_count, copy.table_avg]]
    for period in periods:
        metrics_by_name = {item.metric: item for item in period.metrics}
        for metric in REPORT_STATISTICS_METRICS:
            item = metrics_by_name.get(metric)
            if item is None or item.measurement_count == 0:
                continue
            table_data.append(
                [
                    _format_datetime(period.period_start, context.locale),
                    copy.metric_label(metric),
                    str(item.measurement_count),
                    _format_decimal(item.average),
                ]
            )

    if len(table_data) == 1:
        lines.append(Paragraph(_escape(copy.no_trends), styles["body"]))
        lines.append(Spacer(1, 0.2 * cm))
        return lines

    table = Table(table_data, repeatRows=1, colWidths=[3.5 * cm, 3.5 * cm, 1.5 * cm, 2.5 * cm])
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), PDF_FONT_NAME),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E5E7EB")),
            ]
        )
    )
    lines.extend([table, Spacer(1, 0.2 * cm)])
    return lines


def _insights_section(
    context: PatientHealthReportContextDTO,
    styles: dict[str, ParagraphStyle],
    copy: ReportCopy,
) -> list:
    overall = copy.overall_status_label(context.clinical_insights.overall_status)
    lines = [
        Paragraph(_escape(copy.insights_title), styles["heading"]),
        Paragraph(
            f"{_escape(copy.overall_status_heading)}: {_escape(overall)}",
            styles["body"],
        ),
    ]
    for insight in context.clinical_insights.insights:
        metric_label = copy.metric_label(insight.metric)
        severity = copy.severity_label(insight.severity)
        lines.append(
            Paragraph(
                f"{_escape(metric_label)} | {_escape(severity)} | "
                f"{_escape(copy.latest_label)}: {_format_decimal(insight.latest_value)} | "
                f"{_escape(copy.average_label)}: {_format_decimal(insight.average_value)}",
                styles["small"],
            )
        )
        lines.append(Paragraph(_escape(insight.message), styles["small"]))
    lines.append(Spacer(1, 0.2 * cm))
    return lines


def _alerts_section(
    context: PatientHealthReportContextDTO,
    styles: dict[str, ParagraphStyle],
    copy: ReportCopy,
) -> list:
    lines = [Paragraph(_escape(copy.alerts_title), styles["heading"])]
    if not context.clinical_insights.alerts:
        lines.append(Paragraph(_escape(copy.no_alerts), styles["body"]))
        lines.append(Spacer(1, 0.2 * cm))
        return lines

    for alert in context.clinical_insights.alerts:
        metric_label = copy.metric_label(alert.metric)
        severity = copy.severity_label(alert.severity)
        lines.append(
            Paragraph(
                f"{_escape(metric_label)} ({_escape(severity)}): {_escape(alert.message)}",
                styles["small"],
            )
        )
    lines.append(Spacer(1, 0.2 * cm))
    return lines


def _recommendations_section(
    context: PatientHealthReportContextDTO,
    styles: dict[str, ParagraphStyle],
    copy: ReportCopy,
) -> list:
    lines = [Paragraph(_escape(copy.recommendations_title), styles["heading"])]
    if not context.clinical_insights.recommendations:
        lines.append(Paragraph(_escape(copy.no_recommendations), styles["body"]))
        lines.append(Spacer(1, 0.2 * cm))
        return lines

    for recommendation in context.clinical_insights.recommendations:
        lines.append(Paragraph(_escape(recommendation.message), styles["small"]))
    lines.append(Spacer(1, 0.2 * cm))
    return lines


def _disclaimer_section(
    context: PatientHealthReportContextDTO,
    styles: dict[str, ParagraphStyle],
    copy: ReportCopy,
) -> list:
    return [
        Paragraph(_escape(copy.disclaimer_title), styles["heading"]),
        Paragraph(_escape(context.insights_disclaimer), styles["disclaimer"]),
        Paragraph(_escape(context.report_disclaimer), styles["disclaimer"]),
    ]


def _format_datetime(value: datetime, locale: str) -> str:
    from app.application.reports.report_i18n import ReportLocale, parse_report_locale

    report_locale: ReportLocale = parse_report_locale(locale)
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return format_report_datetime(value, report_locale)
    return format_report_datetime(value, report_locale)


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
