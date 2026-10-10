"use server";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { createEmployee, reference } from "../../lib/endpoints";
import { describeFailure } from "../../lib/errors";
import { majorToScaled } from "../../lib/format";
import { SESSION_COOKIE } from "../../lib/session";
import type { CreateEmployeeRequest, EmployeeStatus, Level } from "../../lib/types";

export type AddEmployeeState = {
  values: Record<string, string>;
  fieldErrors: Record<string, string>;
  formError: string | null;
  attempt: number;
};

const TEXT_FIELDS = [
  "first_name",
  "last_name",
  "email",
  "job_title",
  "department_id",
  "level",
  "status",
  "country_code",
  "base_salary",
  "variable_pay",
  "hire_date",
  "comp_effective_date",
] as const;

const REQUIRED_TEXT: Record<string, string> = {
  first_name: "Enter a first name.",
  last_name: "Enter a last name.",
  email: "Enter a valid email address.",
  job_title: "Enter a job title.",
  department_id: "Choose a department.",
  level: "Choose a level.",
  status: "Choose a status.",
  country_code: "Choose a country.",
  base_salary: "Enter a valid base salary.",
  hire_date: "Enter a valid hire date.",
  comp_effective_date: "Enter a valid effective date.",
};

const PAY_FIELD_FOR: Record<string, string> = {
  base_salary_scaled: "base_salary",
  variable_pay_scaled: "variable_pay",
};

const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;

export async function addEmployeeAction(
  state: AddEmployeeState,
  formData: FormData,
): Promise<AddEmployeeState> {
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!token) {
    redirect("/login");
  }

  const values: Record<string, string> = {};
  for (const name of TEXT_FIELDS) {
    const raw = formData.get(name);
    values[name] = typeof raw === "string" ? raw.trim() : "";
  }
  const fail = (fieldErrors: Record<string, string>, formError: string | null): AddEmployeeState => ({
    values,
    fieldErrors,
    formError,
    attempt: state.attempt + 1,
  });

  const fieldErrors: Record<string, string> = {};
  for (const [name, message] of Object.entries(REQUIRED_TEXT)) {
    if (values[name] === "") {
      fieldErrors[name] = message;
    }
  }
  for (const name of ["hire_date", "comp_effective_date"]) {
    if (values[name] !== "" && !ISO_DATE.test(values[name] ?? "")) {
      fieldErrors[name] = REQUIRED_TEXT[name] ?? "";
    }
  }
  if (values["department_id"] !== "" && !/^\d+$/.test(values["department_id"] ?? "")) {
    fieldErrors["department_id"] = REQUIRED_TEXT["department_id"] ?? "";
  }

  const ref = await reference(token);
  if (!ref.ok) {
    if (ref.code === "unauthorized") {
      redirect("/logout");
    }
    return fail(fieldErrors, ref.message);
  }
  const country = ref.data.countries.find((item) => item.code === values["country_code"]);
  const currency = ref.data.currencies.find((item) => item.code === country?.currency_code);
  if (values["country_code"] !== "" && !currency) {
    fieldErrors["country_code"] = REQUIRED_TEXT["country_code"] ?? "";
  }

  const payText = (value: string | undefined) => (value ?? "").replace(/,/g, "");
  const base = currency ? majorToScaled(payText(values["base_salary"]), currency.minor_scale) : null;
  const variable = currency
    ? majorToScaled(payText(values["variable_pay"]) || "0", currency.minor_scale)
    : null;
  if (currency && values["base_salary"] !== "" && (base === null || base.startsWith("-"))) {
    fieldErrors["base_salary"] =
      base === null ? "Enter a valid base salary." : "Pay cannot be negative.";
  }
  if (currency && (variable === null || variable.startsWith("-"))) {
    fieldErrors["variable_pay"] =
      variable === null ? "Enter a valid variable pay amount." : "Pay cannot be negative.";
  }

  if (Object.keys(fieldErrors).length > 0 || base === null || variable === null) {
    return fail(fieldErrors, "Check the highlighted fields and try again.");
  }

  const body: CreateEmployeeRequest = {
    first_name: values["first_name"] ?? "",
    last_name: values["last_name"] ?? "",
    email: values["email"] ?? "",
    job_title: values["job_title"] ?? "",
    department_id: Number(values["department_id"]),
    country_code: values["country_code"] ?? "",
    level: (values["level"] ?? "") as Level,
    status: (values["status"] ?? "") as EmployeeStatus,
    base_salary_scaled: base,
    variable_pay_scaled: variable,
    hire_date: values["hire_date"] ?? "",
    comp_effective_date: values["comp_effective_date"] ?? "",
  };

  const created = await createEmployee(token, body);
  if (!created.ok) {
    if (created.code === "unauthorized") {
      redirect("/logout");
    }
    if (created.code === "duplicate_email") {
      return fail({ email: created.message }, null);
    }
    const view = describeFailure(created);
    const mapped: Record<string, string> = {};
    for (const [name, message] of Object.entries(view.fieldErrors)) {
      mapped[PAY_FIELD_FOR[name] ?? name] = message;
    }
    return fail(mapped, view.formError);
  }

  redirect(`/employees/${encodeURIComponent(created.data.id)}?added=${encodeURIComponent(created.data.employee_number)}`);
}
