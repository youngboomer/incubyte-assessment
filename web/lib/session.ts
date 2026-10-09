export const SESSION_COOKIE = "comppulse_session";

export const SESSION_MAX_AGE_SECONDS = 43200;

export const sessionCookieOptions = {
  httpOnly: true,
  sameSite: "lax" as const,
  path: "/",
  maxAge: SESSION_MAX_AGE_SECONDS,
};
