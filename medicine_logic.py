import pandas as pd
from openai import OpenAI
import os
import re
import time
from debug_logger import add_network_log, performance_stats
from datetime import datetime
# from typing import List
# from openai.types.chat import ChatCompletionMessageParam ←不要なので削除

# このファイルのあるディレクトリを基準にCSVファイルの絶対パスを取得
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "otc_medicine_data.csv")

print('CSVファイル絶対パス:', CSV_PATH)
print('ファイル存在:', os.path.exists(CSV_PATH))

def detect_language(text):
    """
    テキストから言語を自動検出
    
    Args:
        text (str): 検出対象のテキスト
    
    Returns:
        str: 検出された言語コード ('ja', 'en', 'ko', 'zh')
    """
    if not text or not isinstance(text, str):
        return 'ja'  # デフォルトは日本語
    
    # 日本語の文字が含まれているかチェック（ひらがな、カタカナ、漢字）
    if re.search(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]', text):
        return 'ja'
    
    # 韓国語の文字が含まれているかチェック（ハングル）
    if re.search(r'[\uAC00-\uD7AF]', text):
        return 'ko'
    
    # 中国語の文字が含まれているかチェック（簡体字・繁体字）
    if re.search(r'[\u4E00-\u9FFF]', text):
        return 'zh'
    
    # デフォルトは英語
    return 'en'

def create_multilingual_attribute_extraction_prompt(user_text, language, user_info=None):
    """
    言語に応じたユーザー属性抽出プロンプトを作成
    
    Args:
        user_text (str): ユーザーの入力テキスト
        language (str): 検出された言語コード
        user_info (dict): 既存のユーザー情報
    
    Returns:
        str: プロンプトテキスト
    """
    prompts = {
        'ja': f"""
あなたは医薬品推奨システムです。ユーザーのメッセージから以下の属性情報を抽出してください。

【ユーザーのメッセージ】
{user_text}

【既存のユーザー情報】
{user_info if user_info else 'なし'}

【抽出すべき属性】
- age: 年齢（数値）
- gender: 性別（男性/女性）
- pregnant: 妊娠中かどうか（true/false）
- breastfeeding: 授乳中かどうか（true/false）
- allergies: アレルギー（リスト）
- current_medications: 服用中の薬（リスト）
- medical_history: 既往症（リスト）
- symptom_duration_days: 症状の期間（日数）
- other_info: その他の情報（文字列）

【回答形式】
以下のJSON形式で回答してください：
{{
    "age": 30,
    "gender": "男性",
    "pregnant": false,
    "breastfeeding": false,
    "allergies": ["なし"],
    "current_medications": [],
    "medical_history": [],
    "symptom_duration_days": 3,
    "other_info": "その他の情報があれば"
}}

情報が不明な場合は null を返してください。
""",
        
        'en': f"""
You are a medicine recommendation system. Extract the following attribute information from the user's message.

【User's Message】
{user_text}

【Existing User Information】
{user_info if user_info else 'None'}

【Attributes to Extract】
- age: Age (number)
- gender: Gender (Male/Female)
- pregnant: Whether pregnant (true/false)
- breastfeeding: Whether breastfeeding (true/false)
- allergies: Allergies (list)
- current_medications: Current medications (list)
- medical_history: Medical history (list)
- symptom_duration_days: Duration of symptoms (days)
- other_info: Other information (string)

【Response Format】
Please respond in the following JSON format:
{{
    "age": 30,
    "gender": "Male",
    "pregnant": false,
    "breastfeeding": false,
    "allergies": ["None"],
    "current_medications": [],
    "medical_history": [],
    "symptom_duration_days": 3,
    "other_info": "Other information if any"
}}

Return null for unknown information.
""",
        
        'ko': f"""
당신은 의약품 추천 시스템입니다. 사용자의 메시지에서 다음 속성 정보를 추출해주세요.

【사용자의 메시지】
{user_text}

【기존 사용자 정보】
{user_info if user_info else '없음'}

【추출해야 할 속성】
- age: 나이 (숫자)
- gender: 성별 (남성/여성)
- pregnant: 임신 여부 (true/false)
- breastfeeding: 수유 여부 (true/false)
- allergies: 알레르기 (목록)
- current_medications: 복용 중인 약 (목록)
- medical_history: 병력 (목록)
- symptom_duration_days: 증상 지속 기간 (일수)
- other_info: 기타 정보 (문자열)

【응답 형식】
다음 JSON 형식으로 응답해주세요:
{{
    "age": 30,
    "gender": "남성",
    "pregnant": false,
    "breastfeeding": false,
    "allergies": ["없음"],
    "current_medications": [],
    "medical_history": [],
    "symptom_duration_days": 3,
    "other_info": "기타 정보가 있다면"
}}

정보를 모르는 경우 null을 반환하세요.
""",
        
        'zh': f"""
您是药品推荐系统。请从用户消息中提取以下属性信息。

【用户消息】
{user_text}

【现有用户信息】
{user_info if user_info else '无'}

【要提取的属性】
- age: 年龄（数字）
- gender: 性别（男性/女性）
- pregnant: 是否怀孕（true/false）
- breastfeeding: 是否哺乳（true/false）
- allergies: 过敏（列表）
- current_medications: 正在服用的药物（列表）
- medical_history: 病史（列表）
- symptom_duration_days: 症状持续时间（天数）
- other_info: 其他信息（字符串）

【回答格式】
请以以下JSON格式回答：
{{
    "age": 30,
    "gender": "男性",
    "pregnant": false,
    "breastfeeding": false,
    "allergies": ["无"],
    "current_medications": [],
    "medical_history": [],
    "symptom_duration_days": 3,
    "other_info": "如有其他信息"
}}

未知信息请返回null。
"""
    }
    
    return prompts.get(language, prompts['ja'])

def extract_user_attributes_multilingual(user_text, client=None, user_info=None):
    """
    多言語対応のユーザー属性抽出
    
    Args:
        user_text (str): ユーザーの入力テキスト
        client: OpenAIクライアント
        user_info (dict): 既存のユーザー情報
    
    Returns:
        dict: 抽出された属性情報
    """
    if client is None:
        from openai import OpenAI
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            return {}
        client = OpenAI(api_key=api_key)
    
    # 言語を自動検出
    detected_language = detect_language(user_text)
    print(f"検出された言語: {detected_language}")
    
    # 言語に応じたプロンプトを作成
    prompt = create_multilingual_attribute_extraction_prompt(user_text, detected_language, user_info)
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a medical AI assistant that extracts user attributes from text."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=1000
        )
        
        result = response.choices[0].message.content
        print(f"ChatGPT属性抽出応答 ({detected_language}): {result}")
        
        # JSON形式の回答を解析
        import json
        try:
            json_start = result.find('{') if result else -1
            json_end = result.rfind('}') + 1 if result else -1
            if json_start != -1 and json_end != -1:
                json_str = result[json_start:json_end]
                parsed_result = json.loads(json_str)
                
                # 言語情報を追加
                parsed_result['detected_language'] = detected_language
                
                return parsed_result
            else:
                return {"detected_language": detected_language}
        except json.JSONDecodeError as e:
            print(f"JSON解析エラー: {e}")
            return {"detected_language": detected_language}
            
    except Exception as e:
        print(f"ChatGPT API呼び出しエラー: {e}")
        return {"detected_language": detected_language}

def translate_medicine_recommendation(text, target_language, client=None):
    """
    AI応答（医薬品推奨）を翻訳
    
    Args:
        text (str): 翻訳対象のテキスト
        target_language (str): 翻訳先言語コード
        client: OpenAIクライアント
    
    Returns:
        str: 翻訳されたテキスト
    """
    if not text or target_language == 'ja':
        return text  # 日本語の場合は翻訳不要
    
    if client is None:
        from openai import OpenAI
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            return text
        client = OpenAI(api_key=api_key)
    
    # 言語名のマッピング
    language_names = {
        'en': 'English',
        'ko': 'Korean',
        'zh': 'Chinese'
    }
    
    target_lang_name = language_names.get(target_language, 'English')
    
    try:
        prompt = f"""
以下の医薬品推奨情報を{target_lang_name}に翻訳してください。
医療専門用語は正確に翻訳し、医薬品名は適切に翻訳してください。

翻訳対象テキスト:
{text}

翻訳:
"""
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a medical translator specializing in medicine recommendations. Translate accurately while maintaining medical terminology."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=2000
        )
        
        translated_text = response.choices[0].message.content.strip()
        print(f"翻訳完了 ({target_language}): {translated_text[:100]}...")
        return translated_text
        
    except Exception as e:
        print(f"翻訳エラー: {e}")
        return text  # 翻訳に失敗した場合は元のテキストを返す

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

def generate_usage_notes(medicine_name: str, medicine_info: dict, user_info: dict = None) -> str:
    """
    ChatGPTを使用して医薬品の使用上の注意を自動生成（キャッシュ機能付き）
    
    Args:
        medicine_name: 医薬品名
        medicine_info: 医薬品情報（成分、効能、年齢制限など）
        user_info: ユーザー情報（年齢、妊娠状態など）
    
    Returns:
        str: 生成された使用上の注意
    """
    try:
        # キャッシュキーの生成（医薬品名とユーザー情報の組み合わせ）
        cache_key = f"{medicine_name}_{hash(str(user_info))}"
        
        # キャッシュから取得を試行
        if cache_key in _usage_notes_cache:
            print(f"📋 使用上の注意をキャッシュから取得: {medicine_name}")
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
        
        # プロンプトの構築
        prompt = f"""
以下の医薬品について、使用上の注意を生成してください。

医薬品名: {medicine_name}
成分: {medicine_info.get('ingredients', '情報なし')}
効能・効果: {medicine_info.get('efficacy', '情報なし')}
年齢制限: {medicine_info.get('age_restriction', '情報なし')}
用法・用量: {medicine_info.get('usage', '情報なし')}
{doping_info}

ユーザー情報:
{user_context if user_context else '情報なし'}

以下の形式で使用上の注意を生成してください：
1. 基本的な使用上の注意
2. 年齢・性別による注意点（年齢制限の詳細を含む）
3. 妊娠・授乳中の注意点
4. アレルギーに関する注意点
5. 副作用について
6. 他の薬との相互作用
7. 保存方法・保管上の注意
8. ドーピング禁止物質に関する注意（該当する場合）

各項目は簡潔で分かりやすく、実際の使用場面で役立つ内容にしてください。
特に年齢制限とドーピング禁止物質については、具体的で明確な注意事項を含めてください。
"""
        
        # ChatGPT APIを呼び出し
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "あなたは医薬品の専門家です。症状に適した医薬品を推奨し、使用上の注意を説明してください。効能・効果が限定された特殊用途の医薬品（例：「食あたり等」「便秘」など）は、ユーザーの症状がその限定用途と完全に一致する場合のみ推奨してください。一般的な症状に対して特殊用途の医薬品を無理に推奨することは避けてください。"},
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
            print(f"💾 使用上の注意をキャッシュに保存: {medicine_name}")
        
        return usage_notes
        
    except Exception as e:
        print(f"使用上の注意生成エラー: {e}")
        return "使用上の注意の生成に失敗しました。医師または薬剤師にご相談ください。"

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
try:
    from dotenv import load_dotenv
    # スクリプトのディレクトリを基準に.envファイルを読み込む
    env_path = os.path.join(BASE_DIR, '.env')
    load_dotenv(env_path)
    print("dotenvを使用して.envファイルから環境変数を読み込みました。")
    # デバッグ用: .envファイルの存在確認
    if os.path.exists(env_path):
        print(f".envファイルのパス: {env_path}")
    else:
        print(f"警告: .envファイルが見つかりません: {env_path}")
except ImportError:
    print("python-dotenvがインストールされていません。環境変数のみを使用します。")

# --- OpenAI APIキー設定 ---
# 環境変数からAPIキーを取得
api_key = os.getenv('OPENAI_API_KEY')

# デバッグ用: 環境変数の確認（値の一部のみ表示）
if api_key:
    print(f"APIキーが読み込まれました（長さ: {len(api_key)}文字）")
else:
    print("WARNING: OpenAI API keyが環境変数に設定されていません。")
    print("環境変数 OPENAI_API_KEY を設定してください。")

# --- OpenAIクライアント初期化 ---
client = None
if api_key:
    try:
        client = OpenAI(api_key=api_key)
        print("OpenAI client initialized successfully.")
    except Exception as e:
        print(f"Error initializing OpenAI client: {e}")
else:
    print("Error: OpenAI API key not found. Please set it in environment variables or .env file.")

# --- CSVファイルの読み込み ---
df = None
csv_load_status = {
    "success": False,
    "encoding": None,
    "error": None,
    "row_count": 0,
    "col_count": 0,
    "columns": [],
    "path": CSV_PATH
}
encodings = ['utf-8', 'shift_jis', 'cp932', 'euc-jp']

for encoding in encodings:
    try:
        df = pd.read_csv(CSV_PATH, encoding=encoding)
        csv_load_status["success"] = True
        csv_load_status["encoding"] = encoding
        csv_load_status["row_count"] = len(df)
        csv_load_status["col_count"] = len(df.columns)
        csv_load_status["columns"] = list(df.columns)
        print(f"CSVファイルを正常に読み込みました（エンコーディング: {encoding}）。")
        break
    except UnicodeDecodeError:
        print(f"エンコーディング {encoding} で読み込みに失敗しました。")
        continue
    except FileNotFoundError:
        csv_load_status["error"] = "FileNotFoundError"
        print("エラー: otc_medicine_data.csvファイルが見つかりません。")
        break
    except Exception as e:
        csv_load_status["error"] = str(e)
        print(f"CSVファイルの読み込みエラー: {e}")
        break

if not csv_load_status["success"]:
    print("すべてのエンコーディングでCSVファイルの読み込みに失敗しました。")

def get_medicines_by_symptom(symptom_text, df=None):
    if df is None:
        try:
            from medicine_logic import df as global_df
            df = global_df
        except ImportError:
            return ["データが読み込まれていません"]
    if df is None:
        return ["データが読み込まれていません"]
    if '効能効果' not in df.columns:
        return ["CSVに効能効果カラムがありません"]
    # 症状テキストが効能効果に部分一致する行を抽出
    matched = df[df['効能効果'].astype(str).str.contains(symptom_text, na=False)]
    if matched.empty:
        return ["該当する市販薬情報が見つかりませんでした。"]
    # 製品名・メーカー名・分類・効能効果・成分をまとめて返す
    result = []
    for _, row in matched.iterrows():
        info = f"製品名: {row['製品名']} / メーカー: {row['メーカー名']} / 分類: {row['分類']}\n効能効果: {row['効能効果']}\n成分: {row['成分']}"
        result.append(info)
    return result

def gpt_guess_symptom(user_text, symptom_list, client=None):
    """
    ChatGPTで症状リストから最も近い症状名を1～3個推定
    """
    if client is None:
        client = OpenAI(api_key=api_key)
    prompt = (
        "あなたは医薬品推奨システムです。\n"
        "以下は症状リストです。\n"
        "ユーザーの症状文から最も近い症状名を日本語で返してください。(複数選択可)\n\n"
        "【症状リスト】\n" +
        "\n".join(f"{i+1}. {s}" for i, s in enumerate(symptom_list)) +
        f"\nユーザーの症状: {user_text}"
    )
    messages = [
        {"role": "system", "content": prompt}
    ]
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        temperature=0
    )
    content = response.choices[0].message.content if response.choices[0].message.content else ""
    print("ChatGPT返答:\n", content.strip())
    # 改行やカンマ区切りで分割
    symptoms = [s.strip() for s in re.split(r'[\n,、]', content) if s.strip()]
    return symptoms

def find_otc_candidates(symptoms, df_otc, max_candidates=20):
    """
    症状名リストのいずれかが効能効果に含まれる市販薬を抽出
    """
    mask = df_otc['効能効果'].astype(str).apply(lambda x: any(s in x for s in symptoms))
    return df_otc[mask].head(max_candidates)

def gpt_select_best_otc(user_text, candidates, client=None):
    """
    ChatGPTで候補リストから最適な市販薬3つを選ばせる
    """
    if client is None:
        client = OpenAI(api_key=api_key)
    prompt = (
        f"あなたは医薬品推奨システムです。ユーザーの症状「{user_text}」に最も適した市販薬を3つ選び、理由も簡単に説明してください。(市販薬の重複は避けてください)\n\n"
        "【候補リスト】\n" +
        "\n".join(
            f"{i+1}. 製品名: {row['製品名']} / 効能効果: {row['効能効果']} / 成分: {row['成分']}"
            for i, (_, row) in enumerate(candidates.iterrows())
        )
    )
    messages = [
        {"role": "system", "content": prompt}
    ]
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        temperature=0
    )
    content = response.choices[0].message.content if response.choices[0].message.content else ""
    print("ChatGPT返答:\n", content.strip())
    return content.strip()

def recommend_otc_medicines_via_gpt(user_text, symptom_csv_path=None, otc_csv_path=None, max_candidates=20, client=None):
    """
    ユーザー症状文→ChatGPTで症状名推定→候補薬抽出→ChatGPTで最適薬3つ選定
    """
    import pandas as pd
    import os
    # CSV読み込み
    base_dir = os.path.dirname(os.path.abspath(__file__))
    symptom_csv = symptom_csv_path or os.path.join(base_dir, "症状-薬.csv")
    otc_csv = otc_csv_path or os.path.join(base_dir, "otc_medicine_data.csv")
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
    print("ChatGPT返答:\n", result)
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
    base_dir = os.path.dirname(os.path.abspath(__file__))
    summarized_csv = summarized_csv_path or os.path.join(base_dir, "summarized_efficacy_data.csv")
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
    print("ChatGPT返答:\n", content.strip())
    return content.strip() 

def gpt_select_efficacy_candidates(user_text, summarized_csv_path=None, max_candidates=30, client=None):
    """
    ChatGPTにsummarized_efficacy_data.csvの効能効果リストを渡し、
    ユーザー症状に最も近い効能効果（複数可）を選ばせる
    """
    import pandas as pd
    import os
    base_dir = os.path.dirname(os.path.abspath(__file__))
    summarized_csv = summarized_csv_path or os.path.join(base_dir, "summarized_efficacy_data.csv")
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
    print("ChatGPT返答:\n", content.strip())
    # リスト形式で返す
    selected = [line.strip(" ・-0123456789.") for line in content.splitlines() if line.strip()]
    # 元の効能効果リストと突合して正規化
    selected_set = set(selected)
    matched_efficacy = [e for e in efficacy_list if any(s in e or e in s for s in selected_set)]
    return matched_efficacy

def select_symptoms_via_gpt(user_text, symptoms_csv_path=None, client=None, max_symptoms=250):
    """
    ユーザーの症状文からChatGPTを使って適切な症状を抽出する
    """
    import pandas as pd
    import os
    import re
    
    # より包括的な症状リストを作成
    comprehensive_symptom_list = [
        # 風邪・インフルエンザ関連
        "頭痛", "発熱", "咳", "鼻水", "鼻づまり", "のどの痛み", "くしゃみ", "寒気", "悪寒",
        # 消化器系
        "腹痛", "下痢", "便秘", "吐き気", "嘔吐", "胃痛", "胸やけ", "胃もたれ",
        # 神経系・全身症状
        "めまい", "疲労感", "倦怠感", "筋肉痛", "関節痛", "肩こり", "腰痛",
        # 皮膚系
        "かゆみ", "発疹", "湿疹", "蕁麻疹", "皮膚の乾燥",
        # 睡眠・精神系
        "不眠", "眠気", "イライラ", "不安", "ストレス",
        # 女性特有
        "生理痛", "月経不順", "更年期症状",
        # その他
        "口内炎", "目の疲れ", "目のかゆみ", "目の充血", "耳鳴り", "動悸"
    ]
    
    # 症状抽出のプロンプトを改善
    prompt = f"""
あなたは医薬品推奨システムです。ユーザーの症状文から該当する症状を正確に抽出してください。

【ユーザーの症状文】
{user_text}

【抽出すべき症状リスト】
{', '.join(comprehensive_symptom_list)}

【指示】
1. ユーザーの症状文から該当する症状のみを抽出してください
2. 症状文に明示的に書かれていない症状は含めないでください
3. 症状文が曖昧な場合は、最も可能性の高い症状のみを選択してください
4. 「こんにちは」などの挨拶のみの場合は、症状なしとして空のリストを返してください

【回答形式】
該当する症状を以下の形式で出力してください：
症状1, 症状2, 症状3

該当する症状がない場合は「なし」と出力してください。
"""
    
    messages = [
        {"role": "system", "content": "あなたは医薬品推奨システムです。ユーザーの症状文から正確に症状を抽出してください。"},
        {"role": "user", "content": prompt}
    ]
    
    if client is None:
        client = OpenAI(api_key=api_key)
    
    print("ユーザー入力:", user_text)
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.1,
            max_tokens=500
        )
        content = response.choices[0].message.content if response.choices[0].message.content else ""
    except Exception as e:
        print(f"ChatGPT API エラー: {e}")
        return {
            'status': 'error',
            'symptoms': [],
            'message': f'ChatGPT API エラー: {e}'
        }
    print("ChatGPT返答:\n", content.strip())
    
    # 症状抽出の結果を処理
    if "なし" in content or "症状なし" in content or not content.strip():
        return {
            'status': 'success',
            'symptoms': [],
            'message': 'No symptoms detected'
        }
    
    # カンマ区切りで症状を抽出
    symptoms = []
    if "," in content:
        symptoms = [s.strip() for s in content.split(",") if s.strip()]
    else:
        # 改行区切りの場合
        symptoms = [line.strip(" ・-0123456789.") for line in content.splitlines() if line.strip()]
    
    # 症状リストと照合して正規化
    matched_symptoms = []
    for symptom in symptoms:
        # 完全一致を探す
        if symptom in comprehensive_symptom_list:
            matched_symptoms.append(symptom)
        else:
            # 部分一致を探す
            for ref_symptom in comprehensive_symptom_list:
                if symptom in ref_symptom or ref_symptom in symptom:
                    matched_symptoms.append(ref_symptom)
                    break
    
    # 重複を除去
    matched_symptoms = list(set(matched_symptoms))
    
    return {
        'status': 'success',
        'symptoms': matched_symptoms,
        'message': f'Extracted {len(matched_symptoms)} symptoms'
    } 

def analyze_symptoms_and_medicine_type(user_text, client=None):
    """
    症状文と症状リスト、医薬品の種類のデータをChatGPTに渡して
    症状（複数選択可）と適する医薬品の種類を返す
    """
    if client is None:
        client = OpenAI(api_key=api_key)
    
    # 医薬品の種類リスト（CSVファイルの実際の内容に基づく）
    medicine_types = [
        "筋肉痛", "睡眠障害", "精神症状", "その他", "胃腸薬", 
        "解熱鎮痛薬", "外用薬（皮膚）", "抗アレルギー薬", "禁煙補助薬", 
        "鼻炎用薬", "風邪薬", "目薬", "更年期障害"
    ]
    
    # 症状リスト（包括的なリストを使用）
    symptoms_list = [
        "頭痛", "発熱", "咳", "鼻水", "鼻づまり", "のどの痛み", "くしゃみ", "寒気", "悪寒",
        "腹痛", "下痢", "便秘", "吐き気", "嘔吐", "胃痛", "胸やけ", "胃もたれ",
        "めまい", "疲労感", "倦怠感", "筋肉痛", "関節痛", "肩こり", "腰痛",
        "かゆみ", "発疹", "湿疹", "蕁麻疹", "皮膚の乾燥",
        "不眠", "眠気", "イライラ", "不安", "ストレス",
        "生理痛", "月経不順", "更年期症状",
        "口内炎", "目の疲れ", "目のかゆみ", "目の充血", "耳鳴り", "動悸"
    ]
    
    prompt = f"""
あなたは医薬品推奨システムです。ユーザーの症状文を分析して、該当する症状と適する医薬品の種類を選択してください。

【ユーザーの症状文】
{user_text}

【選択可能な症状リスト】
{', '.join(symptoms_list)}

【医薬品の種類】
{', '.join(medicine_types)}

【重要な判断ルール】
- 「目が痒い」「目のかゆみ」「目の痒み」などの目の症状は「目のかゆみ」として抽出し、医薬品の種類は「目薬」を選択してください
- 「目がかゆい」は皮膚のかゆみ（「かゆみ」）ではなく、「目のかゆみ」として分類してください
- 目の症状（目のかゆみ、目の充血、目の疲れ）がある場合は、必ず「目薬」を選択してください（最優先）
- 皮膚のかゆみ（「かゆみ」「かゆい」）は「目のかゆみ」とは区別し、「外用薬（皮膚）」を選択してください
- 鼻症状（鼻水、鼻づまり、くしゃみ）のみで発熱・のどの痛み・咳がない場合は「鼻炎用薬」を選択してください
- 複数症状がある場合は、以下の優先順位で医薬品の種類を選択してください：
  1. 目の症状 → 目薬
  2. 皮膚症状 → 外用薬（皮膚）
  3. 消化器症状 → 胃腸薬
  4. 筋肉痛・関節痛・肩こり・腰痛 → 解熱鎮痛薬 または 筋肉痛
  5. 鼻症状のみ → 鼻炎用薬
  6. その他の風邪症状 → 風邪薬
  7. 頭痛・生理痛 → 解熱鎮痛薬

【指示】
1. 症状文から該当する症状のみを抽出してください
2. 症状文に明示的に書かれていない症状は含めないでください
3. 症状文が曖昧な場合は、最も可能性の高い症状のみを選択してください
4. 「こんにちは」などの挨拶のみの場合は、症状なしとして空のリストを返してください
5. 医薬品の種類は1つ選択してください

【回答形式】
以下のJSON形式で回答してください：
{{
    "symptoms": ["症状1", "症状2"],
    "medicine_type": "適する医薬品の種類"
}}

該当する症状がない場合は：
{{
    "symptoms": [],
    "medicine_type": "その他"
}}
"""

    print(f"=== 症状分析開始 ===")
    print(f"症状文: {user_text}")
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "あなたは医薬品の専門家です。症状に適した医薬品を推奨し、使用上の注意を説明してください。効能・効果が限定された特殊用途の医薬品（例：「食あたり等」「便秘」など）は、ユーザーの症状がその限定用途と完全に一致する場合のみ推奨してください。一般的な症状に対して特殊用途の医薬品を無理に推奨することは避けてください。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=500
        )
        
        result = response.choices[0].message.content
        print(f"ChatGPT応答: {result}")
        if not result:
            print("ChatGPTからの応答が空です")
            return {"symptoms": [], "medicine_type": "その他"}
        # JSON形式の回答を解析
        import json
        try:
            # JSON部分を抽出
            json_start = result.find('{') if result else -1
            json_end = result.rfind('}') + 1 if result else -1
            if json_start != -1 and json_end != -1:
                json_str = result[json_start:json_end]
                parsed_result = json.loads(json_str)
                print(f"解析結果: {parsed_result}")
                return parsed_result
            else:
                print("JSON形式が見つかりませんでした")
                return {"symptoms": [], "medicine_type": "その他"}
        except json.JSONDecodeError as e:
            print(f"JSON解析エラー: {e}")
            return {"symptoms": [], "medicine_type": "その他"}
            
    except Exception as e:
        print(f"ChatGPT API呼び出しエラー: {e}")
        print("フォールバック: 簡易症状検出を使用します")
        return simple_symptom_and_type_detection(user_text)

def simple_symptom_and_type_detection(user_text):
    """
    簡易的な症状と医薬品種類の検出（APIフォールバック用）
    """
    import re
    
    # 症状キーワードマッピング（目の症状を優先的に検出するため、先に定義）
    # rule_based_recommendation.pyのSYMPTOM_DICTIONARYと整合性を保つ
    symptom_keywords = {
        # 目薬関連症状（最優先）
        "目のかゆみ": ["目が痒", "目がかゆ", "目の痒", "目のかゆ", "目痒", "目かゆ", "目のかゆみ"],
        "目の充血": ["目の充血", "目が赤い", "目赤", "充血", "目の血走り"],
        "目の疲れ": ["目の疲れ", "目が疲", "眼精疲労", "目の重い感じ"],
        # 風邪関連症状
        "頭痛": ["頭痛", "頭が痛い", "ズキズキ", "偏頭痛", "頭が重い"],
        "発熱": ["熱", "発熱", "熱っぽい", "高熱", "微熱", "体温が高い"],
        "のどの痛み": ["のどが痛い", "喉が痛い", "のどの痛み", "咽頭痛", "喉痛", "のど痛", "喉の腫れ"],
        "咳": ["咳", "せき", "咳が出る", "咳込む", "空咳"],
        "鼻水": ["鼻水", "鼻みず", "鼻汁", "鼻が出る", "水っぽい鼻水"],
        "鼻づまり": ["鼻づまり", "鼻詰まり", "鼻が詰まる", "鼻閉"],
        "くしゃみ": ["くしゃみ", "クシャミ", "くしゃみが出る"],
        "寒気": ["寒気", "さむけ", "悪寒", "ゾクゾクする", "悪寒がする"],
        "悪寒": ["悪寒", "寒気", "さむけ", "ゾクゾクする", "悪寒がする"],
        # 消化器症状
        "胃痛": ["胃痛", "胃が痛い", "胃の痛み", "胃部痛", "みぞおちの痛み", "胃が痛む"],
        "腹痛": ["腹痛", "お腹が痛い", "腹部痛", "おなかが痛い", "腹が痛い", "腹痛が続く"],
        "下痢": ["下痢", "軟便", "水様便", "便がゆるい", "便が緩い", "下痢が続く"],
        "便秘": ["便秘", "便が出ない", "便通がない", "便が硬い", "便秘が続く"],
        "吐き気": ["吐き気", "嘔吐", "むかつき", "気持ち悪い", "嘔吐感", "吐きそう"],
        "胸やけ": ["胸やけ", "胸焼け", "胃の重い感じ", "酸が上がる", "胸が苦い"],
        "胃もたれ": ["胃もたれ", "もたれる", "消化不良", "胃の重い感じ", "消化が悪い", "胃の不快感"],
        # 皮膚症状
        "かゆみ": ["かゆい", "痒み", "かゆみ", "皮膚のかゆみ", "皮膚が痒い"],
        "発疹": ["発疹", "ブツブツ", "赤い斑点", "皮膚の異常", "皮膚に赤い斑点が出る"],
        "湿疹": ["湿疹", "皮膚炎", "かぶれ", "皮膚の炎症"],
        "蕁麻疹": ["蕁麻疹", "じんましん", "じん麻疹", "蕁麻疹が出る"],
        # 筋肉・関節症状
        "筋肉痛": ["筋肉痛", "筋肉の痛み", "体が痛い", "筋肉が痛い", "筋肉が痛む"],
        "関節痛": ["関節痛", "関節の痛み", "節々が痛い", "関節が痛い", "関節が痛む"],
        "肩こり": ["肩こり", "肩の凝り", "肩の痛み", "首肩の痛み", "肩が凝る"],
        "腰痛": ["腰痛", "腰が痛い", "腰の痛み", "腰が痛む"],
        # その他の症状
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
    
    # 重複を除去
    detected_symptoms = list(set(detected_symptoms))
    
    # 医薬品種類の推定（優先順位に注意）
    medicine_type = "その他"
    
    # 1. 目の症状（最優先）
    eye_symptoms = ["目のかゆみ", "目の充血", "目の疲れ"]
    if any(s in detected_symptoms for s in eye_symptoms):
        medicine_type = "目薬"
    # 2. 皮膚症状 → 外用薬（皮膚）
    elif any(s in detected_symptoms for s in ["かゆみ", "発疹", "湿疹", "蕁麻疹"]):
        medicine_type = "外用薬（皮膚）"
    # 3. 消化器症状 → 胃腸薬
    elif any(s in detected_symptoms for s in ["胃痛", "腹痛", "下痢", "便秘", "吐き気", "胸やけ", "胃もたれ"]):
        medicine_type = "胃腸薬"
    # 4. 筋肉痛・関節痛・肩こり・腰痛 → 解熱鎮痛薬 または 筋肉痛
    elif any(s in detected_symptoms for s in ["筋肉痛", "関節痛", "肩こり", "腰痛"]):
        # 筋肉痛がある場合は「筋肉痛」、それ以外は「解熱鎮痛薬」
        if "筋肉痛" in detected_symptoms:
            medicine_type = "筋肉痛"
        else:
            medicine_type = "解熱鎮痛薬"
    # 5. 鼻炎用薬の判定（鼻症状のみで発熱・喉・咳がない場合）
    elif any(s in detected_symptoms for s in ["鼻水", "鼻づまり", "くしゃみ"]):
        nose_symptoms = ["鼻水", "鼻づまり", "くしゃみ"]
        other_cold_symptoms = ["発熱", "のどの痛み", "咳"]
        # 鼻症状のみで他の風邪症状がない場合は鼻炎用薬
        if not any(s in detected_symptoms for s in other_cold_symptoms):
            medicine_type = "鼻炎用薬"
        # 鼻症状+他の風邪症状がある場合は風邪薬
        else:
            medicine_type = "風邪薬"
    # 6. 風邪薬の判定（鼻症状以外の風邪症状）
    elif any(s in detected_symptoms for s in ["発熱", "のどの痛み", "咳"]):
        medicine_type = "風邪薬"
    # 7. 解熱鎮痛薬の判定（頭痛・生理痛）
    elif any(s in detected_symptoms for s in ["頭痛", "生理痛"]):
        medicine_type = "解熱鎮痛薬"
    
    print(f"=== 簡易検出結果 ===")
    print(f"検出された症状: {detected_symptoms}")
    print(f"推定された医薬品の種類: {medicine_type}")
    
    return {
        "symptoms": detected_symptoms,
        "medicine_type": medicine_type
    }

def get_medicines_by_type(medicine_type, df=None):
    """
    医薬品の種類に基づいてotc_medicine_dataから医薬品リストを取得
    """
    if df is None:
        df = globals().get('df')
    
    if df is None:
        print("データフレームが読み込まれていません")
        return []
    
    # 医薬品の種類カラムから該当する医薬品を抽出
    if '医薬品の種類' in df.columns:
        matched = df[df['医薬品の種類'].astype(str).str.contains(medicine_type, na=False)]
        medicines = []
        for _, row in matched.iterrows():
            medicine_info = {
                '製品名': row.get('製品名', ''),
                'メーカー名': row.get('メーカー名', ''),
                '分類': row.get('分類', ''),
                '医薬品の種類': row.get('医薬品の種類', ''),
                '効能効果': row.get('効能効果', ''),
                '成分': row.get('成分', ''),
                '使用上の注意': row.get('使用上の注意', '')
            }
            medicines.append(medicine_info)
        
        print(f"医薬品の種類 '{medicine_type}' で {len(medicines)} 件の医薬品を抽出しました")
        return medicines
    else:
        print("CSVに医薬品の種類カラムがありません")
        return []

def recommend_medicines_with_retry(user_text, symptoms, medicine_list, client=None, max_retries=3):
    """
    症状と医薬品リストをChatGPTに渡して推奨医薬品を3つ選び、
    使用上の注意を要約して返す。適した医薬品が返ってこなければ再試行
    """
    # セキュリティ検証の追加
    from security_validator import validate_user_input
    from security_config import should_block_input, get_current_phase
    from security_logger import log_input_validation
    
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
    
    for attempt in range(max_retries):
        print(f"=== 医薬品推奨試行 {attempt + 1}/{max_retries} ===")
        
        prompt = f"""
以下の症状と医薬品リストから、最も適切な3つの医薬品を選んでください。

【症状】
{', '.join(symptoms)}

【症状文】
{sanitized_text}

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
            from json_validator import safe_json_parse
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

def comprehensive_medicine_recommendation(user_text, client=None):
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
        user_text, symptoms, medicine_list, client
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

def rule_based_medicine_recommendation(user_text, user_info, client=None):
    """
    ルールベース医薬品推奨システムのラッパー関数
    風邪薬、解熱鎮痛薬、鼻炎用薬に限定
    
    Args:
        user_text: ユーザーの症状入力
        user_info: ユーザー情報（年齢、妊娠など）
        client: OpenAIクライアント
    
    Returns:
        推奨結果
    """
    if client is None:
        client = OpenAI(api_key=api_key)
    
    # ルールベース推奨モジュールをインポート
    try:
        from rule_based_recommendation import rule_based_recommendation, log_recommendation_session
        
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
            top_n=3
        )
        
        # ログ保存
        log_recommendation_session(user_text, user_info, result)
        
        return result
        
    except Exception as e:
        print(f"ルールベース推奨エラー: {e}")
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "reason": f"システムエラー: {str(e)}"
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
    system_intro_keywords = ['あなたについて', 'あなたは', 'システムについて', 'どんなシステム', '何ができる', '機能']
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
            df = pd.read_csv('otc_medicine_data.csv')
            detected_medicines = detect_medicine_name_in_query(user_message, df)
            if detected_medicines:
                medicine_info = ""
                for i, med in enumerate(detected_medicines[:3], 1):
                    medicine_info += f"\n💊 **{i}位: {med['product_name']}** ({med['manufacturer']})\n"
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

def detect_crisis_keywords(user_message):
    """
    自殺・自傷関連の危険ワードを検出する関数
    医薬品相談ツールの特性を考慮した充実したキーワードリスト
    
    Args:
        user_message (str): ユーザーの入力メッセージ
    
    Returns:
        tuple: (検出されたかどうか, 検出されたキーワードのリスト)
    """
    crisis_keywords = [
        # 直接的な表現
        '死にたい', '消えたい', '自殺', '希死念慮', '死にたいです', '消えたいです',
        '生きていても意味がない', '生きる意味がない', '生きていても仕方ない',
        'もうだめ', 'だめだ', '終わり', '終わらせたい', '命を絶ちたい',
        'この世から消えたい', '存在したくない', 'いなくなってしまいたい',
        '自殺願望', '自殺念慮', '死にたい気持ち', '死にたいです',
        
        # 薬物関連の危険表現
        '過量服薬', 'OD', '致死量', '大量服薬', '薬を全部飲む', '薬で死にたい',
        '薬を一気に飲む', '薬を飲みすぎた', '薬で楽になりたい', 'ODしたい',
        '過剰摂取', 'オーバードーズ', '薬を多く飲む', '薬を混ぜる', '薬の致死量', '睡眠薬致死量',
        '薬で眠りたい', 'overdose', '薬を使って消えたい', 'overdoseした',
        '薬で楽になりたい',
        
        # 自傷行為関連
        'リスカ', '自傷', 'リストカット', '手首切った', '血を見たくなる',
        
        # 死に方・方法の表現
        '死に方', '楽な死に方', '眠るように死にたい', '首を吊る', '飛び降り',
        '飛び込み', '死ぬ方法', '消える方法', '死ぬ勇気', '命を捨てたい',
        '死に場所', '死を考えている', '命を終わらせたい', '死ぬ準備',
        '終わりにしたい', '倒れたい', '死ぬしかない',
        
        # 感情・心理状態
        '生きたくない', 'もう終わりたい', '生きるのがつらい', '限界',
        '助けて', '誰にも言えない', '苦しい', 'いなくなりたい',
        '誰も理解してくれない', 'どうでもいい', '生きる意味', '価値がない',
        '自分が嫌い', '存在したくない', '消えてしまいたい', 'もう無理',
        'もういいや', '終わらせたい',
        
        # 英語の危険ワード
        'suicide', 'kill myself', 'want to die', 'end my life', 'overdose'
    ]
    
    # 大文字小文字を区別せずに検索
    user_message_lower = user_message.lower()
    
    detected_keywords = []
    for keyword in crisis_keywords:
        if keyword.lower() in user_message_lower:
            detected_keywords.append(keyword)
    
    return len(detected_keywords) > 0, detected_keywords

def get_crisis_support_resources(language='ja'):
    """
    自殺防止相談先の情報を取得する関数
    
    Args:
        language (str): 言語コード ('ja', 'en', 'ko', 'zh')
    
    Returns:
        dict: 相談先情報とメッセージ
    """
    # 多言語対応のメッセージテンプレート
    messages = {
        'ja': {
            'title': 'あなたの気持ちを大切に思っています',
            'message': '今、とてもつらい状況かもしれません。一人で抱え込まず、信頼できる相談先があります。',
            'emergency': '緊急の場合は、すぐに119番（救急）または110番（警察）に連絡してください。'
        },
        'en': {
            'title': 'Your feelings matter',
            'message': 'Professional support is available. Please contact a crisis counselor.',
            'emergency': 'In emergency, call 119 (ambulance) or 110 (police) immediately.'
        },
        'ko': {
            'title': '당신의 마음을 소중히 생각합니다',
            'message': '전문 상담사가 도움을 드릴 수 있습니다. 위기 상담원에게 연락하세요.',
            'emergency': '응급상황 시 즉시 119(구급차) 또는 110(경찰)에 연락하세요.'
        },
        'zh': {
            'title': '我们关心您的感受',
            'message': '专业支持服务可用。请联系危机咨询师。',
            'emergency': '紧急情况请立即拨打119（救护车）或110（警察）。'
        }
    }
    
    # 相談先情報（日本語メイン、他言語は最低限）
    resources = [
        {
            'name': 'いのちの電話',
            'organization': '一般社団法人 日本いのちの電話連盟',
            'phone': '0120-783-556',
            'hours': '24時間対応',
            'website': 'https://www.inochinodenwa.org/?page_id=267',
            'description': '24時間いつでも相談できる電話窓口です',
            'description_en': '24-hour crisis hotline',
            'description_ko': '24시간 위기 상담 전화',
            'description_zh': '24小时危机热线'
        },
        {
            'name': 'ライフリンク',
            'organization': 'NPO法人 自殺対策支援センター ライフリンク',
            'line': 'https://line.me/R/ti/p/@eds9972b',
            'line_qr': 'https://qr-official.line.me/gs/M_eds9972b_GW.png?openQrModal=true&searchId=eds9972b',
            'description': 'LINEで相談できます',
            'description_en': 'Available via LINE chat',
            'description_ko': 'LINE 채팅 상담 가능',
            'description_zh': '可通过LINE聊天咨询'
        },
        {
            'name': 'いのち支える自殺対策推進センター',
            'organization': 'JSCP',
            'website': 'https://jscp.or.jp/',
            'description': '自殺対策に関する情報と相談窓口',
            'description_en': 'Suicide prevention information and support',
            'description_ko': '자살 예방 정보 및 상담',
            'description_zh': '自杀预防信息和支持'
        },
        {
            'name': 'まもろうよ こころ',
            'organization': '厚生労働省',
            'website': 'https://www.mhlw.go.jp/mamorouyokokoro/',
            'description': '厚生労働省の心の健康に関する情報サイト',
            'description_en': 'Mental health information from Ministry of Health',
            'description_ko': '보건복지부 정신건강 정보 사이트',
            'description_zh': '厚生劳动省心理健康信息网站'
        }
    ]
    
    # 言語に応じた説明文を選択
    for resource in resources:
        if language != 'ja':
            desc_key = f'description_{language}'
            if desc_key in resource:
                resource['description'] = resource[desc_key]
    
    return {
        'title': messages.get(language, messages['ja'])['title'],
        'message': messages.get(language, messages['ja'])['message'],
        'emergency_message': messages.get(language, messages['ja'])['emergency'],
        'resources': resources
    } 
