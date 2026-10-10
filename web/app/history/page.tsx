import type { Metadata } from "next";
import Link from "next/link";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { connection } from "next/server";
import { Shell } from "../../components/shell";
import {
  DataTable,
  EmptyState,
  FilterBar,
  Input,
  LinkButton,
  Notice,
  PageHeader,
  Select,
  Td,
  Th,
} from "../../components/ui";
import { describeFailure } from "../../lib/errors";
import { getAuditFeed, reference } from "../../lib/endpoints";
import {
  formatDate,
  formatLocalMoney,
  formatPercent,
  formatUsd,
  pctChange,
} from "../../lib/format";
import { auditQuery, parseAuditFilters, type SearchParams } from "../../lib/query";
import { SESSION_COOKIE } from "../../lib/session";
import type { AuditFeedItem } from "../../lib/types";
import styles from "./history.module.css";

export const metadata: Metadata = { title: "Change history – CompPulse" };

function Change({ item }: { item: AuditFeedItem }) {
  const money = (scaled: string) => formatLocalMoney(scaled, item.salary_scale, item.currency_code);
  const baseChanged = item.previous_base_salary_scaled !== item.new_base_salary_scaled;
  const variableChanged = item.previous_variable_pay_scaled !== item.new_variable_pay_scaled;
  const basePct = pctChange(item.previous_base_salary_scaled, item.new_base_salary_scaled);
  const variablePct = pctChange(item.previous_variable_pay_scaled, item.new_variable_pay_scaled);
  return (
    <span className={styles.change}>
      {baseChanged ? (
        <span>
          Base pay {money(item.previous_base_salary_scaled)} → {money(item.new_base_salary_scaled)}
          {basePct === null ? null : (
            <span className={styles.delta}> ({formatPercent(basePct, 1, true)})</span>
          )}
        </span>
      ) : null}
      {variableChanged ? (
        <span>
          Variable pay {money(item.previous_variable_pay_scaled)} →{" "}
          {money(item.new_variable_pay_scaled)}
          {variablePct === null ? null : (
            <span className={styles.delta}> ({formatPercent(variablePct, 1, true)})</span>
          )}
        </span>
      ) : null}
      {!baseChanged && !variableChanged ? <span className={styles.delta}>No pay change</span> : null}
    </span>
  );
}

export default async function HistoryPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  await connection();
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!token) redirect("/login");

  const { cursor, ...filters } = parseAuditFilters(await searchParams);
  const [feed, ref] = await Promise.all([getAuditFeed(token, filters, cursor), reference(token)]);
  if (!feed.ok && feed.code === "unauthorized") redirect("/logout");

  const activeCount = Object.keys(filters).filter((key) => key !== "limit").length;
  const baseQuery = auditQuery(filters);
  const retryHref = `/history${baseQuery}`;

  return (
    <Shell>
      <PageHeader
        title="Change history"
        subtitle="Every pay change, newest first. Entries cannot be edited or deleted."
      />
      <div className={styles.page}>
        <div className={styles.tabs}>
          <Link href="/history" className={`${styles.tab} ${styles.active}`} aria-current="page">
            Pay
          </Link>
          <span className={`${styles.tab} ${styles.disabled}`} aria-disabled="true">
            Details
          </span>
          <p className={styles.tabNote}>
            Detail and status changes appear here once the backend adds a combined feed
          </p>
        </div>

        <FilterBar action="/history" activeCount={activeCount}>
          <Select
            label="Department"
            name="department_id"
            defaultValue={filters.department_id ?? ""}
          >
            <option value="">All departments</option>
            {ref.ok
              ? ref.data.departments.map((item) => (
                  <option key={item.id} value={String(item.id)}>
                    {item.name}
                  </option>
                ))
              : null}
          </Select>
          <Input label="From date" type="date" name="since" defaultValue={filters.since ?? ""} />
          <Input label="To date" type="date" name="until" defaultValue={filters.until ?? ""} />
          <Input
            label="Changed by"
            type="email"
            name="changed_by"
            placeholder="name@company.com"
            defaultValue={filters.changed_by ?? ""}
          />
        </FilterBar>
        {activeCount > 0 ? (
          <Link href="/history" className={styles.clear}>
            Clear filters
          </Link>
        ) : null}

        {!feed.ok ? (
          <Notice
            tone="error"
            title="We could not load the change history."
            action={
              <LinkButton href={retryHref} variant="quiet" size="sm">
                Retry
              </LinkButton>
            }
          >
            {describeFailure(feed).formError}
          </Notice>
        ) : feed.data.items.length === 0 ? (
          <EmptyState title="No changes match these filters." />
        ) : (
          <>
            <DataTable caption="Pay changes, newest first">
              <thead>
                <tr>
                  <Th>Effective</Th>
                  <Th>Employee</Th>
                  <Th>Change</Th>
                  <Th>Reason</Th>
                  <Th>Changed by</Th>
                  <Th numeric>US dollars at the time</Th>
                </tr>
              </thead>
              <tbody>
                {feed.data.items.map((item) => (
                  <tr key={item.id}>
                    <Td label="Effective" primary className={styles.nowrap}>
                      {formatDate(item.effective_date)}
                    </Td>
                    <Td label="Employee">
                      <span className={styles.employee}>
                        <Link href={`/employees/${encodeURIComponent(item.employee_id)}`}>
                          {item.employee_name}
                        </Link>
                        <span className={styles.sub}>
                          {item.employee_number} · {item.department.name}
                        </span>
                      </span>
                    </Td>
                    <Td label="Change" className={styles.words}>
                      <Change item={item} />
                    </Td>
                    <Td label="Reason" className={styles.words}>{item.reason}</Td>
                    <Td label="Changed by" className={styles.words}>{item.changed_by}</Td>
                    <Td label="US dollars" numeric className={styles.nowrap}>
                      {formatUsd(item.new_salary_usd_scaled, item.salary_usd_scale)}
                    </Td>
                  </tr>
                ))}
              </tbody>
            </DataTable>
            <nav aria-label="Pagination" className={styles.more}>
              <p className={styles.hint}>
                {cursor ? "Use your browser's back button to return to newer changes." : "Showing the newest changes."}
              </p>
              {feed.data.next_cursor ? (
                <LinkButton
                  href={`/history${auditQuery(filters, feed.data.next_cursor)}`}
                  variant="quiet"
                >
                  Load older
                </LinkButton>
              ) : (
                <p className={styles.hint}>No older changes.</p>
              )}
            </nav>
          </>
        )}
      </div>
    </Shell>
  );
}
