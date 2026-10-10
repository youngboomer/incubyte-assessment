import { cookies } from "next/headers";
import { connection } from "next/server";
import { redirect } from "next/navigation";
import { Shell } from "../../../components/shell";
import { Breadcrumb, EmptyState, LinkButton, PageHeader } from "../../../components/ui";
import { reference } from "../../../lib/endpoints";
import { SESSION_COOKIE } from "../../../lib/session";
import { AddEmployeeForm } from "../add-form";
import styles from "../add-employee.module.css";

export const metadata = { title: "Add employee | CompPulse" };

export default async function NewEmployeePage() {
  await connection();
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!token) {
    redirect("/login");
  }

  const ref = await reference(token);
  if (!ref.ok && ref.code === "unauthorized") {
    redirect("/logout");
  }

  return (
    <Shell>
      <div className={styles.page}>
        <PageHeader
          title="Add employee"
          breadcrumb={<Breadcrumb items={[{ label: "Employees", href: "/employees" }, { label: "Add employee" }]} />}
        />
      </div>
      {ref.ok ? (
        <AddEmployeeForm reference={ref.data} today={new Date().toISOString().slice(0, 10)} />
      ) : (
        <EmptyState
          title="Could not load the form."
          action={
            <LinkButton href="/employees/new" variant="quiet">
              Retry
            </LinkButton>
          }
        >
          Departments and countries are unavailable right now.
        </EmptyState>
      )}
    </Shell>
  );
}
