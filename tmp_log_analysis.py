import json
import re
import ast
from collections import defaultdict

path = r"c:\Users\yutok\Downloads\downloaded-logs-20260613-060308.json"
with open(path, "r", encoding="utf-8") as f:
    logs = json.load(f)

perf = []
job_lock = []
db_issues = []
post_starts = []
line_sessions = []
moderation = []
triage = []
budget = []
waiting = []

for entry in logs:
    tp = entry.get("textPayload", "")
    ts = entry.get("timestamp", "")

    if "PIPELINE_PERF" in tp:
        m = re.search(r"PIPELINE_PERF (\{.*\})", tp)
        if m:
            try:
                d = ast.literal_eval(m.group(1))
                d["log_ts"] = ts
                perf.append(d)
            except Exception:
                pass

    if "POST処理開始" in tp:
        post_starts.append((ts, tp))
    if any(
        x in tp
        for x in [
            "job lock",
            "LineJobLock",
            "Skipping duplicate",
            "waiting for",
            "acquire",
            "inflight",
        ]
    ):
        job_lock.append((ts, tp[:350]))
    if any(
        x in tp.lower()
        for x in [
            "neon",
            "database",
            "connection",
            "psycopg",
            "sqlalchemy",
            "get_session_from_db",
            "persist_session",
            "db reconnect",
            "operationalerror",
            "timeout",
        ]
    ):
        db_issues.append((ts, tp[:300]))
    if "LINE text message" in tp:
        line_sessions.append((ts, tp[:200]))
    if "ModerationAgent" in tp or "security_validator" in tp or "run_safety_gate" in tp:
        moderation.append((ts, tp[:250]))
    if "TriageAgent" in tp or "llm_triage" in tp:
        triage.append((ts, tp[:250]))
    if "budget" in tp.lower():
        budget.append((ts, tp[:250]))

print("=== PIPELINE_PERF Summary ===")
for ch in ["web", "line"]:
    items = [p for p in perf if p.get("channel") == ch]
    if not items:
        continue
    totals = sorted(p["total_ms"] for p in items)
    print(f"\n{ch.upper()}: count={len(items)}")
    print(
        f"  total_ms: min={totals[0]:.1f} max={totals[-1]:.1f} "
        f"median={totals[len(totals)//2]:.1f} avg={sum(totals)/len(totals):.1f}"
    )
    gaps = []
    tri_gaps = []
    for p in items:
        b = p.get("breakdown", {})
        if "before_security" in b and "after_security" in b:
            gaps.append(b["after_security"] - b["before_security"])
        if "after_security" in b and "before_triage" in b:
            tri_gaps.append(b["before_triage"] - b["after_security"])
    if gaps:
        print(
            f"  security_phase_ms: min={min(gaps):.1f} max={max(gaps):.1f} "
            f"avg={sum(gaps)/len(gaps):.1f} (n={len(gaps)})"
        )
    if tri_gaps:
        print(
            f"  triage_wait_after_security_ms: min={min(tri_gaps):.1f} max={max(tri_gaps):.1f} "
            f"avg={sum(tri_gaps)/len(tri_gaps):.1f}"
        )

print("\n=== All PIPELINE_PERF (chronological) ===")
for p in sorted(perf, key=lambda x: x.get("log_ts", "")):
    b = p.get("breakdown", {})
    extra = ""
    if "before_security" in b and "after_security" in b:
        extra += f" sec={b['after_security']-b['before_security']:.0f}ms"
    if "before_triage" in b and "after_security" in b:
        extra += f" tri_wait={b['before_triage']-b['after_security']:.0f}ms"
    lts = p.get("log_ts", "")[:19]
    print(
        f"{lts} {p['channel']:4s} total={p['total_ms']:9.1f}ms{extra} "
        f"keys={list(b.keys())}"
    )

print(f"\n=== POST starts: {len(post_starts)} ===")
print(f"=== Job lock: {len(job_lock)} ===")
for ts, tp in job_lock[:25]:
    print(f"  {ts[:19]} {tp}")

print(f"\n=== DB issues: {len(db_issues)} (first 40) ===")
for ts, tp in db_issues[:40]:
    print(f"  {ts[:19]} {tp}")

# Correlate slow LINE request around 19:16-19:18
print("\n=== Timeline around slow LINE (2026-06-12 19:16-19:19 UTC) ===")
for entry in logs:
    ts = entry.get("timestamp", "")
    if not ts.startswith("2026-06-12T19:1"):
        continue
    tp = entry.get("textPayload", "")
    if not tp:
        continue
    keywords = [
        "PIPELINE_PERF",
        "POST処理",
        "security",
        "TriageAgent",
        "ModerationAgent",
        "budget",
        "LINE text",
        "loading",
        "job",
        "lock",
        "duplicate",
        "database",
        "neon",
        "connection",
        "timeout",
        "agent_step",
        "llm_triage",
    ]
    if any(k.lower() in tp.lower() for k in keywords):
        print(f"  {ts[:23]} {tp[:220]}")

# HTTP request latencies for / and POST
print("\n=== HTTP POST / chat latencies ===")
chat_lat = []
for entry in logs:
    hr = entry.get("httpRequest", {})
    url = hr.get("requestUrl", "")
    method = hr.get("requestMethod", "")
    if method == "POST" and ("/" == url.split(".run.app")[-1] or url.endswith(".run.app/")):
        lat = hr.get("latency", "")
        if lat:
            chat_lat.append(float(lat.replace("s", "")))
if chat_lat:
    print(f"  count={len(chat_lat)} min={min(chat_lat):.2f}s max={max(chat_lat):.2f}s avg={sum(chat_lat)/len(chat_lat):.2f}s")

print("\n=== LINE webhook POST latencies ===")
wh_lat = []
for entry in logs:
    hr = entry.get("httpRequest", {})
    url = hr.get("requestUrl", "")
    if hr.get("requestMethod") == "POST" and "/line/webhook" in url:
        lat = hr.get("latency", "")
        if lat:
            wh_lat.append(float(lat.replace("s", "")))
if wh_lat:
    print(f"  count={len(wh_lat)} min={min(wh_lat):.3f}s max={max(wh_lat):.3f}s avg={sum(wh_lat)/len(wh_lat):.3f}s")
