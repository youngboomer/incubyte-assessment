import { Shell } from "../../../../components/shell";
import { Breadcrumb, EmptyState, LinkButton, PageHeader } from "../../../../components/ui";

export function EmployeeNotFound() {
  return (
    <Shell>
      <PageHeader
        breadcrumb={
          <Breadcrumb items={[{ label: "Employees", href: "/employees" }, { label: "Not found" }]} />
        }
        title="Employee not found"
      />
      <EmptyState
        title="Employee not found."
        action={<LinkButton href="/employees" variant="quiet">Back to employees</LinkButton>}
      >
        It may have been removed, or the link is wrong.
      </EmptyState>
    </Shell>
  );
}

export function EmployeeLoadError({ message }: { message: string }) {
  return (
    <Shell>
      <EmptyState
        title="Could not load this employee."
        action={<LinkButton href="/employees" variant="quiet">Back to employees</LinkButton>}
      >
        {message}
      </EmptyState>
    </Shell>
  );
}
