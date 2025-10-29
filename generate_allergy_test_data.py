"""
アレルギー28品目を含む100件のテストデータを生成
"""

import csv
import random

def generate_allergy_test_data():
    """アレルギー28品目のテストデータを生成"""
    
    # アレルギー28品目
    ALLERGY_28_ITEMS = [
        'えび', 'かに', 'くるみ', '小麦', 'そば', '卵', '乳', '落花生',
        'ピーナッツ', 'アーモンド', 'あわび', 'いか', 'いくら', 'オレンジ',
        'カシューナッツ', 'キウイフルーツ', '牛肉', 'ごま', 'さけ', 'さば',
        '大豆', '鶏肉', 'バナナ', '豚肉', 'マカダミアナッツ', 'もも',
        'やまいも', 'りんご', 'ゼラチン'
    ]
    
    # 症状パターン
    SYMPTOMS = [
        '頭痛', '発熱', '咳', '鼻水', '鼻づまり', '喉の痛み', '肩こり', '腰痛',
        '胃痛', '胃もたれ', '吐き気', '下痢', '便秘', '腹痛', '目のかゆみ',
        '関節痛', '筋肉痛', 'めまい', '倦怠感', '疲れ', '不眠', '冷え', 'むくみ'
    ]
    
    # 年齢・性別パターン
    AGE_GENDER_PATTERNS = [
        "30代女性", "40代男性", "20代女性", "50代男性", "60代女性",
        "10歳の男の子", "5歳の女の子", "高齢の男性", "若い女性", "中年の男性"
    ]
    
    # アレルギー表現パターン
    ALLERGY_EXPRESSIONS = [
        "{}アレルギーです",
        "{}が食べられません",
        "{}で蕁麻疹が出ます",
        "{}にアレルギーがあります",
        "{}アレルギー体質です",
        "{}で発疹が出ます",
        "{}がダメです",
        "{}でかゆみが出ます"
    ]
    
    # 症状期間パターン
    DURATION_PATTERNS = [
        "昨日から", "2日前から", "3日前から", "1週間前から", "数日前から",
        "今朝から", "先週から", "数日間", "1週間続いています", "数日続いています"
    ]
    
    test_data = []
    
    # 各アレルギー品目について3-4パターン生成
    for i, allergy_item in enumerate(ALLERGY_28_ITEMS):
        for j in range(3):  # 各品目3パターン
            test_id = 501 + i * 3 + j
            
            # 年齢・性別を選択
            age_gender = random.choice(AGE_GENDER_PATTERNS)
            
            # アレルギー表現を選択
            allergy_expression = random.choice(ALLERGY_EXPRESSIONS).format(allergy_item)
            
            # 症状を選択
            symptom = random.choice(SYMPTOMS)
            
            # 期間を選択
            duration = random.choice(DURATION_PATTERNS)
            
            # 自然文を生成
            if j == 0:  # 単一アレルギー
                text = f"{age_gender}で{allergy_expression}。{duration}{symptom}があります。"
            elif j == 1:  # 複数アレルギー（2品目）
                other_allergy = random.choice([item for item in ALLERGY_28_ITEMS if item != allergy_item])
                text = f"{age_gender}で{allergy_item}と{other_allergy}のアレルギーがあります。{duration}{symptom}がひどいです。"
            else:  # アレルギー体質
                text = f"{age_gender}で{allergy_expression}。{duration}{symptom}と倦怠感があります。"
            
            test_data.append([test_id, text])
    
    # 複数アレルギーのパターンを追加（残り16件）
    for i in range(16):
        test_id = 501 + len(ALLERGY_28_ITEMS) * 3 + i
        
        # 2-3品目のアレルギーを選択
        num_allergies = random.choice([2, 3])
        selected_allergies = random.sample(ALLERGY_28_ITEMS, num_allergies)
        
        age_gender = random.choice(AGE_GENDER_PATTERNS)
        symptom = random.choice(SYMPTOMS)
        duration = random.choice(DURATION_PATTERNS)
        
        if num_allergies == 2:
            text = f"{age_gender}で{selected_allergies[0]}と{selected_allergies[1]}のアレルギーがあります。{duration}{symptom}が出ています。"
        else:
            text = f"{age_gender}で{selected_allergies[0]}、{selected_allergies[1]}、{selected_allergies[2]}のアレルギーがあります。{duration}{symptom}が続いています。"
        
        test_data.append([test_id, text])
    
    return test_data

def append_to_natural_language_csv():
    """自然文.csvにアレルギーテストデータを追加"""
    
    # 既存の自然文.csvを読み込み
    existing_data = []
    with open('自然文.csv', 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f, delimiter='\t')
        for row in reader:
            existing_data.append(row)
    
    # 新しいテストデータを生成
    new_data = generate_allergy_test_data()
    
    # 既存データと新しいデータを結合
    all_data = existing_data + new_data
    
    # 自然文.csvを更新
    with open('自然文.csv', 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f, delimiter='\t')
        for row in all_data:
            writer.writerow(row)
    
    print(f"自然文.csvを更新しました")
    print(f"既存データ: {len(existing_data)}件")
    print(f"新規データ: {len(new_data)}件")
    print(f"合計: {len(all_data)}件")

if __name__ == "__main__":
    append_to_natural_language_csv()
