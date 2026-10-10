"use client";

import { useActionState, useState } from "react";
import { Button, Input, Notice, Select, Textarea } from "../../../../components/ui";
import type { Department } from "../../../../lib/types";
import { summarizeChanges, type DetailsValues } from "../_lib/diff";
import { StaleNotice } from "../_lib/stale-notice";
import shared from "../_lib/shared.module.css";
import {
  changeStatusAction,
  updateDetailsAction,
  type EditFormState,
} from "./actions";
import styles from "./edit.module.css";

const INITIAL: EditFormState = { values: null, fieldErrors: {}, formError: null, stale: null, isStale: false };

function Banner({ state, reloadLabel }: { state: EditFormState; reloadLabel: string }) {
  if (state.isStale) {
    return <StaleNotice info={state.stale} reloadLabel={reloadLabel} />;
  }
  return state.formError ? (
    <Notice tone={state.formError === "Nothing to save." ? "info" : "error"}>{state.formError}</Notice>
  ) : null;
}

export function DetailsForm({
  employeeId,
  versionId,
  original,
  departments,
  levels,
  countryName,
  currencyCode,
  today,
}: {
  employeeId: string;
  versionId: number;
  original: DetailsValues;
  departments: Department[];
  levels: string[];
  countryName: string;
  currencyCode: string;
  today: string;
}) {
  const [state, formAction, pending] = useActionState(
    updateDetailsAction.bind(null, employeeId, original),
    INITIAL,
  );
  const [values, setValues] = useState<DetailsValues>(original);
  const [date, setDate] = useState(today);
  const [reason, setReason] = useState("");
  const set = (key: keyof DetailsValues) => (event: { target: { value: string } }) =>
    setValues((current) => ({ ...current, [key]: event.target.value }));
  const errors = state.fieldErrors;
  const changes = summarizeChanges(original, values, departments);

  return (
    <form action={formAction} className={shared.form} noValidate>
      <input type="hidden" name="version_id" value={versionId} />
      <Banner state={state} reloadLabel="Reload latest details" />
      <div className={shared.row}>
        <Input name="first_name" label="First name" value={values.first_name} onChange={set("first_name")} error={errors["first_name"]} required />
        <Input name="last_name" label="Last name" value={values.last_name} onChange={set("last_name")} error={errors["last_name"]} required />
      </div>
      <Input name="email" type="email" label="Email" value={values.email} onChange={set("email")} error={errors["email"]} required />
      <Input name="job_title" label="Job title" value={values.job_title} onChange={set("job_title")} error={errors["job_title"]} required />
      <div className={shared.row}>
        <Select name="department_id" label="Department" value={values.department_id} onChange={set("department_id")} error={errors["department_id"]} required>
          {departments.map((department) => (
            <option key={department.id} value={String(department.id)}>
              {department.name}
            </option>
          ))}
        </Select>
        <Select name="level" label="Level" value={values.level} onChange={set("level")} error={errors["level"]} required>
          {levels.map((level) => (
            <option key={level} value={level}>
              {level}
            </option>
          ))}
        </Select>
      </div>

      <div className={shared.row}>
        <Input label="Country" value={countryName} readOnly disabled />
        <Input label="Currency" value={currencyCode} readOnly disabled />
      </div>
      <p className={styles.hintText}>Country and currency cannot be changed here.</p>

      <div className={shared.row}>
        <Input
          name="effective_date"
          type="date"
          label="Effective date"
          value={date}
          onChange={(event) => setDate(event.target.value)}
          error={errors["effective_date"]}
          required
        />
      </div>
      <Textarea
        name="reason"
        label="Reason"
        hint="Shown in the change history. Cannot be edited later."
        value={reason}
        onChange={(event) => setReason(event.target.value)}
        error={errors["reason"]}
        required
      />

      {changes.length > 0 ? (
        <div className={shared.summary} aria-live="polite">
          <strong>What will change</strong>
          <ul className={shared.summaryList}>
            {changes.map((change) => (
              <li key={change.field}>
                {change.label}: {change.from} {"→"} {change.to}
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <p className={shared.summaryMuted} aria-live="polite">
          No changes yet.
        </p>
      )}

      <div className={shared.actions}>
        <Button type="submit" loading={pending}>
          Save details
        </Button>
      </div>
    </form>
  );
}

export function StatusForm({
  employeeId,
  versionId,
  target,
  today,
}: {
  employeeId: string;
  versionId: number;
  target: "active" | "terminated";
  today: string;
}) {
  const [state, formAction, pending] = useActionState(
    changeStatusAction.bind(null, employeeId, target),
    INITIAL,
  );
  const [date, setDate] = useState(today);
  const [reason, setReason] = useState("");
  const errors = state.fieldErrors;
  const terminating = target === "terminated";
  return (
    <form action={formAction} className={shared.form} noValidate>
      <input type="hidden" name="version_id" value={versionId} />
      <Banner state={state} reloadLabel="Reload latest details" />
      <Input
        name="effective_date"
        type="date"
        label="Effective date"
        value={date}
        onChange={(event) => setDate(event.target.value)}
        error={errors["effective_date"]}
        required
      />
      <Textarea
        name="reason"
        label="Reason"
        hint="Shown in the change history. Cannot be edited later."
        value={reason}
        onChange={(event) => setReason(event.target.value)}
        error={errors["reason"]}
        required
      />
      <div className={shared.actions}>
        <Button type="submit" variant={terminating ? "danger" : "primary"} loading={pending}>
          {terminating ? "Terminate" : "Reactivate"}
        </Button>
      </div>
    </form>
  );
}
