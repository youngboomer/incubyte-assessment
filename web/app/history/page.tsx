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
import { describeChange } from "../../lib/change-words";
import { getAuditFeed, getChangesFeed, reference } from "../../lib/endpoints";
import {
  formatDate,
  formatLocalMoney,
  formatPercent,
  formatUsd,
  pctChange,
} from "../../lib/format";
import {
  historyHref,
  parseAuditFilters,
  parseChangesFilters,
  parseHistoryTab,
  type SearchParams,
} from "../../lib/query";
import { SESSION_COOKIE } from "../../lib/session";
import type { AuditFeedItem, ChangeFeedItem } from "../../lib/types";
import styles from "./history.module.css";

const FIELD_OPTIONS = [
  ["first_name", "First name"],
  ["last_name", "Last name"],
  ["email", "Email"],
  ["job_title", "Job title"],
  ["department_id", "Department"],
  ["level", "Level"],
  ["status", "Status"],
] as const;

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

function PayTable({ items }: { items: AuditFeedItem[] }) {
  return (
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
        {items.map((item) => (
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
  );
}

function DetailsTable({ items }: { items: ChangeFeedItem[] }) {
  return (
    <DataTable caption="Detail changes, newest first">
      <thead>
        <tr>
          <Th>Date</Th>
          <Th>Person</Th>
          <Th>Change</Th>
          <Th>Reason</Th>
          <Th>Changed by</Th>
        </tr>
      </thead>
      <tbody>
        {items.map((item) => (
          <tr key={item.id}>
            <Td label="Date" primary className={styles.nowrap}>
              {formatDate(item.effective_date)}
            </Td>
            <Td label="Person">
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
              {describeChange(item)}
            </Td>
            <Td label="Reason" className={styles.words}>{item.reason}</Td>
            <Td label="Changed by" className={styles.words}>{item.changed_by}</Td>
          </tr>
        ))}
      </tbody>
    </DataTable>
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

  const params = await searchParams;
  const tab = parseHistoryTab(params);
  const { cursor, ...filters } =
    tab === "details" ? parseChangesFilters(params) : parseAuditFilters(params);
  const pay = tab === "pay" ? await getAuditFeed(token, filters, cursor) : null;
  const details = tab === "details" ? await getChangesFeed(token, filters, cursor) : null;
  const ref = await reference(token);
  const feed = pay ?? details;
  if (feed && !feed.ok && feed.code === "unauthorized") redirect("/logout");

  const activeCount = Object.keys(filters).filter((key) => key !== "limit").length;
  const { field, ...sharedFilters } = filters as typeof filters & { field?: string };
  const retryHref = historyHref(tab, filters);
  const clearHref = historyHref(tab, {});

  return (
    <Shell>
      <PageHeader
        title="Change history"
        subtitle="Every change to pay and employee details, newest first. Entries cannot be edited or deleted."
      />
      <div className={styles.page}>
        <nav aria-label="History type" className={styles.tabs}>
          <Link
            href={historyHref("pay", sharedFilters)}
            className={`${styles.tab} ${tab === "pay" ? styles.active : ""}`}
            aria-current={tab === "pay" ? "page" : undefined}
          >
            Pay
          </Link>
          <Link
            href={historyHref("details", sharedFilters)}
            className={`${styles.tab} ${tab === "details" ? styles.active : ""}`}
            aria-current={tab === "details" ? "page" : undefined}
          >
            Details
          </Link>
        </nav>

        <FilterBar
          action="/history"
          activeCount={activeCount}
          hidden={tab === "details" ? { tab } : undefined}
        >
          {tab === "details" ? (
            <Select
              label="What changed"
              name="field"
              defaultValue={field ?? ""}
            >
              <option value="">All</option>
              {FIELD_OPTIONS.map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </Select>
          ) : null}
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
          <Link href={clearHref} className={styles.clear}>
            Clear filters
          </Link>
        ) : null}

        {!feed || !feed.ok ? (
          <Notice
            tone="error"
            title="We could not load the change history."
            action={
              <LinkButton href={retryHref} variant="quiet" size="sm">
                Retry
              </LinkButton>
            }
          >
            {feed ? describeFailure(feed).formError : null}
          </Notice>
        ) : feed.data.items.length === 0 ? (
          <EmptyState title="No changes match these filters." />
        ) : (
          <>
            {pay?.ok ? <PayTable items={pay.data.items} /> : null}
            {details?.ok ? <DetailsTable items={details.data.items} /> : null}
            <nav aria-label="Pagination" className={styles.more}>
              <p className={styles.hint}>
                {cursor ? "Use your browser's back button to return to newer changes." : "Showing the newest changes."}
              </p>
              {feed.data.next_cursor ? (
                <LinkButton
                  href={historyHref(tab, filters, feed.data.next_cursor)}
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
