import { isIP } from "node:net";

type HeaderSource = { get(name: string): string | null };

function validIp(value: string | null | undefined): string | undefined {
  const candidate = value?.trim();
  return candidate && isIP(candidate) !== 0 ? candidate : undefined;
}

export function pickClientIp(headers: HeaderSource): string | undefined {
  const real = validIp(headers.get("x-real-ip"));
  if (real) {
    return real;
  }
  const forwarded = headers.get("x-forwarded-for");
  if (!forwarded) {
    return undefined;
  }
  return validIp(forwarded.split(",").at(-1));
}
