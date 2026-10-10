import type {
  AuditFilters,
  ChangeField,
  ChangeFilters,
  DirectoryFilters,
  EmployeeStatus,
  Level,
  ScopeFilters,
  SortDirection,
  SortKey,
} from "./types";

export type SearchParams = Record<string, string | string[] | undefined>;

export const LEVELS: readonly Level[] = ["IC1", "IC2", "IC3", "IC4", "IC5", "M1", "M2"];
export const STATUSES: readonly EmployeeStatus[] = ["active", "terminated"];
export const SORTS: readonly SortKey[] = [
  "name",
  "employee_number",
  "department",
  "country",
  "title",
  "base_salary",
  "salary_usd",
  "hire_date",
];
export const CHANGE_FIELDS: readonly ChangeField[] = [
  "first_name",
  "last_name",
  "email",
  "job_title",
  "department_id",
  "level",
  "status",
];
export const HISTORY_TABS = ["pay", "details"] as const;
export type HistoryTab = (typeof HISTORY_TABS)[number];
export const DIRECTIONS: readonly SortDirection[] = ["asc", "desc"];

const MAX_INT64 = BigInt("9223372036854775807");
const MAX_LIMIT = 100;

const DIRECTORY_KEYS = [
  "q",
  "department_id",
  "country",
  "currency",
  "status",
  "level",
  "salary_usd_min",
  "salary_usd_max",
  "sort",
  "direction",
  "limit",
  "cursor",
] as const;

const SCOPE_KEYS = ["department_id", "country", "level", "currency"] as const;

const AUDIT_KEYS = [
  "employee_id",
  "department_id",
  "since",
  "until",
  "changed_by",
  "limit",
  "cursor",
] as const;

const CHANGES_KEYS = [
  "employee_id",
  "department_id",
  "field",
  "since",
  "until",
  "changed_by",
  "limit",
  "cursor",
] as const;

type QueryValue = string | number | null | undefined;

export function buildQuery(
  params: Record<string, QueryValue>,
  order: readonly string[] = Object.keys(params).sort(),
): string {
  const search = new URLSearchParams();
  for (const key of order) {
    const value = params[key];
    if (value === undefined || value === null) {
      continue;
    }
    const text = String(value);
    if (text.trim() !== "") {
      search.append(key, text);
    }
  }
  const encoded = search.toString();
  return encoded === "" ? "" : `?${encoded}`;
}

export function directoryQuery(filters: DirectoryFilters): string {
  return buildQuery({ ...filters }, DIRECTORY_KEYS);
}

export function scopeQuery(filters: ScopeFilters): string {
  return buildQuery({ ...filters }, SCOPE_KEYS);
}

export function auditQuery(filters: AuditFilters, cursor?: string): string {
  return buildQuery({ ...filters, cursor }, AUDIT_KEYS);
}

export function changesQuery(filters: ChangeFilters, cursor?: string): string {
  return buildQuery({ ...filters, cursor }, CHANGES_KEYS);
}

export function historyHref(
  tab: HistoryTab,
  filters: AuditFilters | ChangeFilters,
  cursor?: string,
): string {
  const query =
    tab === "details"
      ? buildQuery({ tab, ...filters, cursor }, ["tab", ...CHANGES_KEYS])
      : auditQuery(filters, cursor);
  return `/history${query}`;
}

function first(params: SearchParams, key: string): string | undefined {
  const raw = params[key];
  const value = Array.isArray(raw) ? raw[0] : raw;
  if (value === undefined) {
    return undefined;
  }
  const trimmed = value.trim();
  return trimmed === "" ? undefined : trimmed;
}

function oneOf<T extends string>(allowed: readonly T[], value: string | undefined): T | undefined {
  return allowed.find((item) => item === value);
}

function digits(value: string | undefined): string | undefined {
  return value !== undefined && /^\d+$/.test(value) ? value : undefined;
}

function money(value: string | undefined): string | undefined {
  const text = digits(value);
  if (text === undefined || BigInt(text) > MAX_INT64) {
    return undefined;
  }
  return text.replace(/^0+(?=\d)/, "");
}

function limit(value: string | undefined): number | undefined {
  const text = digits(value);
  if (text === undefined) {
    return undefined;
  }
  const parsed = Number(text);
  return parsed >= 1 && parsed <= MAX_LIMIT ? parsed : undefined;
}

function isoDate(value: string | undefined): string | undefined {
  if (value === undefined || !/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    return undefined;
  }
  const date = new Date(`${value}T00:00:00Z`);
  return Number.isNaN(date.getTime()) || date.toISOString().slice(0, 10) !== value
    ? undefined
    : value;
}

function compact<T extends object>(value: T): T {
  return Object.fromEntries(
    Object.entries(value).filter(([, entry]) => entry !== undefined),
  ) as T;
}

export function parseDirectoryFilters(params: SearchParams): DirectoryFilters {
  const min = money(first(params, "salary_usd_min"));
  const max = money(first(params, "salary_usd_max"));
  const inverted = min !== undefined && max !== undefined && BigInt(min) > BigInt(max);
  return compact({
    q: first(params, "q"),
    department_id: digits(first(params, "department_id")),
    country: first(params, "country")?.toUpperCase(),
    currency: first(params, "currency")?.toUpperCase(),
    status: oneOf(STATUSES, first(params, "status")),
    level: oneOf(LEVELS, first(params, "level")),
    salary_usd_min: inverted ? undefined : min,
    salary_usd_max: inverted ? undefined : max,
    sort: oneOf(SORTS, first(params, "sort")),
    direction: oneOf(DIRECTIONS, first(params, "direction")),
    limit: limit(first(params, "limit")),
    cursor: first(params, "cursor"),
  });
}

export function parseScopeFilters(params: SearchParams): ScopeFilters {
  return compact({
    department_id: digits(first(params, "department_id")),
    country: first(params, "country")?.toUpperCase(),
    level: oneOf(LEVELS, first(params, "level")),
    currency: first(params, "currency")?.toUpperCase(),
  });
}

export function parseAuditFilters(params: SearchParams): AuditFilters & { cursor?: string } {
  const since = isoDate(first(params, "since"));
  const until = isoDate(first(params, "until"));
  const inverted = since !== undefined && until !== undefined && since > until;
  return compact({
    employee_id: first(params, "employee_id"),
    department_id: digits(first(params, "department_id")),
    since: inverted ? undefined : since,
    until: inverted ? undefined : until,
    changed_by: first(params, "changed_by"),
    limit: limit(first(params, "limit")),
    cursor: first(params, "cursor"),
  });
}

export function parseHistoryTab(params: SearchParams): HistoryTab {
  return oneOf(HISTORY_TABS, first(params, "tab")) ?? "pay";
}

export function parseChangesFilters(params: SearchParams): ChangeFilters & { cursor?: string } {
  return compact({
    ...parseAuditFilters(params),
    field: oneOf(CHANGE_FIELDS, first(params, "field")),
  });
}
