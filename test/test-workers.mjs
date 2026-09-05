#!/usr/bin/env node
// Security-boundary regression tests for the two production Cloudflare Workers.
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

async function importWorker(relativePath) {
  const source = await readFile(new URL(`../${relativePath}`, import.meta.url));
  return import(`data:text/javascript;base64,${source.toString("base64")}`);
}

const contact = (await importWorker("infra/contact-worker.js")).default;
const gate = (await importWorker("infra/gate-worker.js")).default;
const allowedOrigin = "https://dagric.com";

function contactEnv() {
  const writes = [];
  return {
    writes,
    env: {
      RATE_LIMIT: { limit: async () => ({ success: true }) },
      MAIL: {
        put: async (key, value, metadata) => writes.push({ key, value, metadata }),
      },
    },
  };
}

function contactRequest(body, headers = {}) {
  return new Request("https://contact.dagric.com/", {
    method: "POST",
    headers: {
      Origin: allowedOrigin,
      "Content-Type": "application/json",
      ...headers,
    },
    body: typeof body === "string" ? body : JSON.stringify(body),
  });
}

test("contact worker rejects an untrusted browser origin before storage", async () => {
  const { env, writes } = contactEnv();
  const response = await contact.fetch(contactRequest(
    { message: "This must never reach storage." },
    { Origin: "https://attacker.example", "Content-Type": "text/plain" },
  ), env);
  assert.equal(response.status, 403);
  assert.equal(response.headers.get("Access-Control-Allow-Origin"), null);
  assert.equal(writes.length, 0);
});

test("contact worker requires JSON and caps the real UTF-8 body size", async () => {
  const first = contactEnv();
  const wrongType = await contact.fetch(contactRequest(
    "message=This+is+not+JSON",
    { "Content-Type": "application/x-www-form-urlencoded" },
  ), first.env);
  assert.equal(wrongType.status, 415);
  assert.equal(first.writes.length, 0);

  const second = contactEnv();
  const oversized = await contact.fetch(contactRequest({ message: "😀".repeat(5000) }), second.env);
  assert.equal(oversized.status, 413);
  assert.equal(second.writes.length, 0);
});

test("contact worker normalizes topics and emits defensive response headers", async () => {
  const { env, writes } = contactEnv();
  const response = await contact.fetch(contactRequest({
    name: "Owner",
    email: "owner@example.com",
    topic: "../../billing",
    message: "A valid support message for the inbox.",
  }), env);
  assert.equal(response.status, 200);
  assert.equal(response.headers.get("Access-Control-Allow-Origin"), allowedOrigin);
  assert.equal(response.headers.get("Cache-Control"), "no-store");
  assert.equal(response.headers.get("X-Content-Type-Options"), "nosniff");
  assert.equal(writes.length, 1);
  assert.equal(JSON.parse(writes[0].value).topic, "general");
});

const session = "cs_test_12345678";
const machine = "a".repeat(64);

function paidGateEnv() {
  const kv = new Map();
  let objectReads = 0;
  return {
    get objectReads() { return objectReads; },
    env: {
      DISTRIBUTION_ENABLED: "true",
      STRIPE_KEY: "test-only-placeholder",
      RATE_LIMIT: { limit: async () => ({ success: true }) },
      LICENSE: {
        get: async (key) => kv.get(key) ?? null,
        put: async (key, value) => kv.set(key, value),
      },
      PRO: {
        get: async (name) => {
          objectReads += 1;
          return { body: name === "dagric-pro-assets.tar.gz" ? "asset" : "iso", size: 5 };
        },
        head: async () => ({ size: 5 }),
      },
    },
  };
}

test("gate distribution hold blocks before Stripe, KV, or R2", async () => {
  const state = paidGateEnv();
  delete state.env.DISTRIBUTION_ENABLED;
  const originalFetch = globalThis.fetch;
  let stripeCalls = 0;
  globalThis.fetch = async () => { stripeCalls += 1; throw new Error("must not run"); };
  try {
    const response = await gate.fetch(
      new Request(`https://dagric-gate.example/?session_id=${session}`),
      state.env,
    );
    assert.equal(response.status, 503);
    assert.equal(stripeCalls, 0);
    assert.equal(state.objectReads, 0);
    assert.equal(response.headers.get("Cache-Control"), "no-store");
  } finally {
    globalThis.fetch = originalFetch;
  }
});

async function withPaidStripe(run) {
  const originalFetch = globalThis.fetch;
  let calls = 0;
  globalThis.fetch = async () => {
    calls += 1;
    return Response.json({
      payment_status: "paid",
      line_items: { data: [{ price: { id: "price_1TwRxY6lZx4VOIr30Zvozvhb" } }] },
      payment_intent: { latest_charge: { refunded: false, amount_refunded: 0 } },
    });
  };
  try {
    await run(() => calls);
  } finally {
    globalThis.fetch = originalFetch;
  }
}

test("gate rejects unsupported methods before Stripe or storage work", async () => {
  const originalFetch = globalThis.fetch;
  let calls = 0;
  globalThis.fetch = async () => { calls += 1; throw new Error("must not run"); };
  try {
    const response = await gate.fetch(new Request(
      `https://download.dagric.com/?session_id=${session}`,
      { method: "POST" },
    ), {});
    assert.equal(response.status, 405);
    assert.equal(response.headers.get("Allow"), "GET, HEAD");
    assert.equal(response.headers.get("Cache-Control"), "no-store");
    assert.equal(calls, 0);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("gate accepts a private Authorization bearer for Pro assets", async () => {
  await withPaidStripe(async (stripeCalls) => {
    const state = paidGateEnv();
    const response = await gate.fetch(new Request(
      `https://download.dagric.com/assets?m=${machine}`,
      { headers: { Authorization: `Bearer ${session}` } },
    ), state.env);
    assert.equal(response.status, 200);
    assert.equal(response.headers.get("Content-Disposition"),
      'attachment; filename="dagric-pro-assets.tar.gz"');
    assert.equal(response.headers.get("X-Frame-Options"), "DENY");
    assert.equal(stripeCalls(), 1);
    assert.equal(state.objectReads, 1);
  });
});

test("gate rejects malformed byte ranges without reading the ISO", async () => {
  await withPaidStripe(async () => {
    const state = paidGateEnv();
    const response = await gate.fetch(new Request(
      `https://download.dagric.com/?session_id=${session}`,
      { headers: { Range: "bytes=9-2" } },
    ), state.env);
    assert.equal(response.status, 416);
    assert.equal(response.headers.get("Accept-Ranges"), "bytes");
    assert.equal(state.objectReads, 0);
  });
});
