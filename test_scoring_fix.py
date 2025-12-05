"""
スコアリング修正の検証テスト
今回の修正が正確に機能しているかを確認
"""

import sys
import os
import io

# Windows環境での文字エンコーディング問題を回避
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 現在のディレクトリをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from medicine_logic import rule_based_medicine_recommendation, client
import statistics

def test_score_range():
    """テスト1: スコアの範囲が0.7-0.98に収まっているか"""
    print("\n" + "="*80)
    print("テスト1: スコアの範囲検証（0.7-0.98）")
    print("="*80)
    
    test_cases = [
        ("のどが痛いです。", {"age": 30, "gender": "男性"}),
        ("頭が痛いです。", {"age": 25, "gender": "女性"}),
        ("鼻水とくしゃみが止まりません。", {"age": 35, "gender": "女性"}),
        ("肩がこります。", {"age": 30, "gender": "男性"}),
        ("胃が痛いです。", {"age": 30, "gender": "男性"}),
    ]
    
    all_scores = []
    score_ranges = []
    
    for user_text, user_info in test_cases:
        user_info_full = {
            **user_info,
            "pregnant": False,
            "breastfeeding": False,
            "current_medications": [],
            "allergies": []
        }
        
        result = rule_based_medicine_recommendation(user_text, user_info_full, client)
        
        if result.get('status') == 'success':
            medicines = result.get('recommended_medicines', [])
            if medicines:
                scores = [m.get('score', 0) for m in medicines[:3]]
                relative_scores = [m.get('relative_score') for m in medicines[:3] if m.get('relative_score') is not None]
                score_levels = [m.get('score_level') for m in medicines[:3] if m.get('score_level')]
                
                all_scores.extend(scores)
                if scores:
                    score_ranges.append((min(scores), max(scores)))
                
                print(f"\n入力: {user_text}")
                print(f"  スコア範囲: {min(scores):.3f} - {max(scores):.3f}")
                if relative_scores:
                    print(f"  相対スコア: {[f'{s*100:.1f}%' for s in relative_scores[:3]]}")
                if score_levels:
                    print(f"  スコア帯: {score_levels[:3]}")
    
    if all_scores:
        print(f"\n【全体統計】")
        print(f"  全スコア数: {len(all_scores)}")
        print(f"  平均スコア: {statistics.mean(all_scores):.3f}")
        print(f"  中央値: {statistics.median(all_scores):.3f}")
        print(f"  最小スコア: {min(all_scores):.3f}")
        print(f"  最大スコア: {max(all_scores):.3f}")
        print(f"  標準偏差: {statistics.stdev(all_scores) if len(all_scores) > 1 else 0:.3f}")
        
        # 0.7-0.98の範囲に収まっているか確認
        scores_in_range = [s for s in all_scores if 0.7 <= s <= 0.98]
        percentage = (len(scores_in_range) / len(all_scores)) * 100 if all_scores else 0
        print(f"\n  0.7-0.98の範囲内のスコア: {len(scores_in_range)}/{len(all_scores)} ({percentage:.1f}%)")
        
        # 最大スコアが0.98程度か確認
        if max(all_scores) <= 0.98:
            print(f"  ✅ 最大スコアが0.98以下: {max(all_scores):.3f}")
        else:
            print(f"  ⚠️ 最大スコアが0.98を超えています: {max(all_scores):.3f}")
        
        # スコアの分散を確認
        if statistics.stdev(all_scores) > 0.05:
            print(f"  ✅ スコアの分散が確保されています（標準偏差: {statistics.stdev(all_scores):.3f}）")
        else:
            print(f"  ⚠️ スコアの分散が不足しています（標準偏差: {statistics.stdev(all_scores):.3f}）")

def test_specialized_medicine_bonus():
    """テスト2: 特化医薬品のボーナスが適切に機能しているか"""
    print("\n" + "="*80)
    print("テスト2: 特化医薬品のボーナス検証")
    print("="*80)
    
    # のどの痛み特化医薬品のテスト
    user_text = "のどが痛いです。"
    user_info = {
        "age": 30,
        "gender": "男性",
        "pregnant": False,
        "breastfeeding": False,
        "current_medications": [],
        "allergies": []
    }
    
    result = rule_based_medicine_recommendation(user_text, user_info, client)
    
    if result.get('status') == 'success':
        medicines = result.get('recommended_medicines', [])
        if medicines:
            print(f"\n推奨された上位3つの医薬品:")
            for i, med in enumerate(medicines[:3], 1):
                score = med.get('score', 0)
                score_breakdown = med.get('score_breakdown', {})
                product_name = med.get('product_name', '')
                throat_bonus = score_breakdown.get('throat_bonus', 0)
                symptom_boost = score_breakdown.get('symptom_specific_boost', 0)
                
                print(f"\n  {i}. {product_name}")
                print(f"     スコア: {score:.3f}")
                print(f"     throat_bonus: {throat_bonus:.3f}")
                print(f"     symptom_boost: {symptom_boost:.3f}")
                
                # のど特化医薬品か確認
                if "のど" in product_name or "のどの痛み" in med.get('efficacy', ''):
                    if throat_bonus > 0 or symptom_boost > 0:
                        print(f"     ✅ のど特化医薬品にボーナスが適用されています")
                    else:
                        print(f"     ⚠️ のど特化医薬品なのにボーナスが適用されていません")
            
            # のど特化医薬品が上位に来ているか確認
            throat_specific = [m for m in medicines[:3] if "のど" in m.get('product_name', '') or "のどの痛み" in m.get('efficacy', '')]
            if throat_specific:
                print(f"\n  ✅ のど特化医薬品が上位に推奨されています: {[m.get('product_name') for m in throat_specific]}")
            else:
                print(f"\n  ⚠️ のど特化医薬品が上位に推奨されていません")

def test_inappropriate_medicine_penalty():
    """テスト3: 不適切な医薬品のペナルティが適切に機能しているか"""
    print("\n" + "="*80)
    print("テスト3: 不適切な医薬品のペナルティ検証")
    print("="*80)
    
    # のどの痛みのみの場合、せき・たん用医薬品が下位に来るか確認
    user_text = "のどが痛いです。"
    user_info = {
        "age": 30,
        "gender": "男性",
        "pregnant": False,
        "breastfeeding": False,
        "current_medications": [],
        "allergies": []
    }
    
    result = rule_based_medicine_recommendation(user_text, user_info, client)
    
    if result.get('status') == 'success':
        medicines = result.get('recommended_medicines', [])
        if medicines:
            print(f"\n推奨された全医薬品（上位10件）:")
            cough_medicines = []
            throat_specific_medicines = []
            
            for i, med in enumerate(medicines[:10], 1):
                score = med.get('score', 0)
                score_breakdown = med.get('score_breakdown', {})
                product_name = med.get('product_name', '')
                efficacy = med.get('efficacy', '')
                symptom_penalty = score_breakdown.get('symptom_specificity_penalty', 0)
                medicine_type = med.get('medicine_type', '')
                
                # せき・たん用医薬品か確認（のどの痛みが主効能でない場合）
                is_cough_medicine = (
                    ("せき" in efficacy or "咳" in efficacy) and 
                    ("たん" in efficacy or "痰" in efficacy) and
                    "のどの痛み" not in efficacy and
                    "のど" not in product_name
                )
                
                # のど特化医薬品か確認
                is_throat_specific = (
                    "のど" in product_name or 
                    "のどの痛み" in efficacy or
                    ("のど" in efficacy and "せき" not in efficacy and "たん" not in efficacy)
                )
                
                if is_cough_medicine:
                    cough_medicines.append((i, med, score, symptom_penalty))
                    print(f"\n  {i}. {product_name} (せき・たん用)")
                    print(f"     スコア: {score:.3f}")
                    print(f"     症状特異性ペナルティ: {symptom_penalty:.3f}")
                    print(f"     効能: {efficacy[:80]}...")
                    
                    if symptom_penalty < -0.1:
                        print(f"     ✅ 適切なペナルティが適用されています")
                    else:
                        print(f"     ⚠️ ペナルティが弱すぎる可能性があります")
                    
                    if i <= 3:
                        print(f"     ⚠️ 警告: せき・たん用医薬品が上位3位以内にあります（ペナルティが不十分の可能性）")
                    else:
                        print(f"     ✅ せき・たん用医薬品が下位に配置されています（ペナルティが機能）")
                
                if is_throat_specific:
                    throat_specific_medicines.append((i, med, score))
            
            # 統計情報
            print(f"\n【統計情報】")
            print(f"  のど特化医薬品数: {len(throat_specific_medicines)}")
            if throat_specific_medicines:
                throat_ranks = [r[0] for r in throat_specific_medicines]
                print(f"  のど特化医薬品の順位: {throat_ranks}")
                if min(throat_ranks) <= 3:
                    print(f"  ✅ のど特化医薬品が上位に推奨されています")
            
            print(f"  せき・たん用医薬品数: {len(cough_medicines)}")
            if cough_medicines:
                cough_ranks = [r[0] for r in cough_medicines]
                cough_scores = [r[2] for r in cough_medicines]
                cough_penalties = [r[3] for r in cough_medicines]
                print(f"  せき・たん用医薬品の順位: {cough_ranks}")
                print(f"  せき・たん用医薬品のスコア: {[f'{s:.3f}' for s in cough_scores]}")
                print(f"  せき・たん用医薬品のペナルティ: {[f'{p:.3f}' for p in cough_penalties]}")
                
                if min(cough_ranks) > 3:
                    print(f"  ✅ せき・たん用医薬品が下位に配置されています（ペナルティが機能）")
                else:
                    print(f"  ⚠️ せき・たん用医薬品が上位にあります（ペナルティが不十分の可能性）")
                
                # のど特化医薬品とせき・たん用医薬品のスコア比較
                if throat_specific_medicines and cough_medicines:
                    throat_avg_score = statistics.mean([r[2] for r in throat_specific_medicines])
                    cough_avg_score = statistics.mean(cough_scores)
                    score_diff = throat_avg_score - cough_avg_score
                    print(f"\n  のど特化医薬品の平均スコア: {throat_avg_score:.3f}")
                    print(f"  せき・たん用医薬品の平均スコア: {cough_avg_score:.3f}")
                    print(f"  スコア差: {score_diff:.3f}")
                    if score_diff > 0.1:
                        print(f"  ✅ のど特化医薬品が適切に優位になっています")
                    else:
                        print(f"  ⚠️ のど特化医薬品とせき・たん用医薬品のスコア差が小さい")
            else:
                print(f"  ⚠️ せき・たん用医薬品が検出されませんでした（テストケースの改善が必要）")

def test_score_diversity():
    """テスト4: スコアの分散が確保されているか"""
    print("\n" + "="*80)
    print("テスト4: スコアの分散検証")
    print("="*80)
    
    user_text = "のどが痛いです。"
    user_info = {
        "age": 30,
        "gender": "男性",
        "pregnant": False,
        "breastfeeding": False,
        "current_medications": [],
        "allergies": []
    }
    
    result = rule_based_medicine_recommendation(user_text, user_info, client)
    
    if result.get('status') == 'success':
        medicines = result.get('recommended_medicines', [])
        if medicines and len(medicines) >= 3:
            scores = [m.get('score', 0) for m in medicines[:10]]  # 上位10件のスコア
            
            print(f"\n上位10件のスコア:")
            for i, score in enumerate(scores, 1):
                print(f"  {i}. {score:.3f}")
            
            # スコアの分散を確認
            if len(scores) > 1:
                score_range = max(scores) - min(scores)
                score_std = statistics.stdev(scores) if len(scores) > 1 else 0
                
                print(f"\n【分散統計】")
                print(f"  スコア範囲: {min(scores):.3f} - {max(scores):.3f} (範囲: {score_range:.3f})")
                print(f"  標準偏差: {score_std:.3f}")
                
                if score_range > 0.1:
                    print(f"  ✅ スコアの分散が確保されています（範囲: {score_range:.3f}）")
                else:
                    print(f"  ⚠️ スコアの分散が不足しています（範囲: {score_range:.3f}）")
                
                # 1位と2位のスコア差を確認
                if len(scores) >= 2:
                    score_diff = scores[0] - scores[1]
                    print(f"  1位と2位のスコア差: {score_diff:.3f}")
                    if score_diff > 0.01:
                        print(f"  ✅ 1位と2位のスコア差が確保されています")
                    else:
                        print(f"  ⚠️ 1位と2位のスコア差が小さすぎます")

def test_relative_score():
    """テスト5: 相対スコア化が機能しているか"""
    print("\n" + "="*80)
    print("テスト5: 相対スコア化の検証")
    print("="*80)
    
    user_text = "のどが痛いです。"
    user_info = {
        "age": 30,
        "gender": "男性",
        "pregnant": False,
        "breastfeeding": False,
        "current_medications": [],
        "allergies": []
    }
    
    result = rule_based_medicine_recommendation(user_text, user_info, client)
    
    if result.get('status') == 'success':
        medicines = result.get('recommended_medicines', [])
        if medicines:
            print(f"\n上位3つの医薬品のスコア比較:")
            for i, med in enumerate(medicines[:3], 1):
                score = med.get('score', 0)
                relative_score = med.get('relative_score')
                score_level = med.get('score_level', '中')
                product_name = med.get('product_name', '')
                
                print(f"\n  {i}. {product_name}")
                print(f"     絶対スコア: {score:.3f}")
                if relative_score is not None:
                    print(f"     相対スコア: {relative_score*100:.1f}%")
                    print(f"     スコア帯: {score_level}")
                else:
                    print(f"     ⚠️ 相対スコアが設定されていません")
            
            # 相対スコアが設定されているか確認
            relative_scores = [m.get('relative_score') for m in medicines[:3] if m.get('relative_score') is not None]
            if relative_scores:
                print(f"\n  ✅ 相対スコアが設定されています")
                # 最高スコアが100%になっているか確認
                if max(relative_scores) >= 0.99:
                    print(f"  ✅ 最高スコアが100%になっています（{max(relative_scores)*100:.1f}%）")
                else:
                    print(f"  ⚠️ 最高スコアが100%になっていません（{max(relative_scores)*100:.1f}%）")
            else:
                print(f"\n  ⚠️ 相対スコアが設定されていません")

def test_max_score_limit():
    """テスト6: 最大スコアが0.98程度に制限されているか"""
    print("\n" + "="*80)
    print("テスト6: 最大スコアの制限検証（0.98程度）")
    print("="*80)
    
    test_cases = [
        ("のどが痛いです。", {"age": 30, "gender": "男性"}),
        ("頭が痛いです。", {"age": 25, "gender": "女性"}),
        ("肩がこります。", {"age": 30, "gender": "男性"}),
        ("鼻水とくしゃみが止まりません。", {"age": 35, "gender": "女性"}),
    ]
    
    max_scores = []
    
    for user_text, user_info in test_cases:
        user_info_full = {
            **user_info,
            "pregnant": False,
            "breastfeeding": False,
            "current_medications": [],
            "allergies": []
        }
        
        result = rule_based_medicine_recommendation(user_text, user_info_full, client)
        
        if result.get('status') == 'success':
            medicines = result.get('recommended_medicines', [])
            if medicines:
                scores = [m.get('score', 0) for m in medicines[:3]]
                max_score = max(scores)
                max_scores.append(max_score)
                
                print(f"\n入力: {user_text}")
                print(f"  最大スコア: {max_score:.3f}")
                
                if max_score <= 0.98:
                    print(f"  ✅ 最大スコアが0.98以下です")
                else:
                    print(f"  ⚠️ 最大スコアが0.98を超えています")
    
    if max_scores:
        avg_max_score = statistics.mean(max_scores)
        print(f"\n【全体統計】")
        print(f"  平均最大スコア: {avg_max_score:.3f}")
        print(f"  最大スコアの範囲: {min(max_scores):.3f} - {max(max_scores):.3f}")
        
        if avg_max_score <= 0.98:
            print(f"  ✅ 平均最大スコアが0.98以下です")
        else:
            print(f"  ⚠️ 平均最大スコアが0.98を超えています")

def test_bonus_penalty_effectiveness():
    """テスト7: ボーナス/ペナルティの効果検証"""
    print("\n" + "="*80)
    print("テスト7: ボーナス/ペナルティの効果検証")
    print("="*80)
    
    user_text = "のどが痛いです。"
    user_info = {
        "age": 30,
        "gender": "男性",
        "pregnant": False,
        "breastfeeding": False,
        "current_medications": [],
        "allergies": []
    }
    
    result = rule_based_medicine_recommendation(user_text, user_info, client)
    
    if result.get('status') == 'success':
        medicines = result.get('recommended_medicines', [])
        if medicines:
            print(f"\n上位5つの医薬品のスコア内訳:")
            for i, med in enumerate(medicines[:5], 1):
                score = med.get('score', 0)
                score_breakdown = med.get('score_breakdown', {})
                product_name = med.get('product_name', '')
                
                base_score = score_breakdown.get('base_score')
                adjustment_score = score_breakdown.get('adjustment_score')
                throat_bonus = score_breakdown.get('throat_bonus', 0)
                symptom_boost = score_breakdown.get('symptom_specific_boost', 0)
                symptom_penalty = score_breakdown.get('symptom_specificity_penalty', 0)
                
                print(f"\n  {i}. {product_name}")
                print(f"     総合スコア: {score:.3f}")
                if base_score is not None:
                    print(f"     基本スコア: {base_score:.3f}")
                if adjustment_score is not None:
                    print(f"     調整スコア: {adjustment_score:.3f}")
                print(f"     throat_bonus: {throat_bonus:.3f}")
                print(f"     symptom_boost: {symptom_boost:.3f}")
                print(f"     symptom_penalty: {symptom_penalty:.3f}")
                
                # ボーナス/ペナルティの制限を確認
                if abs(throat_bonus) > 0.25:
                    print(f"     ⚠️ throat_bonusが制限（0.25）を超えています")
                if abs(symptom_boost) > 0.25:
                    print(f"     ⚠️ symptom_boostが制限（0.25）を超えています")
                if symptom_penalty < -0.30:
                    print(f"     ⚠️ symptom_penaltyが制限（-0.30）を超えています")

def main():
    """メイン実行関数"""
    print("\n" + "="*80)
    print("スコアリング修正の検証テスト")
    print("="*80)
    
    try:
        test_score_range()
        test_specialized_medicine_bonus()
        test_inappropriate_medicine_penalty()
        test_score_diversity()
        test_relative_score()
        test_max_score_limit()
        test_bonus_penalty_effectiveness()
        
        print("\n" + "="*80)
        print("[OK] 全テスト完了")
        print("="*80)
        
    except Exception as e:
        print(f"\n[ERROR] テスト実行中にエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

