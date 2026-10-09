"use client";

import { useActionState } from "react";
import { updatePayAction, type PayFormState } from "./actions";
import styles from "./profile.module.css";

const initialState: PayFormState = { message: "", conflict: false };

export function PayForm({
  employeeId,
  salaryScale,
  versionId,
  currencyCode,
}: {
  employeeId: string;
  salaryScale: number;
  versionId: number;
  currencyCode: string;
}) {
  const [state, formAction, pending] = useActionState(
    updatePayAction.bind(null, employeeId, salaryScale),
    initialState,
  );
  const profileHref = `/employees/${encodeURIComponent(employeeId)}`;

  return (
    <form className={styles.form} action={formAction}>
      <input type="hidden" name="version_id" value={versionId} />
      <label>
        Reason
        <input name="reason" type="text" required />
      </label>
      <label>
        Effective date
        <input name="effective_date" type="date" required />
      </label>
      <label>
        Base salary ({currencyCode} major units)
        <input name="base_salary" type="text" inputMode="decimal" required />
      </label>
      <label>
        Variable pay ({currencyCode} major units)
        <input name="variable_pay" type="text" inputMode="decimal" required />
      </label>
      <button type="submit" disabled={pending}>
        Save pay
      </button>
      {state.message ? <p className={styles.error}>{state.message}</p> : null}
      {state.conflict ? <a href={profileHref}>Reload</a> : null}
    </form>
  );
}
