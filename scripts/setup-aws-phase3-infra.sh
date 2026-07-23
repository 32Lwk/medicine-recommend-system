#!/usr/bin/env bash
# Phase 3 インフラ一括（Bedrock KB ソース同期 + KB セットアップ）
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
bash "$ROOT/scripts/setup-aws-bedrock-kb.sh"
