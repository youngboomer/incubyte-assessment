"use client";

import { useActionState, useEffect, useState } from "react";
import { Button, Input, Notice } from "../../components/ui";
import { saveRateAction } from "./actions";
import { idleRateState } from "./rate-state";
import styles from "./planning-rates.module.css";

export function RateEditor({ code, current }: { code: string; current: string }) {
  const [state, formAction, pending] = useActionState(saveRateAction, idleRateState);
  const [editing, setEditing] = useState(false);
  const saved = state.status === "saved";

  useEffect(() => {
    if (saved) setEditing(false);
  }, [saved, state]);

  return (
    <div className={styles.editor}>
      {editing ? (
        <form action={formAction} className={styles.form}>
          <input type="hidden" name="code" value={code} />
          <Input
            label={`New ${code} rate`}
            name="rate"
            inputMode="decimal"
            autoComplete="off"
            required
            autoFocus
            defaultValue={state.status === "error" ? state.value : current}
            hint="Units per 1 US dollar"
            error={state.status === "error" ? state.message : undefined}
            fieldClassName={styles.rateField}
          />
          <div className={styles.formActions}>
            <Button type="submit" size="sm" loading={pending}>
              Save rate
            </Button>
            <Button size="sm" variant="quiet" onClick={() => setEditing(false)}>
              Cancel
            </Button>
          </div>
        </form>
      ) : (
        <Button size="sm" variant="quiet" onClick={() => setEditing(true)}>
          Edit
          <span className="sr-only"> {code} rate</span>
        </Button>
      )}
      {saved && !editing ? (
        <div className={styles.saved}>
          <Notice tone="success">{state.message}</Notice>
        </div>
      ) : null}
    </div>
  );
}
