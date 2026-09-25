export type ApiErrorBody = {
  detail?: string | { msg?: string; type?: string }[];
  message?: string;
  details?: { reason_code?: string };
  success?: boolean;
};

export class ApiClientError extends Error {
  readonly status: number;
  readonly body: ApiErrorBody | null;

  constructor(message: string, status: number, body: ApiErrorBody | null = null) {
    super(message);
    this.name = "ApiClientError";
    this.status = status;
    this.body = body;
  }
}

export type ApiRequestOptions = Omit<RequestInit, "body"> & {
  body?: unknown;
  authToken?: string;
};

export type ApiClient = {
  get: <T>(path: string, options?: ApiRequestOptions) => Promise<T>;
  post: <T>(path: string, options?: ApiRequestOptions) => Promise<T>;
  put: <T>(path: string, options?: ApiRequestOptions) => Promise<T>;
  patch: <T>(path: string, options?: ApiRequestOptions) => Promise<T>;
  delete: <T>(path: string, options?: ApiRequestOptions) => Promise<T>;
};

function buildUrl(baseUrl: string, path: string): string {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${baseUrl}${normalizedPath}`;
}

function buildHeaders(
  options: ApiRequestOptions,
  hasJsonBody: boolean,
): Headers {
  const headers = new Headers(options.headers);

  if (hasJsonBody && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  if (options.authToken) {
    headers.set("Authorization", `Bearer ${options.authToken}`);
  }

  return headers;
}

async function parseJsonBody(response: Response): Promise<ApiErrorBody | null> {
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

  if (Array.isArray(body.detail) && body.detail.length > 0) {
    return body.detail[0]?.msg ?? fallback;
  }

  if (body.message) {
    return body.message;
  }

  return fallback;
}

async function request<T>(
  baseUrl: string,
  path: string,
  options: ApiRequestOptions = {},
): Promise<T> {
  const { body, authToken, ...init } = options;
  const hasJsonBody = body !== undefined;
  const response = await fetch(buildUrl(baseUrl, path), {
    ...init,
    headers: buildHeaders({ ...options, authToken }, hasJsonBody),
    body: hasJsonBody ? JSON.stringify(body) : undefined,
  });

  if (!response.ok) {
    const errorBody = await parseJsonBody(response);
    throw new ApiClientError(
      resolveErrorMessage(errorBody, `Request failed with status ${response.status}`),
      response.status,
      errorBody,
    );
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const contentType = response.headers.get("content-type") ?? "";

  if (contentType.includes("application/json")) {
    return (await response.json()) as T;
  }

  return (await response.text()) as T;
}

export function createApiClient(baseUrl: string): ApiClient {
  return {
    get: (path, options) => request(baseUrl, path, { ...options, method: "GET" }),
    post: (path, options) => request(baseUrl, path, { ...options, method: "POST" }),
    put: (path, options) => request(baseUrl, path, { ...options, method: "PUT" }),
    patch: (path, options) => request(baseUrl, path, { ...options, method: "PATCH" }),
    delete: (path, options) => request(baseUrl, path, { ...options, method: "DELETE" }),
  };
}
