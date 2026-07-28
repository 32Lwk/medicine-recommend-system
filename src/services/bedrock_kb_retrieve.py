"""Bedrock Knowledge Base retrieve（Concierge / 医薬品 Q&A RAG 補助）。"""
from __future__ import annotations

import hashlib
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_DEFAULT_MIN_SCORE = 0.4


def _min_kb_score() -> float:
    """低スコア chunk を捨てる閾値（Phase Q2-d）。未設定時 0.4。"""
    raw = (os.getenv("BEDROCK_KB_MIN_SCORE") or "").strip()
    if not raw:
        return _DEFAULT_MIN_SCORE
    try:
        return max(0.0, min(1.0, float(raw)))
    except ValueError:
        return _DEFAULT_MIN_SCORE


def _passes_score_threshold(score: Any, *, min_score: float) -> bool:
    if score is None:
        return True
    try:
        return float(score) >= min_score
    except (TypeError, ValueError):
        return True


def _cache_key(namespace: str, query: str, top_k: int) -> str:
    digest = hashlib.sha256(f"{top_k}:{query}".encode("utf-8")).hexdigest()[:32]
    return f"kb:{namespace}:{digest}"


def _build_retrieval_configuration(top_k: int, search_mode: str) -> Dict[str, Any]:
    n = max(1, min(top_k, 10))
    if search_mode == "managed":
        return {"managedSearchConfiguration": {"numberOfResults": n}}
    return {"vectorSearchConfiguration": {"numberOfResults": n}}


def _empty_result(*, provider: str = "local") -> Dict[str, Any]:
    return {
        "chunks": [],
        "sources": [],
        "kb_retrieve_ms": 0.0,
        "chunk_count": 0,
        "source_uris": [],
        "provider": provider,
    }


def _parse_retrieval_results(
    resp: Dict[str, Any],
    *,
    min_score: float,
) -> tuple[List[str], List[Dict[str, Any]], List[str], int]:
    chunks: List[str] = []
    sources: List[Dict[str, Any]] = []
    source_uris: List[str] = []
    dropped = 0
    for item in resp.get("retrievalResults") or []:
        score = item.get("score")
        if not _passes_score_threshold(score, min_score=min_score):
            dropped += 1
            continue
        text = str(item.get("content", {}).get("text") or "").strip()
        loc = item.get("location") or {}
        s3_loc = loc.get("s3Location") or {}
        uri = str(s3_loc.get("uri") or "").strip()
        if text:
            chunks.append(text)
        if uri and uri not in source_uris:
            source_uris.append(uri)
        sources.append({"uri": uri, "score": score})
    return chunks, sources, source_uris, dropped


def retrieve_kb_context(
    query: str,
    *,
    kb_id: str,
    cache_namespace: str,
    top_k: int = 5,
    use_cache: bool = True,
    search_mode: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Bedrock KB から関連チャンクを取得（Concierge / Medicine 共通）。

    Returns:
        {chunks, sources, kb_retrieve_ms, chunk_count, source_uris, provider, ...}
    """
    from config.aws_features import get_aws_region, get_bedrock_kb_search_mode

    cleaned = (query or "").strip()
    empty = _empty_result()
    if not cleaned or not kb_id:
        return empty

    mode = (search_mode or get_bedrock_kb_search_mode()).strip().lower()
    if mode not in ("managed", "vector"):
        mode = "managed"

    cache_key = _cache_key(cache_namespace, cleaned, top_k)
    if use_cache:
        from src.services.redis_cache import cache_get_json, cache_set_json

        cached = cache_get_json(cache_key)
        if isinstance(cached, dict) and cached.get("chunks") is not None:
            cached["provider"] = "bedrock_kb_cache"
            return cached

    import boto3

    start = time.time()
    client = boto3.client("bedrock-agent-runtime", region_name=get_aws_region())
    try:
        resp = client.retrieve(
            knowledgeBaseId=kb_id,
            retrievalQuery={"text": cleaned},
            retrievalConfiguration=_build_retrieval_configuration(top_k, mode),
        )
    except Exception as exc:
        logger.warning(
            "Bedrock KB retrieve failed (kb=%s mode=%s): %s",
            kb_id,
            mode,
            exc,
        )
        return empty

    min_score = _min_kb_score()
    chunks, sources, source_uris, dropped = _parse_retrieval_results(
        resp,
        min_score=min_score,
    )

    elapsed_ms = round((time.time() - start) * 1000, 2)
    result = {
        "chunks": chunks,
        "sources": sources,
        "kb_retrieve_ms": elapsed_ms,
        "chunk_count": len(chunks),
        "source_uris": source_uris,
        "provider": "bedrock_kb",
        "min_score": min_score,
        "dropped_low_score": dropped,
        "kb_id": kb_id,
        "search_mode": mode,
    }
    logger.info(
        "Bedrock KB retrieve: ns=%s kb=%s mode=%s chunks=%d dropped=%d min_score=%.2f ms=%.2f uris=%s",
        cache_namespace,
        kb_id,
        mode,
        len(chunks),
        dropped,
        min_score,
        elapsed_ms,
        source_uris[:3],
    )
    if use_cache and chunks:
        from src.services.redis_cache import cache_set_json

        cache_set_json(cache_key, result, ttl_sec=600)
    return result


def retrieve_concierge_context(
    query: str,
    *,
    top_k: int = 5,
    use_cache: bool = True,
    intent: str = "",
) -> Dict[str, Any]:
    """Concierge 技術 FAQ 用 retrieve（Local RAG のみ）。"""
    from src.services.local_rag_retrieve import retrieve_local_context

    cleaned = (query or "").strip()
    if not cleaned:
        return _empty_result()

    return retrieve_local_context(
        cleaned,
        namespace="concierge",
        top_k=top_k,
        min_score=_min_kb_score(),
        intent=intent,
    )


_CONCIERGE_INTENT_RETRIEVAL_HINTS: Dict[str, str] = {
    "doc_changelog": "更新履歴 CHANGELOG AWS ステージング",
    "capabilities": "機能 できること 制限",
}


def _architecture_retrieval_hint(user_text: str, *, deep: bool = False) -> str:
    """architecture 向け topic 限定ヒント（汎用デプロイ語で ops doc に偏らないよう抑制）。"""
    t = (user_text or "").strip()
    if re.search(r"Local RAG|Bedrock KB|Knowledge Base|ナレッジベース|Managed KB", t, re.I):
        return "Local RAG Bedrock KB AWS_BEDROCK_KB LOCAL_RAG ops Managed KB"
    if re.search(r"デプロイ|CodePipeline|CodeBuild|ECS|ECR|インフラ|infra|反映", t, re.I):
        return "CodePipeline CodeBuild ECS ECR デプロイ ops"
    if re.search(r"AWS.*インフラ|インフラ.*構成|AWS_INFRA", t, re.I):
        return "AWS_INFRA WAF CloudFront ALB ECS ops"
    if re.search(r"データ|保存|PostgreSQL|Neon|プライバシー|個人情報|セキュリティ|チャット", t, re.I):
        return "PostgreSQL Neon データ保存 セキュリティ プライバシー"
    if re.search(r"ルールベース|LLM.*薬|薬.*LLM|スコアリング|PhysicalOrchestrator|なぜ.*選", t, re.I):
        return "ルールベース スコアリング CSV PhysicalOrchestrator LLM hallucination"
    if re.search(r"Chat Pipeline|IntentRouter|v2|マルチエージェント|TriageAgent", t, re.I):
        return "Chat Pipeline v2 IntentRouter orchestrator TriageAgent"
    if re.search(r"翻訳|Translate|DeepL|TTS|Polly", t, re.I):
        return "DeepL Amazon Translate Polly Cloud Text-to-Speech"
    if re.search(r"企業|会社|導入|enterprise|B2B", t, re.I):
        return "企業向け 会社向け概要 enterprise"
    if re.search(r"GCP|AWS|クロスクラウド|ステージング|本番|分けた理由", t, re.I):
        return "GCP AWS クロスクラウド ステージング 本番 分離 理由"
    if deep:
        return "技術 選定 理由 trade-off SSOT"
    return "architecture 技術 SSOT concierge technical"


def build_concierge_retrieval_query(
    user_text: str,
    intent: str = "",
    *,
    deep: bool = False,
) -> str:
    """Concierge intent 別 retrieve クエリ（user_text + 意図キーワード）。"""
    parts: List[str] = []
    cleaned = (user_text or "").strip()
    if cleaned:
        parts.append(cleaned)
    intent_key = (intent or "").strip().lower()
    if intent_key == "architecture":
        parts.append(_architecture_retrieval_hint(cleaned, deep=deep))
    else:
        hint = _CONCIERGE_INTENT_RETRIEVAL_HINTS.get(intent_key)
        if hint:
            parts.append(hint)
    if deep and intent_key == "architecture":
        parts.append("技術 詳細 参照ドキュメント 選定 理由 trade-off")
    merged = " ".join(parts).strip()
    try:
        from src.services.concierge_tech_synonyms import expand_concierge_query

        return expand_concierge_query(merged)
    except ImportError:
        return merged


def _concierge_kb_top_k(intent: str, *, override: Optional[int] = None) -> int:
    if override is not None:
        return max(0, min(int(override), 10))
    intent_key = (intent or "").strip().lower()
    if intent_key in ("capabilities", "app_about"):
        return 2
    if intent_key in ("architecture", "doc_changelog"):
        return 5
    return 5


def build_medicine_retrieval_query(
    user_text: str,
    recommended_medicines: Optional[List[Dict[str, Any]]] = None,
    *,
    nlu_result: Optional[Dict[str, Any]] = None,
    concomitant_medications: Optional[List[str]] = None,
    conversation_history: Optional[List[Dict[str, Any]]] = None,
    use_comprehend: bool = True,
) -> str:
    """Ask / Explanation 向け retrieve クエリ（製品名・症状・併用薬・Comprehend 薬剤名を合成）。"""
    parts: List[str] = []
    cleaned = (user_text or "").strip()
    base = cleaned
    if conversation_history:
        from src.services.local_rag_context import build_contextual_retrieval_query

        contextual = build_contextual_retrieval_query(
            cleaned,
            conversation_history,
            recommended_medicines=recommended_medicines,
        )
        if contextual:
            base = contextual
    if base:
        parts.append(base)

    names: List[str] = []
    for med in recommended_medicines or []:
        name = str(med.get("product_name") or med.get("name") or "").strip()
        if name and name not in names:
            names.append(name)
    if names:
        parts.append("推奨医薬品: " + ", ".join(names[:3]))

    symptom_names: List[str] = []
    for sym in (nlu_result or {}).get("symptoms") or []:
        sname = str(sym.get("name") if isinstance(sym, dict) else sym or "").strip()
        if sname and sname not in symptom_names:
            symptom_names.append(sname)
    if symptom_names:
        parts.append("症状: " + ", ".join(symptom_names[:5]))

    concomitant: List[str] = []
    for med_name in concomitant_medications or []:
        m = str(med_name or "").strip()
        if m and m not in concomitant:
            concomitant.append(m)
    if concomitant:
        parts.append("併用薬: " + ", ".join(concomitant[:5]))

    if use_comprehend and cleaned:
        from config.aws_features import is_comprehend_medical_enabled

        if is_comprehend_medical_enabled():
            from src.services.comprehend_medical import extract_medical_entities

            cm = extract_medical_entities(cleaned)
            if cm:
                cm_meds = [m for m in (cm.get("medications") or []) if m]
                if cm_meds:
                    parts.append("検出薬剤: " + ", ".join(cm_meds[:5]))
                cm_symptoms = [s for s in (cm.get("symptoms") or []) if s]
                for s in cm_symptoms:
                    if s not in symptom_names:
                        parts.append(s)
        else:
            from src.services.local_rag_query import (
                expand_concepts,
                extract_brand_tokens,
            )

            expanded = expand_concepts(cleaned)
            rule_meds: List[str] = []
            for brand in extract_brand_tokens(expanded):
                if brand not in rule_meds:
                    rule_meds.append(brand)
            if conversation_history:
                from src.services.local_rag_context import extract_context_substances

                for sub in extract_context_substances(conversation_history):
                    if sub not in rule_meds:
                        rule_meds.append(sub)
            if rule_meds:
                parts.append("検出薬剤: " + ", ".join(rule_meds[:5]))

    return " ".join(parts).strip()


def _collect_ingredient_tokens(
    recommended_medicines: Optional[List[Dict[str, Any]]],
    extra_terms: Optional[List[str]] = None,
) -> List[str]:
    tokens: List[str] = []
    for med in recommended_medicines or []:
        raw = str(med.get("ingredients") or "")
        for line in raw.split("\n"):
            ing = line.strip()
            if ing and ing not in tokens:
                tokens.append(ing)
    for term in extra_terms or []:
        t = str(term or "").strip()
        if t and t not in tokens:
            tokens.append(t)
    return tokens


def format_csv_high_risk_interaction_block(
    *,
    user_text: str = "",
    recommended_medicines: Optional[List[Dict[str, Any]]] = None,
    nlu_result: Optional[Dict[str, Any]] = None,
) -> str:
    """retrieve が高リスク interaction を返した場合に CSV 直引き段落を優先表示する。"""
    from src.core.scoring_utils import load_interactions_data

    df = load_interactions_data()
    if df is None or df.empty:
        return ""

    extra: List[str] = list(_collect_ingredient_tokens(recommended_medicines))
    from config.aws_features import is_comprehend_medical_enabled

    if is_comprehend_medical_enabled() and user_text.strip():
        from src.services.comprehend_medical import extract_medical_entities

        cm = extract_medical_entities(user_text)
        if cm:
            extra.extend(cm.get("medications") or [])
    for sym in (nlu_result or {}).get("symptoms") or []:
        sname = str(sym.get("name") if isinstance(sym, dict) else sym or "").strip()
        if sname:
            extra.append(sname)

    search_blob = " ".join([user_text] + extra).lower()
    lines: List[str] = []
    for _, row in df.iterrows():
        level = str(row.get("相互作用レベル") or "").strip()
        if level != "高":
            continue
        a = str(row.get("成分A") or "").strip()
        b = str(row.get("成分B") or "").strip()
        if not a or not b:
            continue
        if a.lower() in search_blob and b.lower() in search_blob:
            desc = str(row.get("説明") or "").strip()
            lines.append(f"- {a} × {b}（{level}）: {desc}")
    if not lines:
        return ""
    return "【相互作用（CSV 参照・高リスク）】\n" + "\n".join(lines[:3])


def _chunk_indicates_high_risk_interaction(chunk: str) -> bool:
    text = (chunk or "").strip()
    if not text:
        return False
    if "相互作用" not in text:
        return False
    return bool(
        re.search(r"相互作用レベル[^\n]*高", text)
        or re.search(r"risk_level[^\n]*高", text, re.I)
    )


def format_medicine_kb_context_block(
    result: Dict[str, Any],
    *,
    user_text: str = "",
    recommended_medicines: Optional[List[Dict[str, Any]]] = None,
    nlu_result: Optional[Dict[str, Any]] = None,
) -> str:
    chunks = result.get("chunks") or []
    if not chunks:
        return ""

    csv_block = ""
    if any(_chunk_indicates_high_risk_interaction(c) for c in chunks):
        csv_block = format_csv_high_risk_interaction_block(
            user_text=user_text,
            recommended_medicines=recommended_medicines,
            nlu_result=nlu_result,
        )

    kb_block = format_kb_context_block(
        result,
        heading="【医薬品ナレッジベース参照（相互作用・副作用・効能等）】",
    )
    if csv_block and kb_block:
        return f"{csv_block}\n\n{kb_block}"
    return csv_block or kb_block


def retrieve_medicine_context(
    query: str,
    *,
    recommended_medicines: Optional[List[Dict[str, Any]]] = None,
    nlu_result: Optional[Dict[str, Any]] = None,
    concomitant_medications: Optional[List[str]] = None,
    conversation_history: Optional[List[Dict[str, Any]]] = None,
    top_k: int = 5,
    use_cache: bool = True,
    use_comprehend: bool = True,
    qa_focuses: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """医薬品 Q&A / 説明補強用 KB retrieve。"""
    from config.aws_features import (
        MEDICINE_RAG_NONE,
        get_bedrock_medicine_kb_id,
        get_medicine_rag_provider,
        use_medicine_bedrock_kb_rag,
    )
    from src.services.local_rag_context import normalize_conversation_history

    if get_medicine_rag_provider() == MEDICINE_RAG_NONE:
        return _empty_result()

    hist = normalize_conversation_history(conversation_history)
    retrieval_query = build_medicine_retrieval_query(
        query,
        recommended_medicines,
        nlu_result=nlu_result,
        concomitant_medications=concomitant_medications,
        conversation_history=hist or None,
        use_comprehend=use_comprehend,
    )
    if not retrieval_query:
        return _empty_result()

    if not use_medicine_bedrock_kb_rag():
        from src.services.local_rag_retrieve import (
            retrieve_local_context,
            retrieve_medicine_docs_multi,
        )
        from src.services.local_rag_router import infer_medicine_category

        fs = [f for f in (qa_focuses or []) if f and f != "general"]
        if not fs:
            from src.services.medicine_qa_routing import infer_medicine_qa_focuses

            fs = [
                f
                for f in infer_medicine_qa_focuses(
                    query or "",
                    conversation_history=hist or None,
                    recommended_medicines=recommended_medicines,
                )
                if f != "general"
            ]
        if len(fs) >= 2 or "comparison" in fs:
            multi_result = retrieve_medicine_docs_multi(
                retrieval_query,
                recommended_medicines=recommended_medicines,
                focuses=fs,
                conversation_history=hist or None,
                max_docs=min(top_k, 4),
                min_score=_min_kb_score(),
            )
            if multi_result.get("chunks"):
                return multi_result

        category = infer_medicine_category(
            query or "", conversation_history=hist or None
        )
        if "ingredient" in fs or "product_image" in fs:
            category = "usage"
        elif "age" in fs:
            category = "age"
        elif "doping" in fs:
            category = "doping"
        elif "side_effect" in fs:
            category = "side_effect"
        elif "interaction" in fs:
            category = "interaction"

        return retrieve_local_context(
            retrieval_query,
            namespace="medicine",
            top_k=top_k,
            min_score=_min_kb_score(),
            recommended_medicines=recommended_medicines,
            category=category,
            use_cache=use_cache,
        )

    kb_id = get_bedrock_medicine_kb_id()
    if not kb_id:
        logger.warning(
            "MEDICINE_RAG_PROVIDER=bedrock_kb but BEDROCK_MEDICINE_KB_ID is unset"
        )
        return _empty_result()

    return retrieve_kb_context(
        retrieval_query,
        kb_id=kb_id,
        cache_namespace="medicine",
        top_k=top_k,
        use_cache=use_cache,
    )


def format_kb_context_block(
    result: Dict[str, Any],
    *,
    heading: str = "【Bedrock Knowledge Base 参照（補助）】",
) -> str:
    chunks = result.get("chunks") or []
    if not chunks:
        return ""
    lines = [heading]
    for idx, chunk in enumerate(chunks[:5], start=1):
        snippet = chunk[:1200].strip()
        lines.append(f"[{idx}] {snippet}")
    uris = result.get("source_uris") or []
    if uris:
        lines.append("")
        lines.append("【参照ソース URI】")
        for uri in uris[:5]:
            lines.append(f"- {uri}")
    return "\n".join(lines)


def augment_reference_with_kb(
    query: str,
    base_reference: str,
    *,
    intent: str = "",
    deep: bool = False,
    top_k: Optional[int] = None,
    conversation_history: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """ローカル参照ブロックに Concierge KB チャンクを追記（Local / Bedrock 共通、障害時は base のみ）。"""
    from config.aws_features import CONCIERGE_RAG_LOCAL, get_concierge_rag_provider

    provider = get_concierge_rag_provider()
    if provider != CONCIERGE_RAG_LOCAL:
        return base_reference

    effective_top_k = _concierge_kb_top_k(intent, override=top_k)
    if effective_top_k <= 0:
        return base_reference

    # 法務 direct intent は md 全文参照のみ（RAG スキップで高速化・条項取り違え防止）
    intent_key = (intent or "").strip().lower()
    if intent_key in (
        "doc_privacy",
        "doc_terms",
        "doc_consultation",
        "doc_operator",
    ):
        return base_reference

    retrieval_query = build_concierge_retrieval_query(query, intent, deep=deep)
    if conversation_history:
        try:
            from src.services.concierge_rag_context import (
                build_concierge_meta_contextual_query,
                needs_concierge_meta_context_enrichment,
            )

            if needs_concierge_meta_context_enrichment(query, conversation_history):
                enriched = build_concierge_meta_contextual_query(
                    query,
                    conversation_history,
                    intent=intent,
                )
                if enriched:
                    retrieval_query = enriched
        except ImportError:
            pass
    if not retrieval_query:
        return base_reference

    result = retrieve_concierge_context(
        retrieval_query,
        top_k=effective_top_k,
        intent=intent,
    )
    heading = "【ローカルナレッジ参照（補助）】"
    block = format_kb_context_block(result, heading=heading)
    if not block:
        logger.info(
            "Concierge KB retrieve empty — using SSOT reference only (provider=%s)",
            provider,
        )
        return base_reference
    return f"{base_reference.rstrip()}\n\n{block}"


def augment_medicine_prompt_with_kb(
    query: str,
    base_prompt: str,
    *,
    recommended_medicines: Optional[List[Dict[str, Any]]] = None,
    nlu_result: Optional[Dict[str, Any]] = None,
    concomitant_medications: Optional[List[str]] = None,
    conversation_history: Optional[List[Dict[str, Any]]] = None,
    use_comprehend: bool = True,
    qa_focuses: Optional[List[str]] = None,
    use_cache: bool = True,
) -> str:
    """Ask / Explanation プロンプトに Medicine KB チャンクを追記（Local / Bedrock 共通）。"""
    from config.aws_features import (
        MEDICINE_RAG_BEDROCK,
        MEDICINE_RAG_LOCAL,
        get_medicine_rag_provider,
    )

    provider = get_medicine_rag_provider()
    if provider not in (MEDICINE_RAG_LOCAL, MEDICINE_RAG_BEDROCK):
        return base_prompt

    result = retrieve_medicine_context(
        query,
        recommended_medicines=recommended_medicines,
        nlu_result=nlu_result,
        concomitant_medications=concomitant_medications,
        conversation_history=conversation_history,
        top_k=5,
        use_comprehend=use_comprehend,
        qa_focuses=qa_focuses,
        use_cache=use_cache,
    )
    block = format_medicine_kb_context_block(
        result,
        user_text=query,
        recommended_medicines=recommended_medicines,
        nlu_result=nlu_result,
    )
    if not block:
        logger.info(
            "Medicine KB retrieve empty (provider=%s) — using base prompt only",
            provider,
        )
        return base_prompt
    return f"{base_prompt.rstrip()}\n\n{block}\n"
