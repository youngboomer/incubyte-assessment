import Link from "next/link";
import { Card, EmptyState, Timeline } from "../../../components/ui";
import type { TimelineItem } from "../../../components/ui";
import {
  formatDate,
  formatLocalMoney,
  formatPercent,
  formatUsd,
  pctChange,
} from "../../../lib/format";
import type { AuditEntry, EmployeeChange } from "../../../lib/types";
import { formatRate } from "./_lib/pay-math";
import styles from "./profile.module.css";

export type HistoryTab = "pay" | "details";

const FIELD_LABELS: Record<string, string> = {
  first_name: "First name",
  last_name: "Last name",
  email: "Email",
  job_title: "Job title",
  department_id: "Department",
  department: "Department",
  level: "Level",
  status: "Status",
};

function payLine(
  label: string,
  previous: string,
  next: string,
  scale: number,
  currency: string,
): string | null {
  if (previous === next) {
    return null;
  }
  const change = pctChange(previous, next);
  const percent = change === null ? "" : ` (${formatPercent(change, 1, true)})`;
  return `${label} ${formatLocalMoney(previous, scale, currency)} → ${formatLocalMoney(next, scale, currency)}${percent}`;
}

export function payItems(entries: AuditEntry[]): TimelineItem[] {
  return entries.map((entry) => {
    const lines = [
      payLine(
        "Base pay",
        entry.previous_base_salary_scaled,
        entry.new_base_salary_scaled,
        entry.salary_scale,
        entry.currency_code,
      ),
      payLine(
        "Variable pay",
        entry.previous_variable_pay_scaled,
        entry.new_variable_pay_scaled,
        entry.salary_scale,
        entry.currency_code,
      ),
    ].filter((line): line is string => line !== null);
    return {
      id: String(entry.id),
      date: formatDate(entry.effective_date),
      title: (
        <>
          {lines.length > 0 ? (
            lines.map((line) => (
              <span key={line} className={styles.line}>
                {line}
              </span>
            ))
          ) : (
            <span className={styles.line}>Pay reviewed, no amounts changed</span>
          )}
        </>
      ),
      details: (
        <dl className={styles.meta}>
          <div>
            <dt>Reason</dt>
            <dd>{entry.reason}</dd>
          </div>
          <div>
            <dt>Changed by</dt>
            <dd>{entry.changed_by}</dd>
          </div>
          <div>
            <dt>USD value at the time</dt>
            <dd>
              {formatUsd(entry.new_salary_usd_scaled, entry.salary_usd_scale)} (rate{" "}
              {formatRate(entry.fx_units_per_usd_scaled, entry.fx_scale, entry.currency_code)})
            </dd>
          </div>
        </dl>
      ),
    };
  });
}

function changeTitle(change: EmployeeChange, departmentNames: Map<string, string>): string {
  if (change.field === "status") {
    return change.new_value === "terminated" ? "Terminated" : "Reactivated";
  }
  const label = FIELD_LABELS[change.field] ?? change.field;
  const show = (value: string) =>
    change.field.startsWith("department") ? (departmentNames.get(value) ?? value) : value;
  return `${label}: ${show(change.previous_value)} → ${show(change.new_value)}`;
}

export function changeItems(
  changes: EmployeeChange[],
  departmentNames: Map<string, string>,
): TimelineItem[] {
  return changes.map((change) => ({
    id: String(change.id),
    date: formatDate(change.effective_date),
    title: changeTitle(change, departmentNames),
    details: (
      <dl className={styles.meta}>
        <div>
          <dt>Reason</dt>
          <dd>{change.reason}</dd>
        </div>
        <div>
          <dt>Changed by</dt>
          <dd>{change.changed_by}</dd>
        </div>
      </dl>
    ),
  }));
}

export function ChangeHistory({
  basePath,
  tab,
  payEntries,
  changes,
  departmentNames,
}: {
  basePath: string;
  tab: HistoryTab;
  payEntries: AuditEntry[] | null;
  changes: EmployeeChange[] | null;
  departmentNames: Map<string, string>;
}) {
  const tabs: { key: HistoryTab; label: string; count: number | null }[] = [
    { key: "pay", label: "Pay", count: payEntries?.length ?? null },
    { key: "details", label: "Details", count: changes?.length ?? null },
  ];
  const entries = tab === "pay" ? payEntries : changes;
  return (
    <Card aria-label="Change history">
      <div className={styles.historyHead}>
        <h2 className={styles.historyTitle}>Change history</h2>
        <nav aria-label="History type" className={styles.tabs}>
          {tabs.map((item) => (
            <Link
              key={item.key}
              href={`${basePath}?tab=${item.key}`}
              scroll={false}
              aria-current={item.key === tab ? "page" : undefined}
              className={styles.tab}
            >
              {item.label}
              {item.count !== null ? <span className={styles.badge}>{item.count}</span> : null}
            </Link>
          ))}
        </nav>
      </div>
      {entries === null ? (
        <EmptyState title="Could not load this history.">Reload the page to try again.</EmptyState>
      ) : entries.length === 0 ? (
        <EmptyState title={tab === "pay" ? "No pay changes yet." : "No detail changes yet."}>
          Changes appear here once they are saved.
        </EmptyState>
      ) : tab === "pay" ? (
        <Timeline ariaLabel="Pay changes" items={payItems(payEntries ?? [])} />
      ) : (
        <Timeline ariaLabel="Detail changes" items={changeItems(changes ?? [], departmentNames)} />
      )}
      <p className={styles.footnote}>History cannot be edited or deleted.</p>
    </Card>
  );
}
