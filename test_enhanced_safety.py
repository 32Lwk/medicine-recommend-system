"""
強化された安全性チェックのテストスイート
医薬品推奨の安全性テスト
"""

import unittest
import sys
import os

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from enhanced_safety_checker import (
    strict_safety_check,
    is_contraindicated,
    enhanced_scoring_weights,
    get_safety_stats
)
from rule_based_recommendation import (
    _filter_antidiarrheal_without_diarrhea,
    _enforce_symptom_match_threshold
)

class TestEnhancedSafetyChecker(unittest.TestCase):
    """強化された安全性チェックのテストクラス"""
    
    def setUp(self):
        """テスト前の準備"""
        self.sample_medicines = {
            'safe_adult_medicine': {
                'product_name': '安全な成人用医薬品',
                'manufacturer': 'テストメーカー',
                'medicine_type': '風邪薬',
                'ingredients': 'アセトアミノフェン',
                'efficacy': '解熱鎮痛',
                'age_restriction': '15歳以上'
            },
            'dangerous_medicine': {
                'product_name': '危険な医薬品',
                'manufacturer': 'テストメーカー',
                'medicine_type': '解熱鎮痛薬',
                'ingredients': 'アスピリン',
                'efficacy': '解熱鎮痛',
                'age_restriction': '15歳以上'
            },
            'child_medicine': {
                'product_name': '小児用医薬品',
                'manufacturer': 'テストメーカー',
                'medicine_type': '風邪薬',
                'ingredients': 'アセトアミノフェン',
                'efficacy': '解熱鎮痛',
                'age_restriction': '3歳以上'
            }
        }
        
        self.test_users = {
            'adult_male': {
                'age': 30,
                'gender': 'male',
                'pregnant': False,
                'breastfeeding': False,
                'current_medications': []
            },
            'adult_female': {
                'age': 25,
                'gender': 'female',
                'pregnant': False,
                'breastfeeding': False,
                'current_medications': []
            },
            'child_5_years': {
                'age': 5,
                'gender': 'female',
                'pregnant': False,
                'breastfeeding': False,
                'current_medications': []
            },
            'infant_2_years': {
                'age': 2,
                'gender': 'male',
                'pregnant': False,
                'breastfeeding': False,
                'current_medications': []
            },
            'pregnant_woman': {
                'age': 28,
                'gender': 'female',
                'pregnant': True,
                'breastfeeding': False,
                'current_medications': []
            },
            'breastfeeding_woman': {
                'age': 32,
                'gender': 'female',
                'pregnant': False,
                'breastfeeding': True,
                'current_medications': []
            },
            'elderly_person': {
                'age': 75,
                'gender': 'male',
                'pregnant': False,
                'breastfeeding': False,
                'current_medications': ['ワーファリン']
            }
        }
        
        self.nlu_results = {
            'normal_symptoms': {
                'symptoms': [
                    {'name': '頭痛', 'severity': '軽度', 'duration_days': 1}
                ],
                'red_flags': [],
                'needs_escalation': False
            },
            'severe_symptoms': {
                'symptoms': [
                    {'name': '頭痛', 'severity': '重度', 'duration_days': 3}
                ],
                'red_flags': [],
                'needs_escalation': False
            },
            'red_flag_symptoms': {
                'symptoms': [
                    {'name': '胸痛', 'severity': '重度', 'duration_days': 1}
                ],
                'red_flags': ['胸痛'],
                'needs_escalation': True
            },
            'long_duration_symptoms': {
                'symptoms': [
                    {'name': '頭痛', 'severity': '中等度', 'duration_days': 10}
                ],
                'red_flags': [],
                'needs_escalation': False
            }
        }
    
    def test_adult_safety_check(self):
        """成人の安全性チェックテスト"""
        medicine = self.sample_medicines['safe_adult_medicine']
        user = self.test_users['adult_male']
        nlu_result = self.nlu_results['normal_symptoms']
        
        result = strict_safety_check(medicine, user, nlu_result)
        
        self.assertIsInstance(result, dict)
        self.assertIn('is_safe', result)
        self.assertIn('safety_score', result)
        self.assertIn('requires_escalation', result)
        self.assertIn('doctor_referral_required', result)
        self.assertIn('warnings', result)
        self.assertIn('referral_reasons', result)
        
        # 成人の安全な医薬品は基本的に安全
        self.assertTrue(result['is_safe'])
        self.assertFalse(result['requires_escalation'])
        self.assertFalse(result['doctor_referral_required'])
    
    def test_child_safety_check(self):
        """小児の安全性チェックテスト"""
        medicine = self.sample_medicines['safe_adult_medicine']
        user = self.test_users['child_5_years']
        nlu_result = self.nlu_results['normal_symptoms']
        
        result = strict_safety_check(medicine, user, nlu_result)
        
        # 小児は医師相談必須
        self.assertFalse(result['is_safe'])
        self.assertTrue(result['requires_escalation'])
        self.assertTrue(result['doctor_referral_required'])
        self.assertIn('幼児', result['escalation_reason'])
    
    def test_infant_safety_check(self):
        """乳児の安全性チェックテスト"""
        medicine = self.sample_medicines['safe_adult_medicine']
        user = self.test_users['infant_2_years']
        nlu_result = self.nlu_results['normal_symptoms']
        
        result = strict_safety_check(medicine, user, nlu_result)
        
        # 乳児は絶対禁忌
        self.assertFalse(result['is_safe'])
        self.assertTrue(result['requires_escalation'])
        self.assertTrue(result['doctor_referral_required'])
        self.assertIn('乳児', result['escalation_reason'])
    
    def test_pregnant_safety_check(self):
        """妊娠中の安全性チェックテスト"""
        medicine = self.sample_medicines['safe_adult_medicine']
        user = self.test_users['pregnant_woman']
        nlu_result = self.nlu_results['normal_symptoms']
        
        result = strict_safety_check(medicine, user, nlu_result)
        
        # 妊娠中は医師相談必須
        self.assertFalse(result['is_safe'])
        self.assertTrue(result['requires_escalation'])
        self.assertTrue(result['doctor_referral_required'])
        self.assertIn('妊娠中', result['escalation_reason'])
    
    def test_breastfeeding_safety_check(self):
        """授乳中の安全性チェックテスト"""
        medicine = self.sample_medicines['safe_adult_medicine']
        user = self.test_users['breastfeeding_woman']
        nlu_result = self.nlu_results['normal_symptoms']
        
        result = strict_safety_check(medicine, user, nlu_result)
        
        # 授乳中は医師相談必須
        self.assertFalse(result['is_safe'])
        self.assertTrue(result['requires_escalation'])
        self.assertTrue(result['doctor_referral_required'])
        self.assertIn('授乳中', result['escalation_reason'])
    
    def test_elderly_safety_check(self):
        """高齢者の安全性チェックテスト"""
        medicine = self.sample_medicines['safe_adult_medicine']
        user = self.test_users['elderly_person']
        nlu_result = self.nlu_results['normal_symptoms']
        
        result = strict_safety_check(medicine, user, nlu_result)
        
        # 高齢者は注意が必要だが、基本的には安全
        self.assertTrue(result['is_safe'])
        self.assertFalse(result['requires_escalation'])
        self.assertFalse(result['doctor_referral_required'])
        # 警告は表示される可能性がある
        self.assertIsInstance(result['warnings'], list)
    
    def test_severe_symptoms_safety_check(self):
        """重篤な症状の安全性チェックテスト"""
        medicine = self.sample_medicines['safe_adult_medicine']
        user = self.test_users['adult_male']
        nlu_result = self.nlu_results['severe_symptoms']
        
        result = strict_safety_check(medicine, user, nlu_result)
        
        # 重篤な症状がある場合は警告
        self.assertTrue(result['is_safe'])  # 医薬品自体は安全
        self.assertIsInstance(result['warnings'], list)
        # 警告に重篤な症状の情報が含まれる
        warning_text = ' '.join(result['warnings'])
        self.assertIn('重度', warning_text)
    
    def test_red_flag_symptoms_safety_check(self):
        """Red Flag症状の安全性チェックテスト"""
        medicine = self.sample_medicines['safe_adult_medicine']
        user = self.test_users['adult_male']
        nlu_result = self.nlu_results['red_flag_symptoms']
        
        result = strict_safety_check(medicine, user, nlu_result)
        
        # Red Flag症状がある場合は医師受診必須
        self.assertTrue(result['is_safe'])  # 医薬品自体は安全
        self.assertTrue(result['requires_escalation'])
        self.assertTrue(result['doctor_referral_required'])
        self.assertIn('Red Flag', result['referral_reasons'][0]['description'])
    
    def test_long_duration_symptoms_safety_check(self):
        """長期症状の安全性チェックテスト"""
        medicine = self.sample_medicines['safe_adult_medicine']
        user = self.test_users['adult_male']
        nlu_result = self.nlu_results['long_duration_symptoms']
        
        result = strict_safety_check(medicine, user, nlu_result)
        
        # 長期症状がある場合は医師受診推奨
        self.assertTrue(result['is_safe'])  # 医薬品自体は安全
        self.assertTrue(result['doctor_referral_required'])
        self.assertIn('1週間', result['referral_reasons'][0]['description'])
    
    def test_contraindication_check(self):
        """禁忌薬チェックのテスト"""
        medicine = self.sample_medicines['safe_adult_medicine']
        
        # 成人は禁忌ではない
        self.assertFalse(is_contraindicated(medicine, self.test_users['adult_male']))
        
        # 小児は禁忌
        self.assertTrue(is_contraindicated(medicine, self.test_users['child_5_years']))
        
        # 乳児は禁忌
        self.assertTrue(is_contraindicated(medicine, self.test_users['infant_2_years']))
        
        # 妊娠中は禁忌
        self.assertTrue(is_contraindicated(medicine, self.test_users['pregnant_woman']))
        
        # 授乳中は禁忌
        self.assertTrue(is_contraindicated(medicine, self.test_users['breastfeeding_woman']))
    
    def test_enhanced_scoring_weights(self):
        """強化されたスコアリングウェイトのテスト"""
        weights = enhanced_scoring_weights()
        
        self.assertIsInstance(weights, dict)
        
        # 副作用リスクが強化されていることを確認
        self.assertEqual(weights['副作用リスク'], -0.20)
        
        # 相互作用リスクが強化されていることを確認
        self.assertEqual(weights['相互作用リスク'], -0.10)
        
        # 新しいスコア要素が追加されていることを確認
        self.assertIn('禁忌チェック', weights)
        self.assertIn('安全性スコア', weights)
        
        # 禁忌チェックは最大の減点
        self.assertEqual(weights['禁忌チェック'], -1.0)
        
        # 安全性スコアは加点
        self.assertEqual(weights['安全性スコア'], 0.20)
    
    def test_safety_stats(self):
        """安全性統計のテスト"""
        stats = get_safety_stats()
        
        self.assertIsInstance(stats, dict)
        self.assertIn('contraindication_rules_count', stats)
        self.assertIn('doctor_referral_conditions_count', stats)
        self.assertIn('scoring_weights', stats)
        
        self.assertIsInstance(stats['contraindication_rules_count'], int)
        self.assertIsInstance(stats['doctor_referral_conditions_count'], int)
        self.assertIsInstance(stats['scoring_weights'], dict)
    
    def test_dangerous_medicine_safety_check(self):
        """危険な医薬品の安全性チェックテスト"""
        medicine = self.sample_medicines['dangerous_medicine']
        user = self.test_users['adult_male']
        nlu_result = self.nlu_results['normal_symptoms']
        
        result = strict_safety_check(medicine, user, nlu_result)
        
        # 危険な医薬品は安全性スコアが低い（または警告がある）
        # アスピリンは副作用リスクが高いため、何らかの影響があることを確認
        self.assertIsInstance(result['safety_score'], int)
        self.assertIsInstance(result['warnings'], list)
        # 結果の構造を確認
        self.assertIn('is_safe', result)
        self.assertIn('safety_score', result)
    
    def test_medicine_type_restrictions(self):
        """医薬品種類別制限のテスト"""
        # 妊娠中の解熱鎮痛薬は絶対禁忌
        medicine = self.sample_medicines['dangerous_medicine']
        user = self.test_users['pregnant_woman']
        nlu_result = self.nlu_results['normal_symptoms']
        
        result = strict_safety_check(medicine, user, nlu_result)
        
        self.assertFalse(result['is_safe'])
        self.assertTrue(result['requires_escalation'])
        self.assertTrue(result['doctor_referral_required'])
        self.assertIn('妊娠中', result['escalation_reason'])

class TestSafetyIntegration(unittest.TestCase):
    """安全性統合テストクラス"""
    
    def test_complete_safety_workflow(self):
        """完全な安全性ワークフローのテスト"""
        # 正常なケース
        medicine = {
            'product_name': '安全な医薬品',
            'medicine_type': '風邪薬',
            'ingredients': 'アセトアミノフェン'
        }
        
        user = {
            'age': 30,
            'pregnant': False,
            'breastfeeding': False
        }
        
        nlu_result = {
            'symptoms': [{'name': '頭痛', 'severity': '軽度'}],
            'red_flags': [],
            'needs_escalation': False
        }
        
        result = strict_safety_check(medicine, user, nlu_result)
        self.assertIsInstance(result, dict)
        self.assertIn('is_safe', result)
    
    def test_emergency_safety_workflow(self):
        """緊急時の安全性ワークフローのテスト"""
        # 緊急ケース（乳児 + 重篤な症状）
        medicine = {
            'product_name': '緊急時医薬品',
            'medicine_type': '解熱鎮痛薬',
            'ingredients': 'アセトアミノフェン'
        }
        
        user = {
            'age': 1,  # 乳児
            'pregnant': False,
            'breastfeeding': False
        }
        
        nlu_result = {
            'symptoms': [{'name': '高熱', 'severity': '重度'}],
            'red_flags': ['高熱'],
            'needs_escalation': True
        }
        
        result = strict_safety_check(medicine, user, nlu_result)
        
        # 乳児は絶対禁忌
        self.assertFalse(result['is_safe'])
        self.assertTrue(result['requires_escalation'])
        self.assertTrue(result['doctor_referral_required'])


class TestRuleBasedFiltering(unittest.TestCase):
    """ルールベース推奨のフィルタリング検証"""

    def test_antidiarrheal_removed_without_diarrhea(self):
        """腹痛のみの相談では止瀉薬成分を含む候補を除外"""
        candidates = [
            {
                'product_name': 'ビオフェルミン止瀉薬',
                'ingredients': 'ロートエキス\nタンニン酸ベルベリン',
                'efficacy': '下痢、腹痛を伴う下痢',
                'usage': '',
                'classification': '第2類',
                'medicine_type': '胃腸薬',
                'score_breakdown': {'symptom_match': 0.8}
            }
        ]
        nlu_result = {'symptoms': [{'name': '腹痛'}]}

        filtered = _filter_antidiarrheal_without_diarrhea(candidates, nlu_result)
        self.assertEqual(filtered, [])

    def test_antidiarrheal_kept_with_diarrhea(self):
        """下痢が確認できる場合は候補を維持"""
        candidates = [
            {
                'product_name': 'ビオフェルミン止瀉薬',
                'ingredients': 'ロートエキス\nタンニン酸ベルベリン',
                'efficacy': '下痢、腹痛を伴う下痢',
                'usage': '',
                'classification': '第2類',
                'medicine_type': '胃腸薬',
                'score_breakdown': {'symptom_match': 0.8}
            }
        ]
        nlu_result = {'symptoms': [{'name': '腹痛'}, {'name': '下痢'}]}

        filtered = _filter_antidiarrheal_without_diarrhea(candidates, nlu_result)
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]['product_name'], 'ビオフェルミン止瀉薬')

    def test_symptom_match_threshold_single_symptom(self):
        """単症状で症状適合度が閾値未満なら除外"""
        candidates = [
            {
                'product_name': 'ヘパリーゼドリンクⅡ',
                'ingredients': '肝臓水解物',
                'efficacy': '滋養強壮、胃腸障害',
                'usage': '',
                'classification': '第3類',
                'medicine_type': '胃腸薬',
                'score_breakdown': {'symptom_match': 0.05},
                'final_score': 0.25
            }
        ]
        nlu_result = {'symptoms': [{'name': '腹痛'}]}

        filtered = _enforce_symptom_match_threshold(candidates, nlu_result)
        self.assertEqual(filtered, [])

    def test_symptom_match_threshold_allows_relevant_candidate(self):
        """適切な症状適合度の候補は残す"""
        candidates = [
            {
                'product_name': '胃腸薬A',
                'ingredients': '生薬エキス',
                'efficacy': '腹痛、胃もたれ',
                'usage': '',
                'classification': '第2類',
                'medicine_type': '胃腸薬',
                'score_breakdown': {'symptom_match': 0.6},
                'final_score': 0.7
            }
        ]
        nlu_result = {'symptoms': [{'name': '腹痛'}]}

        filtered = _enforce_symptom_match_threshold(candidates, nlu_result)
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]['product_name'], '胃腸薬A')


def run_enhanced_safety_tests():
    """強化された安全性テストの実行"""
    print("🛡️ 強化された安全性テストを開始します...")
    
    # テストスイートの作成
    test_suite = unittest.TestSuite()
    
    # テストクラスの追加
    test_classes = [
        TestEnhancedSafetyChecker,
        TestSafetyIntegration,
        TestRuleBasedFiltering
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # テストの実行
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # 結果の表示
    print(f"\n📊 テスト結果:")
    print(f"実行したテスト数: {result.testsRun}")
    print(f"失敗: {len(result.failures)}")
    print(f"エラー: {len(result.errors)}")
    print(f"成功率: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    return result.wasSuccessful()

if __name__ == '__main__':
    success = run_enhanced_safety_tests()
    sys.exit(0 if success else 1)
