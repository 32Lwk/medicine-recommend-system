"""
ルールベース医薬品推奨システム
風邪薬、解熱鎮痛薬、鼻炎用薬の3種類に特化

ChatGPT APIはNLU（症状抽出）のみに使用し、
医薬品推奨は登録販売者の判断を再現するルールベース/スコアリング型アルゴリズムで実装
"""

import pandas as pd
import os
import json
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from openai import OpenAI

# ================================================================================
# 1. データ構造と定数定義
# ================================================================================

# 症状辞書（風邪薬、解熱鎮痛薬、鼻炎用薬に関連する症状のみ）
SYMPTOM_DICTIONARY = {
    # 風邪関連症状
    "発熱": {
        "canonical_name": "発熱",
        "synonyms": ["熱がある", "熱っぽい", "高熱", "微熱", "体温が高い", "熱"],
        "severity_tags": ["軽度", "中等度", "重度"],
        "medicine_types": ["風邪薬", "解熱鎮痛薬"],
        "weight": 0.9
    },
    "頭痛": {
        "canonical_name": "頭痛",
        "synonyms": ["頭が痛い", "ズキズキする", "頭が重い", "偏頭痛"],
        "severity_tags": ["軽度", "中等度", "重度"],
        "medicine_types": ["風邪薬", "解熱鎮痛薬"],
        "weight": 0.85
    },
    "のどの痛み": {
        "canonical_name": "のどの痛み",
        "synonyms": ["喉が痛い", "喉の痛み", "のどが痛い", "咽頭痛", "喉の腫れ"],
        "severity_tags": ["軽度", "中等度", "重度"],
        "medicine_types": ["風邪薬"],
        "weight": 0.9
    },
    "咳": {
        "canonical_name": "咳",
        "synonyms": ["せき", "咳が出る", "咳込む", "空咳"],
        "severity_tags": ["軽度", "中等度", "重度"],
        "medicine_types": ["風邪薬"],
        "weight": 0.85
    },
    "痰": {
        "canonical_name": "痰",
        "synonyms": ["たん", "痰が絡む", "痰が出る"],
        "severity_tags": ["軽度", "中等度"],
        "medicine_types": ["風邪薬"],
        "weight": 0.8
    },
    "鼻水": {
        "canonical_name": "鼻水",
        "synonyms": ["鼻みず", "鼻汁", "鼻が出る", "水っぽい鼻水"],
        "severity_tags": ["軽度", "中等度"],
        "medicine_types": ["風邪薬", "鼻炎用薬"],
        "weight": 0.85
    },
    "鼻づまり": {
        "canonical_name": "鼻づまり",
        "synonyms": ["鼻詰まり", "鼻が詰まる", "鼻閉"],
        "severity_tags": ["軽度", "中等度"],
        "medicine_types": ["風邪薬", "鼻炎用薬"],
        "weight": 0.85
    },
    "くしゃみ": {
        "canonical_name": "くしゃみ",
        "synonyms": ["クシャミ", "くしゃみが出る"],
        "severity_tags": ["軽度", "中等度"],
        "medicine_types": ["風邪薬", "鼻炎用薬"],
        "weight": 0.8
    },
    "悪寒": {
        "canonical_name": "悪寒",
        "synonyms": ["寒気", "さむけ", "ゾクゾクする", "悪寒がする"],
        "severity_tags": ["軽度", "中等度", "重度"],
        "medicine_types": ["風邪薬"],
        "weight": 0.85
    },
    "関節痛": {
        "canonical_name": "関節痛",
        "synonyms": ["関節の痛み", "節々が痛い", "関節が痛い"],
        "severity_tags": ["軽度", "中等度"],
        "medicine_types": ["風邪薬", "解熱鎮痛薬"],
        "weight": 0.8
    },
    "筋肉痛": {
        "canonical_name": "筋肉痛",
        "synonyms": ["筋肉の痛み", "体が痛い", "筋肉が痛い"],
        "severity_tags": ["軽度", "中等度"],
        "medicine_types": ["風邪薬", "解熱鎮痛薬"],
        "weight": 0.75
    },
    # 解熱鎮痛薬関連症状
    "生理痛": {
        "canonical_name": "生理痛",
        "synonyms": ["月経痛", "生理の痛み", "下腹部痛"],
        "severity_tags": ["軽度", "中等度", "重度"],
        "medicine_types": ["解熱鎮痛薬"],
        "weight": 0.95
    },
    "歯痛": {
        "canonical_name": "歯痛",
        "synonyms": ["歯が痛い", "歯の痛み"],
        "severity_tags": ["軽度", "中等度", "重度"],
        "medicine_types": ["解熱鎮痛薬"],
        "weight": 0.9
    },
    # 鼻炎用薬関連症状
    "鼻汁過多": {
        "canonical_name": "鼻汁過多",
        "synonyms": ["鼻水が多い", "鼻水がとまらない"],
        "severity_tags": ["軽度", "中等度"],
        "medicine_types": ["鼻炎用薬"],
        "weight": 0.9
    },
    "なみだ目": {
        "canonical_name": "なみだ目",
        "synonyms": ["涙目", "目がかゆい", "目の痒み"],
        "severity_tags": ["軽度", "中等度"],
        "medicine_types": ["鼻炎用薬"],
        "weight": 0.7
    }
}

# 重症疑い症状（赤旗：Red Flag）- 即座にエスカレーション
RED_FLAG_SYMPTOMS = {
    "呼吸困難": ["呼吸が苦しい", "息苦しい", "呼吸困難", "息ができない"],
    "高熱": ["38.5度以上", "39度", "40度"],
    "胸痛": ["胸が痛い", "胸の痛み", "胸部痛"],
    "意識障害": ["意識がもうろう", "意識がない", "気を失う"],
    "激しい頭痛": ["激しい頭痛", "突然の頭痛", "今まで経験したことのない頭痛"],
    "血便": ["血便", "便に血が混じる"],
    "喀血": ["血を吐く", "喀血", "吐血"]
}

# 禁忌チェックルール
CONTRAINDICATION_RULES = {
    "年齢制限": {
        "最小年齢": 7,  # 7歳未満は医師相談
        "推奨年齢": 15  # 15歳未満は注意が必要
    },
    "妊娠中": {
        "風邪薬": "要注意",
        "解熱鎮痛薬": "禁忌（特にNSAIDs）",
        "鼻炎用薬": "要注意"
    },
    "授乳中": {
        "風邪薬": "要注意",
        "解熱鎮痛薬": "要注意",
        "鼻炎用薬": "要注意"
    }
}

# スコアリングウェイト
SCORING_WEIGHTS = {
    "症状適合度": 0.35,
    "効能特異性": 0.25,
    "副作用リスク": -0.20,
    "年齢適合性": 0.10,
    "用法簡便性": 0.05,
    "相互作用リスク": -0.05
}

# ================================================================================
# 2. NLU関数（ChatGPT APIで症状抽出のみ）
# ================================================================================

def simple_pattern_matching_nlu(user_text: str, user_info: Dict) -> Dict:
    """
    簡易パターンマッチングによる症状抽出（APIフォールバック用）
    """
    text_lower = user_text.lower()
    detected_symptoms = []
    red_flags = []
    
    # 症状辞書から同義語でマッチング
    for symptom_name, symptom_data in SYMPTOM_DICTIONARY.items():
        # 正規化名でチェック
        if symptom_data["canonical_name"] in user_text:
            detected_symptoms.append({
                "name": symptom_name,
                "severity": "中等度",  # デフォルト
                "duration_days": None
            })
            continue
        
        # 同義語でチェック
        for synonym in symptom_data["synonyms"]:
            if synonym in user_text:
                detected_symptoms.append({
                    "name": symptom_name,
                    "severity": "中等度",
                    "duration_days": None
                })
                break
    
    # 重症疑い症状のチェック
    for flag_name, flag_keywords in RED_FLAG_SYMPTOMS.items():
        for keyword in flag_keywords:
            if keyword in user_text:
                red_flags.append(flag_name)
                break
    
    # 重症度の推定（キーワードベース）
    for symptom in detected_symptoms:
        if "激しい" in user_text or "ひどい" in user_text or "重い" in user_text:
            symptom["severity"] = "重度"
        elif "少し" in user_text or "軽い" in user_text:
            symptom["severity"] = "軽度"
    
    # 期間の推定
    import re
    duration_match = re.search(r'(\d+)\s*(日|日間)', user_text)
    if duration_match:
        days = int(duration_match.group(1))
        for symptom in detected_symptoms:
            symptom["duration_days"] = days
    
    needs_escalation = len(red_flags) > 0
    escalation_reason = f"重症疑い症状が検出されました: {', '.join(red_flags)}" if needs_escalation else ""
    
    print(f"=== 簡易NLU結果 ===")
    print(f"検出された症状: {[s['name'] for s in detected_symptoms]}")
    print(f"重症疑い: {red_flags}")
    print(f"エスカレーション必要: {needs_escalation}")
    
    return {
        "symptoms": detected_symptoms,
        "red_flags": red_flags,
        "needs_escalation": needs_escalation,
        "escalation_reason": escalation_reason
    }

def extract_symptoms_with_gpt(user_text: str, user_info: Dict, client: OpenAI) -> Dict:
    """
    ChatGPT APIを使用してユーザーの自由入力から症状を抽出・構造化
    
    Args:
        user_text: ユーザーの症状入力
        user_info: ユーザー情報（年齢、性別など）
        client: OpenAI client
    
    Returns:
        構造化された症状データ
    """
    # 症状リストを作成
    all_symptoms = []
    for symptom_name, symptom_data in SYMPTOM_DICTIONARY.items():
        all_symptoms.append(symptom_name)
        all_symptoms.extend(symptom_data["synonyms"])
    
    prompt = f"""
あなたは医療NLUシステムです。ユーザーの症状文から以下の情報を抽出してください。

【ユーザー入力】
{user_text}

【ユーザー情報】
年齢: {user_info.get('age', '不明')}
性別: {user_info.get('gender', '不明')}
妊娠中: {user_info.get('pregnant', False)}
授乳中: {user_info.get('breastfeeding', False)}

【抽出すべき情報】
1. 症状リスト（以下から該当するものを選択）
   {', '.join(list(SYMPTOM_DICTIONARY.keys()))}

2. 各症状の重症度（軽度/中等度/重度）
3. 症状の期間（何日前から）
4. 重症疑い症状の有無（呼吸困難、高熱38.5度以上、胸痛、意識障害など）

【回答形式】
以下のJSON形式で回答してください：
{{
    "symptoms": [
        {{
            "name": "症状名",
            "severity": "軽度 or 中等度 or 重度",
            "duration_days": 数値（不明なら null）
        }}
    ],
    "red_flags": ["重症疑い症状1", "重症疑い症状2"],
    "needs_escalation": true or false,
    "escalation_reason": "エスカレーションが必要な理由"
}}

注意：
- 症状名は必ず上記のリストから選択してください
- 重症疑い症状がある場合は必ず needs_escalation を true にしてください
- 情報が不明な場合は null を使用してください
"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "あなたは医療NLUシステムです。症状文から正確に情報を抽出してください。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=800
        )
        
        result = response.choices[0].message.content
        
        # JSON解析
        json_start = result.find('{')
        json_end = result.rfind('}') + 1
        
        if json_start != -1 and json_end != -1:
            json_str = result[json_start:json_end]
            parsed_result = json.loads(json_str)
            
            print(f"=== NLU結果 ===")
            print(f"抽出された症状: {parsed_result.get('symptoms', [])}")
            print(f"重症疑い: {parsed_result.get('red_flags', [])}")
            print(f"エスカレーション必要: {parsed_result.get('needs_escalation', False)}")
            
            return parsed_result
        else:
            print("JSON形式が見つかりませんでした")
            return {
                "symptoms": [],
                "red_flags": [],
                "needs_escalation": False,
                "escalation_reason": ""
            }
            
    except Exception as e:
        print(f"NLU処理エラー: {e}")
        print(f"フォールバック: 簡易パターンマッチングに切り替えます")
        
        # フォールバック: 簡易パターンマッチング
        return simple_pattern_matching_nlu(user_text, user_info)

# ================================================================================
# 3. 安全性フィルタ層
# ================================================================================

def check_safety_contraindications(user_info: Dict, nlu_result: Dict) -> Dict:
    """
    安全性チェック（禁忌、年齢制限、重症疑い）
    
    Returns:
        {
            "is_safe": bool,
            "warnings": List[str],
            "exclusions": List[str],
            "requires_escalation": bool,
            "escalation_reason": str
        }
    """
    safety_result = {
        "is_safe": True,
        "warnings": [],
        "exclusions": [],
        "requires_escalation": False,
        "escalation_reason": ""
    }
    
    # 1. 重症疑い症状チェック（最優先）
    if nlu_result.get("needs_escalation", False):
        safety_result["is_safe"] = False
        safety_result["requires_escalation"] = True
        safety_result["escalation_reason"] = nlu_result.get("escalation_reason", "重症疑い症状が検出されました")
        return safety_result
    
    # 2. 年齢チェック
    age = user_info.get('age')
    if age is not None:
        if age < CONTRAINDICATION_RULES["年齢制限"]["最小年齢"]:
            safety_result["is_safe"] = False
            safety_result["requires_escalation"] = True
            safety_result["escalation_reason"] = f"{age}歳は市販薬の適応年齢外です。医師の診察を受けてください。"
            return safety_result
        elif age < CONTRAINDICATION_RULES["年齢制限"]["推奨年齢"]:
            safety_result["warnings"].append(f"{age}歳は市販薬使用に注意が必要です。")
    
    # 3. 妊娠中チェック
    if user_info.get('pregnant', False):
        safety_result["warnings"].append("妊娠中のため、使用できる医薬品が限定されます。")
        safety_result["exclusions"].append("NSAIDs含有製品")
    
    # 4. 授乳中チェック
    if user_info.get('breastfeeding', False):
        safety_result["warnings"].append("授乳中のため、医薬品の使用に注意が必要です。")
    
    # 5. 症状の期間チェック
    for symptom in nlu_result.get("symptoms", []):
        duration = symptom.get("duration_days")
        if duration is not None and duration > 7:
            safety_result["warnings"].append(f"症状が{duration}日間続いています。長期化している場合は医師の診察を推奨します。")
    
    # 6. 症状の重症度チェック
    for symptom in nlu_result.get("symptoms", []):
        if symptom.get("severity") == "重度":
            safety_result["warnings"].append(f"重度の{symptom.get('name')}が報告されています。症状が重い場合は医師の診察を推奨します。")
    
    return safety_result

# ================================================================================
# 4. 候補薬取得とスコアリング
# ================================================================================

def get_candidate_medicines(nlu_result: Dict, medicine_df: pd.DataFrame) -> List[Dict]:
    """
    症状に基づいて候補医薬品を取得
    """
    symptoms = nlu_result.get("symptoms", [])
    if not symptoms:
        return []
    
    # 症状から医薬品の種類を推定
    medicine_types = set()
    for symptom in symptoms:
        symptom_name = symptom.get("name")
        if symptom_name in SYMPTOM_DICTIONARY:
            types = SYMPTOM_DICTIONARY[symptom_name]["medicine_types"]
            medicine_types.update(types)
    
    print(f"推定された医薬品の種類: {medicine_types}")
    
    # 該当する医薬品を抽出
    candidates = []
    for medicine_type in medicine_types:
        matched = medicine_df[medicine_df['医薬品の種類'] == medicine_type]
        for _, row in matched.iterrows():
            # CSVのG列（インデックス6）から年齢制限を取得
            age_restriction = row.get('年齢制限', '')
            
            # インデックスでも取得を試みる（バックアップ）
            if not age_restriction and len(row) > 6:
                age_restriction = row.iloc[6] if hasattr(row, 'iloc') else ''
            
            # 用法用量から使用上の注意部分を抽出
            usage_full = row.get('用法用量', '')
            usage_notes = ''
            if '注意' in usage_full or '＜' in usage_full:
                # 注意書き部分を抽出
                parts = usage_full.split('\n')
                note_parts = [p for p in parts if '注意' in p or '＜' in p or '用法' in p]
                usage_notes = '\n'.join(note_parts[:3])  # 最初の3行まで
            
            candidates.append({
                'medicine_id': len(candidates),
                'product_name': row.get('製品名', ''),  # A列
                'manufacturer': row.get('メーカー名', ''),  # B列
                'medicine_type': row.get('医薬品の種類', ''),  # D列
                'classification': row.get('分類', ''),  # C列
                'efficacy': row.get('効能効果', ''),  # E列
                'usage': row.get('用法用量', ''),  # F列
                'age_restriction': age_restriction,  # G列
                'ingredients': row.get('成分', ''),  # H列
                'doping_prohibited': row.get('禁止物質あり', ''),  # I列
                'competition_category': row.get('競技会区分', ''),  # J列
                'conditions': row.get('条件', ''),  # K列
                'usage_notes': usage_notes if usage_notes else '用法用量を守ってご使用ください。',
                'base_score': 0.0
            })
    
    print(f"候補医薬品数: {len(candidates)}")
    return candidates

def calculate_symptom_match_score(candidate: Dict, nlu_result: Dict) -> float:
    """
    症状適合度スコアを計算
    """
    症状スコア = 0.0
    症状数 = len(nlu_result.get("symptoms", []))
    
    if 症状数 == 0:
        return 0.0
    
    efficacy_text = candidate.get('efficacy', '').lower()
    
    for symptom in nlu_result.get("symptoms", []):
        symptom_name = symptom.get("name")
        
        # 効能効果テキストに症状名が含まれるかチェック
        if symptom_name and symptom_name in efficacy_text:
            # 症状辞書の重みを使用
            weight = SYMPTOM_DICTIONARY.get(symptom_name, {}).get("weight", 0.5)
            症状スコア += weight
    
    return 症状スコア / 症状数

def calculate_age_fit_score(candidate: Dict, user_info: Dict) -> float:
    """
    年齢適合性スコアを計算
    """
    age = user_info.get('age')
    if age is None:
        # 年齢不明の場合は成人として扱う（スコアリングのみ）
        age = 30
        return 0.5  # 年齢不明の場合は中立スコア
    
    age_restriction = candidate.get('age_restriction', '')
    
    # NaN（欠損値）のチェック
    import math
    if isinstance(age_restriction, float) and math.isnan(age_restriction):
        age_restriction = ''
    
    # 年齢制限が数値の場合は文字列に変換
    if isinstance(age_restriction, (int, float)):
        try:
            age_restriction = str(int(age_restriction))
        except (ValueError, OverflowError):
            age_restriction = ''
    
    # 年齢制限が文字列でない場合は空文字列に
    if not isinstance(age_restriction, str):
        age_restriction = ''
    
    # 年齢制限の解析（簡易版）
    if '15歳未満' in age_restriction and age < 15:
        return 0.0  # 服用不可
    elif '7歳未満' in age_restriction and age < 7:
        return 0.0  # 服用不可
    elif age >= 15:
        return 1.0  # 成人は問題なし
    else:
        return 0.7  # 小児は減点

def calculate_final_score(candidate: Dict, nlu_result: Dict, user_info: Dict) -> float:
    """
    最終スコアを計算
    """
    # 症状適合度スコア
    symptom_score = calculate_symptom_match_score(candidate, nlu_result)
    
    # 年齢適合性スコア
    age_score = calculate_age_fit_score(candidate, user_info)
    
    # 用法簡便性スコア（簡易版：1日の服用回数が少ないほど高い）
    usage_score = 0.5  # デフォルト
    
    # 最終スコア計算
    final_score = (
        SCORING_WEIGHTS["症状適合度"] * symptom_score +
        SCORING_WEIGHTS["年齢適合性"] * age_score +
        SCORING_WEIGHTS["用法簡便性"] * usage_score
    )
    
    return final_score

# ================================================================================
# 5. 不足情報のチェックと質問生成
# ================================================================================

def check_missing_information(user_info: Dict, nlu_result: Dict) -> Dict:
    """
    不足している情報をチェックし、追加質問を生成
    
    Returns:
        {
            "has_missing_info": bool,
            "missing_fields": List[str],
            "questions": List[str],
            "priority": str  # "critical", "important", "optional"
        }
    """
    missing_info = {
        "has_missing_info": False,
        "missing_fields": [],
        "questions": [],
        "priority": "optional"
    }
    
    # 1. 年齢チェック（最重要）
    if user_info.get('age') is None:
        missing_info["has_missing_info"] = True
        missing_info["missing_fields"].append("age")
        missing_info["questions"].append("年齢を教えてください。（医薬品の適切な選択に必要です）")
        missing_info["priority"] = "critical"
    
    # 2. 症状が検出されない場合
    symptoms = nlu_result.get('symptoms', [])
    if not symptoms:
        missing_info["has_missing_info"] = True
        missing_info["missing_fields"].append("symptoms")
        missing_info["questions"].append("具体的にどのような症状がありますか？（例：頭痛、発熱、咳、鼻水など）")
        missing_info["priority"] = "critical"
    
    # 3. 性別チェック
    if user_info.get('gender') is None:
        missing_info["has_missing_info"] = True
        missing_info["missing_fields"].append("gender")
        missing_info["questions"].append("性別を教えてください。（男性/女性）")
        if missing_info["priority"] != "critical":
            missing_info["priority"] = "important"
    
    # 4. 妊娠・授乳状態の確認（女性または性別不明の場合）
    # 妊娠・授乳の両方が未回答の場合のみ質問（どちらか一方でも回答済みなら質問しない）
    pregnancy_answered = user_info.get('pregnant') is not None
    breastfeeding_answered = user_info.get('breastfeeding') is not None
    
    if user_info.get('gender') == '女性' or user_info.get('gender') is None:
        if not pregnancy_answered and not breastfeeding_answered:
            # 年齢から妊娠可能性を判断
            age = user_info.get('age')
            # 年齢が不明でも念のため確認（または15-50歳の範囲）
            if age is None or (age and 15 <= age <= 50):
                missing_info["has_missing_info"] = True
                missing_info["missing_fields"].append("pregnancy_status")
                missing_info["questions"].append("現在、妊娠中または授乳中ですか？（はい/いいえ）")
                if missing_info["priority"] != "critical":
                    missing_info["priority"] = "important"
    
    # 5. 症状の期間チェック
    # user_infoのsymptom_duration_daysもチェック
    has_duration = any(s.get('duration_days') is not None for s in symptoms) or user_info.get('symptom_duration_days') is not None
    if not has_duration and symptoms:
        missing_info["has_missing_info"] = True
        missing_info["missing_fields"].append("symptom_duration")
        missing_info["questions"].append("症状はいつ頃から続いていますか？（例：昨日から、3日前から）")
        if missing_info["priority"] not in ["critical", "important"]:
            missing_info["priority"] = "optional"
    
    # 6. 現在服用中の薬の確認
    # current_medicationsが未設定、または空リストの場合のみ質問
    medications = user_info.get('current_medications')
    medications_answered = medications is not None and isinstance(medications, list)
    
    if not medications_answered:
        # 症状がある場合は確認
        if symptoms:
            missing_info["has_missing_info"] = True
            missing_info["missing_fields"].append("current_medications")
            missing_info["questions"].append("現在、他に服用している薬はありますか？（ある場合は薬の名前を教えてください）")
            if missing_info["priority"] not in ["critical", "important"]:
                missing_info["priority"] = "optional"
    
    # 7. アレルギーの確認
    # allergiesが未設定、または空リストの場合のみ質問
    allergies = user_info.get('allergies')
    allergies_answered = allergies is not None and isinstance(allergies, list) and len(allergies) > 0
    
    if not allergies_answered:
        missing_info["has_missing_info"] = True
        missing_info["missing_fields"].append("allergies")
        missing_info["questions"].append("薬や食品のアレルギーはありますか？（ある場合は具体的に教えてください）")
        if missing_info["priority"] not in ["critical", "important"]:
            missing_info["priority"] = "optional"
    
    return missing_info

# ================================================================================
# 6. メイン推奨関数
# ================================================================================

def rule_based_recommendation(
    user_text: str,
    user_info: Dict,
    medicine_df: pd.DataFrame,
    client: OpenAI,
    top_n: int = 3
) -> Dict:
    """
    ルールベース医薬品推奨システムのメイン関数
    
    Args:
        user_text: ユーザーの症状入力
        user_info: {
            'age': int,
            'gender': str,
            'pregnant': bool,
            'breastfeeding': bool,
            'current_medications': List[str],
            'allergies': List[str]
        }
        medicine_df: 医薬品データフレーム
        client: OpenAI client
        top_n: 推奨する医薬品の数
    
    Returns:
        推奨結果
    """
    print(f"\n{'='*80}")
    print(f"ルールベース医薬品推奨システム 開始")
    print(f"{'='*80}")
    print(f"症状文: {user_text}")
    print(f"ユーザー情報: {user_info}")
    
    # ステップ1: NLU（症状抽出）
    print(f"\n--- ステップ1: NLU（症状抽出） ---")
    nlu_result = extract_symptoms_with_gpt(user_text, user_info, client)
    
    # ステップ1.5: 不足情報のチェック
    print(f"\n--- ステップ1.5: 不足情報のチェック ---")
    missing_info_result = check_missing_information(user_info, nlu_result)
    
    if missing_info_result["has_missing_info"]:
        priority = missing_info_result["priority"]
        print(f"不足情報検出（優先度: {priority}）")
        print(f"不足フィールド: {missing_info_result['missing_fields']}")
        print(f"推奨は続行しますが、追加質問も表示します")
    
    # ステップ2: 安全性チェック
    print(f"\n--- ステップ2: 安全性チェック ---")
    safety_result = check_safety_contraindications(user_info, nlu_result)
    
    if safety_result["requires_escalation"]:
        print(f"[警告] エスカレーション必要: {safety_result['escalation_reason']}")
        return {
            "status": "escalation_required",
            "reason": safety_result["escalation_reason"],
            "warnings": safety_result["warnings"],
            "recommended_medicines": [],
            "nlu_result": nlu_result,
            "timestamp": datetime.now().isoformat()
        }
    
    # ステップ3: 候補医薬品取得
    print(f"\n--- ステップ3: 候補医薬品取得 ---")
    candidates = get_candidate_medicines(nlu_result, medicine_df)
    
    if not candidates:
        print("該当する候補医薬品が見つかりませんでした")
        return {
            "status": "no_candidates",
            "reason": "該当する医薬品が見つかりませんでした",
            "warnings": safety_result["warnings"],
            "recommended_medicines": [],
            "nlu_result": nlu_result,
            "timestamp": datetime.now().isoformat()
        }
    
    # ステップ4: スコアリング
    print(f"\n--- ステップ4: スコアリング ---")
    for candidate in candidates:
        candidate['final_score'] = calculate_final_score(candidate, nlu_result, user_info)
        print(f"{candidate['product_name']}: {candidate['final_score']:.3f}")
    
    # スコア順にソート
    candidates_sorted = sorted(candidates, key=lambda x: x['final_score'], reverse=True)
    
    # 上位N件を選択
    top_candidates = candidates_sorted[:top_n]
    
    # ステップ5: 説明生成
    print(f"\n--- ステップ5: 説明生成 ---")
    recommendations = []
    for i, candidate in enumerate(top_candidates, 1):
        explanation = generate_explanation(candidate, nlu_result, safety_result, user_info)
        
        recommendations.append({
            "rank": i,
            "number": i,  # ChatGPTベース互換性のため追加
            "product_name": candidate['product_name'],
            "manufacturer": candidate['manufacturer'],
            "medicine_type": candidate['medicine_type'],
            "classification": candidate.get('classification', ''),  # C列
            "efficacy": candidate['efficacy'],  # E列
            "usage": candidate['usage'],  # F列
            "age_restriction": candidate.get('age_restriction', ''),  # G列
            "ingredients": candidate['ingredients'],  # H列
            "doping_prohibited": candidate.get('doping_prohibited', ''),  # I列
            "competition_category": candidate.get('competition_category', ''),  # J列
            "conditions": candidate.get('conditions', ''),  # K列
            "usage_notes": candidate.get('usage_notes', '用法用量を守ってご使用ください。'),
            "score": candidate['final_score'],
            "explanation": explanation,
            "reason": explanation  # ChatGPTベース互換性のため追加
        })
    
    # ステップ6: 使用上の注意と医師相談アドバイスをChatGPTで生成
    print(f"\n--- ステップ6: 使用上の注意と医師相談アドバイスの生成 ---")
    usage_and_consultation = generate_usage_notes_and_consultation_with_gpt(
        recommendations, nlu_result, user_info, client
    )
    
    print(f"\n{'='*80}")
    print(f"推奨完了: {len(recommendations)}件の医薬品を推奨")
    print(f"{'='*80}\n")
    
    # 不足情報の質問を追加（すべての優先度で表示）
    additional_questions = []
    missing_priority = None
    if missing_info_result.get("has_missing_info"):
        additional_questions = missing_info_result.get("questions", [])
        missing_priority = missing_info_result.get("priority")
    
    return {
        "status": "success",
        "recommended_medicines": recommendations,
        "warnings": safety_result["warnings"],
        "usage_notes": usage_and_consultation.get('usage_notes', ''),
        "doctor_consultation": usage_and_consultation.get('doctor_consultation', ''),
        "additional_questions": additional_questions,
        "missing_priority": missing_priority,
        "nlu_result": nlu_result,
        "timestamp": datetime.now().isoformat()
    }

def generate_explanation(candidate: Dict, nlu_result: Dict, safety_result: Dict, user_info: Dict) -> str:
    """
    推奨理由の説明を生成（成分と制限情報を含む）
    """
    explanation_parts = []
    
    # 症状適合の説明
    matched_symptoms = []
    efficacy_text = candidate.get('efficacy', '')
    for symptom in nlu_result.get("symptoms", []):
        symptom_name = symptom.get("name")
        if symptom_name and symptom_name in efficacy_text:
            matched_symptoms.append(symptom_name)
    
    if matched_symptoms:
        explanation_parts.append(f"この医薬品は{', '.join(matched_symptoms)}に適応しています。")
    
    # 主要成分の説明
    ingredients = candidate.get('ingredients', '')
    if ingredients:
        # 改行で分割して最初の3成分を取得
        ingredient_list = [ing.strip() for ing in ingredients.split('\n') if ing.strip()][:3]
        if ingredient_list:
            explanation_parts.append(f"主な成分: {', '.join(ingredient_list)}。")
    
    # 年齢制限の説明
    age_restriction = candidate.get('age_restriction', '')
    user_age = user_info.get('age')
    if age_restriction and isinstance(age_restriction, str):
        if '15歳未満' in age_restriction:
            if user_age and user_age < 15:
                explanation_parts.append(f"[注意] {user_age}歳の方は服用できません。")
            else:
                explanation_parts.append(f"15歳以上の方が対象です。")
        elif '7歳未満' in age_restriction:
            if user_age and user_age < 7:
                explanation_parts.append(f"[注意] {user_age}歳の方は服用できません。")
            else:
                explanation_parts.append(f"7歳以上の方が対象です。")
    
    # 医薬品の種類
    medicine_type = candidate.get('medicine_type', '')
    if medicine_type:
        explanation_parts.append(f"{medicine_type}として効果が期待できます。")
    
    # 警告がある場合
    if safety_result.get("warnings"):
        for warning in safety_result['warnings']:
            explanation_parts.append(f"[警告] {warning}")
    
    return " ".join(explanation_parts)

# ================================================================================
# 6. ChatGPTによる使用上の注意と医師相談アドバイスの生成
# ================================================================================

def generate_individual_usage_notes_with_gpt(
    medicine: Dict,
    client: OpenAI
) -> str:
    """
    個別の医薬品について、CSVのE〜K列を使ってChatGPTで使用上の注意を生成
    """
    prompt = f"""
あなたは登録販売者です。以下の医薬品情報から、使用上の注意を簡潔に生成してください。

【医薬品情報】
製品名: {medicine.get('product_name', '')}
効能効果（E列）: {medicine.get('efficacy', '')}
用法用量（F列）: {medicine.get('usage', '')}
年齢制限（G列）: {medicine.get('age_restriction', '')}
禁止物質（I列）: {medicine.get('doping_prohibited', '')}

【生成ルール】
1. 効能: E列の効能効果を全文記載（省略しない）
2. 用法用量の注意: F列から重要な注意を2〜3項目、100字以内に要約
   - 「用法用量を厳守」は他で記載済みなので省略
   - 小児・乳幼児への注意など、この医薬品特有の注意のみ記載
   - 箇条書き形式
3. 年齢制限: G列にある場合のみ記載
4. ドーピング: I列に「禁止物質あり」がある場合のみ記載

【出力形式】
効能: [全文]

用法用量の注意:
・[この医薬品特有の注意1]
・[この医薬品特有の注意2]

年齢制限: [ある場合のみ]

ドーピング: [ある場合のみ]

【除外すべき内容】
- 服用方法（＜○○の服用方法＞）
- 一般的な注意（用法用量を厳守、など）
"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "あなたは登録販売者です。効能は詳細に、用法用量の注意は簡潔に要約してください。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=400
        )
        
        result = response.choices[0].message.content
        return result.strip()
        
    except Exception as e:
        print(f"個別使用上の注意生成エラー: {e}")
        # フォールバック - CSVデータから完全な情報を取得
        notes = []
        
        # 効能
        efficacy = medicine.get('efficacy', '')
        if efficacy:
            # 全文表示
            notes.append(f"効能: {efficacy}")
        
        # 年齢制限
        age_restriction = medicine.get('age_restriction', '')
        import math
        if isinstance(age_restriction, float):
            if not math.isnan(age_restriction):
                try:
                    age_val = int(age_restriction)
                    notes.append(f"年齢制限: {age_val}歳未満の方は使用しないでください。")
                except:
                    pass
        elif age_restriction and isinstance(age_restriction, str) and age_restriction.strip():
            notes.append(f"年齢制限: {age_restriction}")
        
        # F列（用法用量）から注意事項を抽出（服用方法と一般的な注意は除外）
        usage = medicine.get('usage', '')
        if usage and '注意' in usage:
            usage_lines = usage.split('\n')
            caution_items = []
            skip_section = False
            
            for i, line in enumerate(usage_lines):
                line = line.strip()
                
                # 服用方法セクションはスキップ
                if '服用方法' in line:
                    skip_section = True
                    continue
                elif line.startswith('＜') and '注意' in line:
                    skip_section = False
                    continue
                
                if skip_section or not line:
                    continue
                
                # 番号付きリストを検出（１．、２．など）
                if re.match(r'^[１-９1-9０-９][\．\.]', line):
                    # 一般的な注意を除外
                    if '用法・用量を厳守' in line or '用法用量を厳守' in line:
                        continue
                    if '定められた用法・用量' in line:
                        continue
                    
                    # 特有の注意のみ抽出して簡潔に
                    content = re.sub(r'^[１-９1-9０-９][\．\.]', '', line).strip()
                    
                    # 長い文を要約
                    if '小児に服用させる' in content:
                        caution_items.append('小児服用時は保護者の監督が必要')
                    elif '乳幼児' in content and '医師' in content:
                        caution_items.append('2歳未満は医師の診療を優先')
                    elif '分割' in content and '服用' in content:
                        caution_items.append('分割服用は2日以内に使用')
                    elif len(content) > 10:  # その他の重要な注意
                        # 30字以内に要約
                        summary = content[:30] + ('...' if len(content) > 30 else '')
                        caution_items.append(summary)
            
            # 箇条書きで追加（最大3項目）
            if caution_items:
                notes.append('\n用法用量の注意:')
                for item in caution_items[:3]:
                    notes.append(f'・{item}')
        
        # ドーピング情報
        doping = medicine.get('doping_prohibited', '')
        if doping and '禁止物質あり' in doping:
            notes.append(f"ドーピング: {doping}")
        
        return '\n'.join(notes) if notes else '用法用量を守ってご使用ください。'

def generate_usage_notes_and_consultation_with_gpt(
    recommended_medicines: List[Dict],
    nlu_result: Dict,
    user_info: Dict,
    client: OpenAI
) -> Dict:
    """
    選択された医薬品のCSVデータをChatGPTに渡して、
    使用上の注意と医師相談が必要な場合のアドバイスを生成
    
    各医薬品ごとに個別の使用上の注意を生成
    """
    # 各医薬品の個別の使用上の注意を生成
    individual_notes = []
    
    for i, med in enumerate(recommended_medicines, 1):
        # ChatGPTで個別の使用上の注意を生成
        individual_note = generate_individual_usage_notes_with_gpt(med, client)
        
        # 年齢制限の表示（G列から）
        age_restriction = med.get('age_restriction', '')
        age_restriction_display = ''
        
        import math
        if isinstance(age_restriction, float) and math.isnan(age_restriction):
            age_restriction = ''
        
        if age_restriction and isinstance(age_restriction, str) and age_restriction.strip():
            if '15歳未満' in age_restriction:
                age_restriction_display = '年齢制限: 15歳未満の方は使用しないでください。'
            elif '7歳未満' in age_restriction:
                age_restriction_display = '年齢制限: 7歳未満の方は使用しないでください。'
            elif '12歳未満' in age_restriction:
                age_restriction_display = '年齢制限: 12歳未満の方は使用しないでください。'
            else:
                import re
                match = re.search(r'(\d+)歳', age_restriction)
                if match:
                    age_val = match.group(1)
                    age_restriction_display = f'年齢制限: {age_val}歳未満の方は使用しないでください。'
        elif isinstance(age_restriction, (int, float)):
            if not (isinstance(age_restriction, float) and math.isnan(age_restriction)):
                try:
                    age_val = int(age_restriction)
                    age_restriction_display = f'年齢制限: {age_val}歳未満の方は使用しないでください。'
                except (ValueError, OverflowError):
                    pass
        
        # 個別の注意を整形
        note_text = f"{i}つ目：{med.get('product_name', '')}\n{individual_note}"
        if age_restriction_display:
            note_text += f"\n{age_restriction_display}"
        
        individual_notes.append(note_text)
    
    # 個別の使用上の注意を結合
    usage_notes_individual = '\n\n'.join(individual_notes)
    
    # 全体の使用上の注意を生成（共通の禁忌事項）
    general_notes = generate_default_usage_notes_and_consultation(recommended_medicines, user_info)
    
    # 個別の注意 + 共通の注意を結合
    usage_notes_combined = usage_notes_individual + '\n\n' + general_notes['usage_notes']
    doctor_consultation = general_notes['doctor_consultation']
    
    print(f"=== 使用上の注意生成完了 ===")
    print(f"個別の注意: {len(individual_notes)}件")
    
    return {
        "usage_notes": usage_notes_combined,
        "doctor_consultation": doctor_consultation
    }

def generate_default_usage_notes_and_consultation(recommended_medicines: List[Dict], user_info: Dict) -> Dict:
    """
    デフォルトの使用上の注意と医師相談アドバイスを生成（フォールバック用）
    推奨医薬品のCSVデータから禁忌情報を抽出（年齢制限は個別に表示するので除く）
    """
    usage_notes_parts = []
    
    # 使ってはいけない人の情報を追加（年齢制限は個別表示なので除く）
    contraindications_parts = ["【使ってはいけない人】"]
    
    # 年齢に基づく禁忌
    user_age = user_info.get('age')
    if user_age:
        if user_age < 7:
            contraindications_parts.append("・7歳未満のお子様（医師の診察を受けてください）")
        elif user_age < 15:
            contraindications_parts.append("・一部の医薬品は15歳未満の方は使用できません")
    
    # 妊娠・授乳
    if user_info.get('pregnant'):
        contraindications_parts.append("・妊娠中の方（特にNSAIDs含有製品は禁忌）")
    if user_info.get('breastfeeding'):
        contraindications_parts.append("・授乳中の方（医師にご相談ください）")
    
    # 一般的な禁忌
    contraindications_parts.extend([
        "・過去に医薬品でアレルギー症状を起こしたことがある方",
        "・医師の治療を受けている方",
        "・高齢者の方（医師や薬剤師にご相談ください）"
    ])
    
    usage_notes_parts.extend(contraindications_parts)
    
    # 一般的な使用上の注意
    usage_notes_parts.extend([
        "",
        "【服用時の注意】",
        "・用法用量を厳守してください",
        "・なるべく空腹時の服用は避けてください",
        "・アレルギー体質の方は成分を確認してください",
        "・服用後、乗り物や機械の運転操作をしないでください（眠気が出る場合があります）"
    ])
    
    if user_info.get('age') and user_info['age'] < 15:
        usage_notes_parts.append("・小児が服用する場合は保護者の監督のもとで服用してください")
    
    # 医師相談が必要な場合
    doctor_consultation_parts = [
        "【以下の場合は医師にご相談ください】",
        "・症状が3日以上続く場合",
        "・症状が悪化する場合",
        "・高熱（38.5度以上）が続く場合",
        "・発疹、発赤、かゆみなどの副作用が現れた場合",
        "・他の症状が現れた場合",
        "・長期連用する場合"
    ]
    
    if user_info.get('pregnant') or user_info.get('breastfeeding'):
        doctor_consultation_parts.insert(1, "・妊娠中・授乳中の方は事前に医師にご相談ください")
    
    return {
        "usage_notes": '\n'.join(usage_notes_parts),
        "doctor_consultation": '\n'.join(doctor_consultation_parts)
    }

# ================================================================================
# 7. ロギング関数
# ================================================================================

def log_recommendation_session(user_text: str, user_info: Dict, result: Dict, log_file: str = "recommendation_log.jsonl"):
    """
    推奨セッションをログに保存（監査用）
    """
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "user_text": user_text,
        "user_info": user_info,
        "result": result
    }
    
    log_dir = os.path.dirname(os.path.abspath(__file__))
    log_path = os.path.join(log_dir, "log", log_file)
    
    # logディレクトリがなければ作成
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    
    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
    
    print(f"ログ保存完了: {log_path}")
