import { describe, expect, test } from "vitest";
import {
  auditQuery,
  changesQuery,
  historyHref,
  parseChangesFilters,
  parseHistoryTab,
  buildQuery,
  directoryQuery,
  parseAuditFilters,
  parseDirectoryFilters,
  parseScopeFilters,
  scopeQuery,
} from "./query";

function toParams(query: string): Record<string, string> {
  return Object.fromEntries(new URLSearchParams(query));
}

describe("buildQuery", () => {
  test("skips empty values and encodes", () => {
    expect(buildQuery({ a: "", b: undefined, c: null, d: "  ", e: "x y&z", f: 0 })).toBe(
      "?e=x+y%26z&f=0",
    );
    expect(buildQuery({})).toBe("");
  });

  test("order is stable", () => {
    expect(buildQuery({ b: "1", a: "2" })).toBe("?a=2&b=1");
  });
});

describe("directory filters", () => {
  test("round trip", () => {
    const filters = {
      q: "ada o",
      department_id: "3",
      country: "US",
      currency: "USD",
      status: "active" as const,
      level: "IC3" as const,
      salary_usd_min: "1000000",
      salary_usd_max: "20000000",
      sort: "salary_usd" as const,
      direction: "desc" as const,
      limit: 25,
      cursor: "abc.def",
    };
    const query = directoryQuery(filters);
    expect(parseDirectoryFilters(toParams(query))).toEqual(filters);
    expect(directoryQuery(parseDirectoryFilters(toParams(query)))).toBe(query);
  });

  test("order does not depend on key order", () => {
    expect(directoryQuery({ sort: "name", q: "a", status: "active" })).toBe(
      "?q=a&status=active&sort=name",
    );
  });

  test("drops invalid values", () => {
    const parsed = parseDirectoryFilters({
      level: "IC9",
      status: "fired",
      sort: "salary",
      direction: "up",
      salary_usd_min: "-5",
      salary_usd_max: "1.5",
      department_id: "abc",
      limit: "500",
    });
    expect(parsed).toEqual({});
  });

  test("drops inverted and oversized salary bounds", () => {
    expect(parseDirectoryFilters({ salary_usd_min: "500", salary_usd_max: "100" })).toEqual({});
    expect(parseDirectoryFilters({ salary_usd_min: "9223372036854775808" })).toEqual({});
    expect(parseDirectoryFilters({ salary_usd_min: "007" })).toEqual({ salary_usd_min: "7" });
  });

  test("takes first of repeated params and trims", () => {
    expect(parseDirectoryFilters({ q: ["  ada ", "bob"], country: "in" })).toEqual({
      q: "ada",
      country: "IN",
    });
  });
});

describe("scope filters", () => {
  test("round trip and validation", () => {
    const query = scopeQuery({ department_id: "2", country: "GB", level: "M1", currency: "GBP" });
    expect(query).toBe("?department_id=2&country=GB&level=M1&currency=GBP");
    expect(parseScopeFilters(toParams(query))).toEqual({
      department_id: "2",
      country: "GB",
      level: "M1",
      currency: "GBP",
    });
    expect(parseScopeFilters({ level: "X" })).toEqual({});
  });
});

describe("audit filters", () => {
  test("round trip with cursor", () => {
    const query = auditQuery(
      { employee_id: "e1", department_id: "1", since: "2026-01-01", until: "2026-02-01", limit: 10 },
      "cur",
    );
    expect(query).toBe(
      "?employee_id=e1&department_id=1&since=2026-01-01&until=2026-02-01&limit=10&cursor=cur",
    );
    expect(parseAuditFilters(toParams(query))).toEqual({
      employee_id: "e1",
      department_id: "1",
      since: "2026-01-01",
      until: "2026-02-01",
      limit: 10,
      cursor: "cur",
    });
  });

  test("rejects bad dates and inverted range", () => {
    expect(parseAuditFilters({ since: "2026-02-30" })).toEqual({});
    expect(parseAuditFilters({ since: "2026-03-01", until: "2026-01-01" })).toEqual({});
  });
});

describe("change filters", () => {
  test("round trip with field and cursor", () => {
    const query = changesQuery({ field: "level", department_id: "1", since: "2026-01-01" }, "cur");
    expect(query).toBe("?department_id=1&field=level&since=2026-01-01&cursor=cur");
    expect(parseChangesFilters(toParams(query))).toEqual({
      department_id: "1",
      field: "level",
      since: "2026-01-01",
      cursor: "cur",
    });
  });

  test("drops fields outside the allow-list", () => {
    expect(parseChangesFilters({ field: "base_salary" })).toEqual({});
    expect(parseChangesFilters({ field: "Level" })).toEqual({});
    expect(parseChangesFilters({ field: ["status", "level"] })).toEqual({ field: "status" });
  });

  test("shares date validation with the pay filters", () => {
    expect(parseChangesFilters({ since: "2026-03-01", until: "2026-01-01", field: "email" })).toEqual({
      field: "email",
    });
  });

  test("tab defaults to pay", () => {
    expect(parseHistoryTab({})).toBe("pay");
    expect(parseHistoryTab({ tab: "bogus" })).toBe("pay");
    expect(parseHistoryTab({ tab: "details" })).toBe("details");
  });

  test("history links keep the tab only for details", () => {
    expect(historyHref("pay", { since: "2026-01-01" })).toBe("/history?since=2026-01-01");
    expect(historyHref("details", { field: "status" }, "c")).toBe("/history?tab=details&field=status&cursor=c");
    expect(historyHref("details", {})).toBe("/history?tab=details");
  });
});
