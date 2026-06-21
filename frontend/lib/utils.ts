import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatCost(amount: number): string {
  return `₹${amount.toLocaleString("en-IN")} for two`;
}
