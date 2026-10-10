import { describe, expect, it } from "vitest";
import { currencySymbol, formatRate, previewPay, scaledToMajor } from "./pay-math";

const base = {
  scale: 2,
  rateScaled: "780000",
  rateScale: 6,
  usdScale: 2,
  currentTotalScaled: "12850000",
};

describe("previewPay", () => {
  it("computes total, usd and percent", () => {
    const result = previewPay({ ...base, baseMajor: "134000", variableMajor: "0" });
    expect(result).toEqual({
      totalScaled: "13400000",
      usdScaled: "17179487",
      deltaScaled: "550000",
      percent: 4.28,
    });
  });
  it("handles decimals and variable pay", () => {
    const result = previewPay({ ...base, baseMajor: "100.5", variableMajor: "0.25" });
    expect(result?.totalScaled).toBe("10075");
  });
  it("rejects bad input", () => {
    expect(previewPay({ ...base, baseMajor: "abc", variableMajor: "0" })).toBeNull();
    expect(previewPay({ ...base, baseMajor: "", variableMajor: "0" })).toBeNull();
    expect(previewPay({ ...base, baseMajor: "-5", variableMajor: "0" })).toBeNull();
  });
});

describe("helpers", () => {
  it("scaledToMajor", () => {
    expect(scaledToMajor("12850000", 2)).toBe("128500.00");
    expect(scaledToMajor("5", 2)).toBe("0.05");
    expect(scaledToMajor("7", 0)).toBe("7");
  });
  it("formatRate", () => {
    expect(formatRate("780000", 6, "GBP")).toBe("0.78 GBP per USD");
    expect(formatRate("83123456", 6, "INR")).toBe("83.123456 INR per USD");
  });
  it("currencySymbol", () => {
    expect(currencySymbol("GBP")).toBe("£");
    expect(currencySymbol("USD")).toBe("$");
  });
});
