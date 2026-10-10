import { describe, expect, test } from "vitest";
import { pickClientIp } from "./client-ip";

function h(values: Record<string, string>): Headers {
  return new Headers(values);
}

describe("pickClientIp", () => {
  test("prefers x-real-ip", () => {
    expect(pickClientIp(h({ "x-real-ip": "203.0.113.9", "x-forwarded-for": "1.2.3.4" }))).toBe("203.0.113.9");
  });

  test("uses the last x-forwarded-for entry, ignoring a spoofed first one", () => {
    expect(pickClientIp(h({ "x-forwarded-for": "1.2.3.4, 198.51.100.7" }))).toBe("198.51.100.7");
  });

  test("single x-forwarded-for entry", () => {
    expect(pickClientIp(h({ "x-forwarded-for": "198.51.100.7" }))).toBe("198.51.100.7");
  });

  test("accepts IPv6", () => {
    expect(pickClientIp(h({ "x-real-ip": "2001:db8::1" }))).toBe("2001:db8::1");
    expect(pickClientIp(h({ "x-forwarded-for": "1.2.3.4, ::1" }))).toBe("::1");
  });

  test("rejects garbage", () => {
    expect(pickClientIp(h({ "x-real-ip": "not-an-ip" }))).toBeUndefined();
    expect(pickClientIp(h({ "x-forwarded-for": "1.2.3.4, evil host" }))).toBeUndefined();
    expect(pickClientIp(h({ "x-forwarded-for": "1.2.3.4, 999.1.1.1" }))).toBeUndefined();
    expect(pickClientIp(h({ "x-forwarded-for": "1.2.3.4," }))).toBeUndefined();
  });

  test("garbage x-real-ip falls back to x-forwarded-for", () => {
    expect(pickClientIp(h({ "x-real-ip": "junk", "x-forwarded-for": "198.51.100.7" }))).toBe("198.51.100.7");
  });

  test("missing headers", () => {
    expect(pickClientIp(h({}))).toBeUndefined();
  });
});
