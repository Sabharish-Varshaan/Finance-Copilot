import { type ClassValue, clsx } from "clsx";

export function cn(...inputs: ClassValue[]) {
  return clsx(inputs);
}

export function currency(value: number) {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(value);
}

/**
 * Format currency as exact INR amount (e.g., "₹38,428")
 */
export function formatCurrency(value: number): string {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
}

/**
 * Format currency as compact humanized form (e.g., "₹38.4K" for 38428, "₹1.2L" for 120000, "₹10Cr" for 10000000)
 */
export function formatCurrencyCompact(value: number): string {
  const absValue = Math.abs(value);
  
  if (absValue >= 10000000) {
    const crore = value / 10000000;
    return `₹${crore.toFixed(crore % 1 === 0 ? 0 : 1)}Cr`;
  }
  if (absValue >= 100000) {
    const lakh = value / 100000;
    return `₹${lakh.toFixed(lakh % 1 === 0 ? 0 : 1)}L`;
  }
  if (absValue >= 1000) {
    const thousand = value / 1000;
    return `₹${thousand.toFixed(thousand % 1 === 0 ? 0 : 1)}K`;
  }
  
  return formatCurrency(value);
}

/**
 * Format with hint showing both compact and exact (e.g., "₹38.4K (exact: ₹38,428)")
 */
export function formatCurrencyWithHint(value: number): string {
  const compact = formatCurrencyCompact(value);
  const exact = formatCurrency(value);
  
  if (compact === exact) {
    return exact;
  }
  
  return `${compact} (exact: ${exact})`;
}
