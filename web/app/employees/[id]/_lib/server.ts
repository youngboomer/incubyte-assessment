import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { getEmployee, listEmployeeAudit, listEmployeeChanges } from "../../../../lib/endpoints";
import type { ApiResult } from "../../../../lib/endpoints";
import { formatLocalMoney } from "../../../../lib/format";
import { SESSION_COOKIE } from "../../../../lib/session";
import type { Employee } from "../../../../lib/types";
import { sumScaled } from "./pay-math";

export type StaleInfo = {
  yourVersion: number;
  yourLabel: string | null;
  nowVersion: number;
  nowLabel: string | null;
  changedBy: string | null;
  reason: string | null;
};

export async function requireToken(): Promise<string> {
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!token) {
    redirect("/login");
  }
  return token;
}

export function guard<T>(result: ApiResult<T>): ApiResult<T> {
  if (!result.ok && result.code === "unauthorized") {
    redirect("/logout");
  }
  return result;
}

export function totalLabel(employee: Employee): string {
  return formatLocalMoney(
    sumScaled(employee.base_salary_scaled, employee.variable_pay_scaled),
    employee.salary_scale,
    employee.currency_code,
  );
}

export async function describeStale(
  token: string,
  id: string,
  yourVersion: number,
  yourLabel: string | null,
  kind: "pay" | "details",
): Promise<StaleInfo | null> {
  const [fresh, latest] = await Promise.all([
    getEmployee(token, id),
    kind === "pay"
      ? listEmployeeAudit(token, id).then((r) => (r.ok ? r.data.items[0] : undefined))
      : listEmployeeChanges(token, id).then((r) => (r.ok ? r.data.items[0] : undefined)),
  ]);
  if (!fresh.ok) {
    return null;
  }
  return {
    yourVersion,
    yourLabel,
    nowVersion: fresh.data.version_id,
    nowLabel: kind === "pay" ? totalLabel(fresh.data) : null,
    changedBy: latest?.changed_by ?? null,
    reason: latest?.reason ?? null,
  };
}

export function profilePath(id: string, saved?: string): string {
  const base = `/employees/${encodeURIComponent(id)}`;
  return saved ? `${base}?saved=${saved}` : base;
}

export function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

export function mapFieldErrors(
  errors: Record<string, string>,
  names: Record<string, string>,
): Record<string, string> {
  const mapped: Record<string, string> = {};
  for (const [key, message] of Object.entries(errors)) {
    mapped[names[key] ?? key] = message;
  }
  return mapped;
}

export function isoDate(value: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    return false;
  }
  const date = new Date(`${value}T00:00:00Z`);
  return !Number.isNaN(date.getTime()) && date.toISOString().startsWith(value);
}

export function formText(formData: FormData, key: string): string {
  const value = formData.get(key);
  return typeof value === "string" ? value : "";
}
