"use server";

import { cookies } from "next/headers";
import { connection } from "next/server";
import { redirect } from "next/navigation";
import { backendFetch } from "../../lib/api";
import { majorToScaled } from "../../lib/format";
import { SESSION_COOKIE } from "../../lib/session";
import type { Employee, Reference } from "../../lib/types";

export type AddEmployeeState = {
  error: string;
};

const EMAIL_IN_USE = "That email is already in use.";
const CHECK_FORM = "Check the form and try again.";

export async function addEmployeeAction(
  _state: AddEmployeeState,
  formData: FormData,
): Promise<AddEmployeeState> {
  await connection();
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!token) {
    redirect("/login");
  }

  const first_name = field(formData, "first_name");
  const last_name = field(formData, "last_name");
  const email = field(formData, "email");
  const job_title = field(formData, "job_title");
  const departmentRaw = field(formData, "department_id");
  const country_code = field(formData, "country_code");
  const level = field(formData, "level");
  const status = field(formData, "status");
  const hire_date = field(formData, "hire_date");
  const comp_effective_date = field(formData, "comp_effective_date");
  const baseMajor = field(formData, "base_salary");
  const variableRaw = field(formData, "variable_pay");
  const variableMajor = variableRaw === "" ? "0" : variableRaw;

  if (
    !first_name ||
    !last_name ||
    !email ||
    !job_title ||
    !/^\d+$/.test(departmentRaw) ||
    !country_code ||
    !level ||
    !status ||
    !isIsoDate(hire_date) ||
    !isIsoDate(comp_effective_date) ||
    !baseMajor
  ) {
    return { error: CHECK_FORM };
  }

  const minorScale = await countryMinorScale(token, country_code);
  if (minorScale === null) {
    return { error: CHECK_FORM };
  }

  const base_salary_scaled = majorToScaled(baseMajor, minorScale);
  const variable_pay_scaled = majorToScaled(variableMajor, minorScale);
  if (base_salary_scaled === null || variable_pay_scaled === null) {
    return { error: CHECK_FORM };
  }

  const payload = {
    first_name,
    last_name,
    email,
    job_title,
    department_id: Number(departmentRaw),
    country_code,
    level,
    base_salary_scaled,
    variable_pay_scaled,
    status,
    hire_date,
    comp_effective_date,
  };

  let response: Response;
  try {
    response = await backendFetch("/employees", token, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch {
    return { error: CHECK_FORM };
  }

  if (response.status === 401) {
    redirect("/logout");
  }
  if (response.status === 409) {
    return { error: EMAIL_IN_USE };
  }
  if (response.status === 422) {
    return { error: CHECK_FORM };
  }
  if (!response.ok) {
    return { error: `Could not add employee. ${response.status}` };
  }

  let created: Employee;
  try {
    created = (await response.json()) as Employee;
  } catch {
    return { error: CHECK_FORM };
  }
  if (typeof created.id !== "string" || !/^[A-Za-z0-9_-]+$/.test(created.id)) {
    return { error: CHECK_FORM };
  }
  redirect(`/employees/${created.id}`);
}

function field(formData: FormData, name: string): string {
  const value = formData.get(name);
  return typeof value === "string" ? value.trim() : "";
}

function isIsoDate(value: string): boolean {
  return /^\d{4}-\d{2}-\d{2}$/.test(value);
}

// Scale follows the selected country's currency on the reference payload.
async function countryMinorScale(token: string, countryCode: string): Promise<number | null> {
  let response: Response;
  try {
    response = await backendFetch("/reference", token);
  } catch {
    return null;
  }
  if (response.status === 401) {
    redirect("/logout");
  }
  if (!response.ok) {
    return null;
  }
  try {
    const body = (await response.json()) as Reference;
    const countries = Array.isArray(body.countries) ? body.countries : [];
    const currencies = Array.isArray(body.currencies) ? body.currencies : [];
    const country = countries.find((item) => item.code === countryCode);
    if (!country) {
      return null;
    }
    const currency = currencies.find((item) => item.code === country.currency_code);
    if (!currency || !Number.isInteger(currency.minor_scale) || currency.minor_scale < 0) {
      return null;
    }
    return currency.minor_scale;
  } catch {
    return null;
  }
}
