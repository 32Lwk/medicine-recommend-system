#!/usr/bin/env python3
"""Write R22 accuracy reaffirmation JSON from R21 measured artifacts + fixture SHAs."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
stamp = "20260923_174144"
fixtures = {
    "eval_10": "tests/fixtures/jev_intent_router_eval_10.yaml",
    "holdout_r17": "tests/fixtures/jev_intent_router_holdout_r17.yaml",
    "r21_paraphrase": "tests/fixtures/jev_holdout_r21/paraphrase.yaml",
    "r21_unicode": "tests/fixtures/jev_holdout_r21/unicode_evasion.yaml",
    "r21_persona": "tests/fixtures/jev_holdout_r21/persona.yaml",
    "r21_negative": "tests/fixtures/jev_holdout_r21/negative_control.yaml",
}


def sha16(rel: str) -> str:
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()[:16]


mapping = [
    ("eval10", "seed42", f"jev_r21_eval10_r10_seed42_{stamp}.json"),
    ("eval10", "seed20260922", f"jev_r21_eval10_r10_seed20260922_{stamp}.json"),
    ("holdout_r17", "seed42", f"jev_r21_holdout_r17_r10_seed42_{stamp}.json"),
    ("holdout_r17", "seed20260922", f"jev_r21_holdout_r17_r10_seed20260922_{stamp}.json"),
    ("holdout_para", "seed42", f"jev_r21_holdout_para_r10_seed42_{stamp}.json"),
    ("holdout_para", "seed20260922", f"jev_r21_holdout_para_r10_seed20260922_{stamp}.json"),
    ("holdout_unicode", "seed42", f"jev_r21_holdout_unicode_r10_seed42_{stamp}.json"),
    ("holdout_persona", "seed42", f"jev_r21_holdout_persona_r10_seed42_{stamp}.json"),
    ("holdout_neg", "seed42", f"jev_r21_holdout_neg_r10_seed42_{stamp}.json"),
]
rows = []
for pop, seed, name in mapping:
    d = json.loads((ROOT / "log/analysis" / name).read_text(encoding="utf-8"))
    s = (d.get("summaries") or [{}])[0]
    rows.append(
        {
            "population": pop,
            "seed": seed,
            "artifact": name,
            "accuracy_gate": f"{s.get('accuracy_gate_passed')}/{s.get('accuracy_gate_n')}",
            "accuracy_gate_pct": s.get("accuracy_gate_pct"),
            "membership_unknown": s.get("accuracy_gate_membership_unknown_n"),
            "api_error": s.get("api_error"),
            "fallback": s.get("fallback_count"),
            "mode": "jev_only",
            "evidence_class": "measured_reuse_r21",
        }
    )
out = {
    "program": "R22",
    "reuse_of": "R21 jev_only package",
    "r21_stamp": stamp,
    "application_sha": "f571480",
    "tooling_sha_note": "HEAD may advance; app not redeployed",
    "gold_retarget": False,
    "mode": (
        "jev:minimal only — OpenAI dual blocked (credit_balance_exhausted); "
        "see jev_r22_alt_dual_evaluator_20260924.json"
    ),
    "fixture_shas": {
        k: {"path": v, "sha256_16": sha16(v)} for k, v in fixtures.items()
    },
    "runs": rows,
    "rollup": {
        "all_accuracy_gate_100": all(r["accuracy_gate_pct"] == 100.0 for r in rows),
        "membership_unknown_total": sum(int(r["membership_unknown"] or 0) for r in rows),
        "api_error_total": sum(int(r["api_error"] or 0) for r in rows),
        "fallback_total": sum(int(r["fallback"] or 0) for r in rows),
    },
    "rationale": (
        "App code f571480..HEAD has no src/config delta; fixtures SHA-pinned and "
        "unchanged vs R21 report prefixes (eval_10=122f047cd2aaee1f, "
        "r17=209325dfe8680731). Fresh full r10 remasure deferred; R21 JSON reused "
        "as measured evidence with explicit fixture SHAs."
    ),
}
path = ROOT / "log/analysis/jev_r22_accuracy_reaffirmation_20260924.json"
path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(path)
print(json.dumps(out["rollup"], indent=2))
