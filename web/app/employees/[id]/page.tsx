import { connection } from "next/server";
import { Shell } from "../../../components/shell";
import {
  Breadcrumb,
  Card,
  CardHeader,
  LinkButton,
  Notice,
  PageHeader,
  StatusTag,
} from "../../../components/ui";
import {
  getEmployee,
  listEmployeeAudit,
  listEmployeeChanges,
  reference,
} from "../../../lib/endpoints";
import { formatDate, formatLocalMoney, formatUsd, fullName } from "../../../lib/format";
import { EmployeeLoadError, EmployeeNotFound } from "./_lib/not-found";
import { formatRate, sumScaled } from "./_lib/pay-math";
import { guard, requireToken } from "./_lib/server";
import { ChangeHistory, type HistoryTab } from "./history";
import styles from "./profile.module.css";

const SAVED_MESSAGES: Record<string, string> = {
  pay: "Pay updated. The change is in the history below.",
  details: "Details updated. The change is in the history below.",
  status: "Employment status updated. The change is in the history below.",
};

type PageProps = {
  params: Promise<{ id: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

function first(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

export default async function EmployeePage({ params, searchParams }: PageProps) {
  await connection();
  const [{ id }, query] = await Promise.all([params, searchParams]);
  const token = await requireToken();
  const tab: HistoryTab = first(query["tab"]) === "details" ? "details" : "pay";
  const saved = SAVED_MESSAGES[first(query["saved"]) ?? ""];

  const [employeeResult, auditResult, changesResult, referenceResult] = await Promise.all([
    getEmployee(token, id).then(guard),
    listEmployeeAudit(token, id).then(guard),
    listEmployeeChanges(token, id).then(guard),
    reference(token).then(guard),
  ]);

  if (!employeeResult.ok) {
    return employeeResult.code === "not_found" || employeeResult.status === 422 ? (
      <EmployeeNotFound />
    ) : (
      <EmployeeLoadError message={employeeResult.message} />
    );
  }
  const employee = employeeResult.data;
  const name = fullName(employee);
  const base = `/employees/${encodeURIComponent(employee.id)}`;
  const terminated = employee.status === "terminated";
  const audit = auditResult.ok ? auditResult.data.items : null;
  const changes = changesResult.ok ? changesResult.data.items : null;
  const departments = referenceResult.ok ? referenceResult.data.departments : [];
  const departmentNames = new Map(departments.map((d) => [String(d.id), d.name]));
  const currency = referenceResult.ok
    ? referenceResult.data.currencies.find((c) => c.code === employee.currency_code)
    : undefined;
  const latestAudit = audit?.[0];
  const rateText = currency
    ? formatRate(currency.units_per_usd_scaled, currency.units_per_usd_scale, currency.code)
    : latestAudit
      ? formatRate(latestAudit.fx_units_per_usd_scaled, latestAudit.fx_scale, latestAudit.currency_code)
      : null;
  const terminatedSince = terminated
    ? changes?.find((change) => change.field === "status" && change.new_value === "terminated")
    : undefined;
  const money = (scaled: string) =>
    formatLocalMoney(scaled, employee.salary_scale, employee.currency_code);
  const total = sumScaled(employee.base_salary_scaled, employee.variable_pay_scaled);

  const details: [string, string][] = [
    ["Email", employee.email],
    ["Department", employee.department.name],
    ["Title", employee.job_title],
    ["Level", employee.level],
    ["Country", employee.country.name],
    ["Currency", employee.currency_code],
    ["Employee number", employee.employee_number],
    ["Hire date", formatDate(employee.hire_date)],
  ];

  return (
    <Shell>
      <div className={styles.page}>
        <PageHeader
          breadcrumb={
            <Breadcrumb items={[{ label: "Employees", href: "/employees" }, { label: name }]} />
          }
          title={
            <span className={styles.titleRow}>
              {name}
              <span className={styles.number}>{employee.employee_number}</span>
              <StatusTag status={terminated ? "Terminated" : "Active"} />
            </span>
          }
          subtitle={[
            employee.job_title,
            employee.department.name,
            employee.country.name,
            `Level ${employee.level}`,
            `Hired ${formatDate(employee.hire_date)}`,
          ].join(" · ")}
          actions={
            <>
              <LinkButton href={`${base}/pay`}>Change pay</LinkButton>
              <LinkButton href={`${base}/edit`} variant="quiet">
                Edit details
              </LinkButton>
              {terminated ? null : (
                <LinkButton href={`${base}/edit#status`} variant="danger">
                  Terminate
                </LinkButton>
              )}
            </>
          }
        />

        {saved ? <Notice tone="success">{saved}</Notice> : null}
        {terminated ? (
          <Notice tone="info">
            Terminated since{" "}
            {terminatedSince ? formatDate(terminatedSince.effective_date) : "an unknown date"}.
          </Notice>
        ) : null}

        <div className={styles.cards}>
          <Card>
            <CardHeader
              title="Current pay"
              description={`Effective ${formatDate(employee.comp_effective_date)}`}
            />
            <dl className={styles.payRows}>
              <div>
                <dt>Base pay</dt>
                <dd>{money(employee.base_salary_scaled)}</dd>
              </div>
              <div>
                <dt>Variable pay</dt>
                <dd>{money(employee.variable_pay_scaled)}</dd>
              </div>
              <div className={styles.total}>
                <dt>
                  Total pay
                  <span className={styles.sub}>Annual, in {employee.currency_code}</span>
                </dt>
                <dd>{money(total)}</dd>
              </div>
            </dl>
            <p className={styles.usd}>
              <strong>
                US dollar equivalent: {formatUsd(employee.salary_usd_scaled, employee.salary_usd_scale)}
              </strong>
              {rateText ? <span>Planning rate {rateText}.</span> : null}
            </p>
          </Card>

          <Card>
            <CardHeader title="Details" />
            <dl className={styles.detailRows}>
              {details.map(([label, value]) => (
                <div key={label}>
                  <dt>{label}</dt>
                  <dd>{value}</dd>
                </div>
              ))}
            </dl>
          </Card>
        </div>

        <ChangeHistory
          basePath={base}
          tab={tab}
          payEntries={audit}
          changes={changes}
          departmentNames={departmentNames}
        />
      </div>
    </Shell>
  );
}
