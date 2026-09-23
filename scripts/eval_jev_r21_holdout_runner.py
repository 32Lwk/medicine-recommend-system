#!/usr/bin/env python3
"""R21 Accuracy / Independent Holdout batch runner (Worker D).

Loads .env silently for JEV_API_KEY / OPENAI_API_KEY (never prints values).
Invokes scripts/eval_jev_intent_router_10.py — does not generate or edit gold.
Does not unify evaluator with fixture generator.
"""
from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_dotenv_silent() -> None:
    env_path = ROOT / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        key, _, value = s.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _run(label: str, args: list[str]) -> int:
    print(f"=== START {label} ===", flush=True)
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "eval_jev_intent_router_10.py"), *args],
        cwd=str(ROOT),
        env=os.environ.copy(),
    )
    print(f"=== END {label} rc={proc.returncode} ===", flush=True)
    return int(proc.returncode)


def main() -> int:
    _load_dotenv_silent()
    # Never persist production flags
    os.environ.setdefault("JEV_ENABLED", "0")
    os.environ.setdefault("JEV_INTENT_ROUTER_SHADOW", "0")
    os.environ.setdefault("JEV_INTENT_ROUTER_PRIMARY", "0")
    os.environ.setdefault("POLICY_ENFORCEMENT_D2", "0")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out = ROOT / "log" / "analysis"
    out.mkdir(parents=True, exist_ok=True)

    jev = bool(str(os.getenv("JEV_API_KEY") or "").strip())
    openai = bool(str(os.getenv("OPENAI_API_KEY") or "").strip())
    # Prefer dual backend when OpenAI works; else Jev-only for Gate accuracy.
    # Dual was observed to hit OpenAI credit_balance_exhausted (429) in R21 smoke.
    dual = os.getenv("JEV_R21_FORCE_DUAL", "").strip() in {"1", "true", "yes"}
    backends = "current,jev:minimal" if (dual and openai) else "jev:minimal"
    mode_note = "dual" if backends.startswith("current") else "jev_only"
    print(
        f"keys: JEV_API_KEY={'set' if jev else 'unset'} "
        f"OPENAI_API_KEY={'set' if openai else 'unset'} "
        f"backends={backends} mode={mode_note} stamp={stamp}",
        flush=True,
    )
    if not jev:
        print("BLOCKER: JEV_API_KEY missing — cannot measure Jev accuracy_gate", flush=True)
        return 2
    if mode_note == "jev_only":
        print(
            "NOTE: running jev:minimal only (OpenAI dual blocked or not forced). "
            "Latency CI vs current and current-path Critical/High FN are out-of-scope "
            "for this process; document as blocker in the report.",
            flush=True,
        )

    jobs: list[tuple[str, list[str]]] = []

    def add(
        label: str,
        fixture: str,
        seed: int,
        repeat: int,
        tag: str,
    ) -> None:
        base = f"jev_r21_{tag}_r{repeat}_seed{seed}_{stamp}"
        cli = [
            "--fixture",
            fixture,
            "--backends",
            backends,
            "--repeat",
            str(repeat),
            "--seed",
            str(seed),
            "--order",
            "seed_random",
            "--latency-mode",
            "warm",
            "--output-json",
            str(out / f"{base}.json"),
            "--output-md",
            str(out / f"{base}.md"),
        ]
        if mode_note == "jev_only":
            cli.append("--jev-only")
        jobs.append((label, cli))

    # Required: eval_10 r10 both seeds
    add("eval10_seed42", "tests/fixtures/jev_intent_router_eval_10.yaml", 42, 10, "eval10")
    add(
        "eval10_seed20260922",
        "tests/fixtures/jev_intent_router_eval_10.yaml",
        20260922,
        10,
        "eval10",
    )
    # Required: independent holdout r17 r10 both seeds
    add(
        "holdout_r17_seed42",
        "tests/fixtures/jev_intent_router_holdout_r17.yaml",
        42,
        10,
        "holdout_r17",
    )
    add(
        "holdout_r17_seed20260922",
        "tests/fixtures/jev_intent_router_holdout_r17.yaml",
        20260922,
        10,
        "holdout_r17",
    )
    # R21 holdout-only axes (r10 seed42 primary; second seed for paraphrase only)
    add(
        "para_seed42",
        "tests/fixtures/jev_holdout_r21/paraphrase.yaml",
        42,
        10,
        "holdout_para",
    )
    add(
        "unicode_seed42",
        "tests/fixtures/jev_holdout_r21/unicode_evasion.yaml",
        42,
        10,
        "holdout_unicode",
    )
    add(
        "persona_seed42",
        "tests/fixtures/jev_holdout_r21/persona.yaml",
        42,
        10,
        "holdout_persona",
    )
    add(
        "neg_seed42",
        "tests/fixtures/jev_holdout_r21/negative_control.yaml",
        42,
        10,
        "holdout_neg",
    )

    # Optional second-seed for new paraphrase holdout
    add(
        "para_seed20260922",
        "tests/fixtures/jev_holdout_r21/paraphrase.yaml",
        20260922,
        10,
        "holdout_para",
    )

    rc = 0
    for label, args in jobs:
        code = _run(label, args)
        if code != 0:
            rc = code
            print(f"WARN: {label} failed rc={code}; continuing", flush=True)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
