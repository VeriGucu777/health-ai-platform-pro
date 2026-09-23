import { ApiClientError, type ApiErrorBody } from "@/lib/api/client";
import { getApiV1BaseUrl } from "@/lib/config/env";

function buildPdfUrl(
  patientId: string,
  dateFrom?: string,
  dateTo?: string,
  locale?: string,
): string {
  const base = getApiV1BaseUrl();
  const normalizedBase = base.endsWith("/") ? base.slice(0, -1) : base;
  const search = new URLSearchParams();
  if (dateFrom) {
    search.set("date_from", dateFrom);
  }
  if (dateTo) {
    search.set("date_to", dateTo);
  }
  if (locale === "tr" || locale === "en") {
    search.set("locale", locale);
  }
  const qs = search.toString();
  const path = `${normalizedBase}/patients/${patientId}/reports/health-summary.pdf`;
  return qs ? `${path}?${qs}` : path;
}

async function parseErrorBody(response: Response): Promise<ApiErrorBody | null> {
  const contentType = response.headers.get("content-type") ?? "";
  if (!contentType.includes("application/json")) {
    return null;
  }
  try {
    return (await response.json()) as ApiErrorBody;
  } catch {
    return null;
  }
}

function resolveErrorMessage(body: ApiErrorBody | null, fallback: string): string {
  if (!body) {
    return fallback;
  }
  if (typeof body.detail === "string") {
    return body.detail;
  }
  if (body.message) {
    return body.message;
  }
  return fallback;
}

function filenameFromContentDisposition(header: string | null, fallback: string): string {
  if (!header) {
    return fallback;
  }
  const match = /filename\*=UTF-8''([^;]+)|filename="([^"]+)"/i.exec(header);
  const raw = match?.[1] ?? match?.[2];
  if (!raw) {
    return fallback;
  }
  try {
    return decodeURIComponent(raw);
  } catch {
    return raw;
  }
}

export type HealthSummaryPdfResult = {
  blob: Blob;
  filename: string;
};

export async function fetchHealthSummaryPdf(
  authToken: string,
  patientId: string,
  options?: { date_from?: string; date_to?: string; locale?: string },
): Promise<HealthSummaryPdfResult> {
  const url = buildPdfUrl(patientId, options?.date_from, options?.date_to, options?.locale);
  const acceptLanguage =
    options?.locale === "tr" ? "tr-TR,tr;q=0.9,en;q=0.8" : "en-US,en;q=0.9";

  const response = await fetch(url, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${authToken}`,
      "Accept-Language": acceptLanguage,
    },
  });

  if (!response.ok) {
    const errorBody = await parseErrorBody(response);
    throw new ApiClientError(
      resolveErrorMessage(errorBody, `Request failed with status ${response.status}`),
      response.status,
      errorBody,
    );
  }

  const blob = await response.blob();
  const filename = filenameFromContentDisposition(
    response.headers.get("Content-Disposition"),
    `health-summary-${patientId}.pdf`,
  );

  return { blob, filename };
}

export function triggerBlobDownload(blob: Blob, filename: string): void {
  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = filename;
  anchor.rel = "noopener";
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(objectUrl);
}
