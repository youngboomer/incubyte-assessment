import assert from "node:assert/strict";
import { test } from "node:test";
import { formatScaled, majorToScaled } from "./format.ts";

test("major units become scaled digit strings", () => {
  assert.equal(majorToScaled("120000.50", 2), "12000050");
  assert.equal(majorToScaled("120000.5", 2), "12000050");
  assert.equal(majorToScaled("120000", 2), "12000000");
  assert.equal(majorToScaled("8000000", 0), "8000000");
  assert.equal(majorToScaled("1.225", 2), "122");
  assert.equal(majorToScaled("1.235", 2), "124");
  assert.equal(majorToScaled("1.5", 0), "2");
  assert.equal(majorToScaled("2.5", 0), "2");
  assert.equal(majorToScaled("-1.5", 0), "-2");
  assert.equal(majorToScaled("12.00x", 2), null);
});

test("display divides the scaled string", () => {
  assert.equal(formatScaled("12000050", 2, "USD"), "$120,000.50");
  assert.equal(formatScaled("8000000", 0, "JPY"), "¥8,000,000");
  assert.equal(formatScaled("99", 2), "0.99");
});
