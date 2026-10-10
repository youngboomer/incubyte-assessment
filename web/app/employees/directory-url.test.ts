import { describe, expect, it } from "vitest";
import {
  backendFilters,
  clearedFilters,
  currentPage,
  directoryHref,
  nextSort,
  pageRange,
  readDirectoryState,
} from "./directory-url";

describe("pageRange", () => {
  it("computes ranges across pages", () => {
    expect(pageRange(1, 25, 25, 36)).toEqual({ from: 1, to: 25 });
    expect(pageRange(2, 25, 11, 36)).toEqual({ from: 26, to: 36 });
  });
  it("handles empty results", () => {
    expect(pageRange(1, 25, 0, 0)).toEqual({ from: 0, to: 0 });
  });
});

describe("directory state", () => {
  it("converts dollars to scaled cents for the backend", () => {
    const state = readDirectoryState({ pay_min: "100,000", pay_max: "250000.5" });
    const filters = backendFilters(state);
    expect(filters.salary_usd_min).toBe("10000000");
    expect(filters.salary_usd_max).toBe("25000050");
  });
  it("drops inverted and invalid ranges", () => {
    expect(readDirectoryState({ pay_min: "9", pay_max: "1" })).toEqual({});
    expect(readDirectoryState({ pay_min: "abc" })).toEqual({});
  });
  it("only keeps page with a cursor", () => {
    expect(readDirectoryState({ page: "3" }).page).toBeUndefined();
    expect(currentPage(readDirectoryState({ cursor: "c", page: "3" }))).toBe(3);
    expect(currentPage({})).toBe(1);
  });
  it("builds hrefs and clears filters but keeps sort", () => {
    const state = readDirectoryState({ q: "ann", country: "gb", sort: "title", cursor: "c", page: "2" });
    expect(directoryHref("/employees", clearedFilters(state))).toBe("/employees?sort=title");
  });
  it("toggles sort direction", () => {
    expect(nextSort({}, "name")).toEqual({ href: { sort: "name", direction: "desc" }, direction: "asc" });
    expect(nextSort({ sort: "name", direction: "desc" }, "title").href).toEqual({ sort: "title", direction: "asc" });
  });
});
