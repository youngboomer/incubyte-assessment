import type { ValidationIssue } from "./types";

export type ErrorCode =
  | "unauthorized"
  | "not_found"
  | "stale"
  | "duplicate_email"
  | "duplicate_number"
  | "already_in_status"
  | "conflict"
  | "validation"
  | "rate_limited"
  | "server"
  | "network";

export type ApiFailure = {
  ok: false;
  status: number;
  message: string;
  code: ErrorCode;
  issues: ValidationIssue[];
};

export type ApiSuccess<T> = { ok: true; data: T };

export type ApiResult<T> = ApiSuccess<T> | ApiFailure;

export type FailureView = {
  formError: string | null;
  fieldErrors: Record<string, string>;
  isStale: boolean;
};

export const MESSAGES = {
  stale: "Someone else changed this record. Nothing was saved. Reload to see the latest.",
  duplicateEmail: "This email is already used by another employee.",
  duplicateNumber: "This employee number is already in use.",
  unauthorized: "Your session has expired. Sign in again.",
  notFound: "We could not find that record.",
  rateLimited: "Too many attempts. Try again in a few minutes.",
  server: "Something went wrong. Try again.",
  validation: "Check the highlighted fields and try again.",
  validationGeneric: "Check the values and try again.",
  invalidCredentials: "Email or password is incorrect.",
} as const;

const FIELD_TEXT: Record<string, string> = {
  reason: "Enter a reason for this change.",
  email: "Enter a valid email address.",
  first_name: "Enter a first name.",
  last_name: "Enter a last name.",
  job_title: "Enter a job title.",
  department_id: "Choose a department.",
  country_code: "Choose a country.",
  level: "Choose a level.",
  status: "Choose a status.",
  effective_date: "Enter a valid effective date.",
  comp_effective_date: "Enter a valid effective date.",
  hire_date: "Enter a valid hire date.",
  base_salary_scaled: "Enter a valid base salary.",
  variable_pay_scaled: "Enter a valid variable pay amount.",
  units_per_usd_scaled: "Enter a valid rate.",
  version_id: "Reload the page and try again.",
};

const PAY_FIELDS = ["base_salary_scaled", "variable_pay_scaled", "units_per_usd_scaled"];

export function issueField(issue: ValidationIssue): string | null {
  const parts = issue.loc.filter(
    (part): part is string => typeof part === "string" && part !== "body" && part !== "query",
  );
  return parts.length === 0 ? null : (parts[parts.length - 1] ?? null);
}

export function issueText(field: string, issue: ValidationIssue): string {
  const detail = `${issue.type ?? ""} ${issue.msg}`.toLowerCase();
  if (PAY_FIELDS.includes(field) && /negative|greater_than/.test(detail)) {
    return "Pay cannot be negative.";
  }
  return FIELD_TEXT[field] ?? MESSAGES.validationGeneric;
}

export function fieldErrorsFrom(issues: ValidationIssue[]): Record<string, string> {
  const result: Record<string, string> = {};
  for (const issue of issues) {
    const field = issueField(issue);
    if (field !== null && !(field in result)) {
      result[field] = issueText(field, issue);
    }
  }
  return result;
}

function isIssue(value: unknown): value is ValidationIssue {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const record = value as Record<string, unknown>;
  return Array.isArray(record["loc"]) && typeof record["msg"] === "string";
}

function detailOf(body: unknown): unknown {
  if (typeof body === "object" && body !== null && "detail" in body) {
    return (body as { detail: unknown }).detail;
  }
  return undefined;
}

export function failureFromResponse(status: number, body: unknown): ApiFailure {
  const detail = detailOf(body);
  const text = typeof detail === "string" ? detail.toLowerCase() : "";
  const make = (code: ErrorCode, message: string, issues: ValidationIssue[] = []): ApiFailure => ({
    ok: false,
    status,
    message,
    code,
    issues,
  });

  if (status === 401) {
    return make("unauthorized", MESSAGES.unauthorized);
  }
  if (status === 404) {
    return make("not_found", MESSAGES.notFound);
  }
  if (status === 429) {
    return make("rate_limited", MESSAGES.rateLimited);
  }
  if (status === 409) {
    if (text.includes("email")) {
      return make("duplicate_email", MESSAGES.duplicateEmail);
    }
    if (text.includes("employee number")) {
      return make("duplicate_number", MESSAGES.duplicateNumber);
    }
    if (text.includes("already")) {
      const wanted = text.includes("terminated") ? "terminated" : "active";
      return make("already_in_status", `This employee is already ${wanted}.`);
    }
    return make("stale", MESSAGES.stale);
  }
  if (status === 422) {
    const issues = Array.isArray(detail) ? detail.filter(isIssue) : [];
    return make(
      "validation",
      Object.keys(fieldErrorsFrom(issues)).length > 0
        ? MESSAGES.validation
        : MESSAGES.validationGeneric,
      issues,
    );
  }
  if (status >= 500 || status === 0) {
    return make("server", MESSAGES.server);
  }
  return make("conflict", MESSAGES.server);
}

export function networkFailure(): ApiFailure {
  return { ok: false, status: 0, message: MESSAGES.server, code: "network", issues: [] };
}

export function describeFailure(failure: ApiFailure): FailureView {
  const fieldErrors = fieldErrorsFrom(failure.issues);
  const hasFields = Object.keys(fieldErrors).length > 0;
  return {
    formError: hasFields && failure.code === "validation" ? null : failure.message,
    fieldErrors,
    isStale: failure.code === "stale",
  };
}
