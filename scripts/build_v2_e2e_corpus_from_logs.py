#!/usr/bin/env python3
"""
ログから PR 用 E2E コーパス（既定 500 分岐）を生成する。

方針 C: ログ自動抽出 + クラスタ dedupe + 不足 bucket はテンプレ自動生成。

使い方:
  python scripts/build_v2_e2e_corpus_from_logs.py
  python scripts/build_v2_e2e_corpus_from_logs.py --total 500 --output tests/fixtures/v2_e2e_corpus_pr500.yaml
  python scripts/build_v2_e2e_corpus_from_logs.py --analysis-dirs log/analysis/downloaded-logs-20260729-20260806-20260806-141635

生成後の PR 実行:
  python scripts/local_v2_chat_test_runner.py --scenarios-path tests/fixtures/v2_e2e_corpus_pr500.yaml --report-suffix pr500
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.analysis.e2e_corpus_builder import (  # noqa: E402
    DEFAULT_BUCKET_QUOTAS,
    build_corpus_from_log_sources,
    write_corpus_yaml,
)


def _discover_analysis_dirs(extra: list[str]) -> list[Path]:
    dirs: list[Path] = []
    for raw in extra:
        p = Path(raw)
        if not p.is_absolute():
            p = PROJECT_ROOT / p
        if p.is_dir():
            dirs.append(p)
    if not dirs:
        analysis_root = PROJECT_ROOT / "log" / "analysis"
        if analysis_root.is_dir():
            for child in sorted(analysis_root.iterdir(), reverse=True):
                if child.is_dir() and (
                    (child / "user_sessions.json").exists()
                    or (child / "sections" / "user_sessions.json").exists()
                    or (child / "session_conversations.json").exists()
                ):
                    dirs.append(child)
                    if len(dirs) >= 5:
                        break
    return dirs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build PR E2E corpus from logs")
    parser.add_argument(
        "--counseling-path",
        type=Path,
        default=PROJECT_ROOT / "log" / "counseling_detail_log.jsonl",
    )
    parser.add_argument(
        "--analysis-dirs",
        nargs="*",
        default=[],
        help="GCP/AWS analyze 出力ディレクトリ（session 会話 JSON）",
    )
    parser.add_argument("--total", type=int, default=500)
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "tests" / "fixtures" / "v2_e2e_corpus_pr500.yaml",
    )
    parser.add_argument(
        "--stats-json",
        type=Path,
        default=None,
        help="構築統計 JSON（既定: log/analysis/YYYY-MM-DD_e2e_corpus_build.json）",
    )
    args = parser.parse_args(argv)

    analysis_dirs = _discover_analysis_dirs(list(args.analysis_dirs))
    scenarios, stats = build_corpus_from_log_sources(
        counseling_path=args.counseling_path.expanduser().resolve(),
        analysis_dirs=analysis_dirs,
        total=args.total,
        quotas=DEFAULT_BUCKET_QUOTAS,
    )

    out_path = args.output.expanduser()
    if not out_path.is_absolute():
        out_path = PROJECT_ROOT / out_path
    write_corpus_yaml(scenarios, out_path)

    stats_path = args.stats_json
    if stats_path is None:
        stats_path = PROJECT_ROOT / "log" / "analysis" / f"{date.today().isoformat()}_e2e_corpus_build.json"
    elif not stats_path.is_absolute():
        stats_path = PROJECT_ROOT / stats_path
    stats_path.parent.mkdir(parents=True, exist_ok=True)
    stats["output_yaml"] = str(out_path)
    stats["analysis_dirs"] = [str(p) for p in analysis_dirs]
    stats_path.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Wrote {len(scenarios)} scenarios -> {out_path}")
    print(f"Stats -> {stats_path}")
    print(f"  raw={stats.get('raw_scenarios')} deduped={stats.get('deduped_scenarios')}")
    print(f"  bucket_counts={stats.get('bucket_counts')}")
    print(f"  from_logs={stats.get('from_logs')} generated={stats.get('generated')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
