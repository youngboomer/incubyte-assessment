import { beforeEach, describe, expect, test, vi } from "vitest";

const backendFetch = vi.hoisted(() =>
  vi.fn<(path: string, token?: string, init?: RequestInit) => Promise<Response>>(),
);

vi.mock("./api", () => ({ backendFetch }));

import * as endpoints from "./endpoints";

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

beforeEach(() => {
  backendFetch.mockReset();
});

describe("requests", () => {
  test("listEmployees builds the query and passes the token", async () => {
    backendFetch.mockResolvedValue(json({ items: [], next_cursor: null, prev_cursor: null, total: 0 }));
    const result = await endpoints.listEmployees("tok", { q: "ada", level: "IC3", status: "active" });
    expect(result.ok).toBe(true);
    expect(backendFetch).toHaveBeenCalledWith(
      "/employees?q=ada&status=active&level=IC3",
      "tok",
      { method: "GET" },
    );
  });

  test("exportEmployeesCsv drops cursor and limit and returns the response", async () => {
    backendFetch.mockResolvedValue(new Response("a,b\n", { status: 200 }));
    const result = await endpoints.exportEmployeesCsv("tok", { q: "x", cursor: "c", limit: 5 });
    expect(backendFetch.mock.calls[0]?.[0]).toBe("/employees/export.csv?q=x");
    expect(result.ok && (await result.data.text())).toBe("a,b\n");
  });

  test("changePay sends a JSON body to the compensation route", async () => {
    backendFetch.mockResolvedValue(json({ id: "e1", version_id: 2 }));
    const body = {
      base_salary_scaled: "100",
      variable_pay_scaled: "0",
      reason: "Review",
      effective_date: "2026-04-01",
      version_id: 1,
    };
    await endpoints.changePay("tok", "e 1", body);
    const [path, token, init] = backendFetch.mock.calls[0] ?? [];
    expect(path).toBe("/employees/e%201/compensation");
    expect(token).toBe("tok");
    expect(init?.method).toBe("PATCH");
    expect(JSON.parse(String(init?.body))).toEqual(body);
  });

  test.each([
    ["changeStatus", () => endpoints.changeStatus("t", "e1", { status: "active", reason: "r", effective_date: "2026-01-01", version_id: 1 }), "/employees/e1/status", "POST"],
    ["updateRate", () => endpoints.updateRate("t", "INR", { units_per_usd_scaled: "84000000" }), "/fx/INR", "PATCH"],
    ["listEmployeeChanges", () => endpoints.listEmployeeChanges("t", "e1"), "/employees/e1/changes", "GET"],
    ["listEmployeeAudit", () => endpoints.listEmployeeAudit("t", "e1"), "/employees/e1/audit", "GET"],
    ["getOverview", () => endpoints.getOverview("t", { level: "M1" }), "/analytics/overview?level=M1", "GET"],
    ["getAuditFeed", () => endpoints.getAuditFeed("t", { since: "2026-01-01" }, "cur"), "/audit?since=2026-01-01&cursor=cur", "GET"],
    ["listRates", () => endpoints.listRates("t"), "/fx", "GET"],
    ["reference", () => endpoints.reference("t"), "/reference", "GET"],
    ["me", () => endpoints.me("t"), "/auth/me", "GET"],
    ["getEmployee", () => endpoints.getEmployee("t", "e1"), "/employees/e1", "GET"],
  ])("%s hits the right route", async (_name, run, path, method) => {
    backendFetch.mockResolvedValue(json({}));
    await run();
    expect(backendFetch.mock.calls[0]?.[0]).toBe(path);
    expect(backendFetch.mock.calls[0]?.[2]?.method).toBe(method);
  });
});

describe("failures do not throw", () => {
  test("409 stale", async () => {
    backendFetch.mockResolvedValue(json({ detail: "Record was modified. Reload and try again." }, 409));
    const result = await endpoints.updateEmployee("t", "e1", {
      job_title: "x",
      reason: "r",
      effective_date: "2026-01-01",
      version_id: 1,
    });
    expect(result).toMatchObject({ ok: false, status: 409, code: "stale" });
  });

  test("422 keeps the issues", async () => {
    backendFetch.mockResolvedValue(
      json({ detail: [{ loc: ["body", "email"], msg: "bad", type: "value_error" }] }, 422),
    );
    const result = await endpoints.createEmployee("t", {} as never);
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.issues).toHaveLength(1);
    }
  });

  test("network error", async () => {
    backendFetch.mockRejectedValue(new TypeError("fetch failed"));
    expect(await endpoints.me("t")).toMatchObject({ ok: false, code: "network" });
  });

  test("login 401 says credentials are wrong", async () => {
    backendFetch.mockResolvedValue(json({ detail: "Invalid credentials" }, 401));
    const result = await endpoints.login({ email: "a", password: "b" });
    expect(result).toMatchObject({ ok: false, message: "Email or password is incorrect." });
    expect(backendFetch.mock.calls[0]?.[1]).toBeUndefined();
  });

  test("non-JSON success body is a failure", async () => {
    backendFetch.mockResolvedValue(new Response("oops", { status: 200 }));
    expect(await endpoints.me("t")).toMatchObject({ ok: false, code: "server" });
  });
});
