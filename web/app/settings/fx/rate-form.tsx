"use client";

import { useActionState } from "react";
import { updateRateAction, type RateFormState } from "./actions";
import styles from "./fx.module.css";

const initialState: RateFormState = { message: "" };

export function RateForm({ code }: { code: string }) {
  const [state, formAction, pending] = useActionState(
    updateRateAction.bind(null, code),
    initialState,
  );

  return (
    <form className={styles.form} action={formAction}>
      <label>
        New rate
        <input name="rate" type="text" inputMode="decimal" required />
      </label>
      <button type="submit" disabled={pending}>
        Save planning rate
      </button>
      {state.message ? <p className={styles.error}>{state.message}</p> : null}
    </form>
  );
}
