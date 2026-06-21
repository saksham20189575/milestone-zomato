import * as React from "react";
import { cn } from "@/lib/utils";

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "secondary" | "outline" | "rank-gold" | "rank-silver" | "rank-bronze" | "rating";
}

function Badge({ className, variant = "default", ...props }: BadgeProps) {
  return (
    <div
      className={cn(
        "inline-flex items-center rounded px-2 py-0.5 text-xs font-semibold transition-colors",
        {
          default: "bg-primary-fixed text-on-primary-fixed-variant",
          secondary: "bg-surface-container text-on-surface-variant",
          outline: "border border-outline-variant bg-surface-container-lowest text-on-surface-variant",
          "rank-gold": "bg-gradient-to-br from-amber-300 to-amber-500 text-white shadow-sm",
          "rank-silver": "bg-gradient-to-br from-slate-300 to-slate-400 text-white shadow-sm",
          "rank-bronze": "bg-gradient-to-br from-orange-300 to-orange-500 text-white shadow-sm",
          rating: "bg-emerald-600 text-white",
        }[variant],
        className,
      )}
      {...props}
    />
  );
}

export { Badge };
