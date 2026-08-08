/**
 * Cloudflare Worker — aws-medicine.yutok.dev (single staging entry URL)
 * Wake on 503, proxy when healthy, rewrite legacy host in redirects.
 */
const LEGACY_HOST = "aws.medicine.yutok.dev";

const STARTING_HTML = `<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>ステージングを起動しています</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 32rem; margin: 4rem auto; padding: 0 1rem; color: #334; }
    h1 { font-size: 1.25rem; }
    p { line-height: 1.6; }
    .muted { color: #667; font-size: 0.9rem; }
  </style>
</head>
<body>
  <h1>AWS ステージングを起動しています</h1>
  <p>コスト削減のため停止中でした。タスクを起動しています（通常 <strong>3〜6 分</strong>）。</p>
  <p class="muted" id="status">起動完了を待っています…</p>
  <script>
    async function poll() {
      try {
        const r = await fetch("/health", { cache: "no-store" });
        if (r.ok) {
          const j = await r.json();
          if (j.status === "ok" || j.git_commit) {
            location.replace(location.pathname + location.search + location.hash);
            return;
          }
        }
      } catch (_) {}
      setTimeout(poll, 5000);
    }
    poll();
  </script>
</body>
</html>`;

function rewriteLegacyHost(value, publicOrigin) {
  if (!value) return value;
  return value
    .replaceAll("https://" + LEGACY_HOST, publicOrigin)
    .replaceAll("http://" + LEGACY_HOST, publicOrigin);
}

function touchActivity(env, ctx) {
  if (!env.WAKE_API_URL || !env.WAKE_TOKEN) return;
  ctx.waitUntil(
    fetch(env.WAKE_API_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Wake-Token": env.WAKE_TOKEN,
      },
      body: JSON.stringify({ action: "touch", source: "cloudflare-worker" }),
    }).catch(() => {})
  );
}

function wakeStaging(env, ctx, path) {
  if (!env.WAKE_API_URL || !env.WAKE_TOKEN) return;
  ctx.waitUntil(
    fetch(env.WAKE_API_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Wake-Token": env.WAKE_TOKEN,
      },
      body: JSON.stringify({ action: "wake", source: "cloudflare-worker", path }),
    }).catch(() => {})
  );
}

async function proxyResponse(originResp, publicOrigin) {
  const headers = new Headers(originResp.headers);
  const location = headers.get("Location");
  if (location) {
    headers.set("Location", rewriteLegacyHost(location, publicOrigin));
  }
  return new Response(originResp.body, {
    status: originResp.status,
    statusText: originResp.statusText,
    headers,
  });
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const publicOrigin = url.origin;
    const originBase = (env.ORIGIN_URL || "").replace(/\/$/, "");
    if (!originBase) {
      return new Response("ORIGIN_URL is not configured", { status: 500 });
    }

    const originUrl = `${originBase}${url.pathname}${url.search}`;
    const originHeaders = new Headers(request.headers);
    originHeaders.set("Host", new URL(originBase).host);

    const proxyInit = {
      method: request.method,
      headers: originHeaders,
      redirect: "manual",
    };
    if (request.method !== "GET" && request.method !== "HEAD") {
      proxyInit.body = request.body;
    }

    let originResp;
    try {
      originResp = await fetch(originUrl, proxyInit);
    } catch (_) {
      originResp = null;
    }

    if (originResp && originResp.status < 500) {
      touchActivity(env, ctx);
      if (originResp.status >= 300 && originResp.status < 400) {
        return proxyResponse(originResp, publicOrigin);
      }
      return proxyResponse(originResp, publicOrigin);
    }

    wakeStaging(env, ctx, url.pathname);

    if (url.pathname === "/health") {
      return new Response(
        JSON.stringify({ status: "starting", eta_seconds: 180 }),
        { status: 503, headers: { "Content-Type": "application/json" } }
      );
    }

    return new Response(STARTING_HTML, {
      status: 503,
      headers: { "Content-Type": "text/html; charset=utf-8" },
    });
  },
};
