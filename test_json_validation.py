#!/usr/bin/env python3
"""
JSON検証のテストスクリプト
修正後のjson_validator.pyが正常に動作することを確認
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from json_validator import safe_json_parse

def test_medicine_recommendation_schema():
    """医薬品推奨スキーマのテスト"""
    print("=== JSON検証テスト開始 ===")
    
    # 正常なJSONデータ（ChatGPTが返す形式）
    test_json = '''
    {
        "recommended_medicines": [
            {
                "number": 1,
                "product_name": "加香ヒマシ油",
                "manufacturer": "健栄製薬",
                "reason": "食あたりなどによる腹痛に効果が期待できるため。",
                "usage_notes": "過敏症の方や妊娠中の方は使用を避けるべきです。"
            },
            {
                "number": 2,
                "product_name": "高砂オウレン",
                "manufacturer": "高砂薬業",
                "reason": "胃部膨満感や消化不良に伴う腹痛に効果があるため。",
                "usage_notes": "妊娠中や授乳中の方、肝障害のある方は使用を避けるべきです。"
            }
        ],
        "usage_notes": "一般的な使用上の注意",
        "doctor_consultation": "症状が改善しない場合は医師にご相談ください。"
    }
    '''
    
    try:
        result = safe_json_parse(test_json, schema='medicine_recommendation')
        print("JSON検証成功")
        print(f"推奨医薬品数: {len(result['recommended_medicines'])}")
        for i, med in enumerate(result['recommended_medicines'], 1):
            print(f"  {i}. {med['product_name']} ({med['manufacturer']})")
        return True
    except Exception as e:
        print(f"JSON検証失敗: {e}")
        return False

def test_symptom_analysis_schema():
    """症状分析スキーマのテスト"""
    print("\n=== 症状分析スキーマテスト ===")
    
    test_json = '''
    {
        "symptoms": [
            {
                "name": "腹痛",
                "severity": "中等度",
                "duration_days": 1
            }
        ],
        "red_flags": [],
        "needs_escalation": false,
        "escalation_reason": ""
    }
    '''
    
    try:
        result = safe_json_parse(test_json, schema='symptom_analysis')
        print("症状分析スキーマ検証成功")
        print(f"症状数: {len(result['symptoms'])}")
        return True
    except Exception as e:
        print(f"症状分析スキーマ検証失敗: {e}")
        return False

if __name__ == "__main__":
    print("JSON検証テストを実行します...")
    
    success1 = test_medicine_recommendation_schema()
    success2 = test_symptom_analysis_schema()
    
    if success1 and success2:
        print("\nすべてのテストが成功しました！")
        sys.exit(0)
    else:
        print("\n一部のテストが失敗しました。")
        sys.exit(1)
