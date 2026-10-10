import { describe, expect, test } from "vitest";
import { describeFailure, failureFromResponse, networkFailure } from "./errors";

describe("failureFromResponse", () => {
  test("stale 409", () => {
    const failure = failureFromResponse(409, { detail: "Record was modified. Reload and try again." });
    expect(failure.code).toBe("stale");
    expect(describeFailure(failure)).toEqual({
      formError: "Someone else changed this record. Nothing was saved. Reload to see the latest.",
      fieldErrors: {},
      isStale: true,
    });
  });

  test("duplicate email 409", () => {
    const view = describeFailure(failureFromResponse(409, { detail: "Email already exists" }));
    expect(view.formError).toBe("This email is already used by another employee.");
    expect(view.isStale).toBe(false);
  });

  test("already in status 409", () => {
    const failure = failureFromResponse(409, { detail: "Employee is already terminated" });
    expect(failure.code).toBe("already_in_status");
    expect(failure.message).toBe("This employee is already terminated.");
  });

  test("422 field errors", () => {
    const failure = failureFromResponse(422, {
      detail: [
        { loc: ["body", "reason"], msg: "String should have at least 1 character", type: "string_too_short" },
        { loc: ["body", "email"], msg: "value is not a valid email address", type: "value_error" },
        { loc: ["body", "base_salary_scaled"], msg: "Input should be greater than or equal to 0", type: "greater_than_equal" },
      ],
    });
    const view = describeFailure(failure);
    expect(view.fieldErrors).toEqual({
      reason: "Enter a reason for this change.",
      email: "Enter a valid email address.",
      base_salary_scaled: "Pay cannot be negative.",
    });
    expect(view.formError).toBeNull();
    expect(view.isStale).toBe(false);
  });

  test("422 with string detail falls back to a form error", () => {
    const view = describeFailure(failureFromResponse(422, { detail: "invalid_salary_range: x" }));
    expect(view.formError).toBe("Check the values and try again.");
    expect(view.fieldErrors).toEqual({});
  });

  test("401, 404, 429, 5xx", () => {
    expect(failureFromResponse(401, null).message).toBe("Your session has expired. Sign in again.");
    expect(failureFromResponse(404, null).code).toBe("not_found");
    expect(failureFromResponse(429, { detail: "x" }).message).toBe(
      "Too many attempts. Try again in a few minutes.",
    );
    expect(failureFromResponse(503, null).message).toBe("Something went wrong. Try again.");
    expect(networkFailure()).toMatchObject({ ok: false, status: 0, code: "network" });
  });
});
