/**
 * INR formatting utility for consistent currency display
 * Examples:
 * 100000 → "₹1.0L"
 * 10000000 → "₹1.0Cr"
 * 154000 → "₹1.54L (₹1,54,000)"
 */

export function formatINR(value: number, showExact: boolean = false): string {
  if (!Number.isFinite(value)) return "₹0";

  const abs = Math.abs(value);
  let formatted = "";

  if (abs >= 10000000) {
    // Crore
    const crore = abs / 10000000;
    formatted = `₹${crore.toFixed(crore % 1 === 0 ? 0 : 1)}Cr`;
  } else if (abs >= 100000) {
    // Lakh
    const lakh = abs / 100000;
    formatted = `₹${lakh.toFixed(lakh % 1 === 0 ? 0 : 2)}L`;
  } else {
    // Exact
    formatted = `₹${Math.round(abs).toLocaleString("en-IN")}`;
  }

  if (value < 0) {
    formatted = "-" + formatted;
  }

  if (showExact && abs >= 100000) {
    const exact = Math.round(abs).toLocaleString("en-IN");
    formatted += ` (₹${exact})`;
  }

  return formatted;
}

export function formatINRShort(value: number): string {
  if (!Number.isFinite(value)) return "₹0";

  const abs = Math.abs(value);

  if (abs >= 10000000) {
    const crore = abs / 10000000;
    return `${crore >= 10 ? Math.round(crore) : crore.toFixed(1)}Cr`;
  }
  if (abs >= 100000) {
    const lakh = abs / 100000;
    return `${lakh >= 10 ? Math.round(lakh) : lakh.toFixed(1)}L`;
  }

  return Math.round(abs).toLocaleString("en-IN");
}

export function parseINR(text: string): number {
  const cleaned = (text || "").toUpperCase().replace(/[^0-9.CRL-]/g, "");
  if (!cleaned) return 0;

  let value = 0;
  if (cleaned.includes("CR")) {
    value = parseFloat(cleaned.replace("CR", "")) * 10000000;
  } else if (cleaned.includes("L")) {
    value = parseFloat(cleaned.replace("L", "")) * 100000;
  } else {
    value = parseFloat(cleaned);
  }

  return Math.round(value);
}
