import { majorToScaled } from "../../lib/format";
import { buildQuery, parseDirectoryFilters } from "../../lib/query";
import type { SearchParams } from "../../lib/query";
import type { DirectoryFilters } from "../../lib/types";

export const PAGE_SIZES = [25, 50, 100] as const;
export const DEFAULT_LIMIT = 50;

const USD_SCALE = 2;
const MAX_INT64 = BigInt("9223372036854775807");

export type DirectoryState = {
  q?: string;
  department_id?: string;
  country?: string;
  status?: string;
  level?: string;
  pay_min?: string;
  pay_max?: string;
  sort?: string;
  direction?: string;
  limit?: string;
  cursor?: string;
  page?: string;
};

const URL_ORDER = [
  "q",
  "country",
  "department_id",
  "level",
  "status",
  "pay_min",
  "pay_max",
  "sort",
  "direction",
  "limit",
  "cursor",
  "page",
] as const;

const FILTER_KEYS = [
  "q",
  "country",
  "department_id",
  "level",
  "status",
  "pay_min",
  "pay_max",
] as const;

function firstValue(params: SearchParams, key: string): string | undefined {
  const raw = params[key];
  const value = (Array.isArray(raw) ? raw[0] : raw)?.trim().replace(/,/g, "");
  return value === undefined || value === "" ? undefined : value;
}

function dollars(value: string | undefined): string | undefined {
  if (value === undefined || !/^\d+(\.\d{1,2})?$/.test(value)) {
    return undefined;
  }
  const scaled = majorToScaled(value, USD_SCALE);
  if (scaled === null || BigInt(scaled) > MAX_INT64) {
    return undefined;
  }
  return value.replace(/^0+(?=\d)/, "");
}

function compact(state: DirectoryState): DirectoryState {
  return Object.fromEntries(
    Object.entries(state).filter(([, value]) => value !== undefined),
  ) as DirectoryState;
}

export function readDirectoryState(params: SearchParams): DirectoryState {
  const parsed = parseDirectoryFilters(params);
  let min = dollars(firstValue(params, "pay_min"));
  let max = dollars(firstValue(params, "pay_max"));
  if (min !== undefined && max !== undefined && Number(min) > Number(max)) {
    min = undefined;
    max = undefined;
  }
  const page = firstValue(params, "page");
  return compact({
    q: parsed.q,
    country: parsed.country,
    department_id: parsed.department_id,
    level: parsed.level,
    status: parsed.status,
    pay_min: min,
    pay_max: max,
    sort: parsed.sort,
    direction: parsed.direction,
    limit: parsed.limit === undefined ? undefined : String(parsed.limit),
    cursor: parsed.cursor,
    page: parsed.cursor !== undefined && page !== undefined && /^[1-9]\d{0,5}$/.test(page) ? page : undefined,
  });
}

export function backendFilters(state: DirectoryState): DirectoryFilters {
  const parsed = parseDirectoryFilters({ ...state });
  const min = state.pay_min === undefined ? null : majorToScaled(state.pay_min, USD_SCALE);
  const max = state.pay_max === undefined ? null : majorToScaled(state.pay_max, USD_SCALE);
  const filters: DirectoryFilters = { ...parsed };
  delete filters.salary_usd_min;
  delete filters.salary_usd_max;
  if (min !== null) {
    filters.salary_usd_min = min;
  }
  if (max !== null) {
    filters.salary_usd_max = max;
  }
  return filters;
}

export function directoryHref(base: string, state: DirectoryState): string {
  return `${base}${buildQuery({ ...state }, URL_ORDER)}`;
}

export function withoutPaging(state: DirectoryState): DirectoryState {
  const { cursor: _cursor, page: _page, ...rest } = state;
  return rest;
}

export function without(state: DirectoryState, ...keys: (keyof DirectoryState)[]): DirectoryState {
  const next = { ...withoutPaging(state) };
  for (const key of keys) {
    delete next[key];
  }
  return next;
}

export function clearedFilters(state: DirectoryState): DirectoryState {
  return without(state, ...FILTER_KEYS);
}

export function activeFilterCount(state: DirectoryState): number {
  const pay = state.pay_min !== undefined || state.pay_max !== undefined ? 1 : 0;
  return (
    pay +
    (["q", "country", "department_id", "level", "status"] as const).filter(
      (key) => state[key] !== undefined,
    ).length
  );
}

export function nextSort(
  state: DirectoryState,
  key: string,
): { href: DirectoryState; direction: "asc" | "desc" | null } {
  const current = state.sort ?? "name";
  const direction = state.direction === "desc" ? "desc" : "asc";
  const active = current === key;
  const flipped = active && direction === "asc" ? "desc" : "asc";
  return {
    href: { ...withoutPaging(state), sort: key, direction: flipped },
    direction: active ? direction : null,
  };
}

export type PageRange = { from: number; to: number };

// Keyset cursors carry no offset, so the 1-based page number is tracked in the URL (`page`)
// and the range is derived from it: page 1 is the cursor-less first page.
export function pageRange(page: number, limit: number, count: number, total: number): PageRange {
  if (count === 0 || total === 0) {
    return { from: 0, to: 0 };
  }
  const from = Math.min((page - 1) * limit + 1, total);
  return { from, to: Math.min(from + count - 1, total) };
}

export function currentPage(state: DirectoryState): number {
  return state.cursor === undefined ? 1 : Number(state.page ?? "2");
}
