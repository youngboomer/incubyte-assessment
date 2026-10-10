import type { AnalyticsOverview, LevelBreakdown } from "../lib/types";

const wholeUsd = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});

export function scaledToNumber(scaled: string, scale: number): number {
  return Number(scaled) / 10 ** scale;
}

export function formatWholeUsd(scaled: string, scale: number): string {
  return wholeUsd.format(scaledToNumber(scaled, scale));
}

export function extremes(levels: LevelBreakdown[], scale: number): { min: number; max: number } {
  const lows = levels.map((level) => scaledToNumber(level.min_salary_usd_scaled, scale));
  const highs = levels.map((level) => scaledToNumber(level.max_salary_usd_scaled, scale));
  return { min: Math.min(...lows), max: Math.max(...highs) };
}

export function spreadOf(overview: AnalyticsOverview) {
  const scale = overview.salary_usd_scale;
  const { min, max } = extremes(overview.by_level, scale);
  return {
    min,
    max,
    p25: scaledToNumber(overview.p25_salary_usd_scaled, scale),
    median: scaledToNumber(overview.p50_salary_usd_scaled, scale),
    p75: scaledToNumber(overview.p75_salary_usd_scaled, scale),
  };
}
