"""
医薬品推奨文の翻訳モジュール

DeepL API を用いた翻訳とキャッシュの責務を持つ。
"""
import logging
import os
import time

logger = logging.getLogger(__name__)

from src import PROJECT_ROOT
BASE_DIR = PROJECT_ROOT

# 翻訳キャッシュ
_translation_cache = {}
_max_cache_size = 200


def get_cached_translation(text: str, target_language: str):
    """翻訳キャッシュから結果を取得"""
    cache_key = f"{target_language}:{hash(text)}"
    return _translation_cache.get(cache_key)


def set_cached_translation(text: str, target_language: str, translated_text: str):
    """翻訳キャッシュに結果を保存"""
    global _translation_cache
    if len(_translation_cache) >= _max_cache_size:
        oldest_key = next(iter(_translation_cache))
        del _translation_cache[oldest_key]
    cache_key = f"{target_language}:{hash(text)}"
    _translation_cache[cache_key] = translated_text


def translate_medicine_recommendation(text, target_language, client=None, session_id=None):
    """
    AI応答（医薬品推奨）を翻訳（DeepL API使用、キャッシュ機能付き）

    Args:
        text (str): 翻訳対象のテキスト
        target_language (str): 翻訳先言語コード ('en', 'ko', 'zh')
        client: 後方互換性のためのパラメータ（使用されません）
        session_id: セッションID（ログ用、オプション）

    Returns:
        str: 翻訳されたテキスト
    """
    if not text or target_language == 'ja':
        return text

    cached_result = get_cached_translation(text, target_language)
    if cached_result:
        logger.debug(f"翻訳キャッシュヒット: {target_language}, テキスト長: {len(text)}")
        if session_id:
            try:
                from src.utils.structured_logger import log_translation_detail
                log_translation_detail(
                    session_id=session_id,
                    original_text=text[:500],
                    translated_text=cached_result[:500],
                    target_language=target_language
                )
            except Exception as e:
                logger.warning(f"翻訳ログ記録エラー: {e}")
        return cached_result

    try:
        from dotenv import load_dotenv
        env_path = os.path.join(BASE_DIR, '.env')
        if os.path.exists(env_path):
            load_dotenv(env_path, override=True)
    except ImportError:
        pass
    except Exception:
        pass

    try:
        import deepl
    except ImportError:
        logger.error("deeplライブラリがインストールされていません。'pip install deepl'でインストールしてください。")
        return text

    api_key = os.getenv('DEEPL_API_KEY')
    if not api_key:
        logger.error("DEEPL_API_KEYが設定されていません。")
        return text

    try:
        translator = deepl.Translator(api_key)
        deepl_lang_map = {'en': 'EN-US', 'ko': 'KO', 'zh': 'ZH'}
        deepl_target = deepl_lang_map.get(target_language, 'EN-US')

        start_time = time.time()
        result = translator.translate_text(
            text,
            source_lang='JA',
            target_lang=deepl_target,
            tag_handling='html'
        )
        elapsed_time = time.time() - start_time
        translated_text = result.text

        important_keywords = ['医師', '受診', '質問', '追加', 'お伺い', 'doctor', 'consultation', 'question', 'additional']
        has_important_sections = any(keyword in translated_text for keyword in important_keywords)
        if not has_important_sections and len(translated_text) < len(text) * 0.5:
            logger.warning(f"⚠️ 翻訳結果が不完全の可能性があります。元: {len(text)}, 翻訳後: {len(translated_text)}")

        logger.info(f"✅ DeepL翻訳完了 ({target_language}): {elapsed_time:.2f}秒, {len(translated_text)}文字")
        set_cached_translation(text, target_language, translated_text)

        if session_id:
            try:
                from src.utils.structured_logger import log_translation_detail
                log_translation_detail(
                    session_id=session_id,
                    original_text=text[:500] if len(text) > 500 else text,
                    translated_text=translated_text[:500] if len(translated_text) > 500 else translated_text,
                    target_language=target_language
                )
            except Exception as e:
                logger.warning(f"翻訳ログ記録エラー: {e}")

        return translated_text

    except deepl.exceptions.QuotaExceededException:
        logger.error("❌ DeepL APIのクォータを超過しました。")
        return text
    except deepl.exceptions.AuthorizationException:
        logger.error("❌ DeepL APIキーが無効です。")
        return text
    except Exception as e:
        logger.error(f"❌ DeepL翻訳エラー: {e}")
        return text
