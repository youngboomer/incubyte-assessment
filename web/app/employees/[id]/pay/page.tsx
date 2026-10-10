import { connection } from "next/server";
import { Shell } from "../../../../components/shell";
import { Breadcrumb, Card, PageHeader } from "../../../../components/ui";
import { getEmployee, reference } from "../../../../lib/endpoints";
import { formatDate, formatUsd, fullName } from "../../../../lib/format";
import { EmployeeLoadError, EmployeeNotFound } from "../_lib/not-found";
import { currencySymbol, formatRate, scaledToMajor, sumScaled } from "../_lib/pay-math";
import { guard, requireToken, todayIso, totalLabel } from "../_lib/server";
import { PayForm } from "./pay-form";
import styles from "./pay.module.css";

export default async function ChangePayPage({ params }: { params: Promise<{ id: string }> }) {
  await connection();
  const { id } = await params;
  const token = await requireToken();
  const [employeeResult, referenceResult] = await Promise.all([
    getEmployee(token, id).then(guard),
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
  const currency = referenceResult.ok
    ? referenceResult.data.currencies.find((c) => c.code === employee.currency_code)
    : undefined;
  if (!currency) {
    return <EmployeeLoadError message="The planning rate for this currency could not be loaded." />;
  }

  const name = fullName(employee);
  const base = `/employees/${encodeURIComponent(employee.id)}`;
  const total = sumScaled(employee.base_salary_scaled, employee.variable_pay_scaled);
  const money = (scaled: string) => totalLabel({ ...employee, base_salary_scaled: scaled, variable_pay_scaled: "0" });

  return (
    <Shell>
      <div className={styles.narrow}>
        <PageHeader
          breadcrumb={
            <Breadcrumb
              items={[
                { label: "Employees", href: "/employees" },
                { label: name, href: base },
                { label: "Change pay" },
              ]}
            />
          }
          title="Change pay"
          subtitle={`${name} · ${employee.employee_number} · ${employee.job_title} (${employee.level}) · ${employee.country.name}`}
        />

        <Card>
          <h2>Current pay (version {employee.version_id})</h2>
          <dl className={styles.summaryRow}>
            <div>
              <dt>Base pay</dt>
              <dd>{money(employee.base_salary_scaled)}</dd>
            </div>
            <div>
              <dt>Variable pay</dt>
              <dd>{money(employee.variable_pay_scaled)}</dd>
            </div>
          </dl>
          <p className={styles.foot}>
            Total {money(total)} = {formatUsd(employee.salary_usd_scaled, employee.salary_usd_scale)} at
            planning rate{" "}
            {formatRate(currency.units_per_usd_scaled, currency.units_per_usd_scale, currency.code)}.
            Effective from {formatDate(employee.comp_effective_date)}.
          </p>
        </Card>

        <Card>
          <PayForm
            employeeId={employee.id}
            versionId={employee.version_id}
            currencyCode={employee.currency_code}
            symbol={currencySymbol(employee.currency_code)}
            scale={employee.salary_scale}
            initialBase={scaledToMajor(employee.base_salary_scaled, employee.salary_scale)}
            initialVariable={scaledToMajor(employee.variable_pay_scaled, employee.salary_scale)}
            currentTotalScaled={total}
            currentTotalLabel={money(total)}
            rateScaled={currency.units_per_usd_scaled}
            rateScale={currency.units_per_usd_scale}
            usdScale={employee.salary_usd_scale}
            today={todayIso()}
          />
        </Card>
      </div>
    </Shell>
  );
}
