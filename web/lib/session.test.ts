import { describe, expect, test } from "vitest";
import { clearedSessionCookieOptions, sessionCookieOptions } from "./session";

describe("session cookie options", () => {
  test("is httpOnly, lax, site-wide", () => {
    expect(sessionCookieOptions).toMatchObject({ httpOnly: true, sameSite: "lax", path: "/" });
  });

  test("secure flag follows NODE_ENV", () => {
    expect(sessionCookieOptions.secure).toBe(process.env.NODE_ENV === "production");
  });

  test("clearing differs only in maxAge so deletion matches the set cookie", () => {
    expect(clearedSessionCookieOptions).toEqual({ ...sessionCookieOptions, maxAge: 0 });
  });
});
