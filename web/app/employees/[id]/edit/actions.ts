"use server";

import { redirect } from "next/navigation";
import { changeStatus, updateEmployee } from "../../../../lib/endpoints";
import { describeFailure } from "../../../../lib/errors";
import type { Level } from "../../../../lib/types";
import { changedPayload, type DetailsValues } from "../_lib/diff";
import {
  describeStale,
  formText,
  guard,
  isoDate,
  profilePath,
  requireToken,
} from "../_lib/server";
import type { StaleInfo } from "../_lib/server";

export type EditFormState = {
  values: Record<string, string> | null;
  fieldErrors: Record<string, string>;
  formError: string | null;
  stale: StaleInfo | null;
  isStale: boolean;
};

const DETAIL_KEYS: (keyof DetailsValues)[] = [
  "first_name",
  "last_name",
  "email",
  "job_title",
  "department_id",
  "level",
];

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function failure(
  values: Record<string, string>,
  fieldErrors: Record<string, string>,
  formError: string | null = null,
): EditFormState {
  return { values, fieldErrors, formError, stale: null, isStale: false };
}

function readVersion(formData: FormData): number | null {
  const text = formText(formData, "version_id");
  return /^\d+$/.test(text) ? Number(text) : null;
}

function commonErrors(values: Record<string, string>): Record<string, string> {
  const errors: Record<string, string> = {};
  if (!isoDate(values["effective_date"] ?? "")) {
    errors["effective_date"] = "Enter a valid effective date.";
  }
  if ((values["reason"] ?? "").trim() === "") {
    errors["reason"] = "Enter a reason for this change.";
  }
  return errors;
}

export async function updateDetailsAction(
  employeeId: string,
  original: DetailsValues,
  _state: EditFormState,
  formData: FormData,
): Promise<EditFormState> {
  const token = await requireToken();
  const values: Record<string, string> = {};
  for (const key of [...DETAIL_KEYS, "effective_date", "reason"]) {
    values[key] = formText(formData, key);
  }
  const next = values as unknown as DetailsValues;
  const errors = commonErrors(values);
  for (const key of ["first_name", "last_name", "job_title"] as const) {
    if (next[key].trim() === "") {
      errors[key] = key === "job_title" ? "Enter a job title." : `Enter a ${key === "first_name" ? "first" : "last"} name.`;
    }
  }
  if (!EMAIL_PATTERN.test(next.email.trim())) {
    errors["email"] = "Enter a valid email address.";
  }

  const changes = changedPayload(original, next);
  if (Object.keys(changes).length === 0 && Object.keys(errors).length === 0) {
    return failure(values, {}, "Nothing to save.");
  }
  if (Object.keys(errors).length > 0) {
    return failure(values, errors);
  }
  const versionId = readVersion(formData);
  if (versionId === null) {
    return failure(values, {}, "Reload the page and try again.");
  }

  const result = guard(
    await updateEmployee(token, employeeId, {
      ...changes,
      level: changes.level as Level | undefined,
      reason: (values["reason"] ?? "").trim(),
      effective_date: values["effective_date"] ?? "",
      version_id: versionId,
    }),
  );
  if (result.ok) {
    redirect(profilePath(employeeId, "details"));
  }
  return outcome(result, token, employeeId, versionId, values);
}

export async function changeStatusAction(
  employeeId: string,
  target: "active" | "terminated",
  _state: EditFormState,
  formData: FormData,
): Promise<EditFormState> {
  const token = await requireToken();
  const values: Record<string, string> = {
    effective_date: formText(formData, "effective_date"),
    reason: formText(formData, "reason"),
  };
  const errors = commonErrors(values);
  if (Object.keys(errors).length > 0) {
    return failure(values, errors);
  }
  const versionId = readVersion(formData);
  if (versionId === null) {
    return failure(values, {}, "Reload the page and try again.");
  }

  const result = guard(
    await changeStatus(token, employeeId, {
      status: target,
      reason: (values["reason"] ?? "").trim(),
      effective_date: values["effective_date"] ?? "",
      version_id: versionId,
    }),
  );
  if (result.ok) {
    redirect(profilePath(employeeId, "status"));
  }
  return outcome(result, token, employeeId, versionId, values);
}

async function outcome(
  result: Extract<Awaited<ReturnType<typeof updateEmployee>>, { ok: false }>,
  token: string,
  employeeId: string,
  versionId: number,
  values: Record<string, string>,
): Promise<EditFormState> {
  const view = describeFailure(result);
  if (view.isStale) {
    return {
      values,
      fieldErrors: {},
      formError: null,
      isStale: true,
      stale: await describeStale(token, employeeId, versionId, null, "details"),
    };
  }
  return failure(values, view.fieldErrors, view.formError);
}
