"""
翻訳APIのラッパークラス
複数の翻訳APIをサポートし、フォールバック機能を提供
"""

import os
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class TranslationService:
    """翻訳サービスのラッパークラス"""
    
    def __init__(self, preferred_method: str = 'deepl'):
        """
        Args:
            preferred_method: 優先する翻訳方法 ('chatgpt', 'google', 'deepl')
        """
        self.preferred_method = preferred_method
        self.fallback_methods = ['deepl', 'google', 'chatgpt']
        # 優先メソッドを最初に配置
        if preferred_method in self.fallback_methods:
            self.fallback_methods.remove(preferred_method)
            self.fallback_methods.insert(0, preferred_method)
    
    def translate(self, text: str, target_language: str = 'en', preserve_html: bool = True) -> Tuple[str, str]:
        """
        テキストを翻訳
        
        Args:
            text: 翻訳対象のテキスト
            target_language: 翻訳先言語コード ('en', 'ko', 'zh')
            preserve_html: HTML構造を保持するか
        
        Returns:
            (翻訳されたテキスト, 使用した方法)
        """
        for method in self.fallback_methods:
            try:
                if method == 'chatgpt':
                    translated = self._translate_chatgpt(text, target_language, preserve_html)
                    return translated, 'chatgpt'
                elif method == 'google':
                    translated = self._translate_google(text, target_language, preserve_html)
                    return translated, 'google'
                elif method == 'deepl':
                    translated = self._translate_deepl(text, target_language, preserve_html)
                    return translated, 'deepl'
            except Exception as e:
                logger.warning(f"[{method}] 翻訳失敗: {e}。次の方法を試します...")
                continue
        
        # すべての方法が失敗した場合は元のテキストを返す
        logger.error("すべての翻訳方法が失敗しました。元のテキストを返します。")
        return text, 'none'
    
    def _translate_chatgpt(self, text: str, target_language: str, preserve_html: bool) -> str:
        """ChatGPT APIを使用した翻訳"""
        from openai import OpenAI
        
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found")
        
        client = OpenAI(api_key=api_key)
        
        language_names = {
            'en': 'English',
            'ko': 'Korean',
            'zh': 'Chinese'
        }
        target_lang_name = language_names.get(target_language, 'English')
        
        if preserve_html:
            prompt = f"""
以下の医薬品推奨情報を{target_lang_name}に翻訳してください。
重要な指示：
1. すべてのHTMLタグと構造を完全に保持してください
2. 医療専門用語は正確に翻訳してください
3. HTMLタグ内のテキストのみを翻訳し、タグ自体は変更しないでください

翻訳対象テキスト:
{text}

翻訳（HTML構造を完全に保持してください）:
"""
        else:
            prompt = f"以下のテキストを{target_lang_name}に翻訳してください:\n\n{text}"
        
        text_length = len(text)
        if text_length > 10000:
            max_tokens = 8000
        elif text_length > 5000:
            max_tokens = 6000
        elif text_length > 3000:
            max_tokens = 4000
        else:
            max_tokens = 3000
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a medical translator specializing in medicine recommendations. Translate accurately while maintaining medical terminology and preserving all HTML structure and tags."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=max_tokens
        )
        
        return response.choices[0].message.content.strip()
    
    def _translate_google(self, text: str, target_language: str, preserve_html: bool) -> str:
        """Google翻訳APIを使用した翻訳"""
        try:
            from google.cloud import translate_v2 as translate
        except ImportError:
            raise ImportError("google-cloud-translate not installed. Install with: pip install google-cloud-translate")
        
        credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        if credentials_path:
            client = translate.Client()
        else:
            api_key = os.getenv('GOOGLE_TRANSLATE_API_KEY')
            if not api_key:
                raise ValueError("GOOGLE_TRANSLATE_API_KEY or GOOGLE_APPLICATION_CREDENTIALS not found")
            client = translate.Client(api_key=api_key)
        
        if preserve_html:
            # HTMLタグを保護するために、一時的にプレースホルダーに置き換え
            import re
            html_tags = {}
            tag_counter = 0
            
            def replace_tag(match):
                nonlocal tag_counter
                tag_id = f"__HTML_TAG_{tag_counter}__"
                html_tags[tag_id] = match.group(0)
                tag_counter += 1
                return tag_id
            
            text_without_tags = re.sub(r'<[^>]+>', replace_tag, text)
            
            result = client.translate(
                text_without_tags,
                target_language=target_language,
                source_language='ja'
            )
            
            translated_text = result['translatedText']
            
            # プレースホルダーを元のHTMLタグに戻す
            for tag_id, original_tag in html_tags.items():
                translated_text = translated_text.replace(tag_id, original_tag)
            
            return translated_text
        else:
            result = client.translate(
                text,
                target_language=target_language,
                source_language='ja'
            )
            return result['translatedText']
    
    def _translate_deepl(self, text: str, target_language: str, preserve_html: bool) -> str:
        """DeepL APIを使用した翻訳"""
        try:
            import deepl
        except ImportError:
            raise ImportError("deepl not installed. Install with: pip install deepl")
        
        api_key = os.getenv('DEEPL_API_KEY')
        if not api_key:
            raise ValueError("DEEPL_API_KEY not found")
        
        translator = deepl.Translator(api_key)
        
        deepl_lang_map = {
            'en': 'EN',
            'ko': 'KO',
            'zh': 'ZH'
        }
        deepl_target = deepl_lang_map.get(target_language, 'EN')
        
        if preserve_html:
            result = translator.translate_text(
                text,
                source_lang='JA',
                target_lang=deepl_target,
                tag_handling='html'
            )
        else:
            result = translator.translate_text(
                text,
                source_lang='JA',
                target_lang=deepl_target
            )
        
        return result.text


# 使用例
if __name__ == '__main__':
    # ログ設定
    logging.basicConfig(level=logging.INFO)
    
    # DeepLを優先する翻訳サービス
    translator = TranslationService(preferred_method='deepl')
    
    sample_text = """
    <div>
        <h4>💊 推奨医薬品</h4>
        <p>のどの痛み、発熱に効果的な医薬品をご提案します。</p>
    </div>
    """
    
    translated, method = translator.translate(sample_text, target_language='en')
    print(f"使用した方法: {method}")
    print(f"翻訳結果:\n{translated}")

