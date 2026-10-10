// Run from web/: node --experimental-strip-types --test proxy-rules.test.ts
import assert from "node:assert/strict";
import { test } from "node:test";
import { decideProxy } from "./proxy-rules.ts";

const PROTECTED = [
  "/employees",
  "/employees/new",
  "/employees/7",
  "/employees/7/pay",
  "/employees/7/edit",
  "/history",
  "/planning-rates",
  "/settings/fx",
  "/anything-else",
];

test("root without token rewrites to login", () => {
  assert.deepEqual(decideProxy("/", false), { rewrite: "/login" });
});

test("root with token passes", () => {
  assert.equal(decideProxy("/", true), "next");
});

test("protected routes redirect to login without token", () => {
  for (const path of PROTECTED) assert.deepEqual(decideProxy(path, false), { redirect: "/login" }, path);
});

test("protected routes pass with token", () => {
  for (const path of PROTECTED) assert.equal(decideProxy(path, true), "next", path);
});

test("login is public without token and bounces home with token", () => {
  assert.equal(decideProxy("/login", false), "next");
  assert.deepEqual(decideProxy("/login", true), { redirect: "/" });
});

test("logout handler is always reachable", () => {
  assert.equal(decideProxy("/logout", false), "next");
  assert.equal(decideProxy("/logout", true), "next");
});
