import { cookies } from "next/headers";
import { connection } from "next/server";
import { redirect } from "next/navigation";
import { Shell } from "../../../components/shell";
import { backendFetch } from "../../../lib/api";
import { formatScaled } from "../../../lib/format";
import { SESSION_COOKIE } from "../../../lib/session";
import type { AuditEntry, AuditPage, Department, Employee, EmployeeCountry } from "../../../lib/types";
import { PayForm } from "./pay-form";
import styles from "./profile.module.css";

export default async function EmployeeProfilePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  await connection();
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!token) redirect("/login");

  const { id } = await params;
  const employeePath = `/employees/${encodeURIComponent(id)}`;

  let employeeResponse: Response;
  let auditResponse: Response;
  try {
    [employeeResponse, auditResponse] = await Promise.all([
      backendFetch(employeePath, token),
      backendFetch(`${employeePath}/audit`, token),
    ]);
  } catch {
    return <LoadError />;
  }

  if (employeeResponse.status === 401 || auditResponse.status === 401) {
    redirect("/logout");
  }
  if (employeeResponse.status === 404) {
    return (
      <Shell>
        <p className={styles.error}>Employee not found.</p>
      </Shell>
    );
  }
  if (!employeeResponse.ok) {
    return <LoadError status={employeeResponse.status} />;
  }

  const employeeBody: unknown = await readJson(employeeResponse);
  if (!isEmployee(employeeBody)) {
    return <LoadError status={employeeResponse.status} />;
  }

  const audit = await readAudit(auditResponse);

  return (
    <Shell>
      <div className={styles.page}>
        <h1>
          {employeeBody.first_name} {employeeBody.last_name}
        </h1>
        <dl className={styles.fields}>
          <Field
            label="Name"
            value={`${employeeBody.first_name} ${employeeBody.last_name}`}
          />
          <Field label="Employee number" value={employeeBody.employee_number} />
          <Field label="Email" value={employeeBody.email} />
          <Field label="Title" value={employeeBody.job_title} />
          <Field label="Department" value={employeeBody.department.name} />
          <Field label="Country" value={employeeBody.country.name} />
          <Field label="Level" value={employeeBody.level} />
          <Field label="Status" value={employeeBody.status} />
          <Field label="Hire date" value={employeeBody.hire_date} />
          <Field label="Comp effective date" value={employeeBody.comp_effective_date} />
          <Field label="Version" value={String(employeeBody.version_id)} />
          <Field
            label="Base salary"
            value={formatScaled(
              employeeBody.base_salary_scaled,
              employeeBody.salary_scale,
              employeeBody.currency_code,
            )}
          />
          <Field
            label="Variable pay"
            value={formatScaled(
              employeeBody.variable_pay_scaled,
              employeeBody.salary_scale,
              employeeBody.currency_code,
            )}
          />
          <Field
            label="USD"
            value={formatScaled(
              employeeBody.salary_usd_scaled,
              employeeBody.salary_usd_scale,
              "USD",
            )}
          />
        </dl>
        <section className={styles.section}>
          <h2>Change pay</h2>
          <PayForm
            employeeId={id}
            salaryScale={employeeBody.salary_scale}
            versionId={employeeBody.version_id}
            currencyCode={employeeBody.currency_code}
          />
        </section>
        <section className={styles.section}>
          <h2>Audit</h2>
          {audit.ok ? (
            <AuditList items={audit.items} />
          ) : (
            <p className={styles.error}>
              Could not load this employee.
              {` ${audit.status}`}
            </p>
          )}
        </section>
      </div>
    </Shell>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <>
      <dt>{label}</dt>
      <dd>{value}</dd>
    </>
  );
}

function LoadError({ status }: { status?: number }) {
  return (
    <Shell>
      <p className={styles.error}>
        Could not load this employee.
        {status !== undefined ? ` ${status}` : null}
      </p>
    </Shell>
  );
}

function AuditList({ items }: { items: AuditEntry[] }) {
  if (items.length === 0) {
    return <p>No pay changes yet.</p>;
  }

  return (
    <div className={styles.scroll}>
      <table className={styles.audit}>
        <thead>
          <tr>
            <th>Effective date</th>
            <th>Reason</th>
            <th>Previous local pay</th>
            <th>New local pay</th>
            <th>Previous USD</th>
            <th>New USD</th>
            <th>Planning rate</th>
            <th>changed_by</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.id}>
              <td>{item.effective_date}</td>
              <td>{item.reason}</td>
              <td>{localPay(item, item.previous_base_salary_scaled, item.previous_variable_pay_scaled)}</td>
              <td>{localPay(item, item.new_base_salary_scaled, item.new_variable_pay_scaled)}</td>
              <td>
                {formatScaled(item.previous_salary_usd_scaled, item.salary_usd_scale, "USD")}
              </td>
              <td>{formatScaled(item.new_salary_usd_scaled, item.salary_usd_scale, "USD")}</td>
              <td>{formatScaled(item.fx_units_per_usd_scaled, item.fx_scale)}</td>
              <td>{item.changed_by}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function localPay(item: AuditEntry, baseScaled: string, variableScaled: string) {
  return (
    <>
      <div>
        Base {formatScaled(baseScaled, item.salary_scale, item.currency_code)}
      </div>
      <div>
        Variable {formatScaled(variableScaled, item.salary_scale, item.currency_code)}
      </div>
    </>
  );
}

async function readAudit(
  response: Response,
): Promise<{ ok: true; items: AuditEntry[] } | { ok: false; status: number }> {
  if (!response.ok) {
    return { ok: false, status: response.status };
  }
  const body: unknown = await readJson(response);
  if (!isAuditPage(body)) {
    return { ok: false, status: response.status };
  }
  return { ok: true, items: body.items };
}

async function readJson(response: Response): Promise<unknown> {
  try {
    return await response.json();
  } catch {
    return null;
  }
}

function isEmployee(value: unknown): value is Employee {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const row = value as Record<string, unknown>;
  return (
    typeof row["first_name"] === "string" &&
    typeof row["last_name"] === "string" &&
    typeof row["employee_number"] === "string" &&
    typeof row["email"] === "string" &&
    typeof row["job_title"] === "string" &&
    isDepartment(row["department"]) &&
    isCountry(row["country"]) &&
    typeof row["level"] === "string" &&
    typeof row["status"] === "string" &&
    typeof row["hire_date"] === "string" &&
    typeof row["comp_effective_date"] === "string" &&
    typeof row["base_salary_scaled"] === "string" &&
    typeof row["variable_pay_scaled"] === "string" &&
    typeof row["salary_scale"] === "number" &&
    typeof row["currency_code"] === "string" &&
    typeof row["salary_usd_scaled"] === "string" &&
    typeof row["salary_usd_scale"] === "number" &&
    typeof row["version_id"] === "number"
  );
}

function isDepartment(value: unknown): value is Department {
  return (
    typeof value === "object" &&
    value !== null &&
    typeof (value as Department).name === "string"
  );
}

function isCountry(value: unknown): value is EmployeeCountry {
  return (
    typeof value === "object" &&
    value !== null &&
    typeof (value as EmployeeCountry).name === "string"
  );
}

function isAuditPage(value: unknown): value is AuditPage {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const items = (value as AuditPage).items;
  return Array.isArray(items) && items.every(isAuditEntry);
}

function isAuditEntry(value: unknown): value is AuditEntry {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const row = value as Record<string, unknown>;
  return (
    typeof row["id"] === "number" &&
    typeof row["previous_base_salary_scaled"] === "string" &&
    typeof row["new_base_salary_scaled"] === "string" &&
    typeof row["previous_variable_pay_scaled"] === "string" &&
    typeof row["new_variable_pay_scaled"] === "string" &&
    typeof row["salary_scale"] === "number" &&
    typeof row["currency_code"] === "string" &&
    typeof row["fx_units_per_usd_scaled"] === "string" &&
    typeof row["fx_scale"] === "number" &&
    typeof row["previous_salary_usd_scaled"] === "string" &&
    typeof row["new_salary_usd_scaled"] === "string" &&
    typeof row["salary_usd_scale"] === "number" &&
    typeof row["reason"] === "string" &&
    typeof row["effective_date"] === "string" &&
    typeof row["changed_by"] === "string"
  );
}
