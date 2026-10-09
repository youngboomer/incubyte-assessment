import { cookies } from "next/headers";
import { connection } from "next/server";
import { NextResponse } from "next/server";
import { backendFetch } from "../../../lib/api";
import { SESSION_COOKIE } from "../../../lib/session";

export const dynamic = "force-dynamic";

const SORTS = new Set([
  "name",
  "employee_number",
  "department",
  "country",
  "title",
  "base_salary",
  "salary_usd",
  "hire_date",
]);

const FILTERS = ["q", "department_id", "country", "currency", "status", "sort", "direction"] as const;

function redirectTo(location: string): NextResponse {
  return new NextResponse(null, {
    status: 307,
    headers: { location },
  });
}

export async function GET(request: Request): Promise<NextResponse> {
  await connection();
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!token) {
    return redirectTo("/login");
  }

  const incoming = new URL(request.url).searchParams;
  const filters = new URLSearchParams();
  for (const key of FILTERS) {
    const value = incoming.get(key)?.trim() ?? "";
    if (!value) {
      continue;
    }
    if (key === "sort" && !SORTS.has(value)) {
      continue;
    }
    if (key === "direction" && value !== "asc" && value !== "desc") {
      continue;
    }
    filters.set(key, value);
  }

  let response: Response;
  try {
    response = await backendFetch(`/employees/export.csv?${filters.toString()}`, token);
  } catch {
    return new NextResponse("Could not load employees.", { status: 502 });
  }

  if (response.status === 401) {
    return redirectTo("/logout");
  }
  if (!response.ok) {
    return new NextResponse(`Could not load employees. ${response.status}`, {
      status: response.status,
    });
  }

  const csv = await response.text();
  return new NextResponse(csv, {
    status: 200,
    headers: {
      "content-type": "text/csv",
      "content-disposition": 'attachment; filename="employees.csv"',
      "cache-control": "no-store",
    },
  });
}
