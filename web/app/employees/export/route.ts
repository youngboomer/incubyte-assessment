import { cookies } from "next/headers";
import { connection, NextResponse } from "next/server";
import { exportEmployeesCsv } from "../../../lib/endpoints";
import { parseDirectoryFilters } from "../../../lib/query";
import { SESSION_COOKIE } from "../../../lib/session";

export const dynamic = "force-dynamic";

function redirectTo(location: string): NextResponse {
  return new NextResponse(null, { status: 307, headers: { location } });
}

export async function GET(request: Request): Promise<NextResponse> {
  await connection();
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!token) {
    return redirectTo("/login");
  }

  const params = Object.fromEntries(new URL(request.url).searchParams);
  const result = await exportEmployeesCsv(token, parseDirectoryFilters(params));

  if (!result.ok) {
    if (result.code === "unauthorized") {
      return redirectTo("/logout");
    }
    return new NextResponse("Could not export employees.", { status: result.status || 502 });
  }

  return new NextResponse(await result.data.text(), {
    status: 200,
    headers: {
      "content-type": "text/csv; charset=utf-8",
      "content-disposition": 'attachment; filename="employees.csv"',
      "cache-control": "no-store",
    },
  });
}
