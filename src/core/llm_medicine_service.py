"""
LLM（GPT）を用いた医薬品推奨サービス

症状推定、症状抽出、医薬品種類分析などGPT呼び出しの責務を持つ。
"""
import json
import logging
import os
import re
from openai import OpenAI

from src.core.medicine_data import BASE_DIR, DATA_DIR
from src.core.diagnosis_detection import is_diagnosis_term

logger = logging.getLogger(__name__)


def _get_api_key():
    """環境変数からAPIキーを取得（必要に応じてload_dotenvを試行）"""
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        return api_key
    try:
        from dotenv import load_dotenv
        load_dotenv(override=True)
        env_path = os.path.join(BASE_DIR, ".env")
        if os.path.exists(env_path):
            load_dotenv(env_path, override=True)
        return os.getenv("OPENAI_API_KEY")
    except ImportError:
        return None


def _get_client(client=None):
    """OpenAIクライアントを取得（未指定時はAPIキーから作成）"""
    if client is not None:
        return client
    api_key = _get_api_key()
    if not api_key:
        raise ValueError("OPENAI_API_KEYが環境変数に設定されていません。")
    return OpenAI(api_key=api_key)


def gpt_guess_symptom(user_text, symptom_list, client=None):
    """ChatGPTで症状リストから最も近い症状名を1～3個推定"""
    client = _get_client(client)
    prompt = (
        "あなたは医薬品推奨システムです。\n"
        "以下は症状リストです。\n"
        "ユーザーの症状文から最も近い症状名を日本語で返してください。(複数選択可)\n\n"
        "【症状リスト】\n" + "\n".join(f"{i+1}. {s}" for i, s in enumerate(symptom_list))
        + f"\nユーザーの症状: {user_text}"
    )
    from src.core.llm_client import chat_completion_create

    response = chat_completion_create(
        client,
        model_role="nlu",
        path="llm_medicine_service.guess_symptom",
        messages=[{"role": "system", "content": prompt}],
        temperature=0,
    )
    content = response.choices[0].message.content or ""
    if os.getenv("DEBUG_MODE", "false").lower() == "true" or logger.level <= logging.DEBUG:
        logger.debug(f"ChatGPT返答:\n{content.strip()}")
    symptoms = [s.strip() for s in re.split(r"[\n,、]", content) if s.strip()]
    return symptoms


def gpt_select_best_otc(user_text, candidates, client=None):
    """ChatGPTで候補リストから最適な市販薬3つを選ばせる"""
    client = _get_client(client)
    prompt = (
        f"あなたは医薬品推奨システムです。ユーザーの症状「{user_text}」に最も適した市販薬を3つ選び、理由も簡単に説明してください。(市販薬の重複は避けてください)\n\n"
        "【候補リスト】\n"
        + "\n".join(
            f"{i+1}. 製品名: {row['製品名']} / 効能効果: {row['効能効果']} / 成分: {row['成分']}"
            for i, (_, row) in enumerate(candidates.iterrows())
        )
    )
    from src.core.llm_client import chat_completion_create

    response = chat_completion_create(
        client,
        model_role="admin",
        path="llm_medicine_service.select_best_otc",
        messages=[{"role": "system", "content": prompt}],
        temperature=0,
    )
    content = response.choices[0].message.content or ""
    if os.getenv("DEBUG_MODE", "false").lower() == "true" or logger.level <= logging.DEBUG:
        logger.debug(f"ChatGPT返答:\n{content.strip()}")
    return content.strip()


def select_symptoms_via_gpt(user_text, symptoms_csv_path=None, client=None, max_symptoms=250):
    """ユーザーの症状文からChatGPTを使って適切な症状を抽出する"""
    comprehensive_symptom_list = [
        "頭痛", "発熱", "咳", "せき", "たん", "痰", "鼻水", "鼻づまり", "のどの痛み", "くしゃみ", "寒気", "悪寒",
        "腹痛", "下痢", "便秘", "吐き気", "嘔吐", "胃痛", "胸やけ", "胃もたれ",
        "めまい", "疲労感", "倦怠感", "だるさ", "むくみ", "筋肉痛", "関節痛", "肩こり", "腰痛",
        "かゆみ", "発疹", "湿疹", "蕁麻疹", "皮膚の乾燥",
        "打ち身", "打撲", "あざ", "青あざ", "内出血", "炎症",
        "不眠", "眠気", "イライラ", "不安", "ストレス",
        "生理痛", "月経不順", "更年期症状",
        "口内炎", "目の疲れ", "目のかゆみ", "目の充血", "耳鳴り", "動悸",
    ]
    user_text_lower = user_text.lower()
    inferred_symptoms = []
    cold_keywords = ["風邪", "かぜ", "風邪をひ", "風邪気味", "風邪っぽい", "風邪の症状"]
    if any(kw in user_text_lower for kw in cold_keywords):
        inferred_symptoms.extend(["頭痛", "発熱", "咳", "鼻水", "のどの痛み"])
    flu_keywords = ["インフルエンザ", "インフル", "インフルエンザの症状", "インフルエンザっぽい"]
    if any(kw in user_text_lower for kw in flu_keywords):
        inferred_symptoms.extend(["発熱", "頭痛", "関節痛", "筋肉痛", "悪寒", "咳"])
    gastroenteritis_keywords = ["胃腸炎", "胃腸の調子", "お腹の調子", "お腹を壊"]
    if any(kw in user_text_lower for kw in gastroenteritis_keywords):
        inferred_symptoms.extend(["腹痛", "下痢", "吐き気"])
    if "打ち身" in user_text:
        inferred_symptoms.append("打ち身")
    if "打撲" in user_text:
        inferred_symptoms.append("打撲")
    if "あざ" in user_text or "青あざ" in user_text or "あおたん" in user_text:
        inferred_symptoms.append("あざ")
    if "炎症" in user_text:
        inferred_symptoms.append("炎症")
    if "にえる" in user_text or "にえている" in user_text or "にえた" in user_text:
        inferred_symptoms.extend(["打ち身", "打撲", "あざ"])

    prompt = f"""
あなたは医薬品推奨システムです。ユーザーの症状文から該当する症状を正確に抽出してください。

【ユーザーの症状文】
{user_text}

【抽出すべき症状リスト】
{', '.join(comprehensive_symptom_list)}

【重要な指示】
1. ユーザーの症状文から該当する症状を抽出してください
2. 一般的な表現から典型的な症状を推測してください
3. 症状文に明示的に書かれていない症状でも、一般的な表現から推測できる典型的な症状は含めてください
4. 「完治したい」「治したい」などの表現が含まれていても、症状を抽出してください
5. 症状文が「こんにちは」などの挨拶のみの場合は、症状なしとして空のリストを返してください

【回答形式】
該当する症状を以下の形式で出力してください：
症状1, 症状2, 症状3

該当する症状がない場合は「なし」と出力してください。
"""
    messages = [
        {"role": "system", "content": "あなたは医薬品推奨システムです。ユーザーの症状文から正確に症状を抽出してください。"},
        {"role": "user", "content": prompt},
    ]
    try:
        client = _get_client(client)
    except ValueError as e:
        return {"status": "error", "symptoms": [], "message": str(e)}

    try:
        from src.core.llm_client import chat_completion_create

        response = chat_completion_create(
            client,
            model_role="nlu",
            path="llm_medicine_service.select_symptoms",
            messages=messages,
            temperature=0.1,
            max_tokens=500,
        )
        content = response.choices[0].message.content or ""
    except Exception as e:
        logger.error(f"ChatGPT API エラー: {e}")
        return {"status": "error", "symptoms": [], "message": f"ChatGPT API エラー: {e}"}

    symptoms = []
    if "なし" in content or "症状なし" in content or not content.strip():
        if inferred_symptoms:
            symptoms = inferred_symptoms
        else:
            return {"status": "success", "symptoms": [], "message": "No symptoms detected"}
    else:
        if "," in content:
            symptoms = [s.strip() for s in content.split(",") if s.strip()]
        else:
            symptoms = [line.strip(" ・-0123456789.") for line in content.splitlines() if line.strip()]
        symptoms = list(set(symptoms + inferred_symptoms))

    matched_symptoms = []
    for symptom in symptoms:
        if symptom in comprehensive_symptom_list:
            matched_symptoms.append(symptom)
        else:
            for ref_symptom in comprehensive_symptom_list:
                if symptom in ref_symptom or ref_symptom in symptom:
                    matched_symptoms.append(ref_symptom)
                    break
    matched_symptoms = list(set(matched_symptoms))
    return {"status": "success", "symptoms": matched_symptoms, "message": f"Extracted {len(matched_symptoms)} symptoms"}


def simple_symptom_and_type_detection(user_text):
    """簡易的な症状と医薬品種類の検出（APIフォールバック用）"""
    symptom_keywords = {
        "目のかゆみ": ["目が痒", "目がかゆ", "目の痒", "目のかゆ", "目痒", "目かゆ", "目のかゆみ"],
        "目の充血": ["目の充血", "目が赤い", "目赤", "充血", "目の血走り"],
        "目の疲れ": ["目の疲れ", "目が疲", "眼精疲労", "目の重い感じ"],
        "頭痛": ["頭痛", "頭が痛い", "ズキズキ", "偏頭痛", "頭が重い"],
        "発熱": ["熱", "発熱", "熱っぽい", "高熱", "微熱", "体温が高い"],
        "のどの痛み": ["のどが痛い", "喉が痛い", "のどの痛み", "咽頭痛", "喉痛", "のど痛", "喉の腫れ"],
        "咳": ["咳", "せき", "咳が出る", "咳込む", "空咳"],
        "鼻水": ["鼻水", "鼻みず", "鼻汁", "鼻が出る", "水っぽい鼻水"],
        "鼻づまり": ["鼻づまり", "鼻詰まり", "鼻が詰まる", "鼻閉"],
        "くしゃみ": ["くしゃみ", "クシャミ", "くしゃみが出る"],
        "寒気": ["寒気", "さむけ", "悪寒", "ゾクゾクする", "悪寒がする"],
        "悪寒": ["悪寒", "寒気", "さむけ", "ゾクゾクする", "悪寒がする"],
        "胃痛": ["胃痛", "胃が痛い", "胃の痛み", "胃部痛", "みぞおちの痛み", "胃が痛む"],
        "腹痛": ["腹痛", "お腹が痛い", "腹部痛", "おなかが痛い", "腹が痛い", "腹痛が続く"],
        "下痢": ["下痢", "軟便", "水様便", "便がゆるい", "便が緩い", "下痢が続く"],
        "便秘": ["便秘", "便が出ない", "便通がない", "便が硬い", "便秘が続く"],
        "吐き気": ["吐き気", "嘔吐", "むかつき", "気持ち悪い", "嘔吐感", "吐きそう"],
        "胸やけ": ["胸やけ", "胸焼け", "胃の重い感じ", "酸が上がる", "胸が苦い"],
        "胃もたれ": ["胃もたれ", "もたれる", "消化不良", "胃の重い感じ", "消化が悪い", "胃の不快感"],
        "かゆみ": ["かゆい", "痒み", "かゆみ", "皮膚のかゆみ", "皮膚が痒い"],
        "発疹": ["発疹", "ブツブツ", "赤い斑点", "皮膚の異常", "皮膚に赤い斑点が出る"],
        "湿疹": ["湿疹", "皮膚炎", "かぶれ", "皮膚の炎症"],
        "蕁麻疹": ["蕁麻疹", "じんましん", "じん麻疹", "蕁麻疹が出る"],
        "筋肉痛": ["筋肉痛", "筋肉の痛み", "体が痛い", "筋肉が痛い", "筋肉が痛む"],
        "関節痛": ["関節痛", "関節の痛み", "節々が痛い", "関節が痛い", "関節が痛む"],
        "肩こり": ["肩こり", "肩の凝り", "肩の痛み", "首肩の痛み", "肩が凝る"],
        "腰痛": ["腰痛", "腰が痛い", "腰の痛み", "腰が痛む"],
        "生理痛": ["生理痛", "月経痛", "生理", "生理の痛み", "下腹部痛", "生理痛が続く"],
        "めまい": ["めまい", "眩暈", "ふらつき", "立ちくらみ", "めまいが続く"],
        "疲労感": ["疲労感", "疲れ", "倦怠感", "だるい", "疲労感が続く"],
        "倦怠感": ["倦怠感", "疲労感", "疲れ", "だるい", "倦怠感が続く"],
        "不眠": ["不眠", "眠れない", "睡眠不足", "寝つきが悪い", "不眠が続く"],
    }
    detected_symptoms = []
    for symptom, keywords in symptom_keywords.items():
        for keyword in keywords:
            if keyword in user_text:
                detected_symptoms.append(symptom)
                break
    detected_symptoms = list(set(detected_symptoms))
    medicine_type = "その他"
    eye_symptoms = ["目のかゆみ", "目の充血", "目の疲れ"]
    if any(s in detected_symptoms for s in eye_symptoms):
        medicine_type = "目薬"
    elif any(s in detected_symptoms for s in ["かゆみ", "発疹", "湿疹", "蕁麻疹"]):
        medicine_type = "外用薬（皮膚）"
    elif any(s in detected_symptoms for s in ["胃痛", "腹痛", "下痢", "便秘", "吐き気", "胸やけ", "胃もたれ"]):
        medicine_type = "胃腸薬"
    elif any(s in detected_symptoms for s in ["筋肉痛", "関節痛", "肩こり", "腰痛"]):
        medicine_type = "筋肉痛" if "筋肉痛" in detected_symptoms else "解熱鎮痛薬"
    elif any(s in detected_symptoms for s in ["鼻水", "鼻づまり", "くしゃみ"]):
        other_cold_symptoms = ["発熱", "のどの痛み", "咳"]
        medicine_type = "鼻炎用薬" if not any(s in detected_symptoms for s in other_cold_symptoms) else "風邪薬"
    elif any(s in detected_symptoms for s in ["発熱", "のどの痛み", "咳"]):
        medicine_type = "風邪薬"
    elif any(s in detected_symptoms for s in ["頭痛", "生理痛"]):
        medicine_type = "解熱鎮痛薬"
    return {"symptoms": detected_symptoms, "medicine_type": medicine_type}


def analyze_symptoms_and_medicine_type(user_text, client=None):
    """症状文から症状と適する医薬品の種類を返す（診断名検出あり）"""
    try:
        client = _get_client(client)
    except ValueError:
        return simple_symptom_and_type_detection(user_text)

    try:
        is_diagnosis, diagnosis_type, diagnosis_response = is_diagnosis_term(user_text)
        if is_diagnosis:
            has_side_effect = diagnosis_response.get("has_side_effect", False)
            should_show_counseling = diagnosis_response.get("should_show_counseling", False)
            if has_side_effect or not should_show_counseling:
                return {
                    "symptoms": [],
                    "medicine_type": "その他",
                    "is_diagnosis": True,
                    "diagnosis_type": diagnosis_type,
                    "diagnosis_response": diagnosis_response,
                }
    except Exception:
        is_diagnosis, diagnosis_type, diagnosis_response = is_diagnosis_term(user_text)
        if is_diagnosis:
            return {
                "symptoms": [],
                "medicine_type": "その他",
                "is_diagnosis": True,
                "diagnosis_type": diagnosis_type,
                "diagnosis_response": diagnosis_response,
            }

    medicine_types = [
        "筋肉痛", "睡眠障害", "精神症状", "その他", "胃腸薬",
        "解熱鎮痛薬", "外用薬（皮膚）", "抗アレルギー薬", "禁煙補助薬",
        "鼻炎用薬", "風邪薬", "目薬", "更年期障害",
    ]
    symptoms_list = [
        "頭痛", "発熱", "咳", "鼻水", "鼻づまり", "のどの痛み", "くしゃみ", "寒気", "悪寒",
        "腹痛", "下痢", "便秘", "吐き気", "嘔吐", "胃痛", "胸やけ", "胃もたれ",
        "めまい", "疲労感", "倦怠感", "筋肉痛", "関節痛", "肩こり", "腰痛",
        "かゆみ", "発疹", "湿疹", "蕁麻疹", "皮膚の乾燥",
        "不眠", "眠気", "イライラ", "不安", "ストレス",
        "生理痛", "月経不順", "更年期症状",
        "口内炎", "目の疲れ", "目のかゆみ", "目の充血", "耳鳴り", "動悸",
    ]
    hangover_keywords = ["二日酔い", "2日酔い", "二日酔", "2日酔", "飲みすぎ", "飲み過ぎ", "深酒", "アルコール"]
    is_hangover = any(keyword in user_text for keyword in hangover_keywords)

    prompt = f"""
あなたは医薬品推奨システムです。ユーザーの症状文を分析して、該当する症状と適する医薬品の種類を選択してください。

【ユーザーの症状文】
{user_text}

【選択可能な症状リスト】
{', '.join(symptoms_list)}

【医薬品の種類】
{', '.join(medicine_types)}

【重要な判断ルール】
- 「二日酔い」「飲みすぎ」などのキーワードが含まれている場合は、「胃腸薬」を選択してください（最優先）
- 目の症状がある場合は「目薬」を選択してください
- 皮膚のかゆみは「外用薬（皮膚）」を選択してください
- 生理痛・月経不順は「解熱鎮痛薬」を選択してください

【回答形式】
以下のJSON形式で回答してください：
{{"symptoms": ["症状1", "症状2"], "medicine_type": "適する医薬品の種類"}}

該当する症状がない場合は：{{"symptoms": [], "medicine_type": "その他"}}
"""
    try:
        from src.core.llm_client import chat_completion_create

        response = chat_completion_create(
            client,
            model_role="nlu",
            path="llm_medicine_service.symptom_and_type",
            messages=[
                {"role": "system", "content": "あなたは医薬品の専門家です。症状に適した医薬品を推奨してください。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=500,
        )
        result = response.choices[0].message.content
        if not result:
            return {"symptoms": [], "medicine_type": None}
        json_start = result.find("{") if result else -1
        json_end = result.rfind("}") + 1 if result else -1
        if json_start != -1 and json_end != -1:
            parsed_result = json.loads(result[json_start:json_end])
            if is_hangover:
                parsed_result["medicine_type"] = "胃腸薬"
            if parsed_result.get("medicine_type") == "その他":
                parsed_result["medicine_type"] = None
            return parsed_result
    except Exception as e:
        logger.warning(f"ChatGPT API呼び出しエラー: {e}、簡易検出にフォールバック")
    return simple_symptom_and_type_detection(user_text)
