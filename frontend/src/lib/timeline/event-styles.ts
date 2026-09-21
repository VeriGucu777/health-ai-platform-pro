export type TimelineVisualCategory =
  | "medical"
  | "measurement"
  | "appointment"
  | "overdue"
  | "derived"
  | "risk"
  | "default";

export function resolveTimelineCategory(eventType: string): TimelineVisualCategory {
  if (eventType === "appointment_overdue") {
    return "overdue";
  }
  if (eventType.startsWith("medical_record")) {
    return "medical";
  }
  if (eventType === "health_measurement") {
    return "measurement";
  }
  if (eventType.startsWith("appointment_")) {
    return "appointment";
  }
  if (eventType === "measurement_trend_derived") {
    return "derived";
  }
  if (eventType === "risk_current_snapshot") {
    return "risk";
  }
  return "default";
}

export function categoryBadgeClass(category: TimelineVisualCategory): string {
  switch (category) {
    case "medical":
      return "bg-brand-100 text-brand-900";
    case "measurement":
      return "bg-teal-100 text-teal-900";
    case "appointment":
      return "bg-slate-100 text-slate-800";
    case "overdue":
      return "bg-amber-100 text-amber-950 ring-1 ring-amber-300";
    case "derived":
      return "bg-violet-100 text-violet-900";
    case "risk":
      return "bg-indigo-100 text-indigo-900";
    default:
      return "bg-gray-100 text-gray-800";
  }
}

export function categoryIconLabel(category: TimelineVisualCategory): string {
  switch (category) {
    case "medical":
      return "MR";
    case "measurement":
      return "M";
    case "appointment":
      return "A";
    case "overdue":
      return "!";
    case "derived":
      return "T";
    case "risk":
      return "R";
    default:
      return "•";
  }
}

export function severityBadgeClass(severity: string | null): string | null {
  if (!severity) {
    return null;
  }

  switch (severity) {
    case "urgent":
      return "bg-red-100 text-red-900";
    case "warning":
      return "bg-amber-100 text-amber-950";
    case "info":
      return "bg-slate-100 text-slate-700";
    default:
      return "bg-slate-100 text-slate-700";
  }
}

export function sortTimelineEventsOldestFirst<T extends { occurred_at: string }>(
  events: T[],
): T[] {
  return [...events].sort(
    (left, right) =>
      new Date(left.occurred_at).getTime() - new Date(right.occurred_at).getTime(),
  );
}

export function dateInputToUtcIsoStart(dateValue: string): string {
  return new Date(`${dateValue}T00:00:00.000Z`).toISOString();
}

export function dateInputToUtcIsoEnd(dateValue: string): string {
  return new Date(`${dateValue}T23:59:59.999Z`).toISOString();
}
