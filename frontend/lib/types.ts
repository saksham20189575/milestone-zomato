export type Budget = "low" | "medium" | "high";

export interface UserPreferences {
  location: string;
  budget: Budget;
  min_rating: number;
  cuisine?: string | null;
  additional_preferences?: string | null;
}

export interface Recommendation {
  rank: number;
  name: string;
  cuisine: string;
  rating: number;
  estimated_cost: number;
  explanation: string;
}

export interface RecommendationMetadata {
  candidates_considered: number;
  filters_applied: Record<string, string | number | null>;
  model: string;
  warnings: string[];
}

export interface RecommendationResponse {
  summary: string | null;
  recommendations: Recommendation[];
  metadata: RecommendationMetadata;
}

export interface HealthResponse {
  status: "ok" | "degraded";
  dataset_loaded: boolean;
  restaurant_count: number;
  message?: string | null;
}

export interface LocationsResponse {
  locations: string[];
}

export interface CuisinesResponse {
  cuisines: string[];
}

export interface ApiValidationError {
  message: string;
  suggestions: string[];
}

export interface ApiError extends Error {
  status: number;
  detail?: ApiValidationError | string;
}
