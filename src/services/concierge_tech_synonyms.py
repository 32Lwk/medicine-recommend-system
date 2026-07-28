"""Concierge 技術 FAQ 向けクエリ synonym 展開（retrieve 前）。"""
from __future__ import annotations

import re
from typing import Dict, List, Tuple

_SYNONYM_GROUPS: Tuple[Tuple[re.Pattern[str], Tuple[str, ...]], ...] = (
    (re.compile(r"Local\s*RAG|ローカル\s*RAG|local\s*rag", re.I), ("LOCAL_RAG", "BM25", "embedding", "hybrid")),
    (re.compile(r"ナレッジベース|Knowledge\s*Base|\bKB\b", re.I), ("Bedrock", "RAG", "retrieve", "ナレッジ")),
    (re.compile(r"\bSSE\b|Server[\s-]?Sent", re.I), ("Server-Sent Events", "ストリーミング", "段階配信")),
    (re.compile(r"Express\s*Gateway", re.I), ("ECS", "ALB", "Fargate")),
    (re.compile(r"作成意図|開発背景|なぜ.*作", re.I), ("mission", "セルフメディケーション", "β版", "試験運用")),
    (re.compile(r"IntentRouter", re.I), ("IntentRouter", "振り分け", "Chat Pipeline")),
    (re.compile(r"マルチエージェント", re.I), ("TriageAgent", "PhysicalOrchestrator", "ConciergeAgent")),
    (re.compile(r"ルールベース", re.I), ("rule_based", "スコアリング", "CSV")),
    (re.compile(r"プラポリ|プライバシー", re.I), ("プライバシーポリシー", "個人情報")),
    (re.compile(r"利用規約|免責", re.I), ("免責事項", "利用規約")),
    (re.compile(r"医薬品相談窓口|#7119", re.I), ("医薬品相談先", "PMDA", "厚労省")),
)

SSOT_URI_BOOST_HINTS: Dict[str, Tuple[Tuple[re.Pattern[str], str, float], ...]] = {
    "architecture": (
        (re.compile(r"Local\s*RAG|ローカル\s*RAG|local\s*rag|ナレッジ.*ローカル|ローカル.*ナレッジ", re.I), "local/concierge/technical/12", 4.0),
        (re.compile(r"Local\s*RAG|Bedrock\s*KB|ナレッジベース", re.I), "local/ops/LOCAL_RAG", 3.5),
        (re.compile(r"GitHub|GitLab|正本|ミラー", re.I), "local/ops/GITLAB", 3.5),
        (re.compile(r"\bECS\b|Express Gateway|Fargate", re.I), "local/ops/AWS_INFRA", 3.0),
        (re.compile(r"Bedrock\s*KB|Managed KB", re.I), "local/ops/AWS_BEDROCK_KB", 3.0),
        (re.compile(r"なぜ|理由|選定|trade|LLM.*薬|薬.*LLM|ルールベース", re.I), "local/concierge/technical/12", 4.0),
        (re.compile(r"作成|意図|背景|なぜ|きっかけ|思い|運営|開発者|mission|セルフメディケーション|試験運用", re.I), "local/concierge/rag/author-mission", 4.0),
        (re.compile(r"データ保存|チャット.*保存|保存.*どこ|PostgreSQL|Neon|プライバシー", re.I), "local/concierge/technical/04", 4.0),
        (re.compile(r"データ保存|プライバシー|セキュリティ", re.I), "local/concierge/technical/12", 3.5),
        (re.compile(r"翻訳|Translate|DeepL", re.I), "local/concierge/technical/01", 3.0),
        (re.compile(r"Chat Pipeline|Pipeline v2|IntentRouter", re.I), "local/dev/CHAT_PIPELINE_V2.md", 3.5),
        (re.compile(r"Chat Pipeline|Pipeline v2", re.I), "local/concierge/technical/12", 3.0),
        (re.compile(r"マルチエージェント|TriageAgent|PhysicalOrchestrator", re.I), "local/concierge/technical/10", 3.0),
        (re.compile(r"企業向け|会社向け|enterprise|導入概要|B2B", re.I), "local/concierge/rag/enterprise-overview", 4.0),
        (re.compile(r"企業向け|会社向け|enterprise|導入概要", re.I), "local/public/企業", 4.0),
        (re.compile(r"プラポリ.*利用規約|免責.*プライバシー|法務.*横断|規約.*境界", re.I), "local/concierge/rag/legal-crossdoc", 4.0),
        (re.compile(r"\bSSE\b|Server[\s-]?Sent", re.I), "local/concierge/technical/09", 3.0),
        (re.compile(r"GitHub|GitLab|正本|ミラー", re.I), "local/concierge/technical/08", 2.0),
        (re.compile(r"Translate|DeepL|Polly|TTS", re.I), "local/concierge/technical/01", 2.0),
        (re.compile(r"開示|公開情報|disclosure|深い情報|深掘り", re.I), "local/concierge/technical/00", 5.0),
        (re.compile(r"RECO_[A-Z0-9_]+|環境変数.*フラグ|フラグ.*環境|feature\s*flag", re.I), "local/concierge/technical/05", 5.0),
        (re.compile(r"デプロイ|CodePipeline|CodeBuild|パイプライン|リリース.*流", re.I), "local/ops/AWS_CODEPIPELINE", 5.0),
        (re.compile(r"デプロイ|CodePipeline|CodeBuild|パイプライン", re.I), "local/concierge/technical/03", 3.5),
    ),
    "doc_app_overview": (
        (re.compile(r"作成|意図|背景|なぜ|β|ベータ|現状", re.I), "local/concierge/technical/11", 2.5),
        (re.compile(r"作成|意図|背景|なぜ|きっかけ|思い|運営|開発者|mission|セルフメディケーション", re.I), "local/concierge/rag/author-mission", 4.0),
    ),
    "app_about": (
        (re.compile(r"誰|何のツール|あなた", re.I), "local/content/concierge_knowledge.ja.json", 3.0),
    ),
    "doc_consultation": (
        (re.compile(r"相談窓口|相談先|PMDA|#7119", re.I), "local/public/医薬品相談先.md", 3.0),
    ),
}


def expand_concierge_query(query: str) -> str:
    base = (query or "").strip()
    if not base:
        return base
    extras: List[str] = []
    for pattern, words in _SYNONYM_GROUPS:
        if pattern.search(base):
            extras.extend(words)
    if not extras:
        return base
    seen = {base.lower()}
    parts = [base]
    for w in extras:
        if w.lower() not in seen:
            parts.append(w)
            seen.add(w.lower())
    return " ".join(parts)


def ssot_uri_boosts_for_query(query: str, intent: str) -> Dict[str, float]:
    boosts: Dict[str, float] = {}
    key = (intent or "").strip().lower()
    for pattern, uri, boost in SSOT_URI_BOOST_HINTS.get(key, ()):
        if pattern.search(query or ""):
            boosts[uri] = max(boosts.get(uri, 0.0), boost)
    return boosts
