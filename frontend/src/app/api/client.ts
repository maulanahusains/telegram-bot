export interface BackendErrorEnvelope {
  ok: false;
  error: {
    code: string;
    message: string;
    request_id?: string | null;
  };
}

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
    public readonly requestId?: string | null
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function apiRequest<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`/api/v1${path}`, {
    ...options,
    headers,
    credentials: "same-origin"
  });
  const payload: unknown = await readJson(response);

  if (!response.ok) {
    throw toApiError(response.status, payload);
  }
  return payload as T;
}

async function readJson(response: Response): Promise<unknown> {
  const contentType = response.headers.get("content-type") ?? "";
  if (!contentType.includes("application/json")) {
    return null;
  }
  return response.json();
}

function toApiError(status: number, payload: unknown): ApiError {
  if (isBackendErrorEnvelope(payload)) {
    return new ApiError(
      status,
      payload.error.code,
      payload.error.message,
      payload.error.request_id
    );
  }
  return new ApiError(status, "unexpected_api_response", "The service could not complete the request.");
}

function isBackendErrorEnvelope(value: unknown): value is BackendErrorEnvelope {
  if (!value || typeof value !== "object") {
    return false;
  }
  const candidate = value as Partial<BackendErrorEnvelope>;
  return (
    candidate.ok === false &&
    typeof candidate.error?.code === "string" &&
    typeof candidate.error.message === "string"
  );
}
