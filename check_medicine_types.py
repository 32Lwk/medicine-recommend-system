#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
医薬品の種類カラムの内容を確認するスクリプト
"""

import pandas as pd
import os

def check_medicine_types():
    """医薬品の種類カラムの内容を確認"""
    
    csv_path = "otc_medicine_data.csv"
    
    print("=== 医薬品の種類カラム確認 ===")
    
    try:
        df = pd.read_csv(csv_path, encoding='utf-8')
        print(f"読み込み成功 - 行数: {len(df)}, 列数: {len(df.columns)}")
        print(f"列名: {list(df.columns)}")
        
        # 医薬品の種類カラムの内容を確認
        if '医薬品の種類' in df.columns:
            print("\n=== 医薬品の種類カラムの内容確認 ===")
            print(f"医薬品の種類カラムのユニーク値数: {df['医薬品の種類'].nunique()}")
            print(f"医薬品の種類カラムのサンプル値（最初の30個）:")
            unique_values = df['医薬品の種類'].dropna().unique()
            for i, value in enumerate(unique_values[:30]):
                print(f"  {i+1}: {value}")
            
            # 各医薬品の種類の件数
            print(f"\n=== 医薬品の種類別件数（上位30件） ===")
            medicine_type_counts = df['医薬品の種類'].value_counts()
            for i, (medicine_type, count) in enumerate(medicine_type_counts.head(30).items()):
                print(f"  {i+1}: {medicine_type} - {count}件")
                
        else:
            print("医薬品の種類カラムが見つかりません")
            print(f"利用可能な列名: {list(df.columns)}")
            
    except Exception as e:
        print(f"CSVファイル読み込みエラー: {e}")

def test_medicine_type_matching():
    """医薬品の種類とのマッチングをテスト"""
    
    print("\n=== 医薬品の種類マッチングテスト ===")
    
    # 医薬品の種類リスト
    medicine_types = [
        "筋肉痛", "睡眠障害", "精神症状", "その他", "胃腸薬", 
        "解熱鎮痛薬", "外用薬(皮膚)", "抗アレルギー薬", "殺虫剤", 
        "鼻炎用薬", "風邪薬", "目薬"
    ]
    
    try:
        df = pd.read_csv("otc_medicine_data.csv", encoding='utf-8')
        
        if '医薬品の種類' in df.columns:
            print("各医薬品の種類でのマッチング結果:")
            for medicine_type in medicine_types:
                # 部分一致検索
                matched = df[df['医薬品の種類'].astype(str).str.contains(medicine_type, na=False)]
                print(f"  {medicine_type}: {len(matched)}件")
                
                # 最初の3件の例を表示
                if len(matched) > 0:
                    print(f"    例: {matched['製品名'].iloc[0]} ({matched['メーカー名'].iloc[0]})")
                    if len(matched) > 1:
                        print(f"    例: {matched['製品名'].iloc[1]} ({matched['メーカー名'].iloc[1]})")
                    if len(matched) > 2:
                        print(f"    例: {matched['製品名'].iloc[2]} ({matched['メーカー名'].iloc[2]})")
                print()
        else:
            print("医薬品の種類カラムが見つかりません")
            
    except Exception as e:
        print(f"マッチングテストエラー: {e}")

if __name__ == "__main__":
    check_medicine_types()
    test_medicine_type_matching() 