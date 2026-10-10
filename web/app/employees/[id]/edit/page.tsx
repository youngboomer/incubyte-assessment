import { connection } from "next/server";
import { Shell } from "../../../../components/shell";
import { Breadcrumb, Card, CardHeader, PageHeader } from "../../../../components/ui";
import { getEmployee, listEmployeeChanges, reference } from "../../../../lib/endpoints";
import { formatDate, fullName } from "../../../../lib/format";
import { detailsOf } from "../_lib/diff";
import { EmployeeLoadError, EmployeeNotFound } from "../_lib/not-found";
import { guard, requireToken, todayIso } from "../_lib/server";
import { DetailsForm, StatusForm } from "./edit-forms";
import styles from "./edit.module.css";

export default async function EditEmployeePage({ params }: { params: Promise<{ id: string }> }) {
  await connection();
  const { id } = await params;
  const token = await requireToken();
  const [employeeResult, referenceResult, changesResult] = await Promise.all([
    getEmployee(token, id).then(guard),
    reference(token).then(guard),
    listEmployeeChanges(token, id).then(guard),
  ]);

  if (!employeeResult.ok) {
    return employeeResult.code === "not_found" || employeeResult.status === 422 ? (
      <EmployeeNotFound />
    ) : (
      <EmployeeLoadError message={employeeResult.message} />
    );
  }
  if (!referenceResult.ok) {
    return <EmployeeLoadError message={referenceResult.message} />;
  }
  const employee = employeeResult.data;
  const name = fullName(employee);
  const base = `/employees/${encodeURIComponent(employee.id)}`;
  const terminated = employee.status === "terminated";
  const since = terminated && changesResult.ok
    ? changesResult.data.items.find((change) => change.field === "status")
    : undefined;
  const today = todayIso();

  return (
    <Shell>
      <div className={styles.page}>
        <PageHeader
          breadcrumb={
            <Breadcrumb
              items={[
                { label: "Employees", href: "/employees" },
                { label: name, href: base },
                { label: "Edit details" },
              ]}
            />
          }
          title="Edit details"
          subtitle={`${name} · ${employee.employee_number}`}
        />
        <div className={styles.columns}>
          <Card>
            <CardHeader
              title="Edit details"
              description="Changes are recorded in the history with your reason."
            />
            <DetailsForm
              employeeId={employee.id}
              versionId={employee.version_id}
              original={detailsOf(employee)}
              departments={referenceResult.data.departments}
              levels={referenceResult.data.levels}
              countryName={employee.country.name}
              currencyCode={employee.currency_code}
              today={today}
            />
          </Card>

          <Card aria-label="Employment status">
            <span id="status" className={styles.anchor} />
            <CardHeader title="Employment status" />
            {terminated ? (
              <div className={styles.block}>
                <h3 className={styles.blockTitle}>
                  Terminated since {since ? formatDate(since.effective_date) : "an unknown date"}
                </h3>
                <p className={styles.blockText}>
                  Reactivating puts them back in the active directory and pay analytics.
                </p>
                <h3 className={styles.blockTitle}>Reactivate employee</h3>
                <StatusForm
                  employeeId={employee.id}
                  versionId={employee.version_id}
                  target="active"
                  today={today}
                />
              </div>
            ) : (
              <div className={styles.danger}>
                <h3 className={styles.blockTitle}>Terminate employee</h3>
                <p className={styles.blockText}>
                  They stay in the directory and history, and drop out of pay analytics.
                </p>
                <StatusForm
                  employeeId={employee.id}
                  versionId={employee.version_id}
                  target="terminated"
                  today={today}
                />
              </div>
            )}
          </Card>
        </div>
      </div>
    </Shell>
  );
}
