const ALLOWED_WEBHOOKS = new Set(["asana", "clickup", "monday", "airtable"]);

function json(data, init = {}) {
  const headers = new Headers(init.headers || {});
  headers.set("content-type", "application/json; charset=utf-8");
  headers.set("cache-control", "no-store");
  return new Response(JSON.stringify(data), { ...init, headers });
}

function corsHeaders() {
  return {
    "access-control-allow-origin": "*",
    "access-control-allow-methods": "GET,POST,OPTIONS",
    "access-control-allow-headers": "authorization,content-type,x-hook-secret,x-hook-signature,x-signature"
  };
}

function requireEnv(env, key) {
  const value = env[key];
  if (!value) throw new Error(`Missing Worker secret/binding: ${key}`);
  return value;
}

async function forwardToGas(request, env, params = {}) {
  const origin = requireEnv(env, "GAS_ORIGIN_URL");
  const shared = requireEnv(env, "GATEWAY_SHARED_SECRET");
  const target = new URL(origin);
  target.searchParams.set("gateway", shared);
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") target.searchParams.set(key, String(value));
  }

  const method = request.method === "GET" ? "GET" : "POST";
  const init = {
    method,
    redirect: "follow",
    headers: { "content-type": request.headers.get("content-type") || "application/json" }
  };
  if (method !== "GET") init.body = await request.text();

  const response = await fetch(target.toString(), init);
  const text = await response.text();
  let parsed;
  try { parsed = JSON.parse(text); } catch { parsed = null; }
  if (!response.ok || (parsed && parsed.ok === false)) {
    throw new Error(`Apps Script origin rejected request: HTTP ${response.status} ${text.slice(0, 800)}`);
  }
  return new Response(text, {
    status: response.status,
    headers: { "content-type": response.headers.get("content-type") || "application/json", "cache-control": "no-store" }
  });
}

function authorizedControl(request, env) {
  const expected = env.CONTROL_TOKEN || "";
  const supplied = request.headers.get("authorization") || "";
  return expected && supplied === `Bearer ${expected}`;
}

async function handleWebhook(request, env, ctx, platform) {
  if (!ALLOWED_WEBHOOKS.has(platform)) return json({ ok: false, error: "UNKNOWN_PLATFORM" }, { status: 404 });

  if (platform === "asana") {
    const hookSecret = request.headers.get("x-hook-secret");
    if (hookSecret) {
      ctx.waitUntil((async () => {
        try {
          await forwardToGas(new Request(request.url, {
            method: "POST",
            headers: { "content-type": "application/json" },
            body: JSON.stringify({ event: "ASANA_HANDSHAKE" })
          }), env, { hook: "asana" });
        } catch (_) {}
      })());
      return new Response(null, {
        status: 200,
        headers: { "x-hook-secret": hookSecret, "cache-control": "no-store" }
      });
    }
  }

  if (platform === "monday") {
    const cloned = request.clone();
    try {
      const body = await cloned.json();
      if (body && body.challenge) return json({ challenge: body.challenge });
    } catch (_) {}
  }

  return forwardToGas(request, env, { hook: platform });
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: corsHeaders() });
    }

    if (request.method === "GET" && (url.pathname === "/" || url.pathname === "/health")) {
      return json({
        ok: true,
        service: "PT HONGLU BAJA INDONESIA - FABRIKASI INTEGRATION GATEWAY",
        version: "1.1.0",
        environment: env.ENVIRONMENT || "unknown",
        appsScriptConfigured: Boolean(env.GAS_ORIGIN_URL),
        timestamp: new Date().toISOString()
      }, { headers: corsHeaders() });
    }

    if (request.method === "GET" && url.pathname === "/origin-health") {
      if (!authorizedControl(request, env)) return json({ ok: false, error: "UNAUTHORIZED" }, { status: 401 });
      return forwardToGas(request, env, { action: "health" });
    }

    if (request.method === "POST" && url.pathname === "/control/process-queue") {
      if (!authorizedControl(request, env)) return json({ ok: false, error: "UNAUTHORIZED" }, { status: 401 });
      return forwardToGas(new Request(request.url, { method: "GET" }), env, { action: "processQueue" });
    }

    const match = url.pathname.match(/^\/hook\/(asana|clickup|monday|airtable)$/);
    if (request.method === "POST" && match) return handleWebhook(request, env, ctx, match[1]);

    return json({ ok: false, error: "NOT_FOUND" }, { status: 404, headers: corsHeaders() });
  },

  async scheduled(_controller, env, ctx) {
    if (String(env.ENABLE_SCHEDULED_SYNC || "false").toLowerCase() !== "true") return;
    ctx.waitUntil(forwardToGas(new Request("https://internal.invalid/queue", { method: "GET" }), env, { action: "processQueue" }));
  }
};
