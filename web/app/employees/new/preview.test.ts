import { describe, expect, it } from "vitest";
import { previewTotal } from "./preview";

const gbp = { code: "GBP", minorScale: 2, unitsPerUsdScaled: "780000", unitsPerUsdScale: 6 };

describe("previewTotal", () => {
  it("adds base and variable and converts without floats", () => {
    expect(previewTotal("120000", "14000", gbp)).toEqual({
      local: "£134,000.00",
      usd: "$171,794.87",
    });
  });
  it("treats empty variable as zero and rejects bad input", () => {
    expect(previewTotal("100", "", gbp)?.local).toBe("£100.00");
    expect(previewTotal("", "", gbp)).toBeNull();
    expect(previewTotal("abc", "", gbp)).toBeNull();
    expect(previewTotal("-5", "", gbp)).toBeNull();
  });
});
