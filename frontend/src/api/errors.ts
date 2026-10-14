import type { ErrorResponse } from "./types";

/** An error response from the API, carrying its status and machine-readable `code`. */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string;

  constructor(status: number, code: string, detail: string) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

function isErrorResponse(value: unknown): value is ErrorResponse {
  return (
    typeof value === "object" &&
    value !== null &&
    typeof (value as Record<string, unknown>).code === "string" &&
    typeof (value as Record<string, unknown>).detail === "string"
  );
}

/** Turn an openapi-fetch result into its data, or throw an ApiError for TanStack Query. */
export async function unwrap<T>(
  request: Promise<{ data?: T; error?: unknown; response: Response }>,
): Promise<T> {
  const { data, error, response } = await request;
  if (error !== undefined || !response.ok) {
    if (isErrorResponse(error)) {
      throw new ApiError(response.status, error.code, error.detail);
    }
    throw new ApiError(response.status, "unexpected_error", "Something went wrong. Try again.");
  }
  return data as T;
}

/** A sentence to show the user for any error a query or mutation produced. */
export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  return "Couldn't reach Roadhouse. Check your connection and try again.";
}
