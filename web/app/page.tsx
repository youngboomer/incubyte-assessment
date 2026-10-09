import { cookies } from "next/headers";
import { connection } from "next/server";
import { redirect } from "next/navigation";
import { Shell } from "../components/shell";
import { backendFetch } from "../lib/api";
import { formatScaled } from "../lib/format";
import { SESSION_COOKIE } from "../lib/session";
import type {
  AnalyticsOverview,
  CountryBreakdown,
  DepartmentBreakdown,
  SalaryHistogramBucket,
} from "../lib/types";
import styles from "./dashboard.module.css";

export default async function Page() {
  await connection();
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!token) redirect("/login");
  const meResponse = await backendFetch("/auth/me", token);
  if (meResponse.status === 401) redirect("/logout");

  const overviewResponse = await backendFetch("/analytics/overview", token);
  if (!overviewResponse.ok) {
    return (
      <Shell>
        <p className={styles.error}>
          Could not load the dashboard. {overviewResponse.status}
        </p>
      </Shell>
    );
  }

  const body = (await overviewResponse.json()) as AnalyticsOverview;
  const scale = body.salary_usd_scale;
  const money = (scaled: string) => formatScaled(scaled, scale, "USD");

  return (
    <Shell>
      <h1>Dashboard</h1>
      {body.headcount === 0 ? (
        <p className={styles.empty}>No active employees.</p>
      ) : null}
      <section className={styles.strip} aria-label="Pay totals">
        <article>
          <h2>Headcount</h2>
          <p>{body.headcount}</p>
        </article>
        <article>
          <h2>Total</h2>
          <p>{money(body.total_salary_usd_scaled)}</p>
        </article>
        <article>
          <h2>Average</h2>
          <p>{money(body.average_salary_usd_scaled)}</p>
        </article>
      </section>
      <section className={styles.strip} aria-label="Quartiles">
        <article>
          <h2>P25</h2>
          <p>{money(body.p25_salary_usd_scaled)}</p>
        </article>
        <article>
          <h2>P50</h2>
          <p>{money(body.p50_salary_usd_scaled)}</p>
        </article>
        <article>
          <h2>P75</h2>
          <p>{money(body.p75_salary_usd_scaled)}</p>
        </article>
      </section>
      <DepartmentBars rows={body.by_department} money={money} />
      <CountryBars rows={body.by_country} money={money} />
      <Histogram buckets={body.histogram} />
    </Shell>
  );
}

function barWidth(count: number, max: number): string {
  if (max === 0) {
    return "0%";
  }
  return `${(count / max) * 100}%`;
}

function DepartmentBars({
  rows,
  money,
}: {
  rows: DepartmentBreakdown[];
  money: (scaled: string) => string;
}) {
  const max = rows.reduce((highest, row) => Math.max(highest, row.headcount), 0);
  return (
    <section className={styles.chart}>
      <h2>Departments</h2>
      <ul className={styles.bars}>
        {rows.map((row) => (
          <li key={row.department_id}>
            <div className={styles.meta}>
              <span className={styles.name}>{row.department_name}</span>
              <span>{row.headcount}</span>
              <span>{money(row.total_salary_usd_scaled)}</span>
            </div>
            <div className={styles.track}>
              <div className={styles.fill} style={{ width: barWidth(row.headcount, max) }} />
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}

function CountryBars({
  rows,
  money,
}: {
  rows: CountryBreakdown[];
  money: (scaled: string) => string;
}) {
  const max = rows.reduce((highest, row) => Math.max(highest, row.headcount), 0);
  return (
    <section className={styles.chart}>
      <h2>Countries</h2>
      <ul className={styles.bars}>
        {rows.map((row) => (
          <li key={row.country_code}>
            <div className={styles.meta}>
              <span className={styles.name}>{row.country_name}</span>
              <span>{row.headcount}</span>
              <span>{money(row.total_salary_usd_scaled)}</span>
            </div>
            <div className={styles.track}>
              <div className={styles.fill} style={{ width: barWidth(row.headcount, max) }} />
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}

function Histogram({ buckets }: { buckets: SalaryHistogramBucket[] }) {
  const max = buckets.reduce((highest, bucket) => Math.max(highest, bucket.count), 0);
  return (
    <section className={styles.chart}>
      <h2>Histogram</h2>
      <ul className={styles.bars}>
        {buckets.map((bucket, index) => (
          <li key={`${index}-${bucket.label}`}>
            <div className={styles.meta}>
              <span className={styles.name}>{bucket.label}</span>
              <span>{bucket.count}</span>
            </div>
            <div className={styles.track}>
              <div className={styles.fill} style={{ width: barWidth(bucket.count, max) }} />
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
