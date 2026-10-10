"use client";

import { useActionState, useMemo, useState } from "react";
import { Button, Input, LinkButton, MoneyInput, Notice, Textarea } from "../../../../components/ui";
import { formatLocalMoney, formatPercent, formatUsd } from "../../../../lib/format";
import { previewPay } from "../_lib/pay-math";
import { StaleNotice } from "../_lib/stale-notice";
import shared from "../_lib/shared.module.css";
import { changePayAction, type PayFormState } from "./actions";
import styles from "./pay.module.css";

export type PayFormProps = {
  employeeId: string;
  versionId: number;
  currencyCode: string;
  symbol: string;
  scale: number;
  initialBase: string;
  initialVariable: string;
  currentTotalScaled: string;
  currentTotalLabel: string;
  rateScaled: string;
  rateScale: number;
  usdScale: number;
  today: string;
};

const INITIAL: PayFormState = { values: null, fieldErrors: {}, formError: null, stale: null, isStale: false };

export function PayForm(props: PayFormProps) {
  const [state, formAction, pending] = useActionState(
    changePayAction.bind(null, props.employeeId, props.scale),
    INITIAL,
  );
  const [base, setBase] = useState(props.initialBase);
  const [variable, setVariable] = useState(props.initialVariable);
  const [date, setDate] = useState(props.today);
  const [reason, setReason] = useState("");

  const preview = useMemo(
    () =>
      previewPay({
        baseMajor: base,
        variableMajor: variable === "" ? "0" : variable,
        scale: props.scale,
        currentTotalScaled: props.currentTotalScaled,
        rateScaled: props.rateScaled,
        rateScale: props.rateScale,
        usdScale: props.usdScale,
      }),
    [base, variable, props],
  );

  const errors = state.fieldErrors;
  let previewText: string | null = null;
  if (preview) {
    const total = formatLocalMoney(preview.totalScaled, props.scale, props.currencyCode);
    const usd = formatUsd(preview.usdScaled, props.usdScale);
    const percent = preview.percent;
    const direction =
      percent === null || percent === 0
        ? "no change"
        : `${percent > 0 ? "up" : "down"} ${formatPercent(Math.abs(percent))}`;
    previewText = `New total ${total}, about ${usd}, ${direction}`;
  }

  return (
    <form action={formAction} className={shared.form} noValidate>
      <input type="hidden" name="version_id" value={props.versionId} />
      <input type="hidden" name="loaded_total" value={props.currentTotalLabel} />
      {state.isStale ? (
        <StaleNotice info={state.stale} reloadLabel="Reload latest pay" />
      ) : state.formError ? (
        <Notice tone="error">{state.formError}</Notice>
      ) : null}

      <div className={shared.row}>
        <MoneyInput
          name="base"
          label={`New base pay (${props.currencyCode}), annual`}
          currencySymbol={props.symbol}
          value={base}
          onChange={(event) => setBase(event.target.value)}
          error={errors["base"]}
          required
        />
        <MoneyInput
          name="variable"
          label={`New variable pay (${props.currencyCode}), annual`}
          currencySymbol={props.symbol}
          value={variable}
          onChange={(event) => setVariable(event.target.value)}
          error={errors["variable"]}
        />
      </div>

      <p className={previewText ? styles.preview : styles.previewMuted} aria-live="polite">
        {previewText ?? "Enter valid amounts to preview the new total."}
      </p>

      <Input
        name="effective_date"
        type="date"
        label="Effective date"
        hint="Changes take effect from this day onward."
        value={date}
        onChange={(event) => setDate(event.target.value)}
        error={errors["effective_date"]}
        fieldClassName={styles.dateField}
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
        <Button type="submit" loading={pending}>
          Save pay change
        </Button>
        <LinkButton href={`/employees/${encodeURIComponent(props.employeeId)}`} variant="quiet">
          Cancel
        </LinkButton>
      </div>
    </form>
  );
}
