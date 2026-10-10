"use server";

import { redirect } from "next/navigation";
import { changePay } from "../../../../lib/endpoints";
import { describeFailure } from "../../../../lib/errors";
import { majorToScaled } from "../../../../lib/format";
import {
  describeStale,
  formText,
  guard,
  isoDate,
  mapFieldErrors,
  profilePath,
  requireToken,
} from "../_lib/server";
import type { StaleInfo } from "../_lib/server";

export type PayValues = {
  base: string;
  variable: string;
  effective_date: string;
  reason: string;
};

export type PayFormState = {
  values: PayValues | null;
  fieldErrors: Record<string, string>;
  formError: string | null;
  stale: StaleInfo | null;
  isStale: boolean;
};

const FIELD_NAMES = {
  base_salary_scaled: "base",
  variable_pay_scaled: "variable",
  effective_date: "effective_date",
  reason: "reason",
};

export async function changePayAction(
  employeeId: string,
  salaryScale: number,
  _state: PayFormState,
  formData: FormData,
): Promise<PayFormState> {
  const token = await requireToken();
  const values: PayValues = {
    base: formText(formData, "base").trim(),
    variable: formText(formData, "variable").trim(),
    effective_date: formText(formData, "effective_date"),
    reason: formText(formData, "reason"),
  };
  const versionText = formText(formData, "version_id");
  const loadedTotal = formText(formData, "loaded_total");
  const versionId = /^\d+$/.test(versionText) ? Number(versionText) : null;
  const failed = (fieldErrors: Record<string, string>, formError: string | null = null): PayFormState => ({
    values,
    fieldErrors,
    formError,
    stale: null,
    isStale: false,
  });

  const base = majorToScaled(values.base, salaryScale);
  const variable = majorToScaled(values.variable === "" ? "0" : values.variable, salaryScale);
  const errors: Record<string, string> = {};
  if (base === null) {
    errors["base"] = "Enter a valid amount.";
  } else if (base.startsWith("-")) {
    errors["base"] = "Pay cannot be negative.";
  }
  if (variable === null) {
    errors["variable"] = "Enter a valid amount.";
  } else if (variable.startsWith("-")) {
    errors["variable"] = "Pay cannot be negative.";
  }
  if (!isoDate(values.effective_date)) {
    errors["effective_date"] = "Enter a valid effective date.";
  }
  if (values.reason.trim() === "") {
    errors["reason"] = "Enter a reason for this change.";
  }
  if (Object.keys(errors).length > 0 || base === null || variable === null) {
    return failed(errors);
  }
  if (versionId === null) {
    return failed({}, "Reload the page and try again.");
  }

  const result = guard(
    await changePay(token, employeeId, {
      base_salary_scaled: base,
      variable_pay_scaled: variable,
      reason: values.reason.trim(),
      effective_date: values.effective_date,
      version_id: versionId,
    }),
  );
  if (result.ok) {
    redirect(profilePath(employeeId, "pay"));
  }

  const view = describeFailure(result);
  if (view.isStale) {
    return {
      values,
      fieldErrors: {},
      formError: null,
      isStale: true,
      stale: await describeStale(token, employeeId, versionId, loadedTotal || null, "pay"),
    };
  }
  return failed(mapFieldErrors(view.fieldErrors, FIELD_NAMES), view.formError);
}
