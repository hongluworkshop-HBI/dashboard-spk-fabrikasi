import test from "node:test";
import assert from "node:assert/strict";
import worker from "../src/index.js";

const ctx = { waitUntil() {} };

test("health endpoint is safe without secrets", async () => {
  const response = await worker.fetch(new Request("https://example.com/health"), { ENVIRONMENT: "test" }, ctx);
  assert.equal(response.status, 200);
  const body = await response.json();
  assert.equal(body.ok, true);
  assert.equal(body.environment, "test");
  assert.equal(body.appsScriptConfigured, false);
});

test("unknown route is 404", async () => {
  const response = await worker.fetch(new Request("https://example.com/nope"), {}, ctx);
  assert.equal(response.status, 404);
});

test("control endpoint rejects missing bearer token", async () => {
  const response = await worker.fetch(new Request("https://example.com/control/process-queue", { method: "POST" }), { CONTROL_TOKEN: "secret" }, ctx);
  assert.equal(response.status, 401);
});
