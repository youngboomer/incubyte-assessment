export const RATE_SCALE = 6;

export type RateFormState = {
  status: "idle" | "error" | "saved";
  code: string;
  value: string;
  message: string;
};

export const idleRateState: RateFormState = { status: "idle", code: "", value: "", message: "" };
