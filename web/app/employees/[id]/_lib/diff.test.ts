import { describe, expect, it } from "vitest";
import { changedPayload, summarizeChanges, type DetailsValues } from "./diff";

const original: DetailsValues = {
  first_name: "Aditi",
  last_name: "Chen",
  email: "a@acme.test",
  job_title: "Engineer",
  department_id: "1",
  level: "IC3",
};
const departments = [
  { id: 1, name: "Engineering" },
  { id: 2, name: "Sales" },
];

describe("details diff", () => {
  it("is empty when nothing changed", () => {
    expect(summarizeChanges(original, { ...original, job_title: " Engineer " }, departments)).toEqual([]);
    expect(changedPayload(original, original)).toEqual({});
  });
  it("lists changes with department names", () => {
    const next = { ...original, job_title: "Staff Engineer", department_id: "2" };
    expect(summarizeChanges(original, next, departments)).toEqual([
      { field: "job_title", label: "Job title", from: "Engineer", to: "Staff Engineer" },
      { field: "department_id", label: "Department", from: "Engineering", to: "Sales" },
    ]);
  });
  it("sends only changed fields with numeric department", () => {
    const next = { ...original, level: "IC4", department_id: "2" };
    expect(changedPayload(original, next)).toEqual({ level: "IC4", department_id: 2 });
  });
});
