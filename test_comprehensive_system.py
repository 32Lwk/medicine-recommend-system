#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
包括的な医薬品推奨システムのテストスクリプト
"""

import sys
import os

# 現在のディレクトリをパスに追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from medicine_logic import comprehensive_medicine_recommendation

def test_comprehensive_system():
    """包括的な医薬品推奨システムをテスト"""
    
    # テスト用の症状文
    test_symptoms = [
        "頭痛がひどくて、熱もあります",
        "喉が痛くて、咳も出ます",
        "胃が痛くて、吐き気がします",
        "目がかゆくて、充血しています",
        "鼻水が出て、くしゃみが止まりません"
    ]
    
    print("=== 包括的医薬品推奨システム テスト開始 ===")
    print()
    
    for i, symptom in enumerate(test_symptoms, 1):
        print(f"テストケース {i}: {symptom}")
        print("-" * 50)
        
        try:
            result = comprehensive_medicine_recommendation(symptom)
            
            print(f"症状: {result.get('symptoms', [])}")
            print(f"医薬品の種類: {result.get('medicine_type', '')}")
            print(f"推奨医薬品数: {len(result.get('recommended_medicines', []))}")
            
            if result.get('recommended_medicines'):
                print("推奨医薬品:")
                for medicine in result['recommended_medicines']:
                    print(f"  {medicine.get('rank', '')}位: {medicine.get('product_name', '')} ({medicine.get('manufacturer', '')})")
                    print(f"    推奨理由: {medicine.get('reason', '')}")
            
            print(f"使用上の注意: {result.get('usage_notes', '')}")
            print(f"医師の受診が必要な場合: {result.get('doctor_consultation', '')}")
            
        except Exception as e:
            print(f"エラー: {e}")
        
        print()
        print("=" * 60)
        print()

if __name__ == "__main__":
    test_comprehensive_system() 