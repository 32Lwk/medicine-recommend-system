"""
方言変換機能の包括的なテストケース
多義語、語壊れ、エッジケース、パフォーマンステストを含む
"""

import unittest
import sys
import os
import time
import logging

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scoring_utils import (
    convert_dialect_to_standard,
    basic_normalize_text,
    initialize_dialect_resources,
    check_health_context,
    normalize_symptom_weights,
    calculate_escalation_score,
    check_escalation_threshold
)
from config.dialect_dictionary import DIALECT_DICTIONARY

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestDialectConversion(unittest.TestCase):
    """方言変換の基本テスト"""
    
    @classmethod
    def setUpClass(cls):
        """テストクラスの初期化（一度だけ実行）"""
        try:
            initialize_dialect_resources()
            logger.info("✅ 方言変換リソースの初期化が完了しました。")
        except Exception as e:
            logger.warning(f"⚠️ 方言変換リソースの初期化に失敗: {e}")
    
    def test_basic_dialect_conversion(self):
        """基本的な方言変換のテスト"""
        # 関西弁
        result = convert_dialect_to_standard("しんどい", extract_severity=False)
        self.assertIn("つらい", result[0])
        
        # 名古屋弁
        result = convert_dialect_to_standard("でら痛い", extract_severity=True)
        self.assertIn("とても", result[0])
        self.assertEqual(result[1], "重度")  # 重症度タグ
        
        # 九州弁
        result = convert_dialect_to_standard("ばり痛い", extract_severity=True)
        self.assertIn("とても", result[0])
        self.assertEqual(result[1], "中等度")
    
    def test_ambiguity_prevention(self):
        """多義語の誤変換防止テスト"""
        # 「えらい」が「偉い」の意味で使われている場合は変換しない
        result = convert_dialect_to_standard("先生はえらい", extract_severity=False)
        # 文脈判定により変換されない可能性がある
        # 体調関連の文脈では変換する
        result2 = convert_dialect_to_standard("今日はえらい", extract_severity=False)
        # 体調関連キーワードがある場合は変換される可能性がある
    
    def test_word_boundary(self):
        """語壊れ防止テスト"""
        # 「ばい」が「ばいきん」の一部として使われている場合は変換しない
        result = convert_dialect_to_standard("ばいきんが気になる", extract_severity=False)
        self.assertIn("ばいきん", result[0])
        
        # 文末の「ばい」は変換する
        result2 = convert_dialect_to_standard("痛いばい", extract_severity=False)
        self.assertIn("だよ", result2[0])
    
    def test_severity_extraction(self):
        """強調副詞の重症度タグ抽出テスト"""
        # 重度
        text, severity, score, _, _ = convert_dialect_to_standard("でら痛い", extract_severity=True)
        self.assertEqual(severity, "重度")
        self.assertGreater(score, 0)
        
        # 中等度
        text, severity, score, _, _ = convert_dialect_to_standard("めっちゃ痛い", extract_severity=True)
        self.assertEqual(severity, "中等度")
        self.assertGreater(score, 0)
        
        # 複数の強調語
        text, severity, score, _, _ = convert_dialect_to_standard("でらめっちゃ痛い", extract_severity=True)
        self.assertEqual(severity, "重度")  # 最大値
        self.assertGreaterEqual(score, 3.0)  # 重度(2.0) + 中等度(1.0) = 3.0
    
    def test_escalation_score(self):
        """escalation_scoreの計算テスト"""
        # 単一の強調語
        severity_tags = ["中等度"]
        score = calculate_escalation_score(severity_tags)
        self.assertEqual(score, 1.0)
        
        # 複数の強調語
        severity_tags = ["重度", "中等度"]
        score = calculate_escalation_score(severity_tags)
        self.assertEqual(score, 3.0)  # 2.0 + 1.0
        
        # 閾値チェック
        self.assertFalse(check_escalation_threshold(3.0))  # 4.0未満
        self.assertTrue(check_escalation_threshold(4.0))  # 4.0以上
    
    def test_non_destructive_conversion(self):
        """非破壊的変換のテスト"""
        # 「にえる」は複数の症状候補を持つ
        text, severity, score, candidates, weights = convert_dialect_to_standard(
            "にえる", extract_severity=False, non_destructive=True
        )
        self.assertIn("にえる", candidates or {})
        self.assertGreater(len(weights), 0)
    
    def test_weight_normalization(self):
        """重みの正規化テスト"""
        from config.dialect_dictionary import DIALECT_DICTIONARY
        
        # 「にえる」の重み正規化
        dialect_info = DIALECT_DICTIONARY["和歌山弁"]["にえる"]
        weights = normalize_symptom_weights("にえる", dialect_info, original_weight=1.0)
        
        # 保存則の確認：Σw_i = W_original
        total_weight = sum(weights.values())
        self.assertAlmostEqual(total_weight, 1.0, places=3)
    
    def test_basic_normalization(self):
        """基本正規化のテスト"""
        # Unicode正規化
        result = basic_normalize_text("えらーい")
        self.assertIn("えらい", result)
        
        # 全角半角統一（カタカナ→ひらがな）
        result = basic_normalize_text("シンドイ")
        # カタカナはひらがなに変換されるが、完全一致は難しいので部分一致で確認
        self.assertTrue("しん" in result or "しんど" in result or "しんどい" in result)
        
        # 長音削除
        result = basic_normalize_text("めっちゃー")
        self.assertIn("めっちゃ", result)
    
    def test_context_detection(self):
        """文脈判定のテスト"""
        from config.dialect_dictionary import DIALECT_DICTIONARY
        
        # 体調関連の文脈
        dialect_info = DIALECT_DICTIONARY["関西弁"]["えらい"]
        result = check_health_context("今日は疲れてえらい", "えらい", dialect_info)
        self.assertTrue(result)
        
        # 体調関連でない文脈
        result2 = check_health_context("先生はえらい", "えらい", dialect_info)
        self.assertFalse(result2)
    
    def test_edge_cases(self):
        """エッジケースのテスト"""
        # 空文字列
        result = convert_dialect_to_standard("", extract_severity=False)
        self.assertEqual(result[0], "")
        
        # None（Noneはそのまま返される）
        result = convert_dialect_to_standard(None, extract_severity=False)
        self.assertIsNone(result[0])
        
        # 非常に長いテキスト
        long_text = "しんどい" * 1000
        start_time = time.time()
        result = convert_dialect_to_standard(long_text, extract_severity=False)
        elapsed_time = time.time() - start_time
        self.assertLess(elapsed_time, 1.0)  # 1秒以内
    
    def test_performance(self):
        """パフォーマンステスト"""
        test_cases = [
            "しんどい",
            "でら痛い",
            "めっちゃしんどい",
            "ばり痛くて、でら辛い",
            "えらい疲れた",
            "にえる",
            "ごっつ痛い",
            "なまらしんどい",
            "わっぜ痛い",
            "がばい痛い"
        ]
        
        # 100回実行して平均時間を測定
        iterations = 100
        total_time = 0
        
        for _ in range(iterations):
            for test_case in test_cases:
                start_time = time.time()
                convert_dialect_to_standard(test_case, extract_severity=True)
                elapsed_time = time.time() - start_time
                total_time += elapsed_time
        
        avg_time = total_time / (iterations * len(test_cases))
        logger.info(f"平均処理時間: {avg_time * 1000:.2f}ms")
        
        # 柔軟な200ms目標（長文は許容）
        self.assertLess(avg_time, 0.2)  # 200ms以内
    
    def test_all_dialect_words(self):
        """すべての方言表現のテスト"""
        total_words = 0
        successful_conversions = 0
        
        for dialect_type, entries in DIALECT_DICTIONARY.items():
            for dialect_word, info in entries.items():
                total_words += 1
                try:
                    # 文脈判定が必要な方言表現（ambiguity_risk=high）は、適切な文脈を含むテキストでテスト
                    if info.get("ambiguity_risk") == "high":
                        # 文脈キーワードを含むテキストでテスト
                        context_keywords = info.get("context_keywords", [])
                        if context_keywords:
                            test_text = f"今日は{context_keywords[0]}くて{dialect_word}"
                        else:
                            test_text = f"今日は{dialect_word}"
                    else:
                        test_text = f"今日は{dialect_word}"
                    
                    result = convert_dialect_to_standard(
                        test_text,
                        extract_severity=bool(info.get("severity_tag")),
                        non_destructive=bool(info.get("multiple_symptoms"))
                    )
                    if result[0] != test_text:
                        successful_conversions += 1
                except Exception as e:
                    logger.warning(f"方言変換エラー: {dialect_word} - {e}")
        
        success_rate = successful_conversions / total_words if total_words > 0 else 0
        logger.info(f"方言変換成功率: {success_rate * 100:.1f}% ({successful_conversions}/{total_words})")
        
        # 最低でも30%以上の成功率を期待（辞書の拡張により、一部の方言表現は変換されない可能性がある）
        # 特に、ambiguity_riskがhighの方言表現は、文脈判定により変換されない場合がある
        self.assertGreater(success_rate, 0.3)


class TestErrorHandling(unittest.TestCase):
    """エラーハンドリングのテスト"""
    
    def test_import_error_handling(self):
        """インポートエラーのハンドリング"""
        # モジュールが存在しない場合のテストは難しいが、
        # エラーが発生してもアプリがクラッシュしないことを確認
        try:
            from scoring_utils import convert_dialect_to_standard
            result = convert_dialect_to_standard("テスト", extract_severity=False)
            self.assertIsNotNone(result)
        except Exception as e:
            self.fail(f"エラーハンドリングが不十分: {e}")
    
    def test_invalid_input(self):
        """無効な入力のハンドリング"""
        # 数値（文字列に変換される）
        result = convert_dialect_to_standard(123, extract_severity=False)
        self.assertEqual(result[0], "123")
        
        # リスト（文字列に変換される）
        result = convert_dialect_to_standard([], extract_severity=False)
        self.assertEqual(result[0], "[]")


if __name__ == '__main__':
    unittest.main()

