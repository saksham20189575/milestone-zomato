"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  IndianRupee,
  MapPin,
  Sparkles,
  Star,
  UtensilsCrossed,
} from "lucide-react";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import { Textarea } from "@/components/ui/textarea";
import {
  getCuisines,
  getLocations,
  isValidationError,
  postRecommend,
} from "@/lib/api";
import {
  BUDGET_OPTIONS,
  preferenceSchema,
  type PreferenceFormValues,
} from "@/lib/schemas";
import type { RecommendationResponse } from "@/lib/types";

interface PreferenceFormProps {
  onResults: (data: RecommendationResponse | null) => void;
  onLoadingChange: (loading: boolean) => void;
  onSubmitted: () => void;
  onServerError: (message: string | null) => void;
}

export function PreferenceForm({
  onResults,
  onLoadingChange,
  onSubmitted,
  onServerError,
}: PreferenceFormProps) {
  const [locationSuggestions, setLocationSuggestions] = useState<string[]>([]);

  const { data: locationsData, isLoading: locationsLoading } = useQuery({
    queryKey: ["locations"],
    queryFn: getLocations,
  });

  const { data: cuisinesData, isLoading: cuisinesLoading } = useQuery({
    queryKey: ["cuisines"],
    queryFn: getCuisines,
  });

  const form = useForm<PreferenceFormValues>({
    resolver: zodResolver(preferenceSchema),
    defaultValues: {
      location: "",
      budget: "medium",
      cuisine: "",
      min_rating: 0,
      additional_preferences: "",
    },
  });

  const {
    handleSubmit,
    setValue,
    watch,
    formState: { errors },
    setError,
    clearErrors,
  } = form;

  const minRating = watch("min_rating");
  const selectedLocation = watch("location");

  const mutation = useMutation({
    mutationFn: postRecommend,
    onMutate: () => {
      onLoadingChange(true);
      onServerError(null);
      setLocationSuggestions([]);
      clearErrors("location");
    },
    onSuccess: (data) => {
      onResults(data);
      onSubmitted();
      onLoadingChange(false);
    },
    onError: (error: unknown) => {
      onLoadingChange(false);

      if (isValidationError(error)) {
        const detail = error.detail;
        setError("location", { message: detail.message });
        setLocationSuggestions(detail.suggestions ?? []);
        onServerError(null);
        return;
      }

      const message =
        error instanceof Error ? error.message : "Something went wrong";
      onServerError(message);
    },
  });

  useEffect(() => {
    onLoadingChange(mutation.isPending);
  }, [mutation.isPending, onLoadingChange]);

  const onSubmit = (values: PreferenceFormValues) => {
    mutation.mutate({
      location: values.location,
      budget: values.budget,
      min_rating: values.min_rating,
      cuisine: values.cuisine || null,
      additional_preferences: values.additional_preferences || null,
    });
  };

  const locations = locationsData?.locations ?? [];
  const cuisines = cuisinesData?.cuisines ?? [];

  return (
    <Card className="h-fit">
      <CardHeader>
        <CardTitle>Your Preferences</CardTitle>
      </CardHeader>
      <CardContent>
        <form
          onSubmit={handleSubmit(onSubmit)}
          className="space-y-6"
          noValidate
        >
          <div className="space-y-2">
            <Label htmlFor="location-select" className="flex items-center gap-2">
              <MapPin className="h-4 w-4 text-primary" aria-hidden="true" />
              Location
            </Label>
            <Select
              value={selectedLocation || undefined}
              onValueChange={(value) => {
                setValue("location", value, { shouldValidate: true });
                clearErrors("location");
                setLocationSuggestions([]);
              }}
              disabled={locationsLoading}
            >
              <SelectTrigger id="location-select" aria-label="Select location">
                <SelectValue
                  placeholder={
                    locationsLoading ? "Loading locations…" : "Select a city"
                  }
                />
              </SelectTrigger>
              <SelectContent>
                {locations.map((location) => (
                  <SelectItem key={location} value={location}>
                    {location}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {errors.location && (
              <p className="text-sm text-error" role="alert">
                {errors.location.message}
              </p>
            )}
            {locationSuggestions.length > 0 && (
              <div className="flex flex-wrap gap-2 pt-1">
                <span className="text-xs text-on-surface-variant">
                  Did you mean:
                </span>
                {locationSuggestions.map((suggestion) => (
                  <button
                    key={suggestion}
                    type="button"
                    className="rounded-full border border-primary/30 bg-primary-fixed/30 px-3 py-1 text-xs font-medium text-primary hover:bg-primary-fixed/60"
                    onClick={() => {
                      setValue("location", suggestion, { shouldValidate: true });
                      clearErrors("location");
                      setLocationSuggestions([]);
                    }}
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="budget-select" className="flex items-center gap-2">
              <IndianRupee className="h-4 w-4 text-primary" aria-hidden="true" />
              Budget for Two
            </Label>
            <Select
              value={watch("budget")}
              onValueChange={(value) =>
                setValue("budget", value as PreferenceFormValues["budget"], {
                  shouldValidate: true,
                })
              }
            >
              <SelectTrigger id="budget-select" aria-label="Select budget">
                <SelectValue placeholder="Select budget" />
              </SelectTrigger>
              <SelectContent>
                {BUDGET_OPTIONS.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label} — {option.helper}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {errors.budget && (
              <p className="text-sm text-error" role="alert">
                {errors.budget.message}
              </p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="cuisine-select" className="flex items-center gap-2">
              <UtensilsCrossed
                className="h-4 w-4 text-primary"
                aria-hidden="true"
              />
              Cuisine
            </Label>
            <Select
              value={watch("cuisine") || "any"}
              onValueChange={(value) =>
                setValue("cuisine", value === "any" ? "" : value, {
                  shouldValidate: true,
                })
              }
              disabled={cuisinesLoading}
            >
              <SelectTrigger id="cuisine-select" aria-label="Select cuisine">
                <SelectValue
                  placeholder={
                    cuisinesLoading ? "Loading cuisines…" : "Any cuisine"
                  }
                />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="any">Any cuisine</SelectItem>
                {cuisines.map((cuisine) => (
                  <SelectItem key={cuisine} value={cuisine}>
                    {cuisine}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <Label htmlFor="min-rating-slider" className="flex items-center gap-2">
                <Star className="h-4 w-4 text-primary" aria-hidden="true" />
                Minimum Rating
              </Label>
              <span className="text-sm font-semibold text-primary">
                {minRating > 0 ? `${minRating.toFixed(1)}+` : "Any"}
              </span>
            </div>
            <Slider
              id="min-rating-slider"
              min={0}
              max={5}
              step={0.5}
              value={[minRating]}
              onValueChange={([value]) =>
                setValue("min_rating", value, { shouldValidate: true })
              }
              aria-label="Minimum rating"
            />
            <div className="flex justify-between text-xs text-on-surface-variant">
              <span>Any</span>
              <span>5.0</span>
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="additional-preferences">
              Additional Preferences
            </Label>
            <Textarea
              id="additional-preferences"
              placeholder="e.g., family-friendly, quick service, romantic vibe…"
              {...form.register("additional_preferences")}
            />
          </div>

          <Button
            type="submit"
            size="lg"
            className="w-full"
            disabled={mutation.isPending || locationsLoading}
          >
            <Sparkles className="h-4 w-4" aria-hidden="true" />
            {mutation.isPending ? "Getting Recommendations…" : "Get Recommendations"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
