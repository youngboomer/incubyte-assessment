import type { Metadata } from "next";
import Link from "next/link";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { connection } from "next/server";
import { Shell } from "../components/shell";
import {
  BarList,
  Card,
  CardHeader,
  DataTable,
  EmptyState,
  FilterBar,
  Histogram,
  LinkButton,
  Notice,
  PageHeader,
  RangeBar,
  Select,
  Td,
  Th,
} from "../components/ui";
import { describeFailure } from "../lib/errors";
import { getOverview, reference } from "../lib/endpoints";
import { formatCompactUsd } from "../lib/format";
import { LEVELS, parseScopeFilters, type SearchParams } from "../lib/query";
import { SESSION_COOKIE } from "../lib/session";
import type { AnalyticsOverview, Reference, ScopeFilters } from "../lib/types";
import styles from "./dashboard.module.css";
import { formatWholeUsd, spreadOf } from "./overview-data";

export const metadata: Metadata = { title: "Pay overview – CompPulse" };

const count = new Intl.NumberFormat("en-US");

function withoutKey(filters: ScopeFilters, key: keyof ScopeFilters): string {
  const search = new URLSearchParams();
  for (const [name, value] of Object.entries(filters)) {
    if (name !== key && value) search.set(name, value);
  }
  const text = search.toString();
  return text === "" ? "/" : `/?${text}`;
}

function chipsFor(filters: ScopeFilters, ref: Reference | null) {
  const chips: { label: string; removeHref: string }[] = [];
  if (filters.department_id) {
    const name = ref?.departments.find((item) => String(item.id) === filters.department_id)?.name;
    chips.push({
      label: `Department: ${name ?? filters.department_id}`,
      removeHref: withoutKey(filters, "department_id"),
    });
  }
  if (filters.country) {
    const name = ref?.countries.find((item) => item.code === filters.country)?.name;
    chips.push({
      label: `Country: ${name ?? filters.country}`,
      removeHref: withoutKey(filters, "country"),
    });
  }
  if (filters.level) {
    chips.push({ label: `Level: ${filters.level}`, removeHref: withoutKey(filters, "level") });
  }
  return chips;
}

export default async function PayOverviewPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  await connection();
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!token) redirect("/login");

  const filters = parseScopeFilters(await searchParams);
  const [overviewResult, referenceResult] = await Promise.all([
    getOverview(token, filters),
    reference(token),
  ]);
  if (!overviewResult.ok && overviewResult.code === "unauthorized") redirect("/logout");

  const ref = referenceResult.ok ? referenceResult.data : null;
  const chips = chipsFor(filters, ref);
  const retryHref = withoutKey(filters, "currency");

  return (
    <Shell>
      <PageHeader title="Pay overview" subtitle="How do we pay people across the company?" />
      <div className={styles.page}>
        <div className={styles.filters}>
          <FilterBar action="/" activeCount={chips.length}>
            <Select
              label="Department"
              name="department_id"
              defaultValue={filters.department_id ?? ""}
            >
              <option value="">All departments</option>
              {ref?.departments.map((item) => (
                <option key={item.id} value={String(item.id)}>
                  {item.name}
                </option>
              ))}
            </Select>
            <Select label="Country" name="country" defaultValue={filters.country ?? ""}>
              <option value="">All countries</option>
              {ref?.countries.map((item) => (
                <option key={item.code} value={item.code}>
                  {item.name}
                </option>
              ))}
            </Select>
            <Select label="Level" name="level" defaultValue={filters.level ?? ""}>
              <option value="">All levels</option>
              {LEVELS.map((level) => (
                <option key={level} value={level}>
                  {level}
                </option>
              ))}
            </Select>
          </FilterBar>
          {chips.length > 0 ? (
            <Link href="/" className={styles.reset}>
              Reset
            </Link>
          ) : null}
          <p className={styles.note}>
            Active employees only · all amounts in US dollars at planning rates
          </p>
        </div>

        {!overviewResult.ok ? (
          <Notice
            tone="error"
            title="We could not load the pay overview."
            action={
              <LinkButton href={retryHref} variant="quiet" size="sm">
                Retry
              </LinkButton>
            }
          >
            {describeFailure(overviewResult).formError}
          </Notice>
        ) : overviewResult.data.headcount === 0 ? (
          <Card>
            <EmptyState title="No active employees match this scope." />
          </Card>
        ) : (
          <Overview data={overviewResult.data} />
        )}
      </div>
    </Shell>
  );
}

function Overview({ data }: { data: AnalyticsOverview }) {
  const scale = data.salary_usd_scale;
  const usd = (scaled: string) => formatWholeUsd(scaled, scale);
  const spread = spreadOf(data);
  const wholeFormat = (value: number) =>
    formatWholeUsd(String(Math.round(value * 10 ** scale)), scale);
  const departments = [...data.by_department].sort((a, b) => b.headcount - a.headcount);
  const countries = [...data.by_country].sort((a, b) => b.headcount - a.headcount);

  return (
    <>
      <dl className={styles.figures}>
        <div className={styles.figure}>
          <dt>People</dt>
          <dd>{count.format(data.headcount)}</dd>
        </div>
        <div className={styles.figure}>
          <dt>Total payroll</dt>
          <dd>{formatCompactUsd(data.total_salary_usd_scaled, scale)}</dd>
        </div>
        <div className={styles.figure}>
          <dt>Average pay</dt>
          <dd>{usd(data.average_salary_usd_scaled)}</dd>
        </div>
        <div className={`${styles.figure} ${styles.accent}`}>
          <dt>Middle pay (median)</dt>
          <dd>{usd(data.p50_salary_usd_scaled)}</dd>
        </div>
      </dl>

      <Card aria-label="Compensation spread">
        <CardHeader
          title="Compensation spread"
          description={`Half of people earn between ${usd(data.p25_salary_usd_scaled)} and ${usd(data.p75_salary_usd_scaled)}`}
        />
        <RangeBar {...spread} format={wholeFormat} ariaLabel="Compensation spread" />
      </Card>

      <div className={styles.pair}>
        <Card aria-label="Pay distribution">
          <CardHeader title="Pay distribution" description="People per pay range" />
          <Histogram data={data.histogram} ariaLabel="People per pay range" />
        </Card>
        <Card aria-label="Pay by level">
          <CardHeader title="Pay by level" description="Base pay in US dollars, by job level" />
          <DataTable caption="Pay by level">
            <thead>
              <tr>
                <Th>Level</Th>
                <Th numeric>People</Th>
                <Th numeric>Lowest</Th>
                <Th numeric>Median</Th>
                <Th numeric>Highest</Th>
                <Th numeric>Average</Th>
              </tr>
            </thead>
            <tbody>
              {data.by_level.map((row) => (
                <tr key={row.level}>
                  <Td label="Level" primary>
                    {row.level}
                  </Td>
                  <Td label="People" numeric className={styles.num}>
                    {count.format(row.headcount)}
                  </Td>
                  <Td label="Lowest" numeric className={styles.num}>
                    {usd(row.min_salary_usd_scaled)}
                  </Td>
                  <Td label="Median" numeric className={styles.num}>
                    {usd(row.p50_salary_usd_scaled)}
                  </Td>
                  <Td label="Highest" numeric className={styles.num}>
                    {usd(row.max_salary_usd_scaled)}
                  </Td>
                  <Td label="Average" numeric className={styles.num}>
                    {usd(row.average_salary_usd_scaled)}
                  </Td>
                </tr>
              ))}
            </tbody>
          </DataTable>
        </Card>
      </div>

      <div className={styles.pair}>
        <Card aria-label="By department">
          <CardHeader title="By department" description="People, with average pay" />
          <BarList
            ariaLabel="People by department"
            items={departments.map((row) => ({
              label: row.department_name,
              value: row.headcount,
              display: `${count.format(row.headcount)} · avg ${usd(row.average_salary_usd_scaled)}`,
            }))}
          />
        </Card>
        <Card aria-label="By country">
          <CardHeader title="By country" description="People, with average pay" />
          <BarList
            ariaLabel="People by country"
            items={countries.map((row) => ({
              label: row.country_name,
              value: row.headcount,
              display: `${count.format(row.headcount)} · avg ${usd(row.average_salary_usd_scaled)}`,
            }))}
          />
        </Card>
      </div>
    </>
  );
}
