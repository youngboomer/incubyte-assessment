"use server";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { backendFetch } from "../../../lib/api";
import { majorToScaled } from "../../../lib/format";
import { SESSION_COOKIE } from "../../../lib/session";

export type RateFormState = {
  message: string;
};

const RATE_ERROR = "Enter a planning rate as a number.";
const MISSING_CURRENCY = "That currency was not found.";

export async function updateRateAction(
  code: string,
  _state: RateFormState,
  formData: FormData,
): Promise<RateFormState> {
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!token) {
    redirect("/login");
  }

  if (code === "") {
    return { message: MISSING_CURRENCY };
  }

  const raw = formData.get("rate");
  if (typeof raw !== "string") {
    return { message: RATE_ERROR };
  }
  // Planning rates are stored at scale 6.
  const unitsPerUsdScaled = majorToScaled(raw, 6);
  if (unitsPerUsdScaled === null) {
    return { message: RATE_ERROR };
  }

  let response: Response;
  try {
    response = await backendFetch(`/fx/${encodeURIComponent(code)}`, token, {
      method: "PATCH",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ units_per_usd_scaled: unitsPerUsdScaled }),
    });
  } catch (error) {
    return { message: saveError(error) };
  }

  if (response.status === 401) {
    redirect("/logout");
  }
  if (response.status === 404) {
    return { message: MISSING_CURRENCY };
  }
  if (response.status === 422) {
    return { message: RATE_ERROR };
  }
  if (!response.ok) {
    return { message: `Could not save the planning rate. ${response.status}` };
  }

  redirect("/settings/fx");
}

function saveError(error: unknown): string {
  if (error instanceof Error && error.message === "BACKEND_URL is not set") {
    return "BACKEND_URL is not set";
  }
  return "Could not save the planning rate.";
}
