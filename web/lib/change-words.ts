import type { ChangeFeedItem } from "./types";

const FIELD_LABELS: Record<string, string> = {
  first_name: "First name",
  last_name: "Last name",
  email: "Email",
  job_title: "Job title",
  department_id: "Department",
  level: "Level",
};

export function describeChange(item: ChangeFeedItem): string {
  if (item.field === "status") {
    return item.new_value === "terminated" ? "Terminated" : "Reactivated";
  }
  const label = FIELD_LABELS[item.field] ?? item.field;
  const previous = item.previous_label ?? item.previous_value;
  const next = item.new_label ?? item.new_value;
  return `${label}: ${previous} → ${next}`;
}
