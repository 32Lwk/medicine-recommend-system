"""
GPT を用いた OTC 推奨フロー

recommend_otc_medicines_via_gpt, recommend_otc_medicines_from_summarized,
gpt_select_efficacy_candidates, recommend_medicines_with_retry を提供。
"""

import logging
import os
import random
import re

import pandas as pd

from src.core.medicine_data import (
    BASE_DIR,
    DATA_DIR,
    find_otc_candidates,
)
from src.core.llm_medicine_service import (
    gpt_guess_symptom,
    gpt_select_best_otc,
)
from src.core.openai_client import client as _default_openai_client

logger = logging.getLogger(__name__)


def recommend_otc_medicines_via_gpt(
    user_text,
    symptom_csv_path=None,
    otc_csv_path=None,
    max_candidates=20,
    client=None,
):
    """
    ユーザー症状文→ChatGPTで症状名推定→候補薬抽出→ChatGPTで最適薬3つ選定
    """
    if client is None:
        client = _default_openai_client
    data_dir = DATA_DIR
    symptom_csv = symptom_csv_path or os.path.join(data_dir, "症状-薬.csv")
    otc_csv = otc_csv_path or os.path.join(data_dir, "otc_medicine_data.csv")
    df_symptom = pd.read_csv(symptom_csv)
    df_otc = pd.read_csv(otc_csv)
    df_otc = df_otc.fillna("")
    symptom_list = df_symptom["症状"].dropna().unique().tolist()
    symptoms = gpt_guess_symptom(user_text, symptom_list, client=client)
    candidates = find_otc_candidates(symptoms, df_otc, max_candidates=max_candidates)
    if candidates.empty:
        return "該当する市販薬情報が見つかりませんでした。"
    result = gpt_select_best_otc(user_text, candidates, client=client)
    if os.getenv("DEBUG_MODE", "false").lower() == "true" or logger.level <= logging.DEBUG:
        logger.debug(f"ChatGPT返答:\n{result}")
    return result


def recommend_otc_medicines_from_summarized(
    user_text,
    summarized_csv_path=None,
    max_candidates=20,
    client=None,
):
    """
    summarized_efficacy_data.csvを用いて、
    1. 症状語リストを自動抽出
    2. ChatGPTで症状名推定（表記ゆれ・複数症状対応）
    3. 候補薬リストを抽出
    4. ChatGPTに候補リスト＋症状文を渡し、最適な3つを選ばせる
    """
    if client is None:
        client = _default_openai_client
    data_dir = DATA_DIR
    summarized_csv = summarized_csv_path or os.path.join(
        data_dir, "summarized_efficacy_data.csv"
    )
    df = pd.read_csv(summarized_csv)
    df = df.fillna("")
    symptom_set = set()
    for eff in df["Summarized Efficacy"].dropna():
        m = re.search(r"（(.+?)）", eff)
        if m:
            for s in re.split(r"[、,]", m.group(1)):
                s = s.strip()
                if s:
                    symptom_set.add(s)
    synonym_map = {
        "咳": ["咳", "せき"],
        "鼻水": ["鼻水", "鼻みず"],
        "痰": ["痰", "たん"],
        "悪寒": ["悪寒", "さむけ"],
        "関節の痛み": ["関節の痛み", "関節痛"],
        "筋肉の痛み": ["筋肉の痛み", "筋肉痛"],
    }
    expanded_symptom_set = set()
    for s in symptom_set:
        expanded_symptom_set.add(s)
        for syns in synonym_map.values():
            if s in syns:
                expanded_symptom_set.update(syns)
    symptom_list = sorted(expanded_symptom_set)
    symptoms = gpt_guess_symptom(user_text, symptom_list, client=client)
    all_symptoms = set(symptoms)
    for s in symptoms:
        for key, syns in synonym_map.items():
            if s in syns:
                all_symptoms.update(syns)
    mask = df["Summarized Efficacy"].astype(str).apply(
        lambda x: any(s in x for s in all_symptoms)
    )
    candidates = df[mask].copy()

    def count_covered(eff):
        return sum(s in eff for s in all_symptoms)

    candidates["_cover_count"] = (
        candidates["Summarized Efficacy"].astype(str).apply(count_covered)
    )
    candidates = candidates.sort_values("_cover_count", ascending=False).head(
        max_candidates
    )
    if candidates.empty:
        return "該当する市販薬情報が見つかりませんでした。"
    prompt = (
        f"あなたは医薬品推奨システムです。ユーザーの症状:『{user_text}』\n"
        f"推定された症状語: {', '.join(symptoms)}\n"
        "以下の候補リストから、症状に最も適した市販薬を3つ選び、それぞれの医薬品の特徴を効果効能から要約して日本語で説明してください。\n"
        "【候補リスト】\n"
        + "\n".join(
            f"{i+1}. 製品名: {row['製品名']} / 効能効果: {row['Summarized Efficacy']}"
            for i, (_, row) in enumerate(candidates.iterrows())
        )
    )
    from src.core.llm_client import chat_completion_create

    messages = [{"role": "system", "content": prompt}]
    response = chat_completion_create(
        client,
        model_role="admin",
        path="medicine_recommendation_gpt.select_otc",
        messages=messages,
        temperature=0,
    )
    content = (
        response.choices[0].message.content
        if response.choices[0].message.content
        else ""
    )
    if (
        os.getenv("DEBUG_MODE", "false").lower() == "true"
        or logger.level <= logging.DEBUG
    ):
        logger.debug(f"ChatGPT返答:\n{content.strip()}")
    return content.strip()


def gpt_select_efficacy_candidates(
    user_text,
    summarized_csv_path=None,
    max_candidates=30,
    client=None,
):
    """
    ChatGPTにsummarized_efficacy_data.csvの効能効果リストを渡し、
    ユーザー症状に最も近い効能効果（複数可）を選ばせる
    """
    if client is None:
        client = _default_openai_client
    summarized_csv = summarized_csv_path or os.path.join(
        DATA_DIR, "summarized_efficacy_data.csv"
    )
    df = pd.read_csv(summarized_csv)
    df = df.fillna("")
    efficacy_list = df["Summarized Efficacy"].dropna().unique().tolist()
    if len(efficacy_list) > max_candidates:
        efficacy_list = random.sample(efficacy_list, max_candidates)
    prompt = (
        f"あなたは医薬品推奨システムです。下記は市販薬の効能効果リストです。\n"
        f"ユーザーの症状:『{user_text}』\n"
        "この中から症状に最も近い効能効果をすべて選び、日本語でリスト形式で出力してください。\n"
        "【効能効果リスト】\n"
        + "\n".join(f"{i+1}. {e}" for i, e in enumerate(efficacy_list))
    )
    from src.core.llm_client import chat_completion_create

    messages = [{"role": "system", "content": prompt}]
    response = chat_completion_create(
        client,
        model_role="admin",
        path="medicine_recommendation_gpt.efficacy_candidates",
        messages=messages,
        temperature=0,
    )
    content = (
        response.choices[0].message.content
        if response.choices[0].message.content
        else ""
    )
    if (
        os.getenv("DEBUG_MODE", "false").lower() == "true"
        or logger.level <= logging.DEBUG
    ):
        logger.debug(f"ChatGPT返答:\n{content.strip()}")
    selected = [
        line.strip(" ・-0123456789.") for line in content.splitlines() if line.strip()
    ]
    selected_set = set(selected)
    matched_efficacy = [
        e for e in efficacy_list if any(s in e or e in s for s in selected_set)
    ]
    return matched_efficacy


def recommend_medicines_with_retry(
    user_text,
    symptoms,
    medicine_list,
    user_info=None,
    client=None,
    max_retries=3,
):
    """
    症状と医薬品リストをChatGPTに渡して推奨医薬品を3つ選び、
    使用上の注意を要約して返す。適した医薬品が返ってこなければ再試行
    """
    from src.security.security_validator import validate_user_input
    from src.security.security_config import should_block_input
    from src.security.security_logger import log_input_validation

    is_safe, risk_score, warnings, sanitized_text = validate_user_input(
        user_text, context="medicine_recommendation"
    )
    log_input_validation(
        user_id="medicine_recommendation",
        input_text=user_text,
        risk_score=risk_score,
        is_safe=is_safe,
        warnings=warnings,
        sanitized_text=sanitized_text,
    )
    if should_block_input(risk_score):
        print(f"⚠️ 医薬品推奨がブロックされました: リスクスコア {risk_score}")
        return {
            "recommended_medicines": [],
            "usage_notes": "入力内容に問題が検出されました。症状や質問を自然な文章で入力してください。",
            "doctor_consultation": "医師にご相談ください。",
        }
    if risk_score >= 80:
        print(f"⚠️ 高リスク入力のため医薬品推奨を停止: リスクスコア {risk_score}")
        return {
            "recommended_medicines": [],
            "usage_notes": "入力内容に不審なパターンが検出されました。症状や質問を自然な文章で入力してください。",
            "doctor_consultation": "医師にご相談ください。",
        }
    if client is None:
        client = _default_openai_client
    medicine_text = ""
    for i, medicine in enumerate(medicine_list[:20]):
        usage_notes = medicine.get("使用上の注意", "")
        medicine_text += f"{i+1}. {medicine['製品名']} ({medicine['メーカー名']})\n"
        medicine_text += f"   効能効果: {medicine['効能効果']}\n"
        medicine_text += f"   成分: {medicine['成分']}\n"
        medicine_text += f"   使用上の注意: {usage_notes}\n\n"
    user_context = user_info if user_info else {}
    for attempt in range(max_retries):
        print(f"=== 医薬品推奨試行 {attempt + 1}/{max_retries} ===")
        prompt = f"""
以下の症状と医薬品リストから、最も適切な3つの医薬品を選んでください。

【症状】
{', '.join(symptoms)}

【症状文】
{sanitized_text}

【ユーザー情報】
{user_context if user_context else '情報なし'}

【選択可能な医薬品】
{medicine_text}

【回答形式】
以下のJSON形式で回答してください：
{{
    "recommended_medicines": [
        {{ "number": 1, "product_name": "製品名", "manufacturer": "メーカー名", "reason": "推奨理由", "usage_notes": "使用上の注意点の要約" }},
        {{ "number": 2, "product_name": "製品名", "manufacturer": "メーカー名", "reason": "推奨理由", "usage_notes": "使用上の注意点の要約" }},
        {{ "number": 3, "product_name": "製品名", "manufacturer": "メーカー名", "reason": "推奨理由", "usage_notes": "使用上の注意点の要約" }}
    ],
    "doctor_consultation": "医師の受診が必要な場合について"
}}

注意：
- 症状に最も適した医薬品を3つ選んでください
- 製品名とメーカー名が同じものは重複として、同じものを複数回推奨しないでください
- 製品名とメーカー名は正確に記載してください
- 各医薬品の「使用上の注意」欄の内容を参考に、必ず各医薬品ごとに使用上の注意点を要約してください
- 効能・効果が限定された特殊用途の医薬品は、ユーザーの症状がその限定用途と完全に一致する場合のみ推奨してください
- リスク成分が含まれる医薬品は、詳細な症状情報がない場合は推奨を避けてください
- インフルエンザの可能性がある場合は、アスピリンを含む医薬品は絶対に推奨しないでください
- 単一症状の場合は、総合感冒薬よりも特化した医薬品を優先してください
"""
        try:
            from src.core.llm_client import chat_completion_create

            response = chat_completion_create(
                client,
                model_role="admin",
                path="medicine_recommendation_gpt.recommend_with_retry",
                messages=[
                    {
                        "role": "system",
                        "content": "あなたは医薬品の専門家です。症状に適した医薬品を推奨し、使用上の注意を説明してください。効能効果が限定された特殊用途の医薬品は症状がその用途と完全に一致する場合のみ推奨してください。リスク成分を含む医薬品は詳細な症状情報がない場合は避けてください。症状に最も適した医薬品を3つ選び、製品名とメーカー名は正確に記載してください。",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=800,
            )
            result = response.choices[0].message.content
            print(f"ChatGPT応答 (試行 {attempt + 1}): {result}")
            if not result:
                continue
            if result.startswith("```json"):
                result = result[7:]
            if result.endswith("```"):
                result = result[:-3]
            result = result.strip()
            from src.security.json_validator import safe_json_parse

            try:
                parsed_result = safe_json_parse(
                    result, schema="medicine_recommendation"
                )
                if parsed_result.get("recommended_medicines"):
                    seen = set()
                    unique_meds = []
                    for med in parsed_result["recommended_medicines"]:
                        key = (
                            med.get("product_name", ""),
                            med.get("manufacturer", ""),
                        )
                        if key not in seen:
                            seen.add(key)
                            unique_meds.append(med)
                        if len(unique_meds) == 3:
                            break
                    parsed_result["recommended_medicines"] = unique_meds
                    if len(unique_meds) >= 3:
                        print("適切な推奨医薬品が見つかりました（重複除去済み）")
                        return parsed_result
            except Exception as e:
                print(f"JSON解析エラー: {e}。再試行します。")
        except Exception as e:
            print(f"ChatGPT API呼び出しエラー: {e}")
    return {
        "recommended_medicines": [],
        "usage_notes": "適切な医薬品が見つかりませんでした。医師にご相談ください。",
        "doctor_consultation": "症状が改善しない場合は医師にご相談ください。",
    }
