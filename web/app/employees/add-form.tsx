"use client";

import { useActionState, useState } from "react";
import type { Country, Currency, Department } from "../../lib/types";
import { addEmployeeAction, type AddEmployeeState } from "./actions";
import styles from "./employees.module.css";

type AddFormProps = {
  departments: Department[];
  countries: Country[];
  currencies: Currency[];
  levels: string[];
  statuses: string[];
};

const initialState: AddEmployeeState = { error: "" };

export function AddForm({
  departments,
  countries,
  currencies,
  levels,
  statuses,
}: AddFormProps) {
  const [state, formAction, pending] = useActionState(addEmployeeAction, initialState);
  const [countryCode, setCountryCode] = useState("");
  const currency = currencyFor(countries, currencies, countryCode);
  const defaultStatus = statuses.includes("active") ? "active" : "";

  return (
    <form action={formAction} className={styles.add}>
      <h2>Add employee</h2>
      <label>
        First name
        <input name="first_name" autoComplete="given-name" required />
      </label>
      <label>
        Last name
        <input name="last_name" autoComplete="family-name" required />
      </label>
      <label>
        Email
        <input name="email" type="email" autoComplete="email" required />
      </label>
      <label>
        Job title
        <input name="job_title" autoComplete="organization-title" required />
      </label>
      <label>
        Department
        <select name="department_id" defaultValue="" required>
          <option value="">Select department</option>
          {departments.map((department) => (
            <option key={department.id} value={department.id}>
              {department.name}
            </option>
          ))}
        </select>
      </label>
      <label>
        Country
        <select
          name="country_code"
          value={countryCode}
          required
          onChange={(event) => setCountryCode(event.target.value)}
        >
          <option value="">Select country</option>
          {countries.map((country) => (
            <option key={country.code} value={country.code}>
              {country.name}
            </option>
          ))}
        </select>
      </label>
      <label className={styles.srOnly}>
        Currency minor scale
        <input type="hidden" name="minor_scale" value={currency?.minor_scale ?? ""} />
      </label>
      <label>
        Level
        <select name="level" defaultValue="" required>
          <option value="">Select level</option>
          {levels.map((level) => (
            <option key={level} value={level}>
              {level}
            </option>
          ))}
        </select>
      </label>
      <label>
        Status
        <select name="status" defaultValue={defaultStatus} required>
          {defaultStatus === "" ? <option value="">Select status</option> : null}
          {statuses.map((status) => (
            <option key={status} value={status}>
              {status}
            </option>
          ))}
        </select>
      </label>
      <label>
        Base salary
        <span className={styles.hint}>
          {currency
            ? `Major units in ${currency.code}, for example 120000.50`
            : "Major units, for example 120000.50"}
        </span>
        <input name="base_salary" inputMode="decimal" autoComplete="off" required />
      </label>
      <label>
        Variable pay
        <span className={styles.hint}>
          {currency ? `Major units in ${currency.code}. May be 0.` : "Major units. May be 0."}
        </span>
        <input name="variable_pay" inputMode="decimal" autoComplete="off" defaultValue="0" />
      </label>
      <label>
        Hire date
        <input name="hire_date" type="date" required />
      </label>
      <label>
        Compensation effective date
        <input name="comp_effective_date" type="date" required />
      </label>
      <button type="submit" disabled={pending} aria-busy={pending}>
        Add employee
      </button>
      {state.error ? (
        <p className={styles.error} role="alert">
          {state.error}
        </p>
      ) : null}
    </form>
  );
}

function currencyFor(
  countries: Country[],
  currencies: Currency[],
  countryCode: string,
): Currency | undefined {
  const country = countries.find((item) => item.code === countryCode);
  if (!country) {
    return undefined;
  }
  return currencies.find((item) => item.code === country.currency_code);
}
