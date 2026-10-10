const SCALED = /^-?\d+$/;

export function formatScaled(scaled: string, scale: number, currency?: string): string {
  if (!SCALED.test(scaled) || !Number.isInteger(scale) || scale < 0) {
    return scaled;
  }
  const value = Number(scaled) / 10 ** scale;
  return new Intl.NumberFormat("en-US", {
    style: currency ? "currency" : "decimal",
    currency,
    minimumFractionDigits: scale,
    maximumFractionDigits: scale,
  }).format(value);
}

// Half-even on the scaled integer, matching decimal_to_scaled.
export function majorToScaled(major: string, scale: number): string | null {
  if (!Number.isInteger(scale) || scale < 0) {
    return null;
  }
  const match = major.trim().match(/^(-?)(\d+)(?:\.(\d+))?$/);
  if (!match) {
    return null;
  }
  const negative = match[1] === "-";
  const whole = BigInt(match[2] ?? "0");
  const fraction = match[3] ?? "";
  let scaled = whole * BigInt(10) ** BigInt(scale);
  if (fraction.length <= scale) {
    scaled += BigInt(fraction.padEnd(scale, "0") || "0");
  } else {
    scaled += BigInt(fraction.slice(0, scale) || "0");
    const next = fraction[scale] ?? "0";
    const rest = fraction.slice(scale + 1);
    const half = next === "5" && !/[1-9]/.test(rest);
    const one = BigInt(1);
    if (next > "5" || (next === "5" && !half) || (half && scaled % BigInt(2) === one)) {
      scaled += one;
    }
  }
  if (negative && scaled !== BigInt(0)) {
    return `-${scaled.toString()}`;
  }
  return scaled.toString();
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

const CURRENCY_LOCALES: Record<string, string> = {
  INR: "en-IN",
  GBP: "en-GB",
  EUR: "en-IE",
  CAD: "en-CA",
  AUD: "en-AU",
};

const ZERO = BigInt(0);
const TEN = BigInt(10);

function splitScaled(scaled: string, scale: number): [boolean, bigint] | null {
  if (!SCALED.test(scaled) || !Number.isInteger(scale) || scale < 0) {
    return null;
  }
  const value = BigInt(scaled);
  return value < ZERO ? [true, -value] : [false, value];
}

export function formatLocalMoney(scaled: string, scale: number, currencyCode: string): string {
  const parts = splitScaled(scaled, scale);
  if (!parts) {
    return scaled;
  }
  const [negative, abs] = parts;
  const divisor = TEN ** BigInt(scale);
  const whole = abs / divisor;
  const fraction = scale === 0 ? "" : `.${(abs % divisor).toString().padStart(scale, "0")}`;
  const sign = negative ? "-" : "";
  let formatted: string;
  try {
    formatted = new Intl.NumberFormat(CURRENCY_LOCALES[currencyCode] ?? "en-US", {
      style: "currency",
      currency: currencyCode,
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(whole);
  } catch {
    return `${sign}${new Intl.NumberFormat("en-US").format(whole)}${fraction} ${currencyCode}`;
  }
  const digitsEnd = formatted.search(/\d(?!.*\d)/) + 1;
  return sign + formatted.slice(0, digitsEnd) + fraction + formatted.slice(digitsEnd);
}

export function formatUsd(scaled: string, scale = 2): string {
  return formatLocalMoney(scaled, scale, "USD");
}

function roundedQuotient(value: bigint, divisor: bigint, decimals: number): string {
  const factor = TEN ** BigInt(decimals);
  const quotient = (value * factor * BigInt(2) + divisor) / (divisor * BigInt(2));
  const whole = quotient / factor;
  const fraction = (quotient % factor).toString().padStart(decimals, "0").replace(/0+$/, "");
  return fraction === "" ? whole.toString() : `${whole}.${fraction}`;
}

const COMPACT_UNITS = [
  { size: BigInt(1_000_000_000), suffix: "B" },
  { size: BigInt(1_000_000), suffix: "M" },
  { size: BigInt(1_000), suffix: "k" },
];

export function formatCompactUsd(scaled: string, scale = 2): string {
  const parts = splitScaled(scaled, scale);
  if (!parts) {
    return scaled;
  }
  const [negative, abs] = parts;
  const divisor = TEN ** BigInt(scale);
  const sign = negative ? "-" : "";
  const dollars = abs / divisor;
  for (const { size, suffix } of COMPACT_UNITS) {
    if (dollars < size) {
      continue;
    }
    const decimals = suffix === "k" && dollars >= size * BigInt(100) ? 0 : suffix === "k" ? 1 : 2;
    const text = roundedQuotient(abs, size * divisor, decimals);
    if (text === "1000" && suffix !== "B") {
      const next = COMPACT_UNITS[COMPACT_UNITS.findIndex((unit) => unit.suffix === suffix) - 1];
      if (next) {
        return `${sign}$${roundedQuotient(abs, next.size * divisor, 2)}${next.suffix}`;
      }
    }
    return `${sign}$${text}${suffix}`;
  }
  return `${sign}$${roundedQuotient(abs, divisor, 0)}`;
}

export function formatPercent(percent: number, digits = 1, signed = false): string {
  if (!Number.isFinite(percent)) {
    return "";
  }
  return `${signed && percent > 0 ? "+" : ""}${percent.toFixed(digits)}%`;
}

export function pctChange(prevScaled: string, nextScaled: string): number | null {
  if (!SCALED.test(prevScaled) || !SCALED.test(nextScaled)) {
    return null;
  }
  const prev = BigInt(prevScaled);
  if (prev === ZERO) {
    return null;
  }
  const delta = (BigInt(nextScaled) - prev) * BigInt(10000);
  const divisor = prev < ZERO ? -prev : prev;
  const magnitude = delta < ZERO ? -delta : delta;
  const basisPoints = Number((magnitude * BigInt(2) + divisor) / (divisor * BigInt(2)));
  return (delta < ZERO !== prev < ZERO ? -basisPoints : basisPoints) / 100 + 0;
}

export function formatDate(iso: string): string {
  const match = iso.match(/^(\d{4})-(\d{2})-(\d{2})/);
  const month = match ? MONTHS[Number(match[2]) - 1] : undefined;
  if (!match || !month) {
    return iso;
  }
  return `${Number(match[3])} ${month} ${match[1]}`;
}

export function formatDateTime(iso: string): string {
  const match = iso.match(/^(\d{4}-\d{2}-\d{2})[T ](\d{2}):(\d{2})/);
  if (!match) {
    return formatDate(iso);
  }
  return `${formatDate(match[1] ?? iso)}, ${match[2]}:${match[3]} UTC`;
}

export function fullName(person: { first_name: string; last_name: string }): string {
  return `${person.first_name} ${person.last_name}`.trim();
}
