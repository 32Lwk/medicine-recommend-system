#!/usr/bin/env python3
"""CodeBuild post-deploy: classify changed paths for conditional sync.

When changed files cannot be determined reliably, callers must treat every
sync step as required (full fallback — no accuracy trade-off).
"""
from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Iterable, Sequence

# Paths that require static/ → S3 + CloudFront invalidation.
STATIC_PREFIXES = ("static/",)
STATIC_SCRIPTS = ("scripts/sync-static-to-s3.sh",)

# Paths that require Concierge / Medicine KB sync + optional ingestion.
KB_PREFIXES = (
    "data/",
    "docs/concierge/",
    "docs/public/",
)
KB_FILES = (
    "CHANGELOG.md",
    "docs/ops/AWS_FEATURES_ROLLOUT.md",
    "docs/ops/AWS_INFRA.md",
    "docs/ops/AWS_CODEPIPELINE.md",
    "docs/ops/CLOUDFLARE_R2_IMAGES.md",
    "docs/ops/AWS_BEDROCK_KB.md",
)
KB_SCRIPTS = (
    "scripts/build_medicine_kb_documents.py",
    "scripts/build_local_rag_index.py",
    "scripts/run_local_rag_eval.sh",
    "scripts/write_changelog_digest.py",
    "scripts/sync-concierge-kb-to-s3.sh",
    "scripts/sync-medicine-kb-to-s3.sh",
    "scripts/sync-all-kb-to-s3.sh",
)

LOCAL_RAG_PREFIXES = (
    "src/services/local_rag",
    "config/local_rag_config.py",
)
LOCAL_RAG_FILES = (
    "scripts/build_local_rag_index.py",
    "scripts/run_local_rag_eval.sh",
    "scripts/eval_local_rag_e2e.py",
    "scripts/local_rag_retrieve_benchmark.py",
    "scripts/compare_rag_eval.py",
    "scripts/report_local_rag_cost.py",
    "tests/fixtures/medicine_kb_eval.yaml",
    "tests/fixtures/concierge_kb_eval.yaml",
    "tests/fixtures/concierge_kb_paraphrase.yaml",
    "tests/fixtures/concierge_kb_technical_deep.yaml",
    "tests/fixtures/concierge_kb_context.yaml",
    "tests/fixtures/concierge_kb_app_overview.yaml",
    "tests/fixtures/concierge_kb_legal_meta.yaml",
    "tests/fixtures/concierge_intent_routing.yaml",
    "tests/fixtures/concierge_technical_quality.yaml",
    "tests/fixtures/concierge_boundary.yaml",
    "tests/fixtures/concierge_line_smoke.yaml",
    "tests/fixtures/local_rag_e2e.yaml",
    "tests/services/test_local_rag_router.py",
)


@dataclass(frozen=True)
class DeployPlan:
    changed_files: tuple[str, ...] | None
    needs_static_sync: bool
    needs_kb_sync: bool
    detection: str

    def as_env(self) -> dict[str, str]:
        reliable = self.changed_files is not None
        return {
            "DEPLOY_CHANGED_FILES_KNOWN": "true" if reliable else "false",
            "DEPLOY_DETECTION": self.detection,
            "DEPLOY_NEEDS_STATIC_SYNC": "true" if self.needs_static_sync else "false",
            "DEPLOY_NEEDS_KB_SYNC": "true" if self.needs_kb_sync else "false",
            "DEPLOY_CHANGED_FILE_COUNT": str(len(self.changed_files or ())),
        }


def _normalize_path(path: str) -> str:
    return path.replace("\\", "/").lstrip("./")


def _matches_any(path: str, prefixes: Sequence[str], files: Sequence[str]) -> bool:
    norm = _normalize_path(path)
    if norm in files:
        return True
    return any(norm.startswith(prefix) for prefix in prefixes)


def classify_changed_files(changed_files: Iterable[str]) -> DeployPlan:
    files = tuple(sorted({_normalize_path(p) for p in changed_files if p.strip()}))
    needs_static = any(
        _matches_any(p, STATIC_PREFIXES, STATIC_SCRIPTS) for p in files
    )
    needs_kb = any(
        _matches_any(p, KB_PREFIXES, KB_FILES + KB_SCRIPTS)
        or _matches_any(p, LOCAL_RAG_PREFIXES, LOCAL_RAG_FILES)
        for p in files
    )
    return DeployPlan(
        changed_files=files,
        needs_static_sync=needs_static,
        needs_kb_sync=needs_kb,
        detection="git_or_api",
    )


def full_sync_plan(detection: str) -> DeployPlan:
    return DeployPlan(
        changed_files=None,
        needs_static_sync=True,
        needs_kb_sync=True,
        detection=detection,
    )


def _run_git(args: list[str], cwd: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def changed_files_git_diff(repo_root: str, base: str, head: str) -> tuple[str, ...] | None:
    proc = _run_git(["diff", "--name-only", f"{base}..{head}"], repo_root)
    if proc.returncode != 0:
        return None
    lines = [ln.strip() for ln in proc.stdout.splitlines() if ln.strip()]
    return tuple(lines)


def changed_files_git_head_parent(repo_root: str) -> tuple[str, ...] | None:
    parent = _run_git(["rev-parse", "HEAD~1"], repo_root)
    if parent.returncode != 0 or not parent.stdout.strip():
        return None
    return changed_files_git_diff(repo_root, parent.stdout.strip(), "HEAD")


def _github_compare(
    repo: str,
    base: str,
    head: str,
    token: str | None,
) -> tuple[str, ...] | None:
    url = f"https://api.github.com/repos/{repo}/compare/{base}...{head}"
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "medicine-recommend-codebuild",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.load(resp)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return None
    files = payload.get("files") or []
    names = []
    for item in files:
        if isinstance(item, dict):
            name = item.get("filename") or item.get("previous_filename")
            if name:
                names.append(str(name))
    return tuple(names) if names or payload.get("status") == "identical" else None


def previous_pipeline_commit(
    pipeline_name: str,
    current_commit: str,
    region: str,
) -> str | None:
    proc = subprocess.run(
        [
            "aws",
            "codepipeline",
            "list-pipeline-executions",
            "--pipeline-name",
            pipeline_name,
            "--max-items",
            "15",
            "--region",
            region,
            "--output",
            "json",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return None
    try:
        summaries = json.loads(proc.stdout).get("pipelineExecutionSummaries") or []
    except json.JSONDecodeError:
        return None
    current = current_commit.lower()
    for item in summaries:
        if item.get("status") != "Succeeded":
            continue
        revisions = item.get("sourceRevisions") or []
        for rev in revisions:
            commit = (rev.get("revisionId") or "").strip()
            if commit and commit.lower() != current:
                return commit
    return None


def resolve_changed_files(repo_root: str) -> DeployPlan:
    force_full = os.environ.get("DEPLOY_FORCE_FULL_SYNC", "").lower() in {
        "1",
        "true",
        "yes",
    }
    if force_full:
        return full_sync_plan("forced_full")

    current = (
        os.environ.get("CODEBUILD_RESOLVED_SOURCE_VERSION")
        or os.environ.get("GIT_COMMIT")
        or ""
    ).strip()
    repo = os.environ.get("GITHUB_REPO", "32Lwk/medicine-recommend-system").strip()
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    region = os.environ.get("AWS_DEFAULT_REGION", "ap-northeast-1")
    pipeline = os.environ.get("PIPELINE_NAME", "medicine-recommend-main")

    git_dir = os.path.join(repo_root, ".git")
    if os.path.isdir(git_dir):
        parent_files = changed_files_git_head_parent(repo_root)
        if parent_files is not None:
            return classify_changed_files(parent_files)

        if current:
            parent_rev = _run_git(["rev-parse", f"{current}~1"], repo_root)
            if parent_rev.returncode == 0 and parent_rev.stdout.strip():
                diff = changed_files_git_diff(
                    repo_root, parent_rev.stdout.strip(), current
                )
                if diff is not None:
                    return classify_changed_files(diff)

    base = os.environ.get("DEPLOY_BASE_COMMIT", "").strip()
    head = current or "HEAD"
    if base and head:
        if os.path.isdir(git_dir):
            diff = changed_files_git_diff(repo_root, base, head)
            if diff is not None:
                return classify_changed_files(diff)
        api_files = _github_compare(repo, base, head, token)
        if api_files is not None:
            return classify_changed_files(api_files)

    if current:
        prev = previous_pipeline_commit(pipeline, current, region)
        if prev:
            if os.path.isdir(git_dir):
                diff = changed_files_git_diff(repo_root, prev, current)
                if diff is not None:
                    return classify_changed_files(diff)
            api_files = _github_compare(repo, prev, current, token)
            if api_files is not None:
                return classify_changed_files(api_files)

    return full_sync_plan("unknown_changes_fallback")


def main(argv: list[str] | None = None) -> int:
    argv = list(argv if argv is not None else sys.argv[1:])
    emit_env = False
    if "--emit-env" in argv:
        emit_env = True
        argv.remove("--emit-env")
    repo_root = argv[0] if argv else os.getcwd()
    plan = resolve_changed_files(repo_root)

    if emit_env:
        for key, value in plan.as_env().items():
            print(f"export {key}={shlex.quote(value)}")
        return 0

    print(f"deploy_plan detection={plan.detection}")
    if plan.changed_files is None:
        print("deploy_plan changed_files=UNKNOWN (running full sync — safe fallback)")
    else:
        print(f"deploy_plan changed_files={len(plan.changed_files)}")
        for path in plan.changed_files[:40]:
            print(f"  - {path}")
        if len(plan.changed_files) > 40:
            print(f"  ... +{len(plan.changed_files) - 40} more")

    print(f"deploy_plan needs_static_sync={plan.needs_static_sync}")
    print(f"deploy_plan needs_kb_sync={plan.needs_kb_sync}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
