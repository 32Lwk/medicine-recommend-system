#!/usr/bin/env python3
"""
翻訳APIのベンチマークスクリプト
ChatGPT、Google翻訳API、DeepL APIのパフォーマンスを比較
"""

import os
import time
import json
from typing import Dict, List, Tuple
from datetime import datetime
import logging

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# テスト用のサンプルテキスト（実際の医薬品推奨結果を模擬）
SAMPLE_TEXTS = {
    'short': """
    <div class="recommendation-result">
        <h4>💊 推奨医薬品</h4>
        <p><strong>1つ目:</strong> ストナアイビージェルＳ</p>
        <p><strong>効能:</strong> のどの痛み、発熱、悪寒</p>
        <p><strong>使用上の注意:</strong> 15歳未満は服用しないでください。</p>
    </div>
    """,
    'medium': """
    <div class="recommendation-result">
        <div style="background: #e3f2fd; padding: 20px; margin: 15px 0; border-radius: 8px;">
            <h4 style="color: #1976d2;">💡 Personalized Advice</h4>
            <p>症状に応じた適切な医薬品をご提案いたします。まずは十分な休息と水分補給を心がけてください。</p>
        </div>
        <h4>🔍 症状分析結果</h4>
        <p><strong>推測される症状:</strong> のどの痛み、発熱</p>
        <p><strong>医薬品の種類:</strong> 風邪薬</p>
        <div style="background: #e8f5e9; padding: 20px; margin: 15px 0;">
            <h4>💊 推奨医薬品</h4>
            <div class="medicine-item">
                <h5>🏆 1つ目: ストナアイビージェルＳ</h5>
                <p><strong>推奨理由:</strong> 症状に非常によく適合</p>
                <p><strong>効能:</strong> のどの痛み、発熱、悪寒</p>
            </div>
        </div>
        <div style="background: #fff3e0; padding: 20px; margin: 15px 0;">
            <h4>⚠️ 使用上の注意</h4>
            <p>・15歳未満は服用しないでください。</p>
            <p>・用法用量を厳守してください。</p>
        </div>
        <div style="background: #ffebee; padding: 20px; margin: 15px 0;">
            <h4>🏥 医師の受診が必要な場合</h4>
            <p>症状が3日以上続く場合は医師にご相談ください。</p>
        </div>
    </div>
    """,
    'long': """
    <div class="recommendation-result">
        <div style="background: #e3f2fd; padding: 20px; margin: 15px 0; border-radius: 8px; border-left: 4px solid #2196f3;">
            <h4 style="color: #1976d2; margin-top: 0;">💡 Personalized Advice</h4>
            <p style="margin: 5px 0; line-height: 1.6;">症状に応じた適切な医薬品をご提案いたします。まずは十分な休息と水分補給を心がけてください。推奨された医薬品は症状に効果的ですが、使用前に添付文書をよくお読みください。</p>
        </div>
        <h4 style="color: #1976d2; border-bottom: 2px solid #1976d2; padding-bottom: 8px;">🔍 症状分析結果</h4>
        <p><strong>推測される症状:</strong> のどの痛み、発熱、悪寒</p>
        <p><strong>医薬品の種類:</strong> 風邪薬</p>
        <div style="background: #e8f5e9; padding: 20px; margin: 15px 0; border-radius: 8px; border-left: 4px solid #4caf50;">
            <h4 style="color: #2e7d32; margin-top: 0;">💊 推奨医薬品</h4>
            <div class="medicine-item" style="padding: 10px 0; margin: 10px 0; border-bottom: 1px solid #ddd;">
                <h5 style="margin: 0 0 10px 0;">🏆 1つ目: ストナアイビージェルＳ <span style="color: #666;">(佐藤製薬)</span></h5>
                <p style="margin: 5px 0;"><strong>📊 最適度:</strong> 100.0% (高)</p>
                <p style="margin: 5px 0;"><strong>推奨理由:</strong> 症状に非常によく適合: のどの痛み, 発熱に特化した効果</p>
                <p><strong>年齢制限:</strong> 15歳以上の方が対象です。</p>
                <p style="margin: 5px 0;"><strong>効能効果:</strong> のどの痛み、発熱、悪寒（発熱によるさむけ）</p>
            </div>
            <div class="medicine-item" style="padding: 10px 0; margin: 10px 0; border-bottom: 1px solid #ddd;">
                <h5 style="margin: 0 0 10px 0;">🏆 2つ目: スルーロン持続性かぜ薬ＥＸ <span style="color: #666;">(協和薬品工業)</span></h5>
                <p style="margin: 5px 0;"><strong>📊 最適度:</strong> 99.3% (高)</p>
                <p style="margin: 5px 0;"><strong>推奨理由:</strong> 症状に非常によく適合: のどの痛み, 発熱に特化した効果</p>
                <p><strong>年齢制限:</strong> 15歳以上の方が対象です。</p>
                <p style="margin: 5px 0;"><strong>効能効果:</strong> 鼻水、鼻づまり、くしゃみ、のどの痛み、せき、たん、悪寒</p>
            </div>
        </div>
        <div style="background: #fff3e0; padding: 20px; margin: 15px 0; border-radius: 8px; border-left: 4px solid #ff9800;">
            <h4 style="color: #e65100; margin-top: 0;">⚠️ 使用上の注意</h4>
            <div style="padding: 10px 0; margin: 10px 0;">
                <h5 style="margin: 0 0 8px 0;">💊 1つ目：ストナアイビージェルＳ</h5>
                <p style="margin: 3px 0;">効能: のどの痛み、発熱、悪寒（発熱によるさむけ）</p>
                <p style="margin: 3px 0;">用法用量の注意:</p>
                <p style="margin: 3px 0; padding-left: 10px;">・15歳未満は服用しないでください。</p>
                <p style="margin: 3px 0; padding-left: 10px;">・カプセルの取り出し方に注意してください。</p>
                <p style="margin: 3px 0;"><strong>年齢制限:</strong> 15歳以上の方が対象です。</p>
                <p style="margin: 3px 0;"><strong>ドーピング:</strong> 禁止物質あり</p>
            </div>
        </div>
        <div style="background: #ffebee; padding: 20px; margin: 15px 0; border-radius: 8px; border-left: 4px solid #f44336;">
            <h4 style="color: #c62828; margin-top: 0;">🏥 医師の受診が必要な場合</h4>
            <p style="margin: 5px 0;">【以下の場合は医師にご相談ください】</p>
            <p style="margin: 5px 0;">・症状が3日以上続く場合</p>
            <p style="margin: 5px 0;">・症状が悪化する場合</p>
            <p style="margin: 5px 0;">・高熱（38.5度以上）が続く場合</p>
        </div>
        <div style="background: #ffebee; padding: 15px; margin: 15px 0; border-radius: 8px; border-left: 4px solid #f44336;">
            <h4 style="color: #c62828; margin-top: 0;">❓ 追加でお伺いしたいこと <span style="font-size: 0.9em;">（優先度: 必須）</span></h4>
            <p style="margin: 10px 0;">より適切な医薬品をご提案するため、以下の情報を教えてください：</p>
            <ul style="margin: 10px 0; padding-left: 20px;">
                <li style="margin: 5px 0;">年齢を教えてください。（医薬品の適切な選択に必要です）</li>
                <li style="margin: 5px 0;">性別を教えてください。（男性/女性）</li>
                <li style="margin: 5px 0;">アレルギーはありますか？（薬物アレルギー、食物アレルギーなど）</li>
            </ul>
        </div>
    </div>
    """
}

# 翻訳方法の実装
class TranslationBenchmark:
    def __init__(self):
        self.results = []
    
    def translate_chatgpt(self, text: str, target_language: str = 'en') -> Tuple[str, float]:
        """ChatGPT APIを使用した翻訳"""
        try:
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
            
            text_length = len(text)
            if text_length > 10000:
                max_tokens = 8000
            elif text_length > 5000:
                max_tokens = 6000
            elif text_length > 3000:
                max_tokens = 4000
            else:
                max_tokens = 3000
            
            start_time = time.time()
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a medical translator specializing in medicine recommendations. Translate accurately while maintaining medical terminology and preserving all HTML structure and tags."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=max_tokens
            )
            elapsed_time = time.time() - start_time
            
            translated_text = response.choices[0].message.content.strip()
            return translated_text, elapsed_time
        except Exception as e:
            logger.error(f"ChatGPT翻訳エラー: {e}")
            raise
    
    def translate_google(self, text: str, target_language: str = 'en') -> Tuple[str, float]:
        """Google翻訳APIを使用した翻訳"""
        try:
            from google.cloud import translate_v2 as translate
            
            # APIキーの設定を確認
            credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
            if not credentials_path:
                # 環境変数から直接APIキーを取得
                api_key = os.getenv('GOOGLE_TRANSLATE_API_KEY')
                if not api_key:
                    raise ValueError("GOOGLE_TRANSLATE_API_KEY or GOOGLE_APPLICATION_CREDENTIALS not found")
                client = translate.Client(api_key=api_key)
            else:
                client = translate.Client()
            
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
            
            # HTMLタグを一時的に置き換え
            text_without_tags = re.sub(r'<[^>]+>', replace_tag, text)
            
            start_time = time.time()
            result = client.translate(
                text_without_tags,
                target_language=target_language,
                source_language='ja'
            )
            elapsed_time = time.time() - start_time
            
            translated_text = result['translatedText']
            
            # プレースホルダーを元のHTMLタグに戻す
            for tag_id, original_tag in html_tags.items():
                translated_text = translated_text.replace(tag_id, original_tag)
            
            return translated_text, elapsed_time
        except ImportError:
            logger.warning("google-cloud-translate not installed. Install with: pip install google-cloud-translate")
            raise
        except Exception as e:
            logger.error(f"Google翻訳エラー: {e}")
            raise
    
    def translate_deepl(self, text: str, target_language: str = 'en') -> Tuple[str, float]:
        """DeepL APIを使用した翻訳"""
        try:
            import deepl
            
            api_key = os.getenv('DEEPL_API_KEY')
            if not api_key:
                raise ValueError("DEEPL_API_KEY not found")
            
            translator = deepl.Translator(api_key)
            
            # DeepLの言語コードに変換
            deepl_lang_map = {
                'en': 'EN',
                'ko': 'KO',
                'zh': 'ZH'
            }
            deepl_target = deepl_lang_map.get(target_language, 'EN')
            
            start_time = time.time()
            result = translator.translate_text(
                text,
                source_lang='JA',
                target_lang=deepl_target,
                tag_handling='html'  # HTMLタグを保護
            )
            elapsed_time = time.time() - start_time
            
            translated_text = result.text
            return translated_text, elapsed_time
        except ImportError:
            logger.warning("deepl not installed. Install with: pip install deepl")
            raise
        except Exception as e:
            logger.error(f"DeepL翻訳エラー: {e}")
            raise
    
    def run_benchmark(self, text_size: str = 'medium', target_language: str = 'en', iterations: int = 3):
        """ベンチマークを実行"""
        text = SAMPLE_TEXTS[text_size]
        text_length = len(text)
        
        logger.info(f"\n{'='*60}")
        logger.info(f"ベンチマーク開始: {text_size} ({text_length}文字)")
        logger.info(f"翻訳先言語: {target_language}, 繰り返し回数: {iterations}")
        logger.info(f"{'='*60}\n")
        
        methods = {
            'ChatGPT': self.translate_chatgpt,
            'Google翻訳': self.translate_google,
            'DeepL': self.translate_deepl
        }
        
        results = {}
        
        for method_name, translate_func in methods.items():
            logger.info(f"\n[{method_name}] テスト開始...")
            times = []
            success_count = 0
            
            for i in range(iterations):
                try:
                    translated_text, elapsed_time = translate_func(text, target_language)
                    times.append(elapsed_time)
                    success_count += 1
                    logger.info(f"  試行 {i+1}/{iterations}: {elapsed_time:.2f}秒")
                    
                    # 最初の試行の結果を保存
                    if i == 0:
                        results[method_name] = {
                            'translated_text': translated_text[:200] + '...' if len(translated_text) > 200 else translated_text,
                            'translated_length': len(translated_text)
                        }
                except Exception as e:
                    logger.error(f"  [{method_name}] 試行 {i+1} エラー: {e}")
                    times.append(None)
            
            if success_count > 0:
                valid_times = [t for t in times if t is not None]
                avg_time = sum(valid_times) / len(valid_times)
                min_time = min(valid_times)
                max_time = max(valid_times)
                
                results[method_name].update({
                    'avg_time': avg_time,
                    'min_time': min_time,
                    'max_time': max_time,
                    'success_rate': success_count / iterations * 100,
                    'times': valid_times
                })
            else:
                results[method_name] = {
                    'error': 'すべての試行が失敗しました'
                }
        
        return results
    
    def print_summary(self, results: Dict):
        """結果のサマリーを表示"""
        logger.info(f"\n{'='*60}")
        logger.info("ベンチマーク結果サマリー")
        logger.info(f"{'='*60}\n")
        
        # テーブル形式で表示
        print(f"{'方法':<15} {'平均時間(秒)':<15} {'最小時間(秒)':<15} {'最大時間(秒)':<15} {'成功率(%)':<12}")
        print("-" * 75)
        
        for method_name, result in results.items():
            if 'error' in result:
                print(f"{method_name:<15} {'エラー':<15} {'-':<15} {'-':<15} {'0%':<12}")
            else:
                print(f"{method_name:<15} {result.get('avg_time', 0):<15.2f} {result.get('min_time', 0):<15.2f} {result.get('max_time', 0):<15.2f} {result.get('success_rate', 0):<12.1f}")
        
        # 最速の方法を特定
        valid_results = {k: v for k, v in results.items() if 'error' not in v and 'avg_time' in v}
        if valid_results:
            fastest = min(valid_results.items(), key=lambda x: x[1]['avg_time'])
            logger.info(f"\n最速の方法: {fastest[0]} ({fastest[1]['avg_time']:.2f}秒)")
    
    def save_results(self, results: Dict, filename: str = None):
        """結果をJSONファイルに保存"""
        if filename is None:
            filename = f"translation_benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        output = {
            'timestamp': datetime.now().isoformat(),
            'results': results
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        
        logger.info(f"\n結果を保存しました: {filename}")


def main():
    """メイン関数"""
    benchmark = TranslationBenchmark()
    
    # 各サイズのテキストでベンチマークを実行
    for text_size in ['short', 'medium', 'long']:
        try:
            results = benchmark.run_benchmark(
                text_size=text_size,
                target_language='en',
                iterations=3
            )
            benchmark.print_summary(results)
            benchmark.save_results(results, f"benchmark_{text_size}.json")
        except Exception as e:
            logger.error(f"ベンチマーク実行エラー ({text_size}): {e}")
    
    logger.info("\nベンチマーク完了！")


if __name__ == '__main__':
    main()

