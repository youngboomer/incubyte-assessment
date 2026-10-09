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
