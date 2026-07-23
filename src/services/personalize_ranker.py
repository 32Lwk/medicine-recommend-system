"""Amazon Personalize — OTC 候補の表示順 rerank（Web AWS のみ）。"""
from __future__ import annotations

import hashlib
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _user_id(session_id: str) -> str:
    digest = hashlib.sha256(session_id.encode("utf-8")).hexdigest()[:32]
    return f"anon-{digest}"


def _item_id(medicine: Dict[str, Any]) -> Optional[str]:
    for key in ("product_id", "id", "jan", "product_code", "name"):
        val = medicine.get(key)
        if val:
            return str(val).strip()
    return None


def record_personalize_event(
    *,
    session_id: str,
    event_type: str,
    item_id: str,
    properties: Optional[Dict[str, Any]] = None,
) -> None:
    """イベント送信（失敗時はログのみ）。"""
    from config.aws_features import get_aws_region, get_personalize_tracking_id

    tracking_id = get_personalize_tracking_id()
    if not tracking_id or not session_id or not item_id:
        return
    import boto3

    client = boto3.client("personalize-events", region_name=get_aws_region())
    try:
        client.put_events(
            trackingId=tracking_id,
            userId=_user_id(session_id),
            sessionId=session_id[:128],
            eventList=[
                {
                    "eventType": event_type,
                    "sentAt": int(__import__("time").time()),
                    "itemId": item_id[:256],
                    "properties": properties or {},
                }
            ],
        )
    except Exception as exc:
        logger.debug("Personalize put_events failed: %s", exc)


def rerank_if_enabled(
    medicines: List[Dict[str, Any]],
    *,
    session_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """PERSONALIZE_CAMPAIGN_ARN 設定時のみ順序を入れ替える。"""
    from config.aws_features import get_aws_region, get_personalize_campaign_arn
    from src.handlers.line.line_session import is_line_session_id
    from src.services.comprehend_medical import is_web_session

    if not medicines or not session_id or not is_web_session(session_id):
        return medicines
    if is_line_session_id(session_id):
        return medicines

    campaign_arn = get_personalize_campaign_arn()
    if not campaign_arn:
        return medicines

    item_ids = []
    id_to_med: Dict[str, Dict[str, Any]] = {}
    for med in medicines:
        iid = _item_id(med)
        if not iid:
            continue
        item_ids.append(iid)
        id_to_med[iid] = med
    if len(item_ids) < 2:
        return medicines

    import boto3

    client = boto3.client("personalize-runtime", region_name=get_aws_region())
    try:
        resp = client.get_personalized_ranking(
            campaignArn=campaign_arn,
            inputList=item_ids,
            userId=_user_id(session_id),
        )
    except Exception as exc:
        logger.warning("Personalize get_personalized_ranking failed: %s", exc)
        return medicines

    ranked: List[Dict[str, Any]] = []
    seen = set()
    for row in resp.get("personalizedRanking") or []:
        iid = str(row.get("itemId") or "")
        if iid in id_to_med and iid not in seen:
            ranked.append(id_to_med[iid])
            seen.add(iid)
            record_personalize_event(
                session_id=session_id,
                event_type="recommend",
                item_id=iid,
            )
    for med in medicines:
        iid = _item_id(med)
        if iid and iid not in seen:
            ranked.append(med)
        elif not iid:
            ranked.append(med)
    return ranked or medicines
