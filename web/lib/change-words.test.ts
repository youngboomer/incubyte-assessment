import { describe, expect, test } from "vitest";
import { describeChange } from "./change-words";
import type { ChangeFeedItem } from "./types";

function item(overrides: Partial<ChangeFeedItem>): ChangeFeedItem {
  return {
    id: 1,
    field: "level",
    previous_value: "IC5",
    new_value: "M1",
    previous_label: null,
    new_label: null,
    reason: "Promotion",
    effective_date: "2026-03-01",
    changed_by: "hr@example.com",
    created_at: "2026-03-01T00:00:00Z",
    employee_id: "e1",
    employee_number: "E-1",
    employee_name: "Ada Lovelace",
    department: { id: 1, name: "Engineering" },
    ...overrides,
  };
}

describe("describeChange", () => {
  test("level and job title", () => {
    expect(describeChange(item({}))).toBe("Level: IC5 → M1");
    expect(describeChange(item({ field: "job_title", previous_value: "A", new_value: "B" }))).toBe(
      "Job title: A → B",
    );
  });

  test("department uses labels and falls back to ids", () => {
    const base = { field: "department_id", previous_value: "2", new_value: "3" };
    expect(describeChange(item({ ...base, previous_label: "Sales", new_label: "Product" }))).toBe(
      "Department: Sales → Product",
    );
    expect(describeChange(item({ ...base, previous_label: "Sales" }))).toBe("Department: Sales → 3");
  });

  test("names and email", () => {
    expect(describeChange(item({ field: "first_name", previous_value: "Ad", new_value: "Ada" }))).toBe(
      "First name: Ad → Ada",
    );
    expect(describeChange(item({ field: "last_name", previous_value: "L", new_value: "Lovelace" }))).toBe(
      "Last name: L → Lovelace",
    );
    expect(describeChange(item({ field: "email", previous_value: "a@x.com", new_value: "b@x.com" }))).toBe(
      "Email: a@x.com → b@x.com",
    );
  });

  test("status reads as terminated or reactivated", () => {
    expect(describeChange(item({ field: "status", previous_value: "active", new_value: "terminated" }))).toBe(
      "Terminated",
    );
    expect(describeChange(item({ field: "status", previous_value: "terminated", new_value: "active" }))).toBe(
      "Reactivated",
    );
  });
});
