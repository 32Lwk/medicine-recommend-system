"""
自然文.csvの事前分析とアノテーション
各自然文から属性情報を抽出し、Googleスプレッドシート形式のCSVファイルを作成
"""

import csv
import os
import re
from openai import OpenAI

def analyze_natural_language_csv():
    """自然文.csvを分析して属性情報を抽出"""
    
    # OpenAI API設定
    os.environ['OPENAI_API_KEY'] = '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'
    client = OpenAI()
    
    input_file = '自然文.csv'
    output_file = '自然文_アノテーション.csv'
    
    # 結果を格納するリスト
    results = []
    
    print("自然文.csvの分析を開始します...")
    
    try:
        with open(input_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.reader(f, delimiter='\t')
            for i, row in enumerate(reader, 1):
                if len(row) < 2:
                    continue
                
                test_id, user_text = row[0], row[1]
                
                print(f"分析中: {i}/500 - {user_text[:30]}...")
                
                # 属性抽出を実行
                try:
                    extracted_attrs = extract_attributes_with_ai(user_text, client)
                    
                    # 結果を格納
                    result = {
                        'test_id': test_id,
                        'input_text': user_text,
                        'age': extracted_attrs.get('age', 'null'),
                        'gender': extracted_attrs.get('gender', 'null'),
                        'pregnant': extracted_attrs.get('pregnant', 'null'),
                        'breastfeeding': extracted_attrs.get('breastfeeding', 'null'),
                        'allergies': extracted_attrs.get('allergies', 'null'),
                        'current_medications': extracted_attrs.get('current_medications', 'null'),
                        'medical_history': extracted_attrs.get('medical_history', 'null'),
                        'constitution': extracted_attrs.get('constitution', 'null'),
                        'doping_concern': extracted_attrs.get('doping_concern', 'null'),
                        'symptoms': extract_symptoms(user_text),
                        'detected_language': extracted_attrs.get('detected_language', 'ja')
                    }
                    
                    results.append(result)
                    
                except Exception as e:
                    print(f"エラー (ID: {test_id}): {e}")
                    # エラーの場合はnullで埋める
                    result = {
                        'test_id': test_id,
                        'input_text': user_text,
                        'age': 'null',
                        'gender': 'null',
                        'pregnant': 'null',
                        'breastfeeding': 'null',
                        'allergies': 'null',
                        'current_medications': 'null',
                        'medical_history': 'null',
                        'constitution': 'null',
                        'doping_concern': 'null',
                        'symptoms': extract_symptoms(user_text),
                        'detected_language': 'ja'
                    }
                    results.append(result)
                
                # 進捗表示（50件ごと）
                if i % 50 == 0:
                    print(f"進捗: {i}/500 完了")
    
    except Exception as e:
        print(f"ファイル読み込みエラー: {e}")
        return
    
    # 結果をCSVファイルに保存
    save_results_to_csv(results, output_file)
    
    print(f"\n分析完了: {len(results)}件のデータを処理しました")
    print(f"結果を {output_file} に保存しました")

def extract_attributes_with_ai(user_text, client):
    """AIを使用して属性を抽出"""
    
    prompt = f"""
以下の自然文から属性情報を抽出してください。

入力テキスト: {user_text}

抽出する属性:
1. 年齢 (age): 数字のみ（例: 30, 35, 40）
2. 性別 (gender): 男性/女性
3. 妊娠中 (pregnant): true/false
4. 授乳中 (breastfeeding): true/false
5. アレルギー (allergies): アレルギー名のリスト
6. 服用中の薬 (current_medications): 薬の名前のリスト
7. 既往症 (medical_history): 病気名のリスト
8. 体質 (constitution): 冷え性、アレルギー体質など
9. ドーピング懸念 (doping_concern): true/false
10. 症状 (symptoms): 症状のリスト

【抽出ルール】
- 年齢: "30代" → 35, "25歳" → 25, "10歳" → 10
- 性別: "女性"、"男性"、"女の子"、"男の子"から判定
- 妊娠中: "妊娠中"、"妊娠"、"妊娠5ヶ月"など
- 授乳中: "授乳中"、"授乳"など
- アレルギー: "アレルギー"、"花粉症"、"アトピー"など
- 服用中の薬: "薬を飲んでいます"、"服用中"など
- 既往症: "糖尿病"、"高血圧"、"便秘"など
- 体質: "冷え性"、"アレルギー体質"、"便秘しやすい"など
- ドーピング懸念: "ドーピング"、"運動"など
- 症状: 具体的な症状（頭痛、発熱、咳など）

【回答形式】
以下のJSON形式で回答してください：
{{
    "age": 数値またはnull,
    "gender": "男性"または"女性"またはnull,
    "pregnant": trueまたはfalse,
    "breastfeeding": trueまたはfalse,
    "allergies": ["アレルギー名"]または[],
    "current_medications": ["薬名"]または[],
    "medical_history": ["病気名"]または[],
    "constitution": "体質"またはnull,
    "doping_concern": trueまたはfalse,
    "symptoms": ["症状名"]または[]
}}
"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {"role": "system", "content": "あなたは属性抽出の専門家です。自然文から正確に属性情報を抽出してください。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0,
            max_completion_tokens=1000
        )
        
        result = response.choices[0].message.content
        
        # JSON解析
        import json
        json_start = result.find('{')
        json_end = result.rfind('}') + 1
        if json_start != -1 and json_end != -1:
            json_str = result[json_start:json_end]
            parsed_result = json.loads(json_str)
            parsed_result['detected_language'] = 'ja'
            return parsed_result
    
    except Exception as e:
        print(f"AI抽出エラー: {e}")
    
    # エラーの場合は空の結果を返す
    return {
        'age': None,
        'gender': None,
        'pregnant': False,
        'breastfeeding': False,
        'allergies': [],
        'current_medications': [],
        'medical_history': [],
        'constitution': None,
        'doping_concern': False,
        'symptoms': []
    }

def extract_symptoms(user_text):
    """症状を抽出（ルールベース）"""
    symptoms = []
    
    # 症状のキーワード
    symptom_keywords = [
        '頭痛', '発熱', '咳', '鼻水', '鼻づまり', '喉の痛み', '喉が痛い', '肩こり', '腰痛',
        '胃痛', '胃もたれ', '吐き気', '下痢', '便秘', '腹痛', '目のかゆみ', '目が乾く',
        '関節痛', '筋肉痛', 'めまい', '立ちくらみ', '倦怠感', '疲れ', '不眠', '眠れない',
        '冷え', 'むくみ', 'かゆみ', '湿疹', 'アレルギー', '花粉症', 'くしゃみ', '鼻血',
        '声がかすれる', '息苦しい', '胸の痛み', '動悸', '息切れ', '手足のしびれ',
        '生理痛', '生理不順', 'つわり', '更年期', 'イライラ', '不安', 'ストレス'
    ]
    
    for keyword in symptom_keywords:
        if keyword in user_text:
            symptoms.append(keyword)
    
    return symptoms

def save_results_to_csv(results, output_file):
    """結果をCSVファイルに保存"""
    
    # ヘッダー
    headers = [
        'test_id', 'input_text', 'age', 'gender', 'pregnant', 'breastfeeding',
        'allergies', 'current_medications', 'medical_history', 'constitution',
        'doping_concern', 'symptoms', 'detected_language'
    ]
    
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        
        for result in results:
            # リスト型の値を文字列に変換
            row = []
            for header in headers:
                value = result.get(header, 'null')
                if isinstance(value, list):
                    if value:
                        row.append('; '.join(value))
                    else:
                        row.append('null')
                elif value is None:
                    row.append('null')
                else:
                    row.append(str(value))
            
            writer.writerow(row)
    
    print(f"結果を {output_file} に保存しました")

if __name__ == "__main__":
    analyze_natural_language_csv()
