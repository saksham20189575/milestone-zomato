"use client";

import { Sparkles, Star } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import type { Recommendation } from "@/lib/types";
import { cn, formatCost } from "@/lib/utils";

interface RecommendationCardProps {
  recommendation: Recommendation;
  index: number;
}

function getRankVariant(rank: number): "rank-gold" | "rank-silver" | "rank-bronze" | "secondary" {
  if (rank === 1) return "rank-gold";
  if (rank === 2) return "rank-silver";
  if (rank === 3) return "rank-bronze";
  return "secondary";
}

function getRatingColor(rating: number): string {
  if (rating >= 4.0) return "bg-emerald-600";
  if (rating >= 3.0) return "bg-amber-500";
  return "bg-orange-600";
}

export function RecommendationCard({
  recommendation,
  index,
}: RecommendationCardProps) {
  const { rank, name, cuisine, rating, estimated_cost, explanation } =
    recommendation;

  return (
    <Card
      className={cn(
        "transition-shadow duration-200 hover:shadow-[0px_8px_24px_rgba(28,28,28,0.12)] animate-fade-in-up",
      )}
      style={{ animationDelay: `${index * 80}ms` }}
    >
      <CardContent className="p-5">
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-start gap-3">
            <Badge
              variant={getRankVariant(rank)}
              className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-sm"
              aria-label={`Rank ${rank}`}
            >
              {rank}
            </Badge>
            <div>
              <h3 className="text-lg font-semibold text-on-surface">{name}</h3>
              <p className="mt-1 text-sm text-on-surface-variant">{cuisine}</p>
              <p className="mt-1 text-sm font-medium text-on-surface-variant">
                {formatCost(estimated_cost)}
              </p>
            </div>
          </div>
          <div
            className={cn(
              "inline-flex items-center gap-1 rounded px-2 py-1 text-xs font-semibold text-white",
              getRatingColor(rating),
            )}
            aria-label={`Rating ${rating} out of 5`}
          >
            {rating.toFixed(1)}
            <Star className="h-3 w-3 fill-current" aria-hidden="true" />
          </div>
        </div>

        <div className="mt-4 rounded-lg bg-surface-container-low p-4">
          <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-primary">
            <Sparkles className="h-4 w-4" aria-hidden="true" />
            Why it fits
          </div>
          <p className="text-sm leading-relaxed text-on-surface-variant">
            {explanation}
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
