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
  histogram: SalaryHistogramBucket[];
};
