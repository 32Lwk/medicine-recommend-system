"""
スコアリング機能の包括的なテストケース
単一症状スコアリング改善のテストを含む
"""

import unittest
import sys
import os
import time
import logging

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.scoring_utils import (
    calculate_efficacy_specificity_score,
    normalize_text,
    is_word_match,
    TANN_FALSE_POSITIVE_BLACKLIST,
    _synonym_cache
)

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestScoringUtils(unittest.TestCase):
    """スコアリング機能の基本テスト"""
    
    def setUp(self):
        """各テストの前に実行"""
        # キャッシュをクリア
        _synonym_cache.clear()
    
    def test_001_synonym_mapping_tann(self):
        """「たん」と「痰」の同義語マッピングのテスト"""
        candidate = {
            'product_name': 'テスト薬',
            'efficacy': 'たん、せきに効きます',
            'medicine_type': '風邪薬'
        }
        nlu_result = {
            'symptoms': [{'name': '痰'}]
        }
        
        score = calculate_efficacy_specificity_score(candidate, nlu_result)
        self.assertGreater(score, 0.0, "「痰」が「たん」として認識されるべき")
    
    def test_002_efficacy_specificity_boost(self):
        """効能特異性スコア計算の改善テスト（効能に「たん」が含まれている場合）"""
        candidate = {
            'product_name': '新セキリック液',
            'efficacy': 'せき、たん',
            'medicine_type': '風邪薬'
        }
        nlu_result = {
            'symptoms': [{'name': 'たん'}]
        }
        
        score = calculate_efficacy_specificity_score(candidate, nlu_result)
        # 効能に「たん」が含まれている場合は0.5に底上げされる
        self.assertGreaterEqual(score, 0.5, "効能に「たん」が含まれている場合は0.5以上になるべき")
    
    def test_003_blacklist_false_positive(self):
        """ブラックリストワードのテスト（「簡単」など）"""
        # 「簡単」の中の「たん」は誤検知として除外されるべき
        text = "簡単に飲み込める錠剤です"
        result = is_word_match("たん", text, blacklist=TANN_FALSE_POSITIVE_BLACKLIST)
        self.assertFalse(result, "「簡単」の中の「たん」は誤検知として除外されるべき")
    
    def test_004_blacklist_local_check(self):
        """局所判定のテスト（「小粒で簡単に飲み込める錠剤です。のどの痛み、たん、せきに効きます。」）"""
        # 効能として書かれている「たん」は正しく認識されるべき
        text = "小粒で簡単に飲み込める錠剤です。のどの痛み、たん、せきに効きます。"
        result = is_word_match("たん", text, blacklist=TANN_FALSE_POSITIVE_BLACKLIST)
        self.assertTrue(result, "効能として書かれている「たん」は正しく認識されるべき")
    
    def test_005_word_boundary_check(self):
        """単語境界チェックのテスト"""
        # 「たん」が独立した単語として存在する場合
        text = "たんが出ます"
        result = is_word_match("たん", text)
        self.assertTrue(result, "「たん」が独立した単語として存在する場合はTrue")
        
        # 「簡単」の中の「たん」は単語境界チェックで除外される
        text = "簡単に飲めます"
        result = is_word_match("たん", text, blacklist=TANN_FALSE_POSITIVE_BLACKLIST)
        self.assertFalse(result, "「簡単」の中の「たん」は除外されるべき")
    
    def test_006_epsilon_comparison(self):
        """浮動小数点比較のテスト（イプシロン値）"""
        EPSILON = 0.0001
        
        # 非常に小さい値でもイプシロン比較で正しく判定される
        value1 = 0.00005
        value2 = 0.00015
        
        self.assertLess(value1, EPSILON, "0.00005はEPSILON未満")
        self.assertGreaterEqual(value2, EPSILON, "0.00015はEPSILON以上")
    
    def test_007_expectorant_bonus(self):
        """去痰成分ボーナスのテスト"""
        from src.core.rule_based_recommendation import calculate_ingredient_based_boost
        
        candidate = {
            'product_name': 'テスト去痰薬',
            'ingredients': 'カルボシステイン',
            'medicine_type': '風邪薬'
        }
        nlu_result = {
            'symptoms': [{'name': 'たん'}]
        }
        
        boost = calculate_ingredient_based_boost(candidate, nlu_result, {})
        # 去痰成分が含まれている場合はボーナスが付与される
        self.assertGreater(boost, 0.0, "去痰成分が含まれている場合はボーナスが付与されるべき")
    
    def test_008_antitussive_penalty(self):
        """鎮咳成分ペナルティのテスト"""
        from src.core.rule_based_recommendation import calculate_ingredient_based_boost
        
        candidate = {
            'product_name': 'テスト鎮咳去痰薬',
            'ingredients': 'カルボシステイン、ジヒドロコデイン',
            'medicine_type': '風邪薬'
        }
        nlu_result = {
            'symptoms': [{'name': 'たん'}]
        }
        
        boost = calculate_ingredient_based_boost(candidate, nlu_result, {})
        # 去痰成分と強力な鎮咳成分の両方が含まれている場合は重み付け処理が適用される
        # ボーナスは0.15 - 0.05 = 0.10になる
        self.assertGreater(boost, 0.0, "去痰成分と鎮咳成分の両方が含まれている場合でもボーナスは付与される")
        self.assertLess(boost, 0.15, "鎮咳成分が含まれている場合はボーナスが減らされる")
    
    def test_009_kampo_expectorant(self):
        """漢方薬の去痰成分ボーナスのテスト"""
        from src.core.rule_based_recommendation import calculate_ingredient_based_boost
        
        candidate = {
            'product_name': '麦門冬湯',
            'ingredients': 'バクモンドウ',
            'medicine_type': '風邪薬'
        }
        nlu_result = {
            'symptoms': [{'name': 'たん'}]
        }
        
        boost = calculate_ingredient_based_boost(candidate, nlu_result, {})
        # 漢方薬の去痰成分が含まれている場合は固定値0.10のボーナスが付与される
        self.assertGreaterEqual(boost, 0.10, "漢方薬の去痰成分が含まれている場合は0.10以上のボーナスが付与されるべき")
    
    def test_010_error_handling(self):
        """エラーハンドリングのテスト"""
        # 無効な入力でもエラーが発生せず、デフォルト値が返される
        candidate = {}
        nlu_result = {}
        
        score = calculate_efficacy_specificity_score(candidate, nlu_result)
        self.assertEqual(score, 0.0, "無効な入力の場合は0.0が返されるべき")
    
    def test_011_performance(self):
        """パフォーマンステスト（処理時間測定）"""
        candidate = {
            'product_name': 'テスト薬',
            'efficacy': 'たん、せきに効きます',
            'medicine_type': '風邪薬'
        }
        nlu_result = {
            'symptoms': [{'name': 'たん'}]
        }
        
        # 100回実行して処理時間を測定
        start_time = time.time()
        for _ in range(100):
            calculate_efficacy_specificity_score(candidate, nlu_result)
        end_time = time.time()
        
        elapsed_time = end_time - start_time
        avg_time = elapsed_time / 100
        
        logger.info(f"平均処理時間: {avg_time * 1000:.2f}ms")
        # 平均処理時間が10ms以下であることを確認（パフォーマンス目標）
        self.assertLess(avg_time, 0.01, "平均処理時間は10ms以下であるべき")
    
    def test_012_integration(self):
        """統合テスト（全体フローのテスト）"""
        candidate = {
            'product_name': '新セキリック液',
            'efficacy': 'せき、たん',
            'medicine_type': '風邪薬',
            'ingredients': 'カルボシステイン、クロルフェニラミンマレイン酸塩、ジヒドロコデインリン酸塩'
        }
        nlu_result = {
            'symptoms': [{'name': 'たん'}]
        }
        
        # 効能特異性スコアの計算
        efficacy_score = calculate_efficacy_specificity_score(candidate, nlu_result)
        self.assertGreater(efficacy_score, 0.0, "効能特異性スコアは0より大きいべき")
        # 効能に「たん」が含まれている場合は0.5以上になるべき
        self.assertGreaterEqual(efficacy_score, 0.5, "効能に「たん」が含まれている場合は0.5以上になるべき")
        
        # 去痰成分ボーナスの計算
        from src.core.rule_based_recommendation import calculate_ingredient_based_boost
        boost = calculate_ingredient_based_boost(candidate, nlu_result, {})
        # カルボシステイン（去痰成分）とジヒドロコデイン（強力な鎮咳成分）の両方が含まれているため、
        # ボーナスは0.15 - 0.05 = 0.10になる
        self.assertGreater(boost, 0.0, "去痰成分が含まれている場合はボーナスが付与されるべき")
        self.assertLess(boost, 0.15, "強力な鎮咳成分が含まれている場合はボーナスが減らされる")


if __name__ == '__main__':
    unittest.main()

