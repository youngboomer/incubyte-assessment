import { describe, expect, test } from "vitest";
import {
  formatCompactUsd,
  formatDate,
  formatDateTime,
  formatLocalMoney,
  formatPercent,
  formatScaled,
  formatUsd,
  fullName,
  majorToScaled,
  pctChange,
} from "./format";

test("major units become scaled digit strings", () => {
  expect(majorToScaled("120000.50", 2)).toBe("12000050");
  expect(majorToScaled("120000.5", 2)).toBe("12000050");
  expect(majorToScaled("120000", 2)).toBe("12000000");
  expect(majorToScaled("8000000", 0)).toBe("8000000");
  expect(majorToScaled("1.225", 2)).toBe("122");
  expect(majorToScaled("1.235", 2)).toBe("124");
  expect(majorToScaled("1.5", 0)).toBe("2");
  expect(majorToScaled("2.5", 0)).toBe("2");
  expect(majorToScaled("-1.5", 0)).toBe("-2");
  expect(majorToScaled("12.00x", 2)).toBeNull();
});

test("display divides the scaled string", () => {
  expect(formatScaled("12000050", 2, "USD")).toBe("$120,000.50");
  expect(formatScaled("8000000", 0, "JPY")).toBe("¥8,000,000");
  expect(formatScaled("99", 2)).toBe("0.99");
});

describe("formatUsd", () => {
  test("groups and keeps cents exactly", () => {
    expect(formatUsd("12000050")).toBe("$120,000.50");
    expect(formatUsd("5")).toBe("$0.05");
    expect(formatUsd("-12050")).toBe("-$120.50");
    expect(formatUsd("9007199254740993123")).toBe("$90,071,992,547,409,931.23");
  });

  test("returns invalid input untouched", () => {
    expect(formatUsd("abc")).toBe("abc");
  });
});

describe("formatCompactUsd", () => {
  test("abbreviates", () => {
    expect(formatCompactUsd("121000000000")).toBe("$1.21B");
    expect(formatCompactUsd("11400000")).toBe("$114k");
    expect(formatCompactUsd("550000")).toBe("$5.5k");
    expect(formatCompactUsd("1480000000")).toBe("$14.8M");
    expect(formatCompactUsd("95000")).toBe("$950");
    expect(formatCompactUsd("0")).toBe("$0");
    expect(formatCompactUsd("-11400000")).toBe("-$114k");
  });

  test("rolls over at unit boundaries", () => {
    expect(formatCompactUsd("99999950")).toBe("$1M");
  });
});

describe("formatLocalMoney", () => {
  test("INR uses lakh grouping", () => {
    expect(formatLocalMoney("123456789", 2, "INR")).toBe("₹12,34,567.89");
  });

  test("JPY has no decimals", () => {
    expect(formatLocalMoney("8000000", 0, "JPY")).toBe("¥8,000,000");
  });

  test("other currencies use their symbol", () => {
    expect(formatLocalMoney("1234500", 2, "GBP")).toBe("£12,345.00");
    expect(formatLocalMoney("1234500", 2, "EUR")).toBe("€12,345.00");
    expect(formatLocalMoney("1234500", 2, "USD")).toBe("$12,345.00");
  });

  test("unknown currency code still renders", () => {
    expect(formatLocalMoney("1234500", 2, "ZZ")).toContain("12,345.00");
  });
});

describe("pctChange", () => {
  test("is exact on bigint input", () => {
    expect(pctChange("15500000", "16000000")).toBe(3.23);
    expect(pctChange("100", "50")).toBe(-50);
    expect(pctChange("100", "100")).toBe(0);
    expect(pctChange("9007199254740993", "9007199254740993")).toBe(0);
  });

  test("handles zero and bad input", () => {
    expect(pctChange("0", "100")).toBeNull();
    expect(pctChange("x", "100")).toBeNull();
  });
});

test("formatPercent", () => {
  expect(formatPercent(3.234)).toBe("3.2%");
  expect(formatPercent(3.234, 2, true)).toBe("+3.23%");
  expect(formatPercent(-1.5, 1, true)).toBe("-1.5%");
  expect(formatPercent(Number.NaN)).toBe("");
});

test("dates are not timezone shifted", () => {
  expect(formatDate("2025-04-01")).toBe("1 Apr 2025");
  expect(formatDate("2025-12-31")).toBe("31 Dec 2025");
  expect(formatDate("bad")).toBe("bad");
  expect(formatDateTime("2026-04-01T09:05:00Z")).toBe("1 Apr 2026, 09:05 UTC");
});

test("fullName", () => {
  expect(fullName({ first_name: "Ada", last_name: "Okoye" })).toBe("Ada Okoye");
});
