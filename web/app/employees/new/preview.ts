import { formatLocalMoney, formatUsd, majorToScaled } from "../../../lib/format";

const ZERO = BigInt(0);
const ONE = BigInt(1);
const TWO = BigInt(2);
const TEN = BigInt(10);
const USD_SCALE = 2;

export type PayPreview = { local: string; usd: string };

export type PreviewRate = {
  code: string;
  minorScale: number;
  unitsPerUsdScaled: string;
  unitsPerUsdScale: number;
};

function divideHalfEven(numerator: bigint, divisor: bigint): bigint {
  const quotient = numerator / divisor;
  const twiceRemainder = (numerator % divisor) * TWO;
  if (twiceRemainder > divisor || (twiceRemainder === divisor && quotient % TWO === ONE)) {
    return quotient + ONE;
  }
  return quotient;
}

function amount(text: string, scale: number): bigint | null {
  const cleaned = text.replace(/,/g, "").trim();
  const scaled = majorToScaled(cleaned === "" ? "0" : cleaned, scale);
  if (scaled === null || scaled.startsWith("-")) {
    return null;
  }
  return BigInt(scaled);
}

export function previewTotal(base: string, variable: string, rate: PreviewRate): PayPreview | null {
  const baseScaled = amount(base, rate.minorScale);
  const variableScaled = amount(variable, rate.minorScale);
  if (baseScaled === null || variableScaled === null || base.trim() === "") {
    return null;
  }
  if (!/^\d+$/.test(rate.unitsPerUsdScaled) || BigInt(rate.unitsPerUsdScaled) === ZERO) {
    return null;
  }
  const total = baseScaled + variableScaled;
  const numerator = total * TEN ** BigInt(rate.unitsPerUsdScale + USD_SCALE);
  const divisor = TEN ** BigInt(rate.minorScale) * BigInt(rate.unitsPerUsdScaled);
  const usd = divideHalfEven(numerator, divisor);
  return {
    local: formatLocalMoney(total.toString(), rate.minorScale, rate.code),
    usd: formatUsd(usd.toString(), USD_SCALE),
  };
}
