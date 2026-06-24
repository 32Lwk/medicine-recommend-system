"""
非同期ユーザー属性抽出サービス

バックグラウンドでLLMによる属性抽出を実行し、
結果をセッションストアに反映する責務を持つ。
メイン処理のレスポンスをブロックしない。
"""
import logging
import threading
from typing import Optional, Callable, Any

logger = logging.getLogger(__name__)


def _merge_list_attribute(existing, incoming):
    from src.utils.allergen_attributes import merge_list_attribute
    return merge_list_attribute(existing, incoming)


def schedule_async_attribute_extraction(
    sid: str,
    message: str,
    get_session_fn: Callable[[str], Optional[dict]],
    save_session_fn: Callable[[str, dict], Any],
) -> None:
    """
    非同期でLLMによる属性抽出を実行し、結果をセッションにマージして保存する。
    メインレスポンスをブロックしない。
    """
    def _run():
        try:
            from src.core.attribute_extractor import extract_user_attributes_multilingual
            from src.utils.allergen_attributes import normalize_environmental_allergens
            from openai import OpenAI
            import os

            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                return

            session_data = get_session_fn(sid)
            if not session_data:
                return

            current_attrs = session_data.get('user_attributes') or {}
            if not isinstance(current_attrs, dict):
                current_attrs = {}

            client = OpenAI(api_key=api_key)
            llm_result = extract_user_attributes_multilingual(
                message, client=client, user_info=current_attrs
            )

            if not llm_result or not isinstance(llm_result, dict):
                return

            def _norm_gender(v):
                if v in ('男性', '女性'):
                    return v
                if v in ('Male', 'male'):
                    return '男性'
                if v in ('Female', 'female'):
                    return '女性'
                return v

            merged = dict(current_attrs)
            updated = False
            for key in ('age', 'gender', 'pregnant', 'breastfeeding', 'allergies',
                        'current_medications', 'medical_history', 'symptom_duration_days', 'other_info'):
                val = llm_result.get(key)
                if val is None:
                    continue
                if key == 'gender':
                    val = _norm_gender(val) if isinstance(val, str) else val
                if key in ('allergies', 'current_medications', 'medical_history'):
                    new_list, list_changed = _merge_list_attribute(merged.get(key) or [], val)
                    if list_changed:
                        merged[key] = new_list
                        updated = True
                elif merged.get(key) != val:
                    merged[key] = val
                    updated = True

            merged = normalize_environmental_allergens(merged)
            if updated or merged != current_attrs:
                session_data['user_attributes'] = merged
                save_session_fn(sid, session_data)
                try:
                    from src.services.line_user_memory import resolve_memory_owner_sid
                    from src.services.line_memory_jobs import schedule_profile_persist

                    owner = resolve_memory_owner_sid(sid, session_data)
                    if owner:
                        schedule_profile_persist(owner, merged)
                except Exception:
                    pass
                logger.info(f"📝 非同期LLM属性抽出完了: session={sid[:20]}...")
        except Exception as e:
            logger.warning(f"⚠️ 非同期属性抽出でエラー: {e}")


    t = threading.Thread(target=_run, daemon=True, name="async-attr-extract")
    t.start()
