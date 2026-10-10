import type { Metadata } from "next";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { connection } from "next/server";
import { Shell } from "../../components/shell";
import { DataTable, LinkButton, Notice, PageHeader, Td, Th } from "../../components/ui";
import { describeFailure } from "../../lib/errors";
import { listEmployees, listRates, reference } from "../../lib/endpoints";
import { formatScaled } from "../../lib/format";
import { SESSION_COOKIE } from "../../lib/session";
import { RateEditor } from "./rate-editor";
import styles from "./planning-rates.module.css";

export const metadata: Metadata = { title: "Planning rates – CompPulse" };

const count = new Intl.NumberFormat("en-US");

async function peopleByCurrency(token: string, codes: string[]): Promise<Map<string, number>> {
  const results = await Promise.all(
    codes.map(
      async (code) =>
        [code, await listEmployees(token, { currency: code, status: "active", limit: 1 })] as const,
    ),
  );
  const counts = new Map<string, number>();
  for (const [code, result] of results) {
    if (result.ok) counts.set(code, result.data.total);
  }
  return counts;
}

export default async function PlanningRatesPage() {
  await connection();
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!token) redirect("/login");

  const [rates, ref] = await Promise.all([listRates(token), reference(token)]);
  if (!rates.ok && rates.code === "unauthorized") redirect("/logout");

  const header = (
    <PageHeader
      title="Planning rates"
      subtitle="One exchange rate per currency. All US dollar figures in pay overview and the directory use these rates. Changing a rate updates everyone paid in that currency. Past change history keeps the rate used at the time."
    />
  );

  if (!rates.ok) {
    return (
      <Shell>
        {header}
        <Notice
          tone="error"
          title="We could not load the planning rates."
          action={
            <LinkButton href="/planning-rates" variant="quiet" size="sm">
              Retry
            </LinkButton>
          }
        >
          {describeFailure(rates).formError}
        </Notice>
      </Shell>
    );
  }

  const countries = ref.ok ? ref.data.countries : [];
  const people = await peopleByCurrency(
    token,
    rates.data.map((currency) => currency.code),
  );

  return (
    <Shell>
      {header}
      <DataTable caption="Planning rates by currency">
        <thead>
          <tr>
            <Th>Currency</Th>
            <Th>Used in</Th>
            <Th numeric>People</Th>
            <Th numeric>Rate (units per 1 US dollar)</Th>
            <Th numeric>
              <span className="sr-only">Edit</span>
            </Th>
          </tr>
        </thead>
        <tbody>
          {rates.data.map((currency) => {
            const usedIn = countries
              .filter((country) => country.currency_code === currency.code)
              .map((country) => country.name)
              .join(", ");
            const total = people.get(currency.code);
            const isUsd = currency.code === "USD";
            return (
              <tr key={currency.code}>
                <Td label="Currency" primary>
                  <span className={styles.code}>{currency.code}</span>
                  <span className={styles.name}>{currency.name}</span>
                </Td>
                <Td label="Used in">{usedIn || "No countries"}</Td>
                <Td label="People" numeric>
                  {total === undefined ? "–" : count.format(total)}
                </Td>
                <Td label="Rate" numeric className={styles.rate}>
                  {formatScaled(currency.units_per_usd_scaled, currency.units_per_usd_scale)}
                </Td>
                <Td label="Edit" numeric>
                  {isUsd ? (
                    <span className={styles.fixed}>Fixed at 1</span>
                  ) : (
                    <RateEditor
                      code={currency.code}
                      current={formatScaled(
                        currency.units_per_usd_scaled,
                        currency.units_per_usd_scale,
                      ).replaceAll(",", "")}
                    />
                  )}
                </Td>
              </tr>
            );
          })}
        </tbody>
      </DataTable>
    </Shell>
  );
}
