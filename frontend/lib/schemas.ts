import { z } from "zod";

export const preferenceSchema = z.object({
  location: z.string().min(1, "Please select a location"),
  budget: z.enum(["low", "medium", "high"], {
    message: "Please select a budget",
  }),
  cuisine: z.string().optional(),
  min_rating: z.number().min(0).max(5),
  additional_preferences: z.string().optional(),
});

export type PreferenceFormValues = z.infer<typeof preferenceSchema>;

export const BUDGET_OPTIONS = [
  { value: "low" as const, label: "Low", helper: "Under ₹500" },
  { value: "medium" as const, label: "Medium", helper: "₹501–1500" },
  { value: "high" as const, label: "High", helper: "Above ₹1500" },
];
