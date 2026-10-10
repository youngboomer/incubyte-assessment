export type LoginResponse = {
  access_token: string;
  token_type: "bearer";
};

export type MeResponse = {
  email: string;
  name: string;
};

export type HealthResponse = {
  status: string;
};

export type Department = {
  id: number;
  name: string;
};

export type Country = {
  code: string;
  name: string;
  currency_code: string;
};

export type EmployeeCountry = {
  code: string;
  name: string;
};

export type Currency = {
  code: string;
  name: string;
  minor_scale: number;
  units_per_usd_scaled: string;
  units_per_usd_scale: number;
};

export type Reference = {
  departments: Department[];
  countries: Country[];
  currencies: Currency[];
  levels: string[];
  statuses: string[];
};

export type Employee = {
  id: string;
  employee_number: string;
  first_name: string;
  last_name: string;
  email: string;
  job_title: string;
  department: Department;
  country: EmployeeCountry;
  currency_code: string;
  level: string;
  base_salary_scaled: string;
  variable_pay_scaled: string;
  salary_scale: number;
  salary_usd_scaled: string;
  salary_usd_scale: number;
  status: string;
  hire_date: string;
  comp_effective_date: string;
  version_id: number;
};

export type DirectoryPage = {
  items: Employee[];
  next_cursor: string | null;
  prev_cursor: string | null;
  total: number;
};

export type AuditEntry = {
  id: number;
  previous_base_salary_scaled: string;
  new_base_salary_scaled: string;
  previous_variable_pay_scaled: string;
  new_variable_pay_scaled: string;
  salary_scale: number;
  currency_code: string;
  fx_units_per_usd_scaled: string;
  fx_scale: number;
  previous_salary_usd_scaled: string;
  new_salary_usd_scaled: string;
  salary_usd_scale: number;
  reason: string;
  effective_date: string;
  changed_by: string;
  created_at: string;
};

export type AuditPage = {
  items: AuditEntry[];
};

export type DepartmentBreakdown = {
  department_id: number;
  department_name: string;
  headcount: number;
  total_salary_usd_scaled: string;
  average_salary_usd_scaled: string;
};

export type CountryBreakdown = {
  country_code: string;
  country_name: string;
  headcount: number;
  total_salary_usd_scaled: string;
  average_salary_usd_scaled: string;
};

export type SalaryHistogramBucket = {
  label: string;
  count: number;
};

export type AnalyticsOverview = {
  headcount: number;
  total_salary_usd_scaled: string;
  salary_usd_scale: number;
  average_salary_usd_scaled: string;
  p25_salary_usd_scaled: string;
  p50_salary_usd_scaled: string;
  p75_salary_usd_scaled: string;
  by_department: DepartmentBreakdown[];
  by_country: CountryBreakdown[];
  by_level: LevelBreakdown[];
  histogram: SalaryHistogramBucket[];
};

export type Level = "IC1" | "IC2" | "IC3" | "IC4" | "IC5" | "M1" | "M2";

export type EmployeeStatus = "active" | "terminated";

export type SortKey =
  | "name"
  | "employee_number"
  | "department"
  | "country"
  | "title"
  | "base_salary"
  | "salary_usd"
  | "hire_date";

export type SortDirection = "asc" | "desc";

export type LevelBreakdown = {
  level: string;
  headcount: number;
  total_salary_usd_scaled: string;
  average_salary_usd_scaled: string;
  min_salary_usd_scaled: string;
  p50_salary_usd_scaled: string;
  max_salary_usd_scaled: string;
};

export type DirectoryFilters = {
  q?: string;
  department_id?: string;
  country?: string;
  currency?: string;
  status?: EmployeeStatus;
  level?: Level;
  salary_usd_min?: string;
  salary_usd_max?: string;
  sort?: SortKey;
  direction?: SortDirection;
  limit?: number;
  cursor?: string;
};

export type ScopeFilters = {
  department_id?: string;
  country?: string;
  level?: Level;
  currency?: string;
};

export type AuditFilters = {
  employee_id?: string;
  department_id?: string;
  since?: string;
  until?: string;
  changed_by?: string;
  limit?: number;
};

export type EmployeeChange = {
  id: number;
  field: string;
  previous_value: string;
  new_value: string;
  reason: string;
  effective_date: string;
  changed_by: string;
  created_at: string;
};

export type EmployeeChangesPage = {
  items: EmployeeChange[];
};

export type AuditFeedItem = AuditEntry & {
  employee_id: string;
  employee_number: string;
  employee_name: string;
  department: Department;
};

export type AuditFeedPage = {
  items: AuditFeedItem[];
  next_cursor: string | null;
};

export type ChangeField =
  | "first_name"
  | "last_name"
  | "email"
  | "job_title"
  | "department_id"
  | "level"
  | "status";

export type ChangeFilters = AuditFilters & {
  field?: ChangeField;
};

export type ChangeFeedItem = EmployeeChange & {
  employee_id: string;
  employee_number: string;
  employee_name: string;
  department: Department;
  previous_label: string | null;
  new_label: string | null;
};

export type ChangeFeedPage = {
  items: ChangeFeedItem[];
  next_cursor: string | null;
};

export type LoginRequest = {
  email: string;
  password: string;
};

export type CreateEmployeeRequest = {
  first_name: string;
  last_name: string;
  email: string;
  job_title: string;
  department_id: number;
  country_code: string;
  level: Level;
  base_salary_scaled: string;
  variable_pay_scaled: string;
  status: EmployeeStatus;
  hire_date: string;
  comp_effective_date: string;
};

export type UpdateEmployeeRequest = {
  first_name?: string;
  last_name?: string;
  email?: string;
  job_title?: string;
  department_id?: number;
  level?: Level;
  reason: string;
  effective_date: string;
  version_id: number;
};

export type ChangeStatusRequest = {
  status: EmployeeStatus;
  reason: string;
  effective_date: string;
  version_id: number;
};

export type ChangePayRequest = {
  base_salary_scaled: string;
  variable_pay_scaled: string;
  reason: string;
  effective_date: string;
  version_id: number;
};

export type UpdateRateRequest = {
  units_per_usd_scaled: string;
};

export type ValidationIssue = {
  loc: (string | number)[];
  msg: string;
  type?: string;
};
