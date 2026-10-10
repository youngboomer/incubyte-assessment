import { backendFetch } from "./api";
import { MESSAGES, failureFromResponse, networkFailure } from "./errors";
import type { ApiResult } from "./errors";
import { auditQuery, changesQuery, directoryQuery, scopeQuery } from "./query";
import type {
  AnalyticsOverview,
  AuditFeedPage,
  AuditFilters,
  AuditPage,
  ChangeFeedPage,
  ChangeFilters,
  ChangePayRequest,
  ChangeStatusRequest,
  CreateEmployeeRequest,
  Currency,
  DirectoryFilters,
  DirectoryPage,
  Employee,
  EmployeeChangesPage,
  LoginRequest,
  LoginResponse,
  MeResponse,
  Reference,
  ScopeFilters,
  UpdateEmployeeRequest,
  UpdateRateRequest,
} from "./types";

export type { ApiFailure, ApiResult } from "./errors";

type Method = "GET" | "POST" | "PATCH";

async function call(
  method: Method,
  path: string,
  token: string | undefined,
  body?: unknown,
): Promise<Response | null> {
  const init: RequestInit = { method };
  if (body !== undefined) {
    init.headers = { "content-type": "application/json" };
    init.body = JSON.stringify(body);
  }
  try {
    return await backendFetch(path, token, init);
  } catch {
    return null;
  }
}

async function readJson(response: Response): Promise<unknown> {
  try {
    return await response.json();
  } catch {
    return undefined;
  }
}

async function request<T>(
  method: Method,
  path: string,
  token: string | undefined,
  body?: unknown,
): Promise<ApiResult<T>> {
  const response = await call(method, path, token, body);
  if (response === null) {
    return networkFailure();
  }
  if (!response.ok) {
    return failureFromResponse(response.status, await readJson(response));
  }
  const data = await readJson(response);
  if (data === undefined) {
    return failureFromResponse(502, undefined);
  }
  return { ok: true, data: data as T };
}

function employeePath(id: string, suffix = ""): string {
  return `/employees/${encodeURIComponent(id)}${suffix}`;
}

export async function login(credentials: LoginRequest): Promise<ApiResult<LoginResponse>> {
  const result = await request<LoginResponse>("POST", "/auth/login", undefined, credentials);
  if (!result.ok && result.status === 401) {
    return { ...result, message: MESSAGES.invalidCredentials };
  }
  return result;
}

export async function logout(token: string): Promise<ApiResult<null>> {
  const response = await call("POST", "/auth/logout", token);
  if (response === null) {
    return networkFailure();
  }
  if (!response.ok) {
    return failureFromResponse(response.status, await readJson(response));
  }
  return { ok: true, data: null };
}

export function me(token: string): Promise<ApiResult<MeResponse>> {
  return request("GET", "/auth/me", token);
}

export function reference(token: string): Promise<ApiResult<Reference>> {
  return request("GET", "/reference", token);
}

export function listEmployees(
  token: string,
  filters: DirectoryFilters = {},
): Promise<ApiResult<DirectoryPage>> {
  return request("GET", `/employees${directoryQuery(filters)}`, token);
}

export async function exportEmployeesCsv(
  token: string,
  filters: DirectoryFilters = {},
): Promise<ApiResult<Response>> {
  const { cursor: _cursor, limit: _limit, ...rest } = filters;
  const response = await call("GET", `/employees/export.csv${directoryQuery(rest)}`, token);
  if (response === null) {
    return networkFailure();
  }
  if (!response.ok) {
    return failureFromResponse(response.status, await readJson(response));
  }
  return { ok: true, data: response };
}

export function getEmployee(token: string, id: string): Promise<ApiResult<Employee>> {
  return request("GET", employeePath(id), token);
}

export function createEmployee(
  token: string,
  body: CreateEmployeeRequest,
): Promise<ApiResult<Employee>> {
  return request("POST", "/employees", token, body);
}

export function updateEmployee(
  token: string,
  id: string,
  body: UpdateEmployeeRequest,
): Promise<ApiResult<Employee>> {
  return request("PATCH", employeePath(id), token, body);
}

export function changeStatus(
  token: string,
  id: string,
  body: ChangeStatusRequest,
): Promise<ApiResult<Employee>> {
  return request("POST", employeePath(id, "/status"), token, body);
}

export function changePay(
  token: string,
  id: string,
  body: ChangePayRequest,
): Promise<ApiResult<Employee>> {
  return request("PATCH", employeePath(id, "/compensation"), token, body);
}

export function listEmployeeChanges(
  token: string,
  id: string,
): Promise<ApiResult<EmployeeChangesPage>> {
  return request("GET", employeePath(id, "/changes"), token);
}

export function listEmployeeAudit(token: string, id: string): Promise<ApiResult<AuditPage>> {
  return request("GET", employeePath(id, "/audit"), token);
}

export function getAuditFeed(
  token: string,
  filters: AuditFilters = {},
  cursor?: string,
): Promise<ApiResult<AuditFeedPage>> {
  return request("GET", `/audit${auditQuery(filters, cursor)}`, token);
}

export function getChangesFeed(
  token: string,
  filters: ChangeFilters = {},
  cursor?: string,
): Promise<ApiResult<ChangeFeedPage>> {
  return request("GET", `/changes${changesQuery(filters, cursor)}`, token);
}

export function getOverview(
  token: string,
  scope: ScopeFilters = {},
): Promise<ApiResult<AnalyticsOverview>> {
  return request("GET", `/analytics/overview${scopeQuery(scope)}`, token);
}

export function listRates(token: string): Promise<ApiResult<Currency[]>> {
  return request("GET", "/fx", token);
}

export function updateRate(
  token: string,
  code: string,
  body: UpdateRateRequest,
): Promise<ApiResult<Currency>> {
  return request("PATCH", `/fx/${encodeURIComponent(code)}`, token, body);
}
