"""Amazon Comprehend Medical — Web NLU 補助 + ログ分析用。"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def is_web_session(session_id: Optional[str]) -> bool:
    if not session_id:
        return True
    from src.handlers.line.line_session import is_line_session_id

    return not is_line_session_id(session_id)


def extract_medical_entities(text: str) -> Optional[Dict[str, Any]]:
    """
    DetectEntitiesV2 で症状・薬剤エンティティを抽出。

    Returns:
        {entities, symptoms, medications, provider, comprehend_ms} or None
    """
    from config.aws_features import get_aws_region, is_comprehend_medical_enabled

    cleaned = (text or "").strip()
    if not is_comprehend_medical_enabled() or not cleaned:
        return None

    import boto3
    import time

    start = time.time()
    client = boto3.client("comprehendmedical", region_name=get_aws_region())
    try:
        resp = client.detect_entities_v2(Text=cleaned)
    except Exception as exc:
        logger.warning("Comprehend Medical detect_entities_v2 failed: %s", exc)
        return None

    entities: List[Dict[str, Any]] = []
    symptoms: List[str] = []
    medications: List[str] = []
    for ent in resp.get("Entities") or []:
        category = str(ent.get("Category") or "")
        ent_type = str(ent.get("Type") or "")
        score = float(ent.get("Score") or 0.0)
        mention = str(ent.get("Text") or "").strip()
        if not mention or score < 0.55:
            continue
        row = {
            "text": mention,
            "category": category,
            "type": ent_type,
            "score": score,
        }
        entities.append(row)
        if category == "MEDICAL_CONDITION" and ent_type in ("DX_NAME", "ACUITY"):
            symptoms.append(mention)
        elif category == "MEDICATION" and ent_type in ("GENERIC_NAME", "BRAND_NAME"):
            medications.append(mention)

    elapsed_ms = round((time.time() - start) * 1000, 2)
    result = {
        "entities": entities,
        "symptoms": symptoms,
        "medications": medications,
        "provider": "comprehend_medical",
        "comprehend_ms": elapsed_ms,
    }
    logger.info(
        "Comprehend Medical: entities=%d symptoms=%d medications=%d ms=%.2f",
        len(entities),
        len(symptoms),
        len(medications),
        elapsed_ms,
    )
    return result


def merge_comprehend_into_nlu(
    nlu: Dict[str, Any],
    user_text: str,
    *,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Web セッションのみ Comprehend 結果を NLU にマージ（低 confidence 時はスキップ）。"""
    from config.aws_features import is_comprehend_medical_enabled

    if not is_comprehend_medical_enabled() or not is_web_session(session_id):
        return nlu

    cm = extract_medical_entities(user_text)
    if not cm or not cm.get("entities"):
        return nlu

    out = dict(nlu)
    out["comprehend_medical"] = cm

    existing = {
        str(s.get("name") if isinstance(s, dict) else s).strip()
        for s in (out.get("symptoms") or [])
        if s
    }
    merged_symptoms = list(out.get("symptoms") or [])
    rule_conf = float(out.get("confidence_score") or 0.0)

    if rule_conf < 0.5:
        for mention in cm.get("symptoms") or []:
            if mention not in existing:
                merged_symptoms.append({"name": mention, "severity": "中等度", "source": "comprehend"})
                existing.add(mention)
        if merged_symptoms and not out.get("symptoms"):
            out["confidence_score"] = max(rule_conf, 0.35)
    out["symptoms"] = merged_symptoms
    return out
