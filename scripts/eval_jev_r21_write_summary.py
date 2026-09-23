#!/usr/bin/env python3
"""Write combined R21 accuracy summary JSON (no secrets)."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
stamp = "20260923_174144"
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
        }
    )
out = {
    "stamp": stamp,
    "mode": "jev:minimal only (OpenAI dual blocked by credit_balance_exhausted)",
    "runs": rows,
}
path = ROOT / "log/analysis/jev_r21_accuracy_summary_20260924.json"
path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(path)
