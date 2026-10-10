import { pctChange } from "../../../../lib/format";

const ZERO = BigInt(0);
const ONE = BigInt(1);
const TWO = BigInt(2);
const TEN = BigInt(10);

export type PreviewInput = {
  baseMajor: string;
  variableMajor: string;
  scale: number;
  currentTotalScaled: string;
  rateScaled: string;
  rateScale: number;
  usdScale: number;
};

export type Preview = {
  totalScaled: string;
  usdScaled: string;
  deltaScaled: string;
  percent: number | null;
};

const AMOUNT = /^(\d+)(?:\.(\d*))?$/;

function amountToScaled(major: string, scale: number): bigint | null {
  const match = major.trim().match(AMOUNT);
  if (!match) {
    return null;
  }
  const fraction = (match[2] ?? "").slice(0, scale).padEnd(scale, "0");
  return BigInt(match[1] ?? "0") * TEN ** BigInt(scale) + BigInt(fraction || "0");
}

function divideHalfEven(numerator: bigint, denominator: bigint): bigint {
  const quotient = numerator / denominator;
  const twice = (numerator % denominator) * TWO;
  if (twice > denominator || (twice === denominator && quotient % TWO === ONE)) {
    return quotient + ONE;
  }
  return quotient;
}

export function previewPay(input: PreviewInput): Preview | null {
  const base = amountToScaled(input.baseMajor, input.scale);
  const variable = amountToScaled(input.variableMajor, input.scale);
  if (base === null || variable === null || !/^\d+$/.test(input.rateScaled)) {
    return null;
  }
  const rate = BigInt(input.rateScaled);
  if (rate === ZERO) {
    return null;
  }
  const total = base + variable;
  const usd = divideHalfEven(
    total * TEN ** BigInt(input.usdScale + input.rateScale),
    rate * TEN ** BigInt(input.scale),
  );
  return {
    totalScaled: total.toString(),
    usdScaled: usd.toString(),
    deltaScaled: (total - BigInt(input.currentTotalScaled)).toString(),
    percent: pctChange(input.currentTotalScaled, total.toString()),
  };
}

export function scaledToMajor(scaled: string, scale: number): string {
  if (!/^-?\d+$/.test(scaled)) {
    return scaled;
  }
  const value = BigInt(scaled);
  const abs = value < ZERO ? -value : value;
  const divisor = TEN ** BigInt(scale);
  const fraction = scale === 0 ? "" : `.${(abs % divisor).toString().padStart(scale, "0")}`;
  return `${value < ZERO ? "-" : ""}${(abs / divisor).toString()}${fraction}`;
}

export function sumScaled(a: string, b: string): string {
  return (BigInt(a) + BigInt(b)).toString();
}

export function formatRate(unitsPerUsdScaled: string, rateScale: number, currencyCode: string): string {
  const major = scaledToMajor(unitsPerUsdScaled, rateScale);
  const [whole = "0", fraction = ""] = major.split(".");
  const trimmed = fraction.replace(/0+$/, "").padEnd(2, "0");
  return `${whole}.${trimmed} ${currencyCode} per USD`;
}

export function currencySymbol(currencyCode: string): string {
  try {
    const parts = new Intl.NumberFormat("en", {
      style: "currency",
      currency: currencyCode,
      currencyDisplay: "narrowSymbol",
    }).formatToParts(0);
    return parts.find((part) => part.type === "currency")?.value ?? currencyCode;
  } catch {
    return currencyCode;
  }
}
