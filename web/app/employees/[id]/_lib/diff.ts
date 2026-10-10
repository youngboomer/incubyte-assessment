import type { Department, Employee, UpdateEmployeeRequest } from "../../../../lib/types";

export type DetailsValues = {
  first_name: string;
  last_name: string;
  email: string;
  job_title: string;
  department_id: string;
  level: string;
};

export type DetailChange = { field: keyof DetailsValues; label: string; from: string; to: string };

const LABELS: Record<keyof DetailsValues, string> = {
  first_name: "First name",
  last_name: "Last name",
  email: "Email",
  job_title: "Job title",
  department_id: "Department",
  level: "Level",
};

const FIELDS = Object.keys(LABELS) as (keyof DetailsValues)[];

export function detailsOf(employee: Employee): DetailsValues {
  return {
    first_name: employee.first_name,
    last_name: employee.last_name,
    email: employee.email,
    job_title: employee.job_title,
    department_id: String(employee.department.id),
    level: employee.level,
  };
}

export function summarizeChanges(
  original: DetailsValues,
  next: DetailsValues,
  departments: Department[],
): DetailChange[] {
  const departmentName = (id: string) =>
    departments.find((department) => String(department.id) === id)?.name ?? id;
  const changes: DetailChange[] = [];
  for (const field of FIELDS) {
    const from = original[field].trim();
    const to = next[field].trim();
    if (from === to) {
      continue;
    }
    changes.push(
      field === "department_id"
        ? { field, label: LABELS[field], from: departmentName(from), to: departmentName(to) }
        : { field, label: LABELS[field], from, to },
    );
  }
  return changes;
}

export function changedPayload(
  original: DetailsValues,
  next: DetailsValues,
): Partial<Omit<UpdateEmployeeRequest, "reason" | "effective_date" | "version_id">> {
  const payload: Record<string, string | number> = {};
  for (const field of FIELDS) {
    const to = next[field].trim();
    if (original[field].trim() === to) {
      continue;
    }
    payload[field] = field === "department_id" ? Number(to) : to;
  }
  return payload;
}
