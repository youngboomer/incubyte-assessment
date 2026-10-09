import { cookies } from "next/headers";
import { connection } from "next/server";
import { redirect } from "next/navigation";
import { Shell } from "../../../components/shell";
import { backendFetch } from "../../../lib/api";
import { formatScaled } from "../../../lib/format";
import { SESSION_COOKIE } from "../../../lib/session";
import type { Currency } from "../../../lib/types";
import { RateForm } from "./rate-form";
import styles from "./fx.module.css";

export default async function PlanningRatesPage() {
  await connection();
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!token) redirect("/login");

  let response: Response;
  try {
    response = await backendFetch("/fx", token);
  } catch {
    return <LoadError />;
  }

  if (response.status === 401) {
    redirect("/logout");
  }
  if (!response.ok) {
    return <LoadError />;
  }

  const body: unknown = await readJson(response);
  if (!isCurrencyList(body)) {
    return <LoadError />;
  }

  return (
    <Shell>
      <div className={styles.page}>
        <h1>Planning rates</h1>
        <p className={styles.notice}>
          Saving recomputes USD pay for every employee on this currency. Audit history keeps the rate from the original change.
        </p>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Code</th>
              <th>Name</th>
              <th>Planning rate</th>
              <th>Update</th>
            </tr>
          </thead>
          <tbody>
            {body.map((currency) => (
              <tr key={currency.code}>
                <td>{currency.code}</td>
                <td>{currency.name}</td>
                <td>
                  {formatScaled(currency.units_per_usd_scaled, currency.units_per_usd_scale)}{" "}
                  planning rate (local major units per 1 USD)
                </td>
                <td>
                  <RateForm code={currency.code} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Shell>
  );
}

function LoadError() {
  return (
    <Shell>
      <p className={styles.error}>Could not load planning rates.</p>
    </Shell>
  );
}

async function readJson(response: Response): Promise<unknown> {
  try {
    return await response.json();
  } catch {
    return null;
  }
}

function isCurrencyList(value: unknown): value is Currency[] {
  return Array.isArray(value) && value.every(isCurrency);
}

function isCurrency(value: unknown): value is Currency {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const row = value as Record<string, unknown>;
  return (
    typeof row["code"] === "string" &&
    typeof row["name"] === "string" &&
    typeof row["minor_scale"] === "number" &&
    typeof row["units_per_usd_scaled"] === "string" &&
    typeof row["units_per_usd_scale"] === "number"
  );
}
