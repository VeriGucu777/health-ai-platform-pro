import type { SupportedLocale } from "@/lib/i18n/locale";
import type { CommonContent } from "@/lib/i18n/types";
import type { TimelineEvent } from "@/lib/api/clinical-timeline";

const UUID_PATTERN =
  /[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}/gi;

const FLOAT_PATTERN = /(\d+\.\d+)/g;

const APPOINTMENT_HEADLINE = /^Appointment\s+(.+)$/i;
const RISK_SNAPSHOT_HEADLINE = /^(.+)\s+risk snapshot \(current\)$/i;

const OVERDUE_DETAIL =
  /^Scheduled appointment on (\d{4}-\d{2}-\d{2}) \(([^)]+)\) has not been marked completed\.$/i;

const TREND_DETAIL =
  /^Rule-based trend analysis over (\d+) measurements in the selected period shows an increasing pattern \(informational average: ([0-9.]+)\)\.$/i;

const RISK_DETAIL =
  /^On-demand rule-based assessment \(([^)]+)\): risk level ([^,]+), score ([^.]+)\. This is a point-in-time snapshot, not stored clinical history\.$/i;

const APPOINTMENT_TYPE_TR: Record<string, string> = {
  follow_up: "Takip randevusu",
  control: "Kontrol randevusu",
};

const APPOINTMENT_NOTE_TR: Record<string, string> = {
  "DEMO overdue follow-up": "DEMO gecikmiş takip",
  "DEMO completed control visit": "DEMO tamamlanan kontrol ziyareti",
  "DEMO future control visit": "DEMO gelecek kontrol ziyareti",
};

function roundEmbeddedFloats(text: string): string {
  return text.replace(FLOAT_PATTERN, (match) => {
    const value = Number.parseFloat(match);
    if (Number.isNaN(value)) {
      return match;
    }

    return String(Number(value.toFixed(1)));
  });
}

function sanitizeTimelineDetail(detail: string): string {
  let text = detail.replace(/\s*Related measurement IDs:.*$/i, "");
  text = text.replace(UUID_PATTERN, "");
  text = roundEmbeddedFloats(text);
  text = text.replace(/\(\s*,/g, "(").replace(/,\s*\)/g, ")").replace(/\s{2,}/g, " ");
  return text.trim();
}

function formatTrDecimal(value: string): string {
  return value.replace(".", ",");
}

function formatTrDateFromIso(isoDate: string): string {
  const [year, month, day] = isoDate.split("-");
  if (!year || !month || !day) {
    return isoDate;
  }

  return `${day}.${month}.${year}`;
}

function translateAppointmentType(value: string): string {
  const key = value.trim().toLowerCase();
  return APPOINTMENT_TYPE_TR[key] ?? value.replaceAll("_", " ");
}

function translateMeasurementSegment(segment: string): string {
  const text = segment.trim();

  const glucoseMatch = text.match(/^blood glucose ([0-9.]+)(?: \(([^)]+)\))?$/i);
  if (glucoseMatch) {
    const value = glucoseMatch[1];
    const context = glucoseMatch[2]?.trim().toLowerCase();
    if (!context || context === "unspecified context") {
      return `Kan şekeri: ${value}`;
    }

    return `Kan şekeri: ${value} (${context})`;
  }

  const bpMatch = text.match(/^blood pressure ([0-9.]+)\/([0-9.]+) mmHg$/i);
  if (bpMatch) {
    return `Tansiyon: ${bpMatch[1]}/${bpMatch[2]} mmHg`;
  }

  const systolicMatch = text.match(/^systolic pressure ([0-9.]+) mmHg$/i);
  if (systolicMatch) {
    return `Sistolik tansiyon: ${systolicMatch[1]} mmHg`;
  }

  const diastolicMatch = text.match(/^diastolic pressure ([0-9.]+) mmHg$/i);
  if (diastolicMatch) {
    return `Diyastolik tansiyon: ${diastolicMatch[1]} mmHg`;
  }

  const heartRateMatch = text.match(/^heart rate ([0-9.]+) bpm$/i);
  if (heartRateMatch) {
    return `Kalp hızı: ${heartRateMatch[1]} bpm`;
  }

  const weightMatch = text.match(/^weight ([0-9.]+) kg$/i);
  if (weightMatch) {
    return `Kilo: ${weightMatch[1]} kg`;
  }

  const insulinMatch = text.match(/^insulin ([0-9.]+) units$/i);
  if (insulinMatch) {
    return `İnsülin: ${insulinMatch[1]} ünite`;
  }

  const exerciseMatch = text.match(/^exercise ([0-9.]+) min$/i);
  if (exerciseMatch) {
    return `Egzersiz: ${exerciseMatch[1]} dk`;
  }

  return text;
}

function translateHealthMeasurementDetail(detail: string): string {
  return detail
    .split(";")
    .map((segment) => translateMeasurementSegment(segment))
    .join("; ");
}

function translateAppointmentDetail(detail: string): string {
  const parts = detail.split(" — ");
  if (parts.length === 1) {
    return translateAppointmentType(detail);
  }

  const typeLabel = translateAppointmentType(parts[0] ?? "");
  const note = parts.slice(1).join(" — ").trim();
  const translatedNote = APPOINTMENT_NOTE_TR[note] ?? note;

  return `${typeLabel} — ${translatedNote}`;
}

function translateTimelineDetailTr(
  detail: string,
  eventType: string | undefined,
  detailPhrases: CommonContent["timeline"]["detailPhrases"],
): string {
  if (detailPhrases[detail]) {
    return detailPhrases[detail];
  }

  const overdueMatch = detail.match(OVERDUE_DETAIL);
  if (overdueMatch) {
    const dateLabel = formatTrDateFromIso(overdueMatch[1] ?? "");
    const typeLabel = translateAppointmentType(overdueMatch[2] ?? "").toLowerCase();
    return `${dateLabel} tarihli ${typeLabel} tamamlandı olarak işaretlenmemiş.`;
  }

  const trendMatch = detail.match(TREND_DETAIL);
  if (trendMatch) {
    const count = trendMatch[1];
    const average = formatTrDecimal(trendMatch[2] ?? "");
    return `Seçilen dönemdeki ${count} ölçümün kural tabanlı analizi artış eğilimi gösteriyor. Bilgilendirici ortalama: ${average}.`;
  }

  const riskMatch = detail.match(RISK_DETAIL);
  if (riskMatch) {
    const model = riskMatch[1];
    const level = riskMatch[2]?.trim() ?? "";
    const score = riskMatch[3]?.trim() ?? "";
    return `Talep üzerine kural tabanlı değerlendirme (${model}): risk düzeyi ${level}, skor ${score}. Bu, saklanan klinik geçmiş değil; anlık bir görüntüdür.`;
  }

  if (eventType === "health_measurement" || detail.includes("blood glucose")) {
    return applyDetailLexicon(translateHealthMeasurementDetail(detail), detailPhrases);
  }

  if (
    eventType?.startsWith("appointment") ||
    detail.includes("_") ||
    detail.includes(" — ")
  ) {
    return applyDetailLexicon(translateAppointmentDetail(detail), detailPhrases);
  }

  return applyDetailLexicon(detail, detailPhrases);
}

function applyDetailLexicon(
  text: string,
  detailPhrases: CommonContent["timeline"]["detailPhrases"],
): string {
  let result = text;

  for (const [source, target] of Object.entries(detailPhrases)) {
    if (result === source) {
      return target;
    }
  }

  for (const [source, target] of Object.entries(detailPhrases)) {
    if (source.length <= 2) {
      continue;
    }

    result = result.replaceAll(source, target);
  }

  return result;
}

/** Removes UUID lists and normalizes numeric precision; localizes detail text for TR. */
export function formatTimelineDetail(
  detail: string,
  locale: SupportedLocale,
  eventType?: string,
  detailPhrases: CommonContent["timeline"]["detailPhrases"] = {},
): string {
  const sanitized = sanitizeTimelineDetail(detail);

  if (locale === "en") {
    return sanitized;
  }

  return translateTimelineDetailTr(sanitized, eventType, detailPhrases);
}

function resolveHeadlineForLocale(
  headline: string,
  locale: SupportedLocale,
  headlines: CommonContent["timeline"]["headlines"],
): string {
  if (locale === "en") {
    return headline;
  }

  const exact = headlines[headline];
  if (exact) {
    return exact;
  }

  const appointmentMatch = headline.match(APPOINTMENT_HEADLINE);
  if (appointmentMatch) {
    const statusKey = `Appointment ${appointmentMatch[1]}`;
    return headlines[statusKey] ?? headline;
  }

  const riskMatch = headline.match(RISK_SNAPSHOT_HEADLINE);
  if (riskMatch) {
    const diseaseKey = `${riskMatch[1]} risk snapshot (current)`;
    return headlines[diseaseKey] ?? headline;
  }

  return headline;
}

export function formatTimelineHeadline(
  event: TimelineEvent,
  locale: SupportedLocale,
  headlines: CommonContent["timeline"]["headlines"],
): string {
  return resolveHeadlineForLocale(event.headline, locale, headlines);
}

export function formatSourceKind(
  kind: string,
  sourceKinds: CommonContent["timeline"]["sourceKinds"],
): string {
  return sourceKinds[kind] ?? kind.replaceAll("_", " ");
}

export function formatSeverityLevel(
  severity: string | null,
  severityLevels: CommonContent["timeline"]["severityLevels"],
): string | null {
  if (!severity) {
    return null;
  }

  const key = severity.toLowerCase();
  return severityLevels[key] ?? severity;
}

export function formatPatientGender(
  gender: string,
  genders: CommonContent["patients"]["genders"],
): string {
  const key = gender.trim().toLowerCase();
  return genders[key] ?? gender;
}

export function calculateAgeYears(dateOfBirth: string): number {
  const birth = new Date(dateOfBirth);
  const today = new Date();
  let age = today.getFullYear() - birth.getFullYear();
  const monthDelta = today.getMonth() - birth.getMonth();

  if (monthDelta < 0 || (monthDelta === 0 && today.getDate() < birth.getDate())) {
    age -= 1;
  }

  return age;
}
