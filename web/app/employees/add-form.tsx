"use client";

import { useActionState, useMemo, useState } from "react";
import { Button, Card, Input, LinkButton, MoneyInput, Notice, Select } from "../../components/ui";
import type { Reference } from "../../lib/types";
import { addEmployeeAction, type AddEmployeeState } from "./actions";
import styles from "./add-employee.module.css";
import { previewTotal } from "./new/preview";

export type AddFormProps = {
  reference: Reference;
  today: string;
};

function symbolFor(code: string): string {
  try {
    const parts = new Intl.NumberFormat("en", {
      style: "currency",
      currency: code,
      currencyDisplay: "narrowSymbol",
    }).formatToParts(0);
    return parts.find((part) => part.type === "currency")?.value ?? code;
  } catch {
    return code;
  }
}

export function AddEmployeeForm({ reference, today }: AddFormProps) {
  const initial: AddEmployeeState = {
    values: { hire_date: today, comp_effective_date: today, status: "active" },
    fieldErrors: {},
    formError: null,
    attempt: 0,
  };
  const [state, formAction, pending] = useActionState(addEmployeeAction, initial);
  const values = state.values;
  const errors = state.fieldErrors;

  const [country, setCountry] = useState(values["country_code"] ?? "");
  const [base, setBase] = useState(values["base_salary"] ?? "");
  const [variable, setVariable] = useState(values["variable_pay"] ?? "");

  const currency = useMemo(() => {
    const code = reference.countries.find((item) => item.code === country)?.currency_code;
    return reference.currencies.find((item) => item.code === code) ?? null;
  }, [reference, country]);

  const preview = useMemo(
    () =>
      currency === null
        ? null
        : previewTotal(base, variable, {
            code: currency.code,
            minorScale: currency.minor_scale,
            unitsPerUsdScaled: currency.units_per_usd_scaled,
            unitsPerUsdScale: currency.units_per_usd_scale,
          }),
    [currency, base, variable],
  );

  const symbol = currency === null ? "" : symbolFor(currency.code);

  return (
    <form action={formAction} className={styles.form} noValidate>
      {state.formError ? <Notice tone="error">{state.formError}</Notice> : null}

      <Card>
        <fieldset className={styles.section}>
          <legend className={styles.legend}>Person</legend>
          <div className={styles.grid}>
            <Input name="first_name" label="First name" required autoComplete="off" defaultValue={values["first_name"]} error={errors["first_name"]} />
            <Input name="last_name" label="Last name" required autoComplete="off" defaultValue={values["last_name"]} error={errors["last_name"]} />
          </div>
          <Input name="email" label="Email" type="email" required autoComplete="off" defaultValue={values["email"]} error={errors["email"]} />
        </fieldset>
      </Card>

      <Card>
        <fieldset className={styles.section}>
          <legend className={styles.legend}>Role</legend>
          <Input name="job_title" label="Job title" required autoComplete="off" defaultValue={values["job_title"]} error={errors["job_title"]} />
          <div className={styles.grid}>
            <Select key={`dept-${state.attempt}`} name="department_id" label="Department" required defaultValue={values["department_id"] ?? ""} error={errors["department_id"]}>
              <option value="" disabled>
                Choose a department
              </option>
              {reference.departments.map((department) => (
                <option key={department.id} value={String(department.id)}>
                  {department.name}
                </option>
              ))}
            </Select>
            <Select key={`level-${state.attempt}`} name="level" label="Level" required defaultValue={values["level"] ?? ""} error={errors["level"]}>
              <option value="" disabled>
                Choose a level
              </option>
              {reference.levels.map((level) => (
                <option key={level} value={level}>
                  {level}
                </option>
              ))}
            </Select>
            <Select key={`status-${state.attempt}`} name="status" label="Status" required defaultValue={values["status"] ?? "active"} error={errors["status"]}>
              {reference.statuses.map((status) => (
                <option key={status} value={status}>
                  {status.charAt(0).toUpperCase() + status.slice(1)}
                </option>
              ))}
            </Select>
          </div>
        </fieldset>
      </Card>

      <Card>
        <fieldset className={styles.section}>
          <legend className={styles.legend}>Location</legend>
          <Select
            name="country_code"
            label="Country"
            required
            key={`country-${state.attempt}`}
            defaultValue={country}
            onChange={(event) => setCountry(event.target.value)}
            error={errors["country_code"]}
            hint={currency ? `Paid in ${currency.code}` : "Pay is entered in the country's currency."}
          >
            <option value="" disabled>
              Choose a country
            </option>
            {reference.countries.map((item) => (
              <option key={item.code} value={item.code}>
                {item.name}
              </option>
            ))}
          </Select>
        </fieldset>
      </Card>

      <Card>
        <fieldset className={styles.section}>
          <legend className={styles.legend}>Pay</legend>
          <div className={styles.grid}>
            <MoneyInput
              name="base_salary"
              label="Base salary"
              required
              currencySymbol={symbol || "–"}
              disabled={currency === null}
              placeholder="0.00"
              key={`base-${state.attempt}`}
              defaultValue={base}
              onChange={(event) => setBase(event.target.value)}
              error={errors["base_salary"]}
              hint={currency ? `Annual, in ${currency.code}` : "Choose a country first."}
            />
            <MoneyInput
              name="variable_pay"
              label="Variable pay"
              currencySymbol={symbol || "–"}
              disabled={currency === null}
              placeholder="0.00"
              key={`variable-${state.attempt}`}
              defaultValue={variable}
              onChange={(event) => setVariable(event.target.value)}
              error={errors["variable_pay"]}
              hint="Bonus or commission. Leave empty for none."
            />
          </div>
          {preview ? (
            <p className={styles.preview} aria-live="polite">
              Total {preview.local}, about {preview.usd}
            </p>
          ) : null}
        </fieldset>
      </Card>

      <Card>
        <fieldset className={styles.section}>
          <legend className={styles.legend}>Dates</legend>
          <div className={styles.grid}>
            <Input name="hire_date" label="Hire date" type="date" required defaultValue={values["hire_date"]} error={errors["hire_date"]} />
            <Input
              name="comp_effective_date"
              label="Effective date"
              type="date"
              required
              defaultValue={values["comp_effective_date"]}
              error={errors["comp_effective_date"]}
              hint="When this pay takes effect."
            />
          </div>
        </fieldset>
      </Card>

      <div className={styles.actions}>
        <Button type="submit" loading={pending}>
          Add employee
        </Button>
        <LinkButton href="/employees" variant="quiet">
          Cancel
        </LinkButton>
      </div>
    </form>
  );
}
