import type {
  ApiError,
  ApiValidationError,
  CuisinesResponse,
  HealthResponse,
  LocationsResponse,
  RecommendationResponse,
  UserPreferences,
} from "./types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;

  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...init?.headers,
      },
    });
  } catch {
    const error = new Error("Unable to reach server") as ApiError;
    error.status = 0;
    throw error;
  }

  if (!response.ok) {
    let detail: ApiValidationError | string | undefined;
    try {
      const body = await response.json();
      detail = body.detail ?? body.message ?? body;
    } catch {
      detail = response.statusText;
    }

    const error = new Error(
      typeof detail === "string" ? detail : detail?.message ?? "Request failed",
    ) as ApiError;
    error.status = response.status;
    error.detail = detail;
    throw error;
  }

  return response.json() as Promise<T>;
}

export function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/api/v1/health");
}

export function getLocations(): Promise<LocationsResponse> {
  return request<LocationsResponse>("/api/v1/locations");
}

export function getCuisines(): Promise<CuisinesResponse> {
  return request<CuisinesResponse>("/api/v1/cuisines");
}

export function postRecommend(
  preferences: UserPreferences,
): Promise<RecommendationResponse> {
  return request<RecommendationResponse>("/api/v1/recommend", {
    method: "POST",
    body: JSON.stringify({
      location: preferences.location,
      budget: preferences.budget,
      min_rating: preferences.min_rating,
      cuisine: preferences.cuisine || null,
      additional_preferences: preferences.additional_preferences || null,
    }),
  });
}

export function isValidationError(
  error: unknown,
): error is ApiError & { detail: ApiValidationError } {
  return (
    typeof error === "object" &&
    error !== null &&
    "detail" in error &&
    typeof (error as ApiError).detail === "object" &&
    (error as ApiError).detail !== null &&
    "message" in ((error as ApiError).detail as ApiValidationError)
  );
}
