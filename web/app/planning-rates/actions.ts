"use server";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { revalidatePath } from "next/cache";
import { describeFailure } from "../../lib/errors";
import { updateRate } from "../../lib/endpoints";
import { majorToScaled } from "../../lib/format";
import { SESSION_COOKIE } from "../../lib/session";
import { RATE_SCALE, type RateFormState } from "./rate-state";

const NOT_POSITIVE = "Rate must be greater than zero.";
const NOT_A_NUMBER = "Enter the rate as a number, for example 83.5.";

export async function saveRateAction(
  _previous: RateFormState,
  formData: FormData,
): Promise<RateFormState> {
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!token) redirect("/login");

  const code = String(formData.get("code") ?? "");
  const value = String(formData.get("rate") ?? "").trim();
  const failed = (message: string): RateFormState => ({ status: "error", code, value, message });

  const scaled = majorToScaled(value, RATE_SCALE);
  if (scaled === null) return failed(NOT_A_NUMBER);
  if (BigInt(scaled) <= BigInt(0)) return failed(NOT_POSITIVE);

  const result = await updateRate(token, code, { units_per_usd_scaled: scaled });
  if (!result.ok) {
    if (result.code === "unauthorized") redirect("/logout");
    const view = describeFailure(result);
    return failed(view.fieldErrors["units_per_usd_scaled"] ?? view.formError ?? NOT_A_NUMBER);
  }

  revalidatePath("/planning-rates");
  return {
    status: "saved",
    code,
    value: "",
    message: `Rate saved. US dollar figures for ${code} people were recalculated.`,
  };
}
