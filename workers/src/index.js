/**
 * Cloudflare Worker — wake AWS staging on 503, then poll until ready.
 * Route: aws-medicine.yutok.dev/* (Proxied; Universal SSL covers 1-level subdomain)
 */
const STARTING_HTML = `<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="refresh" content="15">
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
  <p class="muted">このページは自動で更新されます。しばらくお待ちください。</p>
</body>
</html>`;

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const originBase = (env.ORIGIN_URL || "").replace(/\/$/, "");
    if (!originBase) {
      return new Response("ORIGIN_URL is not configured", { status: 500 });
    }

    const originUrl = `${originBase}${url.pathname}${url.search}`;
    const originHeaders = new Headers(request.headers);
    originHeaders.set("Host", new URL(originBase).host);

    let originResp;
    try {
      originResp = await fetch(originUrl, {
        method: request.method,
        headers: originHeaders,
        redirect: "follow",
      });
    } catch (_) {
      originResp = null;
    }

    if (originResp && originResp.status < 500) {
      return originResp;
    }

    if (env.WAKE_API_URL && env.WAKE_TOKEN) {
      ctx.waitUntil(
        fetch(env.WAKE_API_URL, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Wake-Token": env.WAKE_TOKEN,
          },
          body: JSON.stringify({ source: "cloudflare-worker", path: url.pathname }),
        }).catch(() => {})
      );
    }

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
