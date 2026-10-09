"use server";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { backendFetch } from "../../../lib/api";
import { majorToScaled } from "../../../lib/format";
import { SESSION_COOKIE } from "../../../lib/session";

export type PayFormState = {
  message: string;
  conflict: boolean;
};

const AMOUNT_ERROR = "Check the amounts and try again.";
const CONFLICT_MESSAGE = "Record was modified. Reload and try again.";

type PayInput = {
  baseSalaryScaled: string;
  variablePayScaled: string;
  reason: string;
  effectiveDate: string;
  versionId: number;
};

export async function updatePayAction(
  employeeId: string,
  salaryScale: number,
  _state: PayFormState,
  formData: FormData,
): Promise<PayFormState> {
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!token) {
    redirect("/login");
  }

  const parsed = readPayInput(formData, salaryScale);
  if (!parsed) {
    return { message: AMOUNT_ERROR, conflict: false };
  }

  let response: Response;
  try {
    response = await backendFetch(
      `/employees/${encodeURIComponent(employeeId)}/compensation`,
      token,
      {
        method: "PATCH",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          base_salary_scaled: parsed.baseSalaryScaled,
          variable_pay_scaled: parsed.variablePayScaled,
          reason: parsed.reason,
          effective_date: parsed.effectiveDate,
          version_id: parsed.versionId,
        }),
      },
    );
  } catch (error) {
    return { message: saveError(error), conflict: false };
  }

  if (response.status === 401) {
    redirect("/logout");
  }
  if (response.status === 409) {
    // Stale version_id. Return once and do not PATCH again.
    return { message: CONFLICT_MESSAGE, conflict: true };
  }
  if (response.status === 422) {
    return { message: AMOUNT_ERROR, conflict: false };
  }
  if (response.status === 404) {
    return { message: "Employee not found.", conflict: false };
  }
  if (!response.ok) {
    return { message: `Could not save pay. ${response.status}`, conflict: false };
  }

  redirect(`/employees/${encodeURIComponent(employeeId)}`);
}

function readPayInput(formData: FormData, salaryScale: number): PayInput | null {
  const reason = formData.get("reason");
  const effectiveDate = formData.get("effective_date");
  const baseAmount = formData.get("base_salary");
  const variableAmount = formData.get("variable_pay");
  const versionId = readVersion(formData.get("version_id"));
  if (
    typeof reason !== "string" ||
    reason === "" ||
    typeof effectiveDate !== "string" ||
    !isIsoDate(effectiveDate) ||
    typeof baseAmount !== "string" ||
    typeof variableAmount !== "string" ||
    versionId === null
  ) {
    return null;
  }

  const baseSalaryScaled = majorToScaled(baseAmount, salaryScale);
  const variablePayScaled = majorToScaled(variableAmount, salaryScale);
  if (baseSalaryScaled === null || variablePayScaled === null) {
    return null;
  }

  return {
    baseSalaryScaled,
    variablePayScaled,
    reason,
    effectiveDate,
    versionId,
  };
}

function readVersion(value: FormDataEntryValue | null): number | null {
  if (typeof value !== "string" || !/^\d+$/.test(value)) {
    return null;
  }
  const versionId = Number(value);
  if (!Number.isSafeInteger(versionId)) {
    return null;
  }
  return versionId;
}

function isIsoDate(value: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    return false;
  }
  const [yearText, monthText, dayText] = value.split("-");
  const year = Number(yearText);
  const month = Number(monthText);
  const day = Number(dayText);
  const date = new Date(Date.UTC(year, month - 1, day));
  return (
    date.getUTCFullYear() === year &&
    date.getUTCMonth() === month - 1 &&
    date.getUTCDate() === day
  );
}

function saveError(error: unknown): string {
  if (error instanceof Error && error.message === "BACKEND_URL is not set") {
    return "BACKEND_URL is not set";
  }
  return "Could not save pay.";
}
