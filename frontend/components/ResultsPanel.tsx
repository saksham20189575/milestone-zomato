"use client";

import { AlertTriangle, Sparkles, UtensilsCrossed } from "lucide-react";
import { RecommendationCard } from "@/components/RecommendationCard";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import type { RecommendationResponse } from "@/lib/types";

interface ResultsPanelProps {
  data: RecommendationResponse | null;
  isLoading: boolean;
  hasSubmitted: boolean;
}

function formatFilterLabel(key: string, value: string | number | null): string {
  if (value === null || value === undefined || value === "") return "";
  switch (key) {
    case "budget":
      return `${String(value).charAt(0).toUpperCase()}${String(value).slice(1)} budget`;
    case "min_rating":
      return `Rating ${value}+`;
    case "location":
      return String(value);
    case "cuisine":
      return String(value);
    default:
      return `${key}: ${value}`;
  }
}

function LoadingSkeletons() {
  return (
    <div className="space-y-4" aria-live="polite" aria-busy="true">
      <p className="text-sm font-medium text-on-surface-variant">
        AI is ranking restaurants for you…
      </p>
      {Array.from({ length: 3 }).map((_, i) => (
        <Card key={i}>
          <CardContent className="space-y-3 p-5">
            <Skeleton className="h-6 w-2/3" />
            <Skeleton className="h-4 w-1/3" />
            <Skeleton className="h-20 w-full" />
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex h-full min-h-[400px] flex-col items-center justify-center rounded-lg border border-dashed border-outline-variant/60 bg-surface-container-low p-12 text-center">
      <UtensilsCrossed
        className="mb-4 h-12 w-12 text-on-surface-variant/50"
        aria-hidden="true"
      />
      <h3 className="text-lg font-semibold text-on-surface">
        Ready to discover?
      </h3>
      <p className="mt-2 max-w-sm text-sm leading-relaxed text-on-surface-variant">
        Set your preferences on the left and click Get Recommendations to see
        AI-powered restaurant picks tailored for you.
      </p>
    </div>
  );
}

function NoResultsState() {
  return (
    <div className="flex min-h-[300px] flex-col items-center justify-center rounded-lg border border-outline-variant/40 bg-surface-container-low p-10 text-center">
      <AlertTriangle
        className="mb-4 h-10 w-10 text-warning"
        aria-hidden="true"
      />
      <h3 className="text-lg font-semibold text-on-surface">
        No restaurants match
      </h3>
      <p className="mt-2 max-w-md text-sm leading-relaxed text-on-surface-variant">
        Try broadening your filters — lower the minimum rating, choose a
        different budget tier, or pick &quot;Any cuisine&quot;.
      </p>
    </div>
  );
}

export function ResultsPanel({
  data,
  isLoading,
  hasSubmitted,
}: ResultsPanelProps) {
  if (!hasSubmitted && !isLoading) {
    return <EmptyState />;
  }

  if (isLoading) {
    return <LoadingSkeletons />;
  }

  if (!data) {
    return null;
  }

  const filterChips = Object.entries(data.metadata.filters_applied)
    .map(([key, value]) => ({
      key,
      label: formatFilterLabel(key, value),
    }))
    .filter((chip) => chip.label);

  const isFallback =
    data.metadata.model === "fallback" ||
    data.recommendations.some((r) =>
      r.explanation.toLowerCase().includes("fallback"),
    );

  return (
    <div className="space-y-4">
      {data.metadata.warnings.length > 0 && (
        <div
          role="status"
          className="flex items-start gap-3 rounded-lg border border-warning/30 bg-warning-container px-4 py-3 text-sm text-on-warning-container"
        >
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
          <div>
            <p className="font-semibold">Filters relaxed</p>
            <ul className="mt-1 list-inside list-disc space-y-1">
              {data.metadata.warnings.map((warning) => (
                <li key={warning}>{warning}</li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {isFallback && (
        <div
          role="status"
          className="rounded-lg border border-outline-variant/40 bg-surface-container-low px-4 py-3 text-sm text-on-surface-variant"
        >
          AI ranking was unavailable. Showing top-rated matches using fallback
          ranking.
        </div>
      )}

      {filterChips.length > 0 && (
        <div className="flex flex-wrap gap-2" aria-label="Applied filters">
          {filterChips.map((chip) => (
            <Badge key={chip.key} variant="default">
              {chip.label}
            </Badge>
          ))}
        </div>
      )}

      {data.summary && (
        <Card className="border-primary-fixed bg-primary-fixed/40">
          <CardContent className="p-5">
            <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-primary">
              <Sparkles className="h-4 w-4" aria-hidden="true" />
              Here&apos;s what we found
            </div>
            <p className="text-sm leading-relaxed text-on-surface-variant">
              {data.summary}
            </p>
          </CardContent>
        </Card>
      )}

      {data.recommendations.length === 0 ? (
        <NoResultsState />
      ) : (
        <div className="space-y-4">
          {data.recommendations.map((rec, index) => (
            <RecommendationCard
              key={`${rec.rank}-${rec.name}`}
              recommendation={rec}
              index={index}
            />
          ))}
        </div>
      )}
    </div>
  );
}
