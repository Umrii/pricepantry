/**
 * Price freshness + timestamp formatting.
 *
 * Prices are collected by an on-demand scraper (there is no fixed automated
 * schedule in the project today), so "freshness" is a best-effort signal, not a
 * guarantee the price is live. The threshold is configurable via
 * NEXT_PUBLIC_PRICE_FRESH_HOURS and defaults to 24h — a reasonable window for a
 * manually/daily-run grocery scraper. Adjust it to match the real cadence once
 * a schedule exists.
 */

const DEFAULT_FRESH_HOURS = 24;

export function freshThresholdHours(): number {
  const raw = process.env.NEXT_PUBLIC_PRICE_FRESH_HOURS;
  const n = raw ? Number(raw) : NaN;
  return Number.isFinite(n) && n > 0 ? n : DEFAULT_FRESH_HOURS;
}

/** Format a UTC ISO timestamp for display in UK local time, e.g. "18 Oct, 12:21". */
export function formatObservedAt(iso: string | null | undefined): string | null {
  if (!iso) return null;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return null;
  return new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "Europe/London",
  }).format(d);
}

/** Short date for chart axes/tooltips, e.g. "18 Oct". UK timezone, UTC-safe. */
export function formatShortDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "short",
    timeZone: "Europe/London",
  }).format(d);
}

export type Freshness = "fresh" | "stale" | "unknown";

/** Classify an observation timestamp relative to the freshness threshold. */
export function freshnessOf(
  iso: string | null | undefined,
  now: Date = new Date(),
): Freshness {
  if (!iso) return "unknown";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "unknown";
  const ageHours = (now.getTime() - d.getTime()) / 3_600_000;
  return ageHours <= freshThresholdHours() ? "fresh" : "stale";
}
