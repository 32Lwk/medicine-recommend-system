import pandas as pd
from openai import OpenAI
import os
import re
import time
import logging
from typing import Dict
from src.utils.debug_logger import add_network_log, performance_stats
from datetime import datetime
# from typing import List
# from openai.types.chat import ChatCompletionMessageParam ←不要なので削除

# ログ設定
logger = logging.getLogger(__name__)

# 医薬品データ（CSV読み込み・検索）は medicine_data に集約
from src.core.medicine_data import (
    BASE_DIR,
    CSV_PATH,
    DATA_DIR,
    clean_csv_data,
    csv_load_status,
    df,
    find_otc_candidates,
    get_medicines_by_symptom,
    get_medicines_by_type,
)

from src.core.language_utils import detect_language
from src.core.diagnosis_detection import is_diagnosis_term, is_diagnosis_only, has_side_effect_mention
from src.core.attribute_extractor import (
    create_multilingual_attribute_extraction_prompt,
    extract_user_attributes_multilingual,
)
# 後方互換: medicine_logic 経由の import を許容


from src.core.translation_service import translate_medicine_recommendation
from src.core.user_detection import (
    PENALTY_MAP,
    calculate_completeness_penalty,
    detect_digestive_sensitivity,
    detect_postpartum_breastfeeding,
    detect_severity_escalation,
    determine_pain_urgency,
    extract_user_preferences,
    generate_doctor_referral_message,
)
from src.core.llm_medicine_service import (
    analyze_symptoms_and_medicine_type,
    gpt_guess_symptom,
    gpt_select_best_otc,
    select_symptoms_via_gpt,
    simple_symptom_and_type_detection,
)

# Markdown太文字をHTML太文字に変換する関数
def convert_markdown_bold(text):
    """Markdown形式の太文字（**文字**）をHTML太文字タグに変換"""
    if text is None:
        return ""
    # **文字** を <strong>文字</strong> に変換
    result = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
    # ### で始まる行を除去
    result = re.sub(r'^###+\s*', '', result, flags=re.MULTILINE)
    # ## で始まる行を除去
    result = re.sub(r'^##+\s*', '', result, flags=re.MULTILINE)
    # # で始まる行を除去
    result = re.sub(r'^#+\s*', '', result, flags=re.MULTILINE)
    # 行頭の余分な空白を除去
    result = re.sub(r'^\s+', '', result, flags=re.MULTILINE)
    return result

# 使用上の注意生成のキャッシュ
_usage_notes_cache = {}

def generate_usage_notes(medicine_name: str, medicine_info: dict, user_info: dict = None, symptoms: list = None) -> str:
    """
    ChatGPTを使用して医薬品の使用上の注意を自動生成（キャッシュ機能付き）
    
    Args:
        medicine_name: 医薬品名
        medicine_info: 医薬品情報（成分、効能、年齢制限など）
        user_info: ユーザー情報（年齢、妊娠状態など）
        symptoms: ユーザーの症状情報（リスト形式、例：['眠気', '不眠']）
    
    Returns:
        str: 生成された使用上の注意
    """
    try:
        # カフェイン含有の確認（キャッシュキーにも含める）
        ingredients_str = str(medicine_info.get('ingredients', '')).lower()
        efficacy_str = str(medicine_info.get('efficacy', '')).lower()
        contains_caffeine = any(keyword in ingredients_str or keyword in efficacy_str 
                               for keyword in ['カフェイン', 'caffeine', '眠気', '眠気の除去', '眠気・倦怠感の除去'])
        
        # キャッシュキーの生成（医薬品名、ユーザー情報、カフェイン含有情報、症状情報の組み合わせ）
        # カフェイン剤の場合はプロンプトが異なるため、キャッシュキーにも含める
        # 症状情報も含める（症状に合わせた使用上の注意を生成するため）
        symptoms_str = ','.join(sorted(symptoms)) if symptoms else ''
        cache_key = f"{medicine_name}_{hash(str(user_info))}_{contains_caffeine}_{symptoms_str}"
        
        # キャッシュから取得を試行
        if cache_key in _usage_notes_cache:
            if os.getenv('DEBUG_MODE', 'false').lower() == 'true' or logger.level <= logging.DEBUG:
                logger.debug(f"📋 使用上の注意をキャッシュから取得: {medicine_name}")
            return _usage_notes_cache[cache_key]
        
        # ユーザー情報の準備
        user_context = ""
        if user_info:
            if user_info.get('age'):
                user_context += f"年齢: {user_info['age']}歳\n"
            if user_info.get('pregnant'):
                user_context += "妊娠中\n"
            if user_info.get('breastfeeding'):
                user_context += "授乳中\n"
            if user_info.get('allergies'):
                user_context += f"アレルギー: {', '.join(user_info['allergies'])}\n"
        
        # ドーピング禁止物質の情報を追加
        doping_info = ""
        if medicine_info.get('doping_prohibited') == '禁止物質あり':
            doping_info = f"""
ドーピング禁止物質情報:
- 禁止物質あり: {medicine_info.get('doping_prohibited', 'なし')}
- 競技会区分: {medicine_info.get('competition_category', '情報なし')}
- 条件: {medicine_info.get('conditions', '情報なし')}
"""
        
        # カフェイン剤の場合の追加注意事項
        caffeine_note = ""
        if contains_caffeine:
            caffeine_note = """
【カフェイン剤に関する重要な注意事項】
- 添付文書に記載された服用期間や用法・用量を守り、短期間の服用にとどめるようにしてください
- 1日の摂取量を守ること（過剰摂取は避ける）
- カフェインを多く含む飲料と併用した場合には、カフェインの過量摂取となり、重大な健康被害につながるおそれがあります。そのため、コーヒーやお茶、エナジードリンクなどのカフェイン含有飲料と同時に服用しないでください
- 就寝前の使用は避ける（不眠の原因になる可能性がある）
- 常用化のリスクがあるため、一時的な使用に留める
- 慢性的な眠気の場合は医師にご相談ください

【服用してはいけない方】
- 胃酸過多の症状がある方、胃潰瘍と診断された方（カフェインは胃を刺激して胃酸の分泌をうながす働きがあり、胃を荒らすおそれがあるため）
- 心臓病と診断された方（カフェインは中枢神経に作用して眠気を除去するとともに、心臓の収縮や脈拍数を増やし、心臓に負担をかけて症状を悪化させる可能性があるため）

【悪影響のない1日あたりのカフェイン最大摂取量目安】
- 健康な成人：400mg（コーヒーマグカップ3杯分）
- 妊娠中の方：200〜300mg/日（コーヒーマグカップ2杯分）
- 授乳中の方：200mg/日

【15歳未満の小児について】
市販薬としては販売されていないため、薬以外の眠気を覚ます方法を試すか、生活リズムを整えたり、睡眠を見直してみることをおすすめします。

"""
        
        # カフェイン剤の詳細指示を準備
        caffeine_instruction = ""
        if contains_caffeine:
            newline = "\n"
            caffeine_instruction = f"""カフェイン剤の場合、以下の内容を必ず含めてください：
- 添付文書に記載された服用期間や用法・用量を守り、短期間の服用にとどめる
- 1日の摂取量上限（健康な成人400mg、妊娠中200-300mg/日、授乳中200mg/日）
- カフェイン含有飲料（コーヒー、お茶、エナジードリンクなど）との併用禁止
- 就寝前の使用を避けること
- 胃酸過多・胃潰瘍、心臓病の方は服用不可
- 15歳未満の小児は市販薬として販売されていない

【重要な注意事項】
- カフェイン剤は眠気覚ましの薬であり、不眠症向けの睡眠改善薬ではありません
- 「睡眠改善薬」や「不眠症」に関する注意事項は含めないでください
- 緑内障や前立腺肥大の禁忌事項は含めないでください（カフェイン剤には一般的に該当しません）
- 「使ってはいけない人」には、胃酸過多・胃潰瘍、心臓病の方のみを含めてください
"""
        
        caffeine_item = '9. カフェイン剤としての注意事項（1日の摂取量、使用期間、就寝前の使用について）' if contains_caffeine else ''
        
        # system messageの内容をカフェイン剤の場合に調整
        system_message = "あなたは医薬品の専門家です。症状に適した医薬品を推奨し、使用上の注意を説明してください。効能・効果が限定された特殊用途の医薬品（例：「食あたり等」「便秘」など）は、ユーザーの症状がその限定用途と完全に一致する場合のみ推奨してください。一般的な症状に対して特殊用途の医薬品を無理に推奨することは避けてください。"
        
        if contains_caffeine:
            system_message += " カフェイン剤（眠気覚まし）の場合、不眠症向けの睡眠改善薬に関する注意事項（例：「睡眠改善薬は一時的な不眠にのみ効果があります」「不眠症と診断されている場合は医師にご相談ください」など）は含めないでください。また、緑内障や前立腺肥大の禁忌事項も含めないでください。"
        
        # 症状情報の準備
        symptoms_context = ""
        if symptoms:
            symptoms_list = [s.get('name', s) if isinstance(s, dict) else s for s in symptoms]
            symptoms_context = f"ユーザーの症状: {', '.join(symptoms_list)}\n"
        
        # プロンプトの構築
        prompt = f"""
以下の医薬品について、使用上の注意を生成してください。

医薬品名: {medicine_name}
成分: {medicine_info.get('ingredients', '情報なし')}
効能・効果: {medicine_info.get('efficacy', '情報なし')}
年齢制限: {medicine_info.get('age_restriction', '情報なし')}
用法・用量: {medicine_info.get('usage', '情報なし')}
{doping_info}
{caffeine_note}

ユーザー情報:
{user_context if user_context else '情報なし'}
{symptoms_context}

以下の形式で使用上の注意を生成してください：
1. 基本的な使用上の注意
2. 年齢・性別による注意点（年齢制限の詳細を含む）
3. 妊娠・授乳中の注意点
4. アレルギーに関する注意点
5. 副作用について
6. 他の薬との相互作用
7. 保存方法・保管上の注意
8. ドーピング禁止物質に関する注意（該当する場合）
{f'{caffeine_item}' if contains_caffeine else ''}

各項目は簡潔で分かりやすく、実際の使用場面で役立つ内容にしてください。
特に年齢制限とドーピング禁止物質については、具体的で明確な注意事項を含めてください。
{symptoms_context and f'ユーザーの症状（{symptoms_context.split(":")[1].strip()}）に合わせた注意事項を含めてください。' or ''}
{caffeine_instruction}
"""
        
        # ChatGPT APIを呼び出し
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1200,
            temperature=0.7
        )
        
        usage_notes = response.choices[0].message.content.strip()
        
        # HTMLタグを適切に処理
        usage_notes = convert_markdown_bold(usage_notes)
        
        # キャッシュに保存（最大100件まで）
        if len(_usage_notes_cache) < 100:
            _usage_notes_cache[cache_key] = usage_notes
            if os.getenv('DEBUG_MODE', 'false').lower() == 'true' or logger.level <= logging.DEBUG:
                logger.debug(f"💾 使用上の注意をキャッシュに保存: {medicine_name}")
        
        return usage_notes
        
    except Exception as e:
        logger.error(f"使用上の注意生成エラー: {e}")
        return "使用上の注意の生成に失敗しました。薬剤師または登録販売者にご相談ください。"

# テキストを整形して見やすくする関数
def format_text_for_display(text):
    """テキストを整形して見やすくする"""
    if text is None:
        return ""
    
    # ①、②、③などの丸数字の後に改行を追加
    text = re.sub(r'([①②③④⑤⑥⑦⑧⑨⑩])\s*', r'\1<br>', text)
    
    # 1.、2.、3.などの数字の後に改行を追加
    text = re.sub(r'(\d+\.)\s*', r'\1<br>', text)
    
    # - で始まる行の前に改行を追加
    text = re.sub(r'\n\s*-\s*', r'<br>- ', text)
    
    # ・ で始まる行の前に改行を追加
    text = re.sub(r'\n\s*・\s*', r'<br>・ ', text)
    
    # 改行を適切に処理（最初に改行を処理）
    text = text.replace('\n\n', '<br><br>')
    text = text.replace('\n', '<br>')
    
    # 丸数字の後の改行を再度確認
    text = re.sub(r'([①②③④⑤⑥⑦⑧⑨⑩])(?!<br>)', r'\1<br>', text)
    
    # 数字の後の改行を再度確認
    text = re.sub(r'(\d+\.)(?!<br>)', r'\1<br>', text)
    
    # Markdown太文字をHTML太文字に変換
    text = convert_markdown_bold(text)
    
    return text

# .envファイルから環境変数を読み込み（オプショナル）
# load_dotenv関数をグローバルスコープで利用できるようにする
load_dotenv_func = None
try:
    from dotenv import load_dotenv
    load_dotenv_func = load_dotenv  # グローバル変数として保存
    # スクリプトのディレクトリを基準に.envファイルを読み込む（BASE_DIRはプロジェクトルート）
    env_path = os.path.join(BASE_DIR, '.env')
    
    # デバッグ情報（DEBUG_MODE時のみ）
    if os.getenv('DEBUG_MODE', 'false').lower() == 'true':
        logger.debug(f"[DEBUG] BASE_DIR: {BASE_DIR}")
        logger.debug(f"[DEBUG] 現在の作業ディレクトリ: {os.getcwd()}")
        logger.debug(f"[DEBUG] .envファイルのパス（BASE_DIR）: {env_path}")
        logger.debug(f"[DEBUG] .envファイル存在確認（BASE_DIR）: {os.path.exists(env_path)}")
    
    # まず引数なしでload_dotenvを呼び出し、現在の作業ディレクトリから上位ディレクトリを自動検索
    loaded = load_dotenv(override=True)  # override=Trueで確実に読み込む
    if os.getenv('DEBUG_MODE', 'false').lower() == 'true':
        logger.debug(f"[DEBUG] load_dotenv() (引数なし) 結果: {loaded}")
    
    # 明示的なパスも試す（存在する場合は読み込む）
    env_loaded = False
    if os.path.exists(env_path):
        env_loaded = load_dotenv(env_path, override=True)  # override=Trueで確実に読み込む
        if os.getenv('DEBUG_MODE', 'false').lower() == 'true':
            logger.debug(f"[DEBUG] load_dotenv({env_path}) 結果: {env_loaded}")
    else:
        # 現在の作業ディレクトリから.envファイルを確認
        cwd_env = os.path.join(os.getcwd(), '.env')
        if os.getenv('DEBUG_MODE', 'false').lower() == 'true':
            logger.debug(f"[DEBUG] .envファイルのパス（現在の作業ディレクトリ）: {cwd_env}")
            logger.debug(f"[DEBUG] .envファイル存在確認（CWD）: {os.path.exists(cwd_env)}")
        if os.path.exists(cwd_env):
            env_loaded = load_dotenv(cwd_env, override=True)  # override=Trueで確実に読み込む
            if os.getenv('DEBUG_MODE', 'false').lower() == 'true':
                logger.debug(f"[DEBUG] load_dotenv({cwd_env}) 結果: {env_loaded}")
    
    logger.info("dotenvを使用して.envファイルから環境変数を読み込みました。")
except ImportError:
    logger.info("python-dotenvがインストールされていません。環境変数のみを使用します。")

# --- OpenAI APIキー設定 ---
# 環境変数からAPIキーを取得
api_key = os.getenv('OPENAI_API_KEY')

# デバッグ用: 環境変数の確認（値の一部のみ表示）
if api_key:
    if os.getenv('DEBUG_MODE', 'false').lower() == 'true':
        logger.debug(f"APIキーが読み込まれました（長さ: {len(api_key)}文字）")
else:
    logger.warning("WARNING: OpenAI API keyが環境変数に設定されていません。")
    logger.warning("環境変数 OPENAI_API_KEY を設定してください。")

# --- OpenAIクライアント初期化 ---
client = None
if api_key:
    try:
        client = OpenAI(api_key=api_key)
        if os.getenv('DEBUG_MODE', 'false').lower() == 'true':
            logger.debug("OpenAI client initialized successfully.")
    except Exception as e:
        logger.error(f"Error initializing OpenAI client: {e}")
else:
    logger.error("Error: OpenAI API key not found. Please set it in environment variables or .env file.")

def recommend_otc_medicines_via_gpt(user_text, symptom_csv_path=None, otc_csv_path=None, max_candidates=20, client=None):
    """
    ユーザー症状文→ChatGPTで症状名推定→候補薬抽出→ChatGPTで最適薬3つ選定
    """
    import pandas as pd
    import os
    # CSV読み込み
    base_dir = BASE_DIR
    data_dir = DATA_DIR
    symptom_csv = symptom_csv_path or os.path.join(data_dir, "症状-薬.csv")
    otc_csv = otc_csv_path or os.path.join(data_dir, "otc_medicine_data.csv")
    df_symptom = pd.read_csv(symptom_csv)
    df_otc = pd.read_csv(otc_csv)
    
    # NaN値を適切に処理
    df_otc = df_otc.fillna("")
    # 症状リスト作成
    symptom_list = df_symptom["症状"].dropna().unique().tolist()
    # 1. ChatGPTで症状名推定
    symptoms = gpt_guess_symptom(user_text, symptom_list, client=client)
    # 2. 候補薬抽出
    candidates = find_otc_candidates(symptoms, df_otc, max_candidates=max_candidates)
    if candidates.empty:
        return "該当する市販薬情報が見つかりませんでした。"
    # 3. ChatGPTで最適薬3つ選定
    result = gpt_select_best_otc(user_text, candidates, client=client)
    if os.getenv('DEBUG_MODE', 'false').lower() == 'true' or logger.level <= logging.DEBUG:
        logger.debug(f"ChatGPT返答:\n{result}")
    return result

def recommend_otc_medicines_from_summarized(user_text, summarized_csv_path=None, max_candidates=20, client=None):
    """
    summarized_efficacy_data.csvを用いて、
    1. 症状語リストを自動抽出
    2. ChatGPTで症状名推定（表記ゆれ・複数症状対応）
    3. 候補薬リストを抽出
    4. ChatGPTに候補リスト＋症状文を渡し、最適な3つを選ばせる
    """
    import pandas as pd
    import os
    import re
    # CSV読み込み
    base_dir = BASE_DIR
    data_dir = DATA_DIR
    summarized_csv = summarized_csv_path or os.path.join(data_dir, "summarized_efficacy_data.csv")
    df = pd.read_csv(summarized_csv)
    
    # NaN値を適切に処理
    df = df.fillna("")
    # --- 症状語リストを抽出 ---
    symptom_set = set()
    for eff in df["Summarized Efficacy"].dropna():
        # かっこ内の症状語を抽出
        m = re.search(r'（(.+?)）', eff)
        if m:
            for s in re.split(r'[、,]', m.group(1)):
                s = s.strip()
                if s:
                    symptom_set.add(s)
    # 類義語・表記ゆれ対応（例: 咳/せき, 鼻水/鼻みず など）
    synonym_map = {
        "咳": ["咳", "せき"],
        "鼻水": ["鼻水", "鼻みず"],
        "痰": ["痰", "たん"],
        "悪寒": ["悪寒", "さむけ"],
        "関節の痛み": ["関節の痛み", "関節痛"],
        "筋肉の痛み": ["筋肉の痛み", "筋肉痛"],
        # 必要に応じて追加
    }
    # 症状語リストを展開
    expanded_symptom_set = set()
    for s in symptom_set:
        expanded_symptom_set.add(s)
        for syns in synonym_map.values():
            if s in syns:
                expanded_symptom_set.update(syns)
    symptom_list = sorted(expanded_symptom_set)
    # --- 1. ChatGPTで症状名推定 ---
    symptoms = gpt_guess_symptom(user_text, symptom_list, client=client)
    # --- 2. 類義語も含めて候補薬抽出 ---
    # 入力症状の類義語も展開
    all_symptoms = set(symptoms)
    for s in symptoms:
        for key, syns in synonym_map.items():
            if s in syns:
                all_symptoms.update(syns)
    # 候補薬抽出（すべての症状語のいずれかを含むもの）
    mask = df["Summarized Efficacy"].astype(str).apply(lambda x: any(s in x for s in all_symptoms))
    candidates = df[mask].copy()
    # カバー症状数でソート（多くカバーする薬を上位に）
    def count_covered(eff):
        return sum(s in eff for s in all_symptoms)
    candidates["_cover_count"] = candidates["Summarized Efficacy"].astype(str).apply(count_covered)
    candidates = candidates.sort_values("_cover_count", ascending=False).head(max_candidates)
    if candidates.empty:
        return "該当する市販薬情報が見つかりませんでした。"
    # --- 3. ChatGPTで最適薬3つ選定 ---
    # プロンプト工夫: 症状文・推定症状語・候補リストを明示
    prompt = (
        f"あなたは医薬品推奨システムです。ユーザーの症状:『{user_text}』\n"
        f"推定された症状語: {', '.join(symptoms)}\n"
        "以下の候補リストから、症状に最も適した市販薬を3つ選び、それぞれの医薬品の特徴を効果効能から要約して日本語で説明してください。\n"
        "【候補リスト】\n" +
        "\n".join(
            f"{i+1}. 製品名: {row['製品名']} / 効能効果: {row['Summarized Efficacy']}"
            for i, (_, row) in enumerate(candidates.iterrows())
        )
    )
    messages = [
        {"role": "system", "content": prompt}
    ]
    if client is None:
        client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        temperature=0
    )
    content = response.choices[0].message.content if response.choices[0].message.content else ""
    if os.getenv('DEBUG_MODE', 'false').lower() == 'true' or logger.level <= logging.DEBUG:
        logger.debug(f"ChatGPT返答:\n{content.strip()}")
    return content.strip() 

def gpt_select_efficacy_candidates(user_text, summarized_csv_path=None, max_candidates=30, client=None):
    """
    ChatGPTにsummarized_efficacy_data.csvの効能効果リストを渡し、
    ユーザー症状に最も近い効能効果（複数可）を選ばせる
    """
    import pandas as pd
    import os
    summarized_csv = summarized_csv_path or os.path.join(DATA_DIR, "summarized_efficacy_data.csv")
    df = pd.read_csv(summarized_csv)
    
    # NaN値を適切に処理
    df = df.fillna("")
    efficacy_list = df["Summarized Efficacy"].dropna().unique().tolist()
    # 候補数が多すぎる場合はランダムサンプリング
    import random
    if len(efficacy_list) > max_candidates:
        efficacy_list = random.sample(efficacy_list, max_candidates)
    prompt = (
        f"あなたは医薬品推奨システムです。下記は市販薬の効能効果リストです。\n"
        f"ユーザーの症状:『{user_text}』\n"
        "この中から症状に最も近い効能効果をすべて選び、日本語でリスト形式で出力してください。\n"
        "【効能効果リスト】\n" +
        "\n".join(f"{i+1}. {e}" for i, e in enumerate(efficacy_list))
    )
    messages = [
        {"role": "system", "content": prompt}
    ]
    if client is None:
        client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        temperature=0
    )
    content = response.choices[0].message.content if response.choices[0].message.content else ""
    if os.getenv('DEBUG_MODE', 'false').lower() == 'true' or logger.level <= logging.DEBUG:
        logger.debug(f"ChatGPT返答:\n{content.strip()}")
    # リスト形式で返す
    selected = [line.strip(" ・-0123456789.") for line in content.splitlines() if line.strip()]
    # 元の効能効果リストと突合して正規化
    selected_set = set(selected)
    matched_efficacy = [e for e in efficacy_list if any(s in e or e in s for s in selected_set)]
    return matched_efficacy


def recommend_medicines_with_retry(user_text, symptoms, medicine_list, user_info=None, client=None, max_retries=3):
    """
    症状と医薬品リストをChatGPTに渡して推奨医薬品を3つ選び、
    使用上の注意を要約して返す。適した医薬品が返ってこなければ再試行
    """
    # セキュリティ検証の追加
    from src.security.security_validator import validate_user_input
    from src.security.security_config import should_block_input, get_current_phase
    from src.security.security_logger import log_input_validation
    
    # 入力検証
    is_safe, risk_score, warnings, sanitized_text = validate_user_input(
        user_text, context='medicine_recommendation'
    )
    
    # ログ記録
    log_input_validation(
        user_id='medicine_recommendation',
        input_text=user_text,
        risk_score=risk_score,
        is_safe=is_safe,
        warnings=warnings,
        sanitized_text=sanitized_text
    )
    
    # ブロック判定
    if should_block_input(risk_score):
        print(f"⚠️ 医薬品推奨がブロックされました: リスクスコア {risk_score}")
        return {
            "recommended_medicines": [],
            "usage_notes": "入力内容に問題が検出されました。症状や質問を自然な文章で入力してください。",
            "doctor_consultation": "医師にご相談ください。"
        }
    
    # 高リスク入力の場合は医薬品推奨を停止
    if risk_score >= 80:
        print(f"⚠️ 高リスク入力のため医薬品推奨を停止: リスクスコア {risk_score}")
        return {
            "recommended_medicines": [],
            "usage_notes": "入力内容に不審なパターンが検出されました。症状や質問を自然な文章で入力してください。",
            "doctor_consultation": "医師にご相談ください。"
        }
    
    if client is None:
        client = OpenAI(api_key=api_key)
    
    # 医薬品リストを文字列に変換（使用上の注意も含める）
    medicine_text = ""
    for i, medicine in enumerate(medicine_list[:20]):  # 最初の20個のみ使用
        usage_notes = medicine.get('使用上の注意', '')
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
        {{
            "number": 1,
            "product_name": "製品名",
            "manufacturer": "メーカー名",
            "reason": "推奨理由",
            "usage_notes": "この医薬品の使用上の注意点の要約"
        }},
        {{
            "number": 2,
            "product_name": "製品名",
            "manufacturer": "メーカー名",
            "reason": "推奨理由",
            "usage_notes": "この医薬品の使用上の注意点の要約"
        }},
        {{
            "number": 3,
            "product_name": "製品名",
            "manufacturer": "メーカー名",
            "reason": "推奨理由",
            "usage_notes": "この医薬品の使用上の注意点の要約"
        }}
    ],
    "doctor_consultation": "医師の受診が必要な場合について"
}}

注意：
- 症状に最も適した医薬品を3つ選んでください
- 製品名とメーカー名が同じものは重複として、同じものを複数回推奨しないでください
- 番号は1つ目、2つ目、3つ目の順で出力してください（例："number": 1, "number": 2, "number": 3）
- 製品名とメーカー名は正確に記載してください
- 各医薬品の「使用上の注意」欄の内容を参考に、必ず各医薬品ごとに使用上の注意点を要約してください
- 医師の受診が必要な場合についても記載してください
- 効能・効果が限定された特殊用途の医薬品（例：「食あたり等」「便秘のみ」「腸内容物の急速な排除」など）は、ユーザーの症状がその限定用途と完全に一致する場合のみ推奨してください
- 一般的な症状に対して特殊用途の医薬品を無理に推奨することは避けてください
- リスク成分（ヒマシ油、センナ、アロエエキス、ビサコジル、アスピリン、トラマドールなど）が含まれる医薬品は、詳細な症状情報がない場合は推奨を避けてください
- インフルエンザの可能性がある場合（高熱38.5度以上+複数の風邪症状）は、アスピリンを含む医薬品は絶対に推奨しないでください
- 単一症状（例：発熱のみ）の場合は、総合感冒薬よりも特化した医薬品（例：解熱鎮痛薬）を優先してください
"""

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": """あなたは医薬品の専門家です。症状に適した医薬品を推奨し、使用上の注意を説明してください。

重要な推奨ルール：
- 効能効果が限定された特殊用途の医薬品（「食あたり等」「便秘のみ」「腸内容物の急速な排除」など）は、ユーザーの症状がその限定用途と完全に一致する場合のみ推奨してください
- 一般的な症状に対して特殊用途の医薬品を無理に推奨することは避けてください
- リスク成分（ヒマシ油、センナ、アロエエキス、ビサコジル、アスピリン、トラマドールなど）が含まれる医薬品は、詳細な症状情報がない場合は推奨を避けてください
- インフルエンザの可能性がある場合（高熱38.5度以上+複数の風邪症状）は、アスピリンを含む医薬品は絶対に推奨しないでください
- 単一症状（例：発熱のみ）の場合は、総合感冒薬よりも特化した医薬品（例：解熱鎮痛薬）を優先してください
- 症状に最も適した医薬品を3つ選び、製品名とメーカー名は正確に記載してください"""},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=800
            )
            
            result = response.choices[0].message.content
            print(f"ChatGPT応答 (試行 {attempt + 1}): {result}")
            if not result:
                print("ChatGPTからの応答が空です。再試行します。")
                continue
            
            # ChatGPTの応答から```json```マークダウンブロックを除去
            if result.startswith('```json'):
                result = result[7:]  # ```jsonを除去
            if result.endswith('```'):
                result = result[:-3]  # ```を除去
            result = result.strip()
            
            # 安全なJSON解析
            from src.security.json_validator import safe_json_parse
            try:
                parsed_result = safe_json_parse(result, schema='medicine_recommendation')
                
                # 推奨医薬品が3つあるかチェック＋重複除去
                if (parsed_result.get('recommended_medicines')):
                    # 製品名・メーカー名の重複を除去
                    seen = set()
                    unique_meds = []
                    for med in parsed_result['recommended_medicines']:
                        key = (med.get('product_name', ''), med.get('manufacturer', ''))
                        if key not in seen:
                            seen.add(key)
                            unique_meds.append(med)
                        if len(unique_meds) == 3:
                            break
                    parsed_result['recommended_medicines'] = unique_meds
                    if len(unique_meds) >= 3:
                        print(f"適切な推奨医薬品が見つかりました（重複除去済み）")
                        return parsed_result
                    else:
                        print(f"推奨医薬品が不足しています（重複除去後）。再試行します。")
                else:
                    print(f"推奨医薬品が不足しています。再試行します。")
            except Exception as e:
                print(f"JSON解析エラー: {e}。再試行します。")
                
        except Exception as e:
            print(f"ChatGPT API呼び出しエラー: {e}")
    
    print("最大試行回数に達しました。デフォルトの推奨を返します。")
    return {
        "recommended_medicines": [],
        "usage_notes": "適切な医薬品が見つかりませんでした。医師にご相談ください。",
        "doctor_consultation": "症状が改善しない場合は医師にご相談ください。"
    }

def get_medicine_details(recommended_medicines, medicine_list):
    """
    推奨医薬品の詳細情報（使用上の注意など）を取得
    """
    detailed_medicines = []
    
    for rec in recommended_medicines:
        product_name = rec.get('product_name', '')
        manufacturer = rec.get('manufacturer', '')
        
        # NaN値を適切に処理
        if product_name is None or str(product_name) == 'nan':
            product_name = ''
        if manufacturer is None or str(manufacturer) == 'nan':
            manufacturer = ''

        # まず完全一致で検索
        matched_medicine = None
        for medicine in medicine_list:
            csv_product = medicine.get('製品名', '')
            csv_manufacturer = medicine.get('メーカー名', '')
            
            # NaN値を適切に処理
            if csv_product is None or str(csv_product) == 'nan':
                csv_product = ''
            if csv_manufacturer is None or str(csv_manufacturer) == 'nan':
                csv_manufacturer = ''
            
            if product_name == csv_product and manufacturer == csv_manufacturer:
                matched_medicine = medicine
                break
        # 完全一致が見つからない場合は製品名のみで検索
        if not matched_medicine:
            for medicine in medicine_list:
                csv_product = medicine.get('製品名', '')
                
                # NaN値を適切に処理
                if csv_product is None or str(csv_product) == 'nan':
                    csv_product = ''
                
                if product_name == csv_product:
                    matched_medicine = medicine
                    break
        
        if matched_medicine:
            # usage_notesはChatGPT返答を優先、なければDB内容
            usage_notes = rec.get('usage_notes')
            if not usage_notes:
                usage_notes = matched_medicine.get('使用上の注意', '')
            # NaN値を適切に処理して医薬品詳細情報を構築
            def safe_get(value):
                if value is None or str(value) == 'nan':
                    return ''
                return value
            
            # スコアリング計算（管理者画面用）
            def calculate_medicine_score(medicine_data, rec_data, notes):
                score = 0
                max_score = 100
                
                # 基本スコア（順位による）
                rank_score = max(0, 30 - (rec_data.get('number', 1) - 1) * 5)
                score += rank_score
                
                # 効能効果の充実度
                efficacy = safe_get(medicine_data.get('効能効果', ''))
                if efficacy and len(efficacy) > 50:
                    score += 20
                elif efficacy and len(efficacy) > 20:
                    score += 10
                
                # 成分情報の充実度
                ingredients = safe_get(medicine_data.get('成分', ''))
                if ingredients and len(ingredients) > 30:
                    score += 15
                elif ingredients and len(ingredients) > 10:
                    score += 8
                
                # 使用上の注意の充実度
                usage_notes_safe = safe_get(notes)
                if usage_notes_safe and len(usage_notes_safe) > 50:
                    score += 15
                elif usage_notes_safe and len(usage_notes_safe) > 20:
                    score += 8
                
                # ドーピング情報の有無
                doping = safe_get(medicine_data.get('禁止物質あり', ''))
                if doping and doping != '':
                    score += 10
                
                # 推奨理由の充実度
                reason = safe_get(rec_data.get('reason', ''))
                if reason and len(reason) > 30:
                    score += 10
                elif reason and len(reason) > 10:
                    score += 5
                
                return min(score, max_score)
            
            medicine_score = calculate_medicine_score(matched_medicine, rec, usage_notes)
            
            detailed_medicine = {
                'number': rec.get('number', 0),
                'product_name': safe_get(matched_medicine.get('製品名', product_name)),
                'manufacturer': safe_get(matched_medicine.get('メーカー名', manufacturer)),
                'reason': safe_get(rec.get('reason', '')),
                'efficacy': safe_get(matched_medicine.get('効能効果', '')),
                'ingredients': safe_get(matched_medicine.get('成分', '')),
                'usage_notes': safe_get(usage_notes),
                'doping_prohibited': safe_get(matched_medicine.get('禁止物質あり', '')),
                'competition_category': safe_get(matched_medicine.get('競技会区分', '')),
                'doping_conditions': safe_get(matched_medicine.get('条件', '')),
                # 管理画面表示に合わせて 0-1 の範囲に正規化
                'score': (medicine_score / 100.0)  # スコアリング情報を追加（正規化）
            }
            detailed_medicines.append(detailed_medicine)
            print(f"医薬品詳細情報取得: {product_name} ({manufacturer}) -> {matched_medicine.get('製品名', '')} ({matched_medicine.get('メーカー名', '')})")
        else:
            print(f"医薬品詳細情報が見つかりません: {product_name} ({manufacturer})")
            # 詳細情報が見つからない場合でも、ChatGPTのusage_notesを優先
            usage_notes = rec.get('usage_notes')
            if not usage_notes:
                usage_notes = '詳細情報が見つかりませんでした'
            # NaN値を適切に処理して医薬品詳細情報を構築
            def safe_get(value):
                if value is None or str(value) == 'nan':
                    return ''
                return value
            
            # 詳細情報が見つからない場合のスコアリング
            def calculate_fallback_score(rec_data):
                score = 0
                # 基本スコア（順位による）
                rank_score = max(0, 30 - (rec_data.get('number', 1) - 1) * 5)
                score += rank_score
                
                # 推奨理由の充実度
                reason = safe_get(rec_data.get('reason', ''))
                if reason and len(reason) > 30:
                    score += 20
                elif reason and len(reason) > 10:
                    score += 10
                
                return min(score, 50)  # 詳細情報がない場合は最大50点
            
            fallback_score = calculate_fallback_score(rec)
            
            detailed_medicine = {
                'number': rec.get('number', 0),
                'product_name': safe_get(product_name),
                'manufacturer': safe_get(manufacturer),
                'reason': safe_get(rec.get('reason', '')),
                'efficacy': '詳細情報が見つかりませんでした',
                'ingredients': '詳細情報が見つかりませんでした',
                'usage_notes': safe_get(usage_notes),
                'doping_prohibited': '詳細情報が見つかりませんでした',
                'competition_category': '詳細情報が見つかりませんでした',
                'doping_conditions': '詳細情報が見つかりませんでした',
                # 管理画面表示に合わせて 0-1 の範囲に正規化
                'score': (fallback_score / 100.0)  # スコアリング情報を追加（正規化）
            }
            detailed_medicines.append(detailed_medicine)
    
    return detailed_medicines

def comprehensive_medicine_recommendation(user_text, user_info=None, client=None):
    """
    包括的な医薬品推奨システムのメイン関数
    """
    print(f"=== 包括的医薬品推奨システム開始 ===")
    print(f"症状文: {user_text}")
    
    # ステップ1: 症状と医薬品の種類を分析
    analysis_result = analyze_symptoms_and_medicine_type(user_text, client)
    symptoms = analysis_result.get('symptoms', [])
    medicine_type = analysis_result.get('medicine_type', 'その他')
    
    print(f"分析結果 - 症状: {symptoms}")
    print(f"分析結果 - 医薬品の種類: {medicine_type}")
    
    # ステップ2: 医薬品の種類に基づいて医薬品リストを取得
    medicine_list = get_medicines_by_type(medicine_type)
    
    if not medicine_list:
        print("該当する医薬品が見つかりませんでした")
        return {
            'symptoms': symptoms,
            'medicine_type': medicine_type,
            'recommended_medicines': [],
            'usage_notes': '該当する医薬品が見つかりませんでした。医師にご相談ください。',
            'doctor_consultation': '症状が改善しない場合は医師にご相談ください。'
        }
    
    # ステップ3: ChatGPTに推奨医薬品を選択させる
    recommendation_result = recommend_medicines_with_retry(
        user_text, symptoms, medicine_list, user_info=user_info, client=client
    )
    
    # ステップ4: 推奨医薬品の詳細情報を取得
    detailed_medicines = get_medicine_details(
        recommendation_result.get('recommended_medicines', []), 
        medicine_list
    )
    
    # スコア順にソート（降順：スコアが高い順）
    detailed_medicines.sort(key=lambda x: x.get('score', 0), reverse=True)
    
    # ソート後の順位を更新
    for i, medicine in enumerate(detailed_medicines, 1):
        medicine['number'] = i
    
    # 最終結果を構築
    final_result = {
        'symptoms': symptoms,
        'medicine_type': medicine_type,
        'recommended_medicines': detailed_medicines,
        'usage_notes': recommendation_result.get('usage_notes', ''),
        'doctor_consultation': recommendation_result.get('doctor_consultation', '')
    }
    
    print(f"=== 推奨結果 ===")
    print(f"症状: {symptoms}")
    print(f"医薬品の種類: {medicine_type}")
    print(f"推奨医薬品数: {len(detailed_medicines)}")
    
    return final_result 

# ================================================================================
# ルールベース推奨システム（新規追加）
# ================================================================================

def rule_based_medicine_recommendation(user_text, user_info, client=None, session_id=None):
    """
    ルールベース医薬品推奨システムのラッパー関数
    風邪薬、解熱鎮痛薬、鼻炎用薬に限定
    
    Args:
        user_text: ユーザーの症状入力
        user_info: ユーザー情報（年齢、妊娠など）
        client: OpenAIクライアント
        session_id: セッションID（オプション、ログ用）
    
    Returns:
        推奨結果
    """
    if client is None:
        client = OpenAI(api_key=api_key)
    
    # ルールベース推奨モジュールをインポート
    try:
        # モジュールをインポート（関数内でインポートすることで循環インポートを回避）
        import src.core.rule_based_recommendation as rbr_module
        
        # 関数が存在するか確認
        if not hasattr(rbr_module, 'rule_based_recommendation'):
            raise AttributeError(f"rule_based_recommendation関数が見つかりません。利用可能な属性: {[attr for attr in dir(rbr_module) if not attr.startswith('_')][:20]}")
        
        if not hasattr(rbr_module, 'log_recommendation_session'):
            raise AttributeError(f"log_recommendation_session関数が見つかりません。")
        
        # 関数を取得
        rule_based_recommendation = rbr_module.rule_based_recommendation
        log_recommendation_session = rbr_module.log_recommendation_session
        
        # グローバルdfを使用
        global df
        if df is None:
            return {
                "status": "error",
                "reason": "医薬品データが読み込まれていません"
            }
        
        # ルールベース推奨を実行
        result = rule_based_recommendation(
            user_text=user_text,
            user_info=user_info,
            medicine_df=df,
            client=client,
            top_n=3,
            session_id=session_id
        )
        
        # ログ保存はapp.pyでbot_contentが生成された後に実行されるため、ここではスキップ
        # （app.pyから完全なapp_outputを渡してログを記録する）
        
        return result
        
    except ImportError as e:
        logger.error(f"ルールベース推奨モジュールのインポートエラー: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            "status": "error",
            "reason": f"システムエラー(モジュールインポートエラー: {str(e)})",
            "error_type": "import_error"
        }
    except AttributeError as e:
        logger.error(f"ルールベース推奨関数の属性エラー: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            "status": "error",
            "reason": f"システムエラー(関数が見つかりません: {str(e)})",
            "error_type": "attribute_error"
        }
    except Exception as e:
        logger.error(f"ルールベース推奨エラー: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            "status": "error",
            "reason": f"システムエラー({str(e)})",
            "error_type": "unknown_error"
        }

def detect_medicine_name_in_query(user_message, medicine_df):
    """
    ユーザーの質問から医薬品名を検出する
    
    Args:
        user_message: ユーザーの質問
        medicine_df: 医薬品データフレーム
    
    Returns:
        list: 検出された医薬品のリスト
    """
    if medicine_df is None or medicine_df.empty:
        return []
    
    detected_medicines = []
    user_message_lower = user_message.lower()
    
    # 成分名での検索を優先（ビタミンC、イブプロフェンなど）
    for _, row in medicine_df.iterrows():
        ingredients = str(row.get('成分', '')).lower()
        if ingredients:
            ingredient_list = [ing.strip() for ing in ingredients.split(',')]
            for ingredient in ingredient_list:
                if ingredient and ingredient in user_message_lower:
                    detected_medicines.append({
                        'product_name': row.get('製品名', ''),
                        'manufacturer': row.get('メーカー名', ''),
                        'efficacy': row.get('効能効果', ''),
                        'usage': row.get('用法用量', ''),
                        'age_restriction': row.get('年齢制限', ''),
                        'ingredients': row.get('成分', ''),
                        'doping_prohibited': row.get('禁止物質あり', ''),
                        'medicine_type': row.get('医薬品の種類', '')
                    })
                    break  # 重複を避ける
    
    # 効能効果での検索を追加（「風邪薬」「頭痛薬」など）
    efficacy_keywords = {'風邪': '風邪', 'ビタミン': 'ビタミン', '頭痛': '頭痛', '胃痛': '胃', '胃薬': '胃', 'かぜ': '風邪'}
    for keyword, search_term in efficacy_keywords.items():
        if keyword in user_message_lower:
            matched = medicine_df[medicine_df['効能効果'].str.contains(search_term, na=False)]
            for _, row in matched.head(5).iterrows():  # 最大5件
                detected_medicines.append({
                    'product_name': row.get('製品名', ''),
                    'manufacturer': row.get('メーカー名', ''),
                    'efficacy': row.get('効能効果', ''),
                    'usage': row.get('用法用量', ''),
                    'age_restriction': row.get('年齢制限', ''),
                    'ingredients': row.get('成分', ''),
                    'doping_prohibited': row.get('禁止物質あり', ''),
                    'medicine_type': row.get('医薬品の種類', '')
                })
    
    # 医薬品名で検索（部分一致）
    for _, row in medicine_df.iterrows():
        product_name = str(row.get('製品名', '')).lower()
        if product_name and any(word in product_name for word in user_message_lower.split() if len(word) > 2):
            detected_medicines.append({
                'product_name': row.get('製品名', ''),
                'manufacturer': row.get('メーカー名', ''),
                'efficacy': row.get('効能効果', ''),
                'usage': row.get('用法用量', ''),
                'age_restriction': row.get('年齢制限', ''),
                'ingredients': row.get('成分', ''),
                'doping_prohibited': row.get('禁止物質あり', ''),
                'medicine_type': row.get('医薬品の種類', '')
            })
    
    # 重複を除去
    unique_medicines = []
    seen_names = set()
    for med in detected_medicines:
        if med['product_name'] not in seen_names:
            unique_medicines.append(med)
            seen_names.add(med['product_name'])
    
    return unique_medicines[:10]  # 最大10件に制限

def chat_with_medicine_context(user_message, conversation_history, recommended_medicines, client=None):
    """
    会話履歴と推奨医薬品の情報をChatGPTに渡して、医薬品に関する質問に回答する
    
    Args:
        user_message: ユーザーの質問
        conversation_history: 会話履歴（最新の5件程度）
        recommended_medicines: 推奨医薬品のリスト
        client: OpenAIクライアント
    
    Returns:
        dict: ChatGPTの回答
    """
    if client is None:
        client = OpenAI(api_key=api_key)
    
    # システム紹介質問を検出
    system_intro_keywords = ['あなたについて', 'あなたは', 'システムについて', 'どんなシステム', '何ができる', '機能','自己紹介','自己紹介して','自己紹介してください']
    is_system_intro = any(keyword in user_message for keyword in system_intro_keywords)
    
    if is_system_intro and not recommended_medicines:
        # HTMLではなく、テキストで簡潔に回答を返す（他システムへの影響を避ける）
        answer_text = (
            "🏥 医薬品推奨システムについて\n"
            "このシステムは、症状に基づいて適切な市販薬（OTC医薬品）を提示するサポートを行います。\n\n"
            "📋 主な機能\n"
            "・症状に基づく医薬品の推奨\n"
            "・効能や用法用量などの基本情報の提示\n"
            "・相互作用や副作用に関する注意喚起\n"
            "・競技者向けのドーピング観点の補足\n\n"
            "🔍 できること\n"
            "・「頭痛がする」「のどが痛い」などの症状で検索\n"
            "・医薬品名での検索や質問\n"
            "・推奨結果についての追加質問\n\n"
            "⚠️ ご注意\n"
            "本システムは参考情報の提供を目的としており、最終判断は登録販売者・薬剤師などの専門家にご相談ください。"
        )
        return {
            "answer": answer_text,
            "medicine_details": "",
            "interactions": "",
            "doping_check": "",
            "side_effects": "",
            "consultation_advice": ""
        }
    
    # 推奨医薬品が空の場合でも、まず会話履歴から復元を試みる
    if not recommended_medicines and conversation_history:
        try:
            for hist in reversed(conversation_history):
                diag = hist.get('diagnosis') if isinstance(hist, dict) else None
                if isinstance(diag, dict) and diag.get('recommended_medicines'):
                    recommended_medicines = diag.get('recommended_medicines') or []
                    if recommended_medicines:
                        print(f"会話履歴から推奨医薬品を復元: {len(recommended_medicines)}件")
                        break
        except Exception as e:
            print(f"履歴復元エラー: {e}")

    # それでも推奨医薬品がない場合、医薬品名での直接検索を試行（成功時のみ早期return）
    if not recommended_medicines:
        try:
            import pandas as pd
            df = pd.read_csv(CSV_PATH)
            detected_medicines = detect_medicine_name_in_query(user_message, df)
            if detected_medicines:
                medicine_info = ""
                for i, med in enumerate(detected_medicines[:3], 1):
                    medicine_info += f"\n💊 **{i}つ目: {med['product_name']}** ({med['manufacturer']})\n"
                    medicine_info += f"**効能効果:** {med['efficacy']}\n"
                    medicine_info += f"**成分:** {med['ingredients']}\n"
                    if med['age_restriction']:
                        medicine_info += f"**年齢制限:** {med['age_restriction']}\n"
                    if med['usage']:
                        medicine_info += f"**用法用量:** {med['usage']}\n"
                    medicine_info += "\n"
                return {
                    "answer": f"🔍 **医薬品検索結果**\n\n{medicine_info}\n⚠️ **ご注意**\n・医薬品の使用前には必ず登録販売者や薬剤師にご相談ください\n・アレルギー体質の方は成分を確認してください\n・用法用量を守ってご使用ください",
                    "medicine_details": "検出された医薬品の情報",
                    "interactions": "医薬品の相互作用については登録販売者にご相談ください",
                    "doping_check": "ドーピング検査については各競技団体にご確認ください",
                    "side_effects": "副作用については登録販売者にご相談ください",
                    "consultation_advice": "お近くの登録販売者にご相談ください"
                }
        except Exception as e:
            print(f"医薬品検索エラー: {e}")
        # 検索でも見つからない場合は、会話履歴を踏まえた一般回答にフォールバック（以降の処理で生成）
    
    # 会話履歴を整形（最新の5件程度）
    history_text = ""
    if conversation_history is not None:
        recent_messages = conversation_history[-5:]  # 最新5件
        for msg in recent_messages:
            if msg.get('type') == 'user':
                history_text += f"ユーザー: {msg.get('content', '')}\n"
            elif msg.get('type') == 'bot':
                # botメッセージから診断結果を抽出
                diagnosis = msg.get('diagnosis')
                if diagnosis is not None and diagnosis.get('recommended_medicines'):
                    medicines = diagnosis.get('recommended_medicines', [])
                    history_text += f"AI: 推奨医薬品: {', '.join([m.get('product_name', '') for m in medicines])}\n"
                else:
                    history_text += f"AI: {msg.get('content', '')}\n"
    
    # 推奨医薬品の詳細情報を整形
    medicines_text = ""
    if recommended_medicines:
        for i, medicine in enumerate(recommended_medicines, 1):
            medicines_text += f"""
{i}つ目: {medicine.get('product_name', '')}
- メーカー: {medicine.get('manufacturer', '')}
- 効能効果: {medicine.get('efficacy', '')}
- 成分: {medicine.get('ingredients', '')}
- 使用上の注意: {medicine.get('usage_notes', '')}
- ドーピング禁止物質: {medicine.get('doping_prohibited', '')}
- 競技会区分: {medicine.get('competition_category', '')}
- ドーピング条件: {medicine.get('doping_conditions', '')}
"""
    
    prompt = f"""
あなたは医薬品推奨システムです。ユーザーの医薬品に関する質問に、推奨医薬品の情報を基に回答してください。

【会話履歴】
{history_text}

【推奨医薬品の詳細情報】
{medicines_text}

【ユーザーの質問】
{user_message}

以下の点について回答してください：
1. 医薬品の詳細説明（効能効果、成分、使用方法）
2. 他の医薬品との飲み合わせ（相互作用）
3. スポーツ競技でのドーピング規制対象かどうか
4. 副作用や注意点
5. 医師に相談すべき場合

回答は以下の形式で構造化してください：
{{
    "answer": "ユーザーへの直接的な回答",
    "medicine_details": "医薬品の詳細説明",
    "interactions": "飲み合わせ・相互作用の説明",
    "doping_check": "ドーピング規制の確認結果",
    "side_effects": "副作用・注意点",
    "consultation_advice": "医師相談のアドバイス"
}}

注意：
- 推奨医薬品の情報を基に具体的に回答してください
- 飲み合わせについては、一般的な相互作用を説明してください
- ドーピングについては、WADA（世界アンチ・ドーピング機関）の規制を参考にしてください
- 安全性を最優先に考え、不明な点がある場合は医師相談を推奨してください
- 質問の内容が推奨医薬品の情報では回答できない場合は、「お近くの登録販売者にご相談ください」と回答してください
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "あなたは医薬品推奨システムです。医薬品の安全性と効果について正確な情報を提供してください。推奨医薬品の情報で回答できない質問については、お近くの登録販売者にご相談するよう推奨してください。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=1000
        )
        
        result = response.choices[0].message.content
        print(f"ChatGPT応答: {result}")
        
        # JSON形式の回答を解析
        import json
        try:
            # JSON部分を抽出
            json_start = result.find('{') if result else -1
            json_end = result.rfind('}') + 1 if result else -1
            if json_start != -1 and json_end != -1:
                json_str = result[json_start:json_end]
                parsed_result = json.loads(json_str)
                
                # 回答が不十分な場合や「分からない」系の回答の場合は登録販売者相談を推奨
                answer = parsed_result.get('answer', '')
                if any(keyword in answer.lower() for keyword in ['分からない', '不明', '確認できません', '情報がありません', '回答できません']):
                    return {
                        "answer": "申し訳ございません。この質問については推奨医薬品の情報では回答できません。お近くの登録販売者にご相談ください。",
                        "medicine_details": "推奨医薬品の情報では回答できません",
                        "interactions": "推奨医薬品の情報では回答できません",
                        "doping_check": "推奨医薬品の情報では回答できません",
                        "side_effects": "推奨医薬品の情報では回答できません",
                        "consultation_advice": "お近くの登録販売者にご相談ください"
                    }
                
                return parsed_result
            else:
                # JSON形式でない場合は直接回答として返す
                return {
                    "answer": result,
                    "medicine_details": "詳細情報を取得できませんでした",
                    "interactions": "飲み合わせ情報を取得できませんでした",
                    "doping_check": "ドーピング規制の確認ができませんでした",
                    "side_effects": "副作用情報を取得できませんでした",
                    "consultation_advice": "お近くの登録販売者にご相談ください"
                }
        except json.JSONDecodeError as e:
            print(f"JSON解析エラー: {e}")
            return {
                "answer": result,
                "medicine_details": "詳細情報を取得できませんでした",
                "interactions": "飲み合わせ情報を取得できませんでした",
                "doping_check": "ドーピング規制の確認ができませんでした",
                "side_effects": "副作用情報を取得できませんでした",
                "consultation_advice": "お近くの登録販売者にご相談ください"
            }
        
    except Exception as e:
        print(f"ChatGPT API呼び出しエラー: {e}")
        return {
            "answer": "申し訳ございません。システムエラーが発生しました。お近くの登録販売者にご相談ください。",
            "medicine_details": "詳細情報を取得できませんでした",
            "interactions": "飲み合わせ情報を取得できませんでした",
            "doping_check": "ドーピング規制の確認ができませんでした",
            "side_effects": "副作用情報を取得できませんでした",
            "consultation_advice": "お近くの登録販売者にご相談ください"
        }


