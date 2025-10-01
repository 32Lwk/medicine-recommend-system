import pandas as pd
from openai import OpenAI
import os
import re
import time
from debug_logger import add_network_log, performance_stats
from datetime import datetime
# from typing import List
# from openai.types.chat import ChatCompletionMessageParam ←不要なので削除

# こ�?�ファイルのある�?ィレクトリを基準にCSVファイルの絶対パスを取�?
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "otc_medicine_data.csv")

print('CSVファイル絶対パス:', CSV_PATH)
print('ファイル存在:', os.path.exists(CSV_PATH))

# Markdown太�?字をHTML太�?字に変換する関数
def convert_markdown_bold(text):
    """Markdown形式�?�太�?字�?**�?�?**?��をHTML太�?字タグに変換"""
    if text is None:
        return ""
    # **�?�?** �? <strong>�?�?</strong> に変換
    result = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
    # ### で始まる行を除去
    result = re.sub(r'^###+\s*', '', result, flags=re.MULTILINE)
    # ## で始まる行を除去
    result = re.sub(r'^##+\s*', '', result, flags=re.MULTILINE)
    # # で始まる行を除去
    result = re.sub(r'^#+\s*', '', result, flags=re.MULTILINE)
    # 行�?�の余�?な空白を除去
    result = re.sub(r'^\s+', '', result, flags=re.MULTILINE)
    return result

# �?キストを整形して見やすくする関数
def format_text_for_display(text):
    """�?キストを整形して見やすくする"""
    if text is None:
        return ""
    
    # �?、②、③などの丸数字�?�後に改行を追�?
    text = re.sub(r'([�?②③④⑤⑥⑦⑧⑨⑩])\s*', r'\1<br>', text)
    
    # 1.�?2.�?3.などの数字�?�後に改行を追�?
    text = re.sub(r'(\d+\.)\s*', r'\1<br>', text)
    
    # - で始まる行�?�前に改行を追�?
    text = re.sub(r'\n\s*-\s*', r'<br>- ', text)
    
    # ・ で始まる行�?�前に改行を追�?
    text = re.sub(r'\n\s*・\s*', r'<br>・ ', text)
    
    # 改行を適�?に処�??��最初に改行を処�??�?
    text = text.replace('\n\n', '<br><br>')
    text = text.replace('\n', '<br>')
    
    # 丸数字�?�後�?�改行を再度確�?
    text = re.sub(r'([�?②③④⑤⑥⑦⑧⑨⑩])(?!<br>)', r'\1<br>', text)
    
    # 数字�?�後�?�改行を再度確�?
    text = re.sub(r'(\d+\.)(?!<br>)', r'\1<br>', text)
    
    # Markdown太�?字をHTML太�?字に変換
    text = convert_markdown_bold(text)
    
    return text

# .envファイルから環�?変数を読み込み?��オプショナル?�?
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("dotenvを使用して.envファイルから環�?変数を読み込みました�?")
except ImportError:
    print("python-dotenvがインスト�?�ルされて�?ません。環�?変数のみを使用します�??")

# --- OpenAI APIキー設�? ---
# 環�?変数からAPIキーを取�?
api_key = os.getenv('OPENAI_API_KEY')

# 環�?変数が設定されて�?な�?場合�?�フォールバック
if not api_key:
    # 直接APIキーを設定（開発・�?スト用?�?
    api_key = "sk-proj-REDACTED"
    print("環�?変数からAPIキーを取得できませんでした。直接設定されたAPIキーを使用します�??")

# --- OpenAIクライアント�?�期�? ---
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
        print(f"CSVファイルを正常に読み込みました?��エンコー�?ィング: {encoding}?���??")
        break
    except UnicodeDecodeError:
        print(f"エンコー�?ィング {encoding} で読み込みに失敗しました�?")
        continue
    except FileNotFoundError:
        csv_load_status["error"] = "FileNotFoundError"
        print("エラー: otc_medicine_data.csvファイルが見つかりません�?")
        break
    except Exception as e:
        csv_load_status["error"] = str(e)
        print(f"CSVファイルの読み込みエラー: {e}")
        break

if not csv_load_status["success"]:
    print("すべてのエンコー�?ィングでCSVファイルの読み込みに失敗しました�?")

def get_medicines_by_symptom(symptom_text, df=None):
    if df is None:
        try:
            from medicine_logic import df as global_df
            df = global_df
        except ImportError:
            return ["�?ータが読み込まれて�?ません"]
    if df is None:
        return ["�?ータが読み込まれて�?ません"]
    if '効能効�?' not in df.columns:
        return ["CSVに効能効果カラ�?がありません"]
    # �?状�?キストが効能効果に部�?�?致する行を抽出
    matched = df[df['効能効�?'].astype(str).str.contains(symptom_text, na=False)]
    if matched.empty:
        return ["該当する市販薬�?報が見つかりませんでした�?"]
    # 製品名・メーカー名�?��?類�?�効能効果�?�成�?をまとめて返す
    result = []
    for _, row in matched.iterrows():
        info = f"製品名: {row['製品名']} / メーカー: {row['メーカー�?']} / �?�?: {row['�?�?']}\n効能効�?: {row['効能効�?']}\n成�?: {row['成�?']}"
        result.append(info)
    return result

def gpt_guess_symptom(user_text, symptom_list, client=None):
    """
    ChatGPTで�?状リストから最も近い�?状名を1?�?3個推�?
    """
    if client is None:
        client = OpenAI(api_key=api_key)
    prompt = (
        "あなた�?�薬剤師AIです�?�以下�?��?状リストです�??\n"
        "ユーザーの�?状�?から�?も近い�?状名を日本語で返してください�?(�?数選択可)\n\n"
        "【症状リスト�?�\n" +
        "\n".join(f"{i+1}. {s}" for i, s in enumerate(symptom_list)) +
        f"\nユーザーの�?状: {user_text}"
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
    print("ChatGPT返�?:\n", content.strip())
    # 改行やカンマ区�?りで�?割
    symptoms = [s.strip() for s in re.split(r'[\n,、]', content) if s.strip()]
    return symptoms

def find_otc_candidates(symptoms, df_otc, max_candidates=20):
    """
    �?状名リスト�?��?ずれかが効能効果に含まれる市販薬を抽出
    """
    mask = df_otc['効能効�?'].astype(str).apply(lambda x: any(s in x for s in symptoms))
    return df_otc[mask].head(max_candidates)

def gpt_select_best_otc(user_text, candidates, client=None):
    """
    ChatGPTで候補リストから最適な市販薬3つを選ばせる
    """
    if client is None:
        client = OpenAI(api_key=api_key)
    prompt = (
        f"あなた�?�薬剤師AIです�?�ユーザーの�?状「{user_text}」に�?も適した市販薬�?3つ選び、理由も簡単に説明してください�?(市販薬の重�?は避けてください)\n\n"
        "【�?�補リスト�?�\n" +
        "\n".join(
            f"{i+1}. 製品名: {row['製品名']} / 効能効�?: {row['効能効�?']} / 成�?: {row['成�?']}"
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
    print("ChatGPT返�?:\n", content.strip())
    return content.strip()

def recommend_otc_medicines_via_gpt(user_text, symptom_csv_path=None, otc_csv_path=None, max_candidates=20, client=None):
    """
    ユーザー�?状�?→ChatGPTで�?状名推定�?��?�補薬抽出→ChatGPTで�?適薬3つ選�?
    """
    import pandas as pd
    import os
    # CSV読み込み
    base_dir = os.path.dirname(os.path.abspath(__file__))
    symptom_csv = symptom_csv_path or os.path.join(base_dir, "�?状-薬.csv")
    otc_csv = otc_csv_path or os.path.join(base_dir, "otc_medicine_data.csv")
    df_symptom = pd.read_csv(symptom_csv)
    df_otc = pd.read_csv(otc_csv)
    
    # NaN値を適�?に処�?
    df_otc = df_otc.fillna("")
    # �?状リスト作�??
    symptom_list = df_symptom["�?状"].dropna().unique().tolist()
    # 1. ChatGPTで�?状名推�?
    symptoms = gpt_guess_symptom(user_text, symptom_list, client=client)
    # 2. 候補薬抽出
    candidates = find_otc_candidates(symptoms, df_otc, max_candidates=max_candidates)
    if candidates.empty:
        return "該当する市販薬�?報が見つかりませんでした�?"
    # 3. ChatGPTで�?適薬3つ選�?
    result = gpt_select_best_otc(user_text, candidates, client=client)
    print("ChatGPT返�?:\n", result)
    return result

def recommend_otc_medicines_from_summarized(user_text, summarized_csv_path=None, max_candidates=20, client=None):
    """
    summarized_efficacy_data.csvを用�?て�?
    1. �?状語リストを自動抽出
    2. ChatGPTで�?状名推定（表記ゆれ�?��?数�?状対応�?
    3. 候補薬リストを抽出
    4. ChatGPTに候補リスト＋症状�?を渡し�?�最適な3つを選ばせる
    """
    import pandas as pd
    import os
    import re
    # CSV読み込み
    base_dir = os.path.dirname(os.path.abspath(__file__))
    summarized_csv = summarized_csv_path or os.path.join(base_dir, "summarized_efficacy_data.csv")
    df = pd.read_csv(summarized_csv)
    
    # NaN値を適�?に処�?
    df = df.fillna("")
    # --- �?状語リストを抽出 ---
    symptom_set = set()
    for eff in df["Summarized Efficacy"].dropna():
        # かっこ�??の�?状語を抽出
        m = re.search(r'?�?(.+?)?�?', eff)
        if m:
            for s in re.split(r'[�?,]', m.group(1)):
                s = s.strip()
                if s:
                    symptom_set.add(s)
    # 類義語�?�表記ゆれ対応（�?: 咳/せき, 鼻水/鼻み�? など?�?
    synonym_map = {
        "咳": ["咳", "せき"],
        "鼻水": ["鼻水", "鼻み�?"],
        "痰": ["痰", "たん"],
        "悪�?": ["悪�?", "さ�?�?"],
        "関�?の痛み": ["関�?の痛み", "関�?�?"],
        "筋肉の痛み": ["筋肉の痛み", "筋肉�?"],
        # �?要に応じて追�?
    }
    # �?状語リストを展開
    expanded_symptom_set = set()
    for s in symptom_set:
        expanded_symptom_set.add(s)
        for syns in synonym_map.values():
            if s in syns:
                expanded_symptom_set.update(syns)
    symptom_list = sorted(expanded_symptom_set)
    # --- 1. ChatGPTで�?状名推�? ---
    symptoms = gpt_guess_symptom(user_text, symptom_list, client=client)
    # --- 2. 類義語も含めて候補薬抽出 ---
    # 入力症状の類義語も展開
    all_symptoms = set(symptoms)
    for s in symptoms:
        for key, syns in synonym_map.items():
            if s in syns:
                all_symptoms.update(syns)
    # 候補薬抽出?��すべての�?状語�?��?ずれかを含�?も�?�?�?
    mask = df["Summarized Efficacy"].astype(str).apply(lambda x: any(s in x for s in all_symptoms))
    candidates = df[mask].copy()
    # カバ�?��?状数でソート（多くカバ�?�する薬を上位に?�?
    def count_covered(eff):
        return sum(s in eff for s in all_symptoms)
    candidates["_cover_count"] = candidates["Summarized Efficacy"].astype(str).apply(count_covered)
    candidates = candidates.sort_values("_cover_count", ascending=False).head(max_candidates)
    if candidates.empty:
        return "該当する市販薬�?報が見つかりませんでした�?"
    # --- 3. ChatGPTで�?適薬3つ選�? ---
    # プロンプト工夫: �?状�?・推定症状語�?�候補リストを明示
    prompt = (
        f"あなた�?�薬剤師AIです�?�ユーザーの�?状:『{user_text}』\n"
        f"推定された�?状�?: {', '.join(symptoms)}\n"
        "以下�?�候補リストから�?�症状に�?も適した市販薬�?3つ選び、それぞれ�?�医薬品�?�特徴を効果効能から要�?して日本語で説明してください�?\n"
        "【�?�補リスト�?�\n" +
        "\n".join(
            f"{i+1}. 製品名: {row['製品名']} / 効能効�?: {row['Summarized Efficacy']}"
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
    print("ChatGPT返�?:\n", content.strip())
    return content.strip() 

def gpt_select_efficacy_candidates(user_text, summarized_csv_path=None, max_candidates=30, client=None):
    """
    ChatGPTにsummarized_efficacy_data.csvの効能効果リストを渡し�??
    ユーザー�?状に�?も近い効能効果（�?数可?��を選ばせる
    """
    import pandas as pd
    import os
    base_dir = os.path.dirname(os.path.abspath(__file__))
    summarized_csv = summarized_csv_path or os.path.join(base_dir, "summarized_efficacy_data.csv")
    df = pd.read_csv(summarized_csv)
    
    # NaN値を適�?に処�?
    df = df.fillna("")
    efficacy_list = df["Summarized Efficacy"].dropna().unique().tolist()
    # 候補数が多すぎる場合�?�ラン�?�?サンプリング
    import random
    if len(efficacy_list) > max_candidates:
        efficacy_list = random.sample(efficacy_list, max_candidates)
    prompt = (
        f"あなた�?�薬剤師AIです�?�下記�?�市販薬の効能効果リストです�??\n"
        f"ユーザーの�?状:『{user_text}』\n"
        "こ�?�中から�?状に�?も近い効能効果をすべて選び、日本語でリスト形式で出力してください�?\n"
        "【効能効果リスト�?�\n" +
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
    print("ChatGPT返�?:\n", content.strip())
    # リスト形式で返す
    selected = [line.strip(" ・-0123456789.") for line in content.splitlines() if line.strip()]
    # �?の効能効果リストと突合して正規化
    selected_set = set(selected)
    matched_efficacy = [e for e in efficacy_list if any(s in e or e in s for s in selected_set)]
    return matched_efficacy

def select_symptoms_via_gpt(user_text, symptoms_csv_path=None, client=None, max_symptoms=250):
    """
    unique_symptoms_from_summarized_efficacy.csvの�?状リストとユーザー�?状�?をChatGPTに渡し�??
    該当する症状?���?数可?��を返答させる。ユーザー入力とChatGPT返答をターミナルにprint表示�?
    """
    import pandas as pd
    import os
    base_dir = os.path.dirname(os.path.abspath(__file__))
    symptoms_csv = symptoms_csv_path or os.path.join(base_dir, "unique_symptoms_from_summarized_efficacy.csv")
    
    # ファイルの存在確�?
    if not os.path.exists(symptoms_csv):
        print(f"�??�? Warning: {symptoms_csv} not found. Using fallback symptom list.")
        # フォールバック用の�?状リス�?
        symptom_list = [
            "頭�?", "発熱", "咳", "鼻水", "鼻づま�?", "のどの痛み", "腹�?", "下痢", "便�?",
            "吐き�?", "めま�?", "疲労�?", "筋肉�?", "関�?�?", "かゆみ", "発疹", "不眠"
        ]
        return {
            'status': 'success',
            'symptoms': symptom_list[:max_symptoms],
            'message': 'Fallback symptom list used'
        }
    
    df = pd.read_csv(symptoms_csv, header=0)
    
    # NaN値を適�?に処�?
    df = df.fillna("")
    symptom_list = df.iloc[:, 0].dropna().unique().tolist()
    if len(symptom_list) > max_symptoms:
        symptom_list = symptom_list[:max_symptoms]
    prompt = (
        f"あなた�?�薬剤師AIです�?�下記�?�市販薬の代表�?な�?状リストです�??\n"
        f"ユーザーの�?状:『{user_text}』\n"
        "こ�?�中から該当する症状をすべて選び、日本語でリスト形式で出力してください�?\n"
        "【症状リスト�?�\n" +
        "\n".join(f"{i+1}. {s}" for i, s in enumerate(symptom_list))
    )
    messages = [
        {"role": "system", "content": prompt}
    ]
    if client is None:
        client = OpenAI(api_key=api_key)
    print("ユーザー入�?:", user_text)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        temperature=0
    )
    content = response.choices[0].message.content if response.choices[0].message.content else ""
    print("ChatGPT返�?:\n", content.strip())
    # リスト形式で返す
    selected = [line.strip(" ・-0123456789.") for line in content.splitlines() if line.strip()]
    # �?の�?状リストと突合して正規化
    selected_set = set(selected)
    matched_symptoms = [s for s in symptom_list if any(sel in s or s in sel for sel in selected_set)]
    return matched_symptoms 

def analyze_symptoms_and_medicine_type(user_text, client=None):
    """
    �?状�?と�?状リスト�?�医薬品�?�種類�?��?ータをChatGPTに渡して
    �?状?���?数選択可?��と適する医薬品�?�種類を返す
    """
    if client is None:
        client = OpenAI(api_key=api_key)
    
    # 医薬品�?�種類リスト�?CSVファイルの実際の�?容に基づく�?
    medicine_types = [
        "筋肉�?", "睡�?障害", "精神症状", "そ�?��?", "�?腸薬", 
        "解熱鎮痛薬", "外用薬?��皮膚�?", "抗アレルギー薬", "殺虫剤", 
        "鼻炎用薬", "風邪薬", "目薬"
    ]
    
    # �?状リストを読み込み
    symptoms_csv_path = os.path.join(BASE_DIR, "unique_symptoms_from_summarized_efficacy.csv")
    symptoms_list = []
    
    # ファイルの存在確�?
    if not os.path.exists(symptoms_csv_path):
        print(f"�??�? Warning: {symptoms_csv_path} not found. Using fallback symptom list.")
        symptoms_list = [
            "頭�?", "発熱", "咳", "鼻水", "鼻づま�?", "のどの痛み", "腹�?", "下痢", "便�?",
            "吐き�?", "めま�?", "疲労�?", "筋肉�?", "関�?�?", "かゆみ", "発疹", "不眠"
        ]
    else:
        try:
            symptoms_df = pd.read_csv(symptoms_csv_path)
            
            # NaN値を適�?に処�?
            symptoms_df = symptoms_df.fillna("")
            symptoms_list = symptoms_df['�?状'].tolist()
        except Exception as e:
            print(f"�?状リスト�?�読み込みエラー: {e}")
            symptoms_list = [
                "頭�?", "発熱", "咳", "鼻水", "鼻づま�?", "のどの痛み", "腹�?", "下痢", "便�?",
                "吐き�?", "めま�?", "疲労�?", "筋肉�?", "関�?�?", "かゆみ", "発疹", "不眠"
            ]
    
    prompt = f"""
以下�?��?状�?を�?析して、該当する症状と適する医薬品�?�種類を選択してください�?

【症状�?�?
{user_text}

【選択可能な�?状リスト�??
{', '.join(symptoms_list[:100])}  # �?初�?�100個�?�み表示

【医薬品�?�種類�??
{', '.join(medicine_types)}

【回答形式�??
以下�?�JSON形式で回答してください?�?
{{
    "symptoms": ["�?状1", "�?状2", "�?状3"],
    "medicine_type": "適する医薬品�?�種�?"
}}

注意�?
- �?状は�?数選択可能で�?
- 医薬品�?�種類�?�1つ選択してください
- 該当する症状�?医薬品�?�種類が見つからな�?場合�?�、最も近いも�?�を選択してください
- そ�?��?(医薬品�?�種類に当てはまらな�?も�?�はそ�?�他とする)
"""

    print(f"=== �?状�?析開�? ===")
    print(f"�?状�?: {user_text}")
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "あなた�?�医薬品�?�専門家です�?�症状�?を�?析して適�?な�?状と医薬品�?�種類を選択してください�?"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=500
        )
        
        result = response.choices[0].message.content
        print(f"ChatGPT応�?: {result}")
        if not result:
            print("ChatGPTからの応答が空で�?")
            return {"symptoms": [], "medicine_type": "そ�?��?"}
        # JSON形式�?�回答を解�?
        import json
        try:
            # JSON部�?を抽出
            json_start = result.find('{') if result else -1
            json_end = result.rfind('}') + 1 if result else -1
            if json_start != -1 and json_end != -1:
                json_str = result[json_start:json_end]
                parsed_result = json.loads(json_str)
                print(f"解析結果: {parsed_result}")
                return parsed_result
            else:
                print("JSON形式が見つかりませんでした")
                return {"symptoms": [], "medicine_type": "そ�?��?"}
        except json.JSONDecodeError as e:
            print(f"JSON解析エラー: {e}")
            return {"symptoms": [], "medicine_type": "そ�?��?"}
            
    except Exception as e:
        print(f"ChatGPT API呼び出しエラー: {e}")
        print("フォールバック: 簡易症状検�?�を使用しま�?")
        return simple_symptom_and_type_detection(user_text)

def simple_symptom_and_type_detection(user_text):
    """
    簡易的な�?状と医薬品種類�?�検�?�?�?APIフォールバック用?�?
    """
    import re
    
    # �?状キーワード�?�ッピング
    symptom_keywords = {
        "頭�?": ["頭�?", "頭が痛�?", "ズキズキ", "偏�?��?"],
        "発熱": ["熱", "発熱", "熱っぽ�?", "高�?�"],
        "のどの痛み": ["�?", "のど", "咽頭�?"],
        "咳": ["咳", "せき"],
        "鼻水": ["鼻水", "鼻み�?", "鼻�?"],
        "鼻づま�?": ["鼻づま�?", "鼻詰ま�?"],
        "くし�?み": ["くし�?み", "クシャ�?"],
        "生理�?": ["生理�?", "月経痛", "生理"],
        "�?�?": ["�?�?", "�?が痛�?"],
        "吐き�?": ["吐き�?", "嘔吐"],
    }
    
    detected_symptoms = []
    for symptom, keywords in symptom_keywords.items():
        for keyword in keywords:
            if keyword in user_text:
                detected_symptoms.append(symptom)
                break
    
    # 医薬品種類�?�推�?
    medicine_type = "そ�?��?"
    
    # 鼻炎用薬の判定（鼻�?状のみで発熱・喉�?�咳がな�?場合�?
    nose_symptoms = ["鼻水", "鼻づま�?", "くし�?み"]
    other_cold_symptoms = ["発熱", "のどの痛み", "咳"]
    
    if any(s in detected_symptoms for s in nose_symptoms):
        # 鼻�?状のみで他�?�風邪�?状がな�?場合�?�鼻炎用薬
        if not any(s in detected_symptoms for s in other_cold_symptoms):
            medicine_type = "鼻炎用薬"
        # 鼻�?状+他�?�風邪�?状がある�?�合�?�風邪薬
        else:
            medicine_type = "風邪薬"
    # 風邪薬の判定（鼻�?状以外�?�風邪�?状?�?
    elif any(s in detected_symptoms for s in other_cold_symptoms):
        medicine_type = "風邪薬"
    
    # 解熱鎮痛薬の判�?
    elif any(s in detected_symptoms for s in ["頭�?", "生理�?"]):
        medicine_type = "解熱鎮痛薬"
    
    # �?腸薬の判�?
    elif any(s in detected_symptoms for s in ["�?�?", "吐き�?"]):
        medicine_type = "�?腸薬"
    
    print(f"=== 簡易検�?�結果 ===")
    print(f"検�?�された症状: {detected_symptoms}")
    print(f"推定された医薬品�?�種�?: {medicine_type}")
    
    return {
        "symptoms": detected_symptoms,
        "medicine_type": medicine_type
    }

def get_medicines_by_type(medicine_type, df=None):
    """
    医薬品�?�種類に基づ�?てotc_medicine_dataから医薬品リストを取�?
    """
    if df is None:
        df = globals().get('df')
    
    if df is None:
        print("�?ータフレー�?が読み込まれて�?ません")
        return []
    
    # 医薬品�?�種類カラ�?から該当する医薬品を抽出
    if '医薬品�?�種�?' in df.columns:
        matched = df[df['医薬品�?�種�?'].astype(str).str.contains(medicine_type, na=False)]
        medicines = []
        for _, row in matched.iterrows():
            medicine_info = {
                '製品名': row.get('製品名', ''),
                'メーカー�?': row.get('メーカー�?', ''),
                '�?�?': row.get('�?�?', ''),
                '医薬品�?�種�?': row.get('医薬品�?�種�?', ''),
                '効能効�?': row.get('効能効�?', ''),
                '成�?': row.get('成�?', ''),
                '使用上�?�注�?': row.get('使用上�?�注�?', '')
            }
            medicines.append(medicine_info)
        
        print(f"医薬品�?�種�? '{medicine_type}' で {len(medicines)} 件の医薬品を抽出しました")
        return medicines
    else:
        print("CSVに医薬品�?�種類カラ�?がありません")
        return []

def recommend_medicines_with_retry(user_text, symptoms, medicine_list, client=None, max_retries=3):
    """
    �?状と医薬品リストをChatGPTに渡して推奨医薬品を3つ選び�?
    使用上�?�注意を要�?して返す。適した医薬品が返ってこなければ再試�?
    """
    if client is None:
        client = OpenAI(api_key=api_key)
    
    # 医薬品リストを�?字�?�に変換?��使用上�?�注意も含める?�?
    medicine_text = ""
    for i, medicine in enumerate(medicine_list[:20]):  # �?初�?�20個�?�み使用
        usage_notes = medicine.get('使用上�?�注�?', '')
        medicine_text += f"{i+1}. {medicine['製品名']} ({medicine['メーカー�?']})\n"
        medicine_text += f"   効能効�?: {medicine['効能効�?']}\n"
        medicine_text += f"   成�?: {medicine['成�?']}\n"
        medicine_text += f"   使用上�?�注�?: {usage_notes}\n\n"
    
    for attempt in range(max_retries):
        print(f"=== 医薬品推奨試�? {attempt + 1}/{max_retries} ===")
        
        prompt = f"""
以下�?��?状と医薬品リストから�?�最も適�?な3つの医薬品を選んでください�?

【症状�?
{', '.join(symptoms)}

【症状�?�?
{user_text}

【選択可能な医薬品�??
{medicine_text}

【回答形式�??
以下�?�JSON形式で回答してください?�?
{{
    "recommended_medicines": [
        {{
            "number": 1,
            "product_name": "製品名",
            "manufacturer": "メーカー�?",
            "reason": "推奨�?由",
            "usage_notes": "こ�?�医薬品�?�使用上�?�注意点の要�?"
        }},
        {{
            "number": 2,
            "product_name": "製品名",
            "manufacturer": "メーカー�?",
            "reason": "推奨�?由",
            "usage_notes": "こ�?�医薬品�?�使用上�?�注意点の要�?"
        }},
        {{
            "number": 3,
            "product_name": "製品名",
            "manufacturer": "メーカー�?",
            "reason": "推奨�?由",
            "usage_notes": "こ�?�医薬品�?�使用上�?�注意点の要�?"
        }}
    ],
    "doctor_consultation": "医師の受診が�?要な場合につ�?て"
}}

注意�?
- �?状に�?も適した医薬品を3つ選んでください
- 製品名とメーカー名が同じも�?�は重�?として、同じものを�?数回推奨しな�?でください
- 番号は1つ目�?2つ目�?3つ目の�?で出力してください?��例�?"number": 1, "number": 2, "number": 3?�?
- 製品名とメーカー名�?�正確に記載してください
- �?医薬品�?�「使用上�?�注意�?��?の�?容を参�?に、�?ず各医薬品ごとに使用上�?�注意点を要�?してください
- 医師の受診が�?要な場合につ�?ても記載してください
"""

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "あなた�?�医薬品�?�専門家です�?�症状に適した医薬品を推奨し�?�使用上�?�注意を説明してください�?"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=800
            )
            
            result = response.choices[0].message.content
            print(f"ChatGPT応�? (試�? {attempt + 1}): {result}")
            if not result:
                print("ChatGPTからの応答が空です�?��?�試行します�??")
                continue
            # JSON形式�?�回答を解�?
            import json
            try:
                # JSON部�?を抽出
                json_start = result.find('{') if result else -1
                json_end = result.rfind('}') + 1 if result else -1
                if json_start != -1 and json_end != -1:
                    json_str = result[json_start:json_end]
                    parsed_result = json.loads(json_str)
                    
                    # 推奨医薬品が3つあるかチェ�?ク?��重�?除去
                    if (parsed_result.get('recommended_medicines')):
                        # 製品名・メーカー名�?�重�?を除去
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
                            print(f"適�?な推奨医薬品が見つかりました?��重�?除去済み?�?")
                            return parsed_result
                        else:
                            print(f"推奨医薬品が不足して�?ます（重�?除去後）�?��?�試行します�??")
                    else:
                        print(f"推奨医薬品が不足して�?ます�?��?�試行します�??")
                else:
                    print("JSON形式が見つかりませんでした。�?�試行します�??")
            except json.JSONDecodeError as e:
                print(f"JSON解析エラー: {e}。�?�試行します�??")
                
        except Exception as e:
            print(f"ChatGPT API呼び出しエラー: {e}")
    
    print("�?大試行回数に達しました。デフォルト�?�推奨を返します�??")
    return {
        "recommended_medicines": [],
        "usage_notes": "適�?な医薬品が見つかりませんでした。医師にご相�?ください�?",
        "doctor_consultation": "�?状が改�?しな�?場合�?�医師にご相�?ください�?"
    }

def get_medicine_details(recommended_medicines, medicine_list):
    """
    推奨医薬品�?�詳細�?報?��使用上�?�注意など?��を取�?
    """
    detailed_medicines = []
    
    for rec in recommended_medicines:
        product_name = rec.get('product_name', '')
        manufacturer = rec.get('manufacturer', '')
        
        # NaN値を適�?に処�?
        if product_name is None or str(product_name) == 'nan':
            product_name = ''
        if manufacturer is None or str(manufacturer) == 'nan':
            manufacturer = ''

        # まず完�?��?致で検索
        matched_medicine = None
        for medicine in medicine_list:
            csv_product = medicine.get('製品名', '')
            csv_manufacturer = medicine.get('メーカー�?', '')
            
            # NaN値を適�?に処�?
            if csv_product is None or str(csv_product) == 'nan':
                csv_product = ''
            if csv_manufacturer is None or str(csv_manufacturer) == 'nan':
                csv_manufacturer = ''
            
            if product_name == csv_product and manufacturer == csv_manufacturer:
                matched_medicine = medicine
                break
        # 完�?��?致が見つからな�?場合�?�製品名のみで検索
        if not matched_medicine:
            for medicine in medicine_list:
                csv_product = medicine.get('製品名', '')
                
                # NaN値を適�?に処�?
                if csv_product is None or str(csv_product) == 'nan':
                    csv_product = ''
                
                if product_name == csv_product:
                    matched_medicine = medicine
                    break
        
        if matched_medicine:
            # usage_notesはChatGPT返答を優先�?�なければDB�?容
            usage_notes = rec.get('usage_notes')
            if not usage_notes:
                usage_notes = matched_medicine.get('使用上�?�注�?', '')
            # NaN値を適�?に処�?して医薬品詳細�?報を構�?
            def safe_get(value):
                if value is None or str(value) == 'nan':
                    return ''
                return value
            
            # スコアリング計算（管�?�?画面用?�?
            def calculate_medicine_score(medicine_data, rec_data):
                score = 0
                max_score = 100
                
                # 基本スコア?���??位による?�?
                rank_score = max(0, 30 - (rec_data.get('number', 1) - 1) * 5)
                score += rank_score
                
                # 効能効果�?��?実度
                efficacy = safe_get(medicine_data.get('効能効�?', ''))
                if efficacy and len(efficacy) > 50:
                    score += 20
                elif efficacy and len(efficacy) > 20:
                    score += 10
                
                # 成�?�?報の�?実度
                ingredients = safe_get(medicine_data.get('成�?', ''))
                if ingredients and len(ingredients) > 30:
                    score += 15
                elif ingredients and len(ingredients) > 10:
                    score += 8
                
                # 使用上�?�注意�?��?実度
                usage_notes = safe_get(usage_notes)
                if usage_notes and len(usage_notes) > 50:
                    score += 15
                elif usage_notes and len(usage_notes) > 20:
                    score += 8
                
                # ド�?�ピング�?報の有無
                doping = safe_get(medicine_data.get('禁止物質あり', ''))
                if doping and doping != '':
                    score += 10
                
                # 推奨�?由の�?実度
                reason = safe_get(rec_data.get('reason', ''))
                if reason and len(reason) > 30:
                    score += 10
                elif reason and len(reason) > 10:
                    score += 5
                
                return min(score, max_score)
            
            medicine_score = calculate_medicine_score(matched_medicine, rec)
            
            detailed_medicine = {
                'number': rec.get('number', 0),
                'product_name': safe_get(matched_medicine.get('製品名', product_name)),
                'manufacturer': safe_get(matched_medicine.get('メーカー�?', manufacturer)),
                'reason': safe_get(rec.get('reason', '')),
                'efficacy': safe_get(matched_medicine.get('効能効�?', '')),
                'ingredients': safe_get(matched_medicine.get('成�?', '')),
                'usage_notes': safe_get(usage_notes),
                'doping_prohibited': safe_get(matched_medicine.get('禁止物質あり', '')),
                'competition_category': safe_get(matched_medicine.get('競�?会区�?', '')),
                'doping_conditions': safe_get(matched_medicine.get('条件', '')),
                'score': medicine_score  # スコアリング�?報を追�?
            }
            detailed_medicines.append(detailed_medicine)
            print(f"医薬品詳細�?報取�?: {product_name} ({manufacturer}) -> {matched_medicine.get('製品名', '')} ({matched_medicine.get('メーカー�?', '')})")
        else:
            print(f"医薬品詳細�?報が見つかりません: {product_name} ({manufacturer})")
            # 詳細�?報が見つからな�?場合でも�?�ChatGPTのusage_notesを優�?
            usage_notes = rec.get('usage_notes')
            if not usage_notes:
                usage_notes = '詳細�?報が見つかりませんでした'
            # NaN値を適�?に処�?して医薬品詳細�?報を構�?
            def safe_get(value):
                if value is None or str(value) == 'nan':
                    return ''
                return value
            
            # 詳細�?報が見つからな�?場合�?�スコアリング
            def calculate_fallback_score(rec_data):
                score = 0
                # 基本スコア?���??位による?�?
                rank_score = max(0, 30 - (rec_data.get('number', 1) - 1) * 5)
                score += rank_score
                
                # 推奨�?由の�?実度
                reason = safe_get(rec_data.get('reason', ''))
                if reason and len(reason) > 30:
                    score += 20
                elif reason and len(reason) > 10:
                    score += 10
                
                return min(score, 50)  # 詳細�?報がな�?場合�?��?大50点
            
            fallback_score = calculate_fallback_score(rec)
            
            detailed_medicine = {
                'number': rec.get('number', 0),
                'product_name': safe_get(product_name),
                'manufacturer': safe_get(manufacturer),
                'reason': safe_get(rec.get('reason', '')),
                'efficacy': '詳細�?報が見つかりませんでした',
                'ingredients': '詳細�?報が見つかりませんでした',
                'usage_notes': safe_get(usage_notes),
                'doping_prohibited': '詳細�?報が見つかりませんでした',
                'competition_category': '詳細�?報が見つかりませんでした',
                'doping_conditions': '詳細�?報が見つかりませんでした',
                'score': fallback_score  # スコアリング�?報を追�?
            }
            detailed_medicines.append(detailed_medicine)
    
    return detailed_medicines

def comprehensive_medicine_recommendation(user_text, client=None):
    """
    �?括�?な医薬品推奨シス�?�?のメイン関数
    """
    print(f"=== �?括�?医薬品推奨シス�?�?開�? ===")
    print(f"�?状�?: {user_text}")
    
    # ス�?�?�?1: �?状と医薬品�?�種類を�?�?
    analysis_result = analyze_symptoms_and_medicine_type(user_text, client)
    symptoms = analysis_result.get('symptoms', [])
    medicine_type = analysis_result.get('medicine_type', 'そ�?��?')
    
    print(f"�?析結果 - �?状: {symptoms}")
    print(f"�?析結果 - 医薬品�?�種�?: {medicine_type}")
    
    # ス�?�?�?2: 医薬品�?�種類に基づ�?て医薬品リストを取�?
    medicine_list = get_medicines_by_type(medicine_type)
    
    if not medicine_list:
        print("該当する医薬品が見つかりませんでした")
        return {
            'symptoms': symptoms,
            'medicine_type': medicine_type,
            'recommended_medicines': [],
            'usage_notes': '該当する医薬品が見つかりませんでした。医師にご相�?ください�?',
            'doctor_consultation': '�?状が改�?しな�?場合�?�医師にご相�?ください�?'
        }
    
    # ス�?�?�?3: ChatGPTに推奨医薬品を選択させる
    recommendation_result = recommend_medicines_with_retry(
        user_text, symptoms, medicine_list, client
    )
    
    # ス�?�?�?4: 推奨医薬品�?�詳細�?報を取�?
    detailed_medicines = get_medicine_details(
        recommendation_result.get('recommended_medicines', []), 
        medicine_list
    )
    
    # �?終結果を構�?
    final_result = {
        'symptoms': symptoms,
        'medicine_type': medicine_type,
        'recommended_medicines': detailed_medicines,
        'usage_notes': recommendation_result.get('usage_notes', ''),
        'doctor_consultation': recommendation_result.get('doctor_consultation', '')
    }
    
    print(f"=== 推奨結果 ===")
    print(f"�?状: {symptoms}")
    print(f"医薬品�?�種�?: {medicine_type}")
    print(f"推奨医薬品数: {len(detailed_medicines)}")
    
    return final_result 

# ================================================================================
# ルールベ�?�ス推奨シス�?�??��新規追�??�?
# ================================================================================

def rule_based_medicine_recommendation(user_text, user_info, client=None):
    """
    ルールベ�?�ス医薬品推奨シス�?�?のラ�?パ�?�関数
    風邪薬、解熱鎮痛薬�?鼻炎用薬に限�?
    
    Args:
        user_text: ユーザーの�?状入�?
        user_info: ユーザー�?報?��年齢、妊�?など?�?
        client: OpenAIクライアン�?
    
    Returns:
        推奨結果
    """
    if client is None:
        client = OpenAI(api_key=api_key)
    
    # ルールベ�?�ス推奨モジュールをインポ�?��?
    try:
        from rule_based_recommendation import rule_based_recommendation, log_recommendation_session
        
        # グローバルdfを使用
        global df
        if df is None:
            return {
                "status": "error",
                "reason": "医薬品データが読み込まれて�?ません"
            }
        
        # ルールベ�?�ス推奨を実�?
        result = rule_based_recommendation(
            user_text=user_text,
            user_info=user_info,
            medicine_df=df,
            client=client,
            top_n=3
        )
        
        # ログ保�?
        log_recommendation_session(user_text, user_info, result)
        
        return result
        
    except Exception as e:
        print(f"ルールベ�?�ス推奨エラー: {e}")
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "reason": f"シス�?�?エラー: {str(e)}"
        }

def chat_with_medicine_context(user_message, conversation_history, recommended_medicines, client=None):
    """
    会話履歴と推奨医薬品�?��?報をChatGPTに渡して、医薬品に関する質問に回答す�?
    
    Args:
        user_message: ユーザーの質�?
        conversation_history: 会話履歴?��最新の5件程度?�?
        recommended_medicines: 推奨医薬品�?�リス�?
        client: OpenAIクライアン�?
    
    Returns:
        dict: ChatGPTの回�?
    """
    if client is None:
        client = OpenAI(api_key=api_key)
    
    # 推奨医薬品がな�?場合�?�登録販売�?相�?を推奨
    if not recommended_medicines:
        return {
            "answer": "申し訳ござ�?ません。推奨医薬品�?��?報がな�?ため、�?�体的な回答ができません。お近くの登録販売�?にご相�?ください�?",
            "medicine_details": "推奨医薬品�?��?報がありません",
            "interactions": "推奨医薬品�?��?報がありません",
            "doping_check": "推奨医薬品�?��?報がありません",
            "side_effects": "推奨医薬品�?��?報がありません",
            "consultation_advice": "お近くの登録販売�?にご相�?ください"
        }
    
    # 会話履歴を整形?��最新の5件程度?�?
    history_text = ""
    if conversation_history is not None:
        recent_messages = conversation_history[-5:]  # �?新5件
        for msg in recent_messages:
            if msg.get('type') == 'user':
                history_text += f"ユーザー: {msg.get('content', '')}\n"
            elif msg.get('type') == 'bot':
                # botメ�?セージから診断結果を抽出
                diagnosis = msg.get('diagnosis')
                if diagnosis is not None and diagnosis.get('recommended_medicines'):
                    medicines = diagnosis.get('recommended_medicines', [])
                    history_text += f"AI: 推奨医薬�?: {', '.join([m.get('product_name', '') for m in medicines])}\n"
                else:
                    history_text += f"AI: {msg.get('content', '')}\n"
    
    # 推奨医薬品�?�詳細�?報を整形
    medicines_text = ""
    if recommended_medicines:
        for i, medicine in enumerate(recommended_medicines, 1):
            medicines_text += f"""
{i}つ目: {medicine.get('product_name', '')}
- メーカー: {medicine.get('manufacturer', '')}
- 効能効�?: {medicine.get('efficacy', '')}
- 成�?: {medicine.get('ingredients', '')}
- 使用上�?�注�?: {medicine.get('usage_notes', '')}
- ド�?�ピング禁止物質: {medicine.get('doping_prohibited', '')}
- 競�?会区�?: {medicine.get('competition_category', '')}
- ド�?�ピング条件: {medicine.get('doping_conditions', '')}
"""
    
    prompt = f"""
あなた�?�薬剤師AIです�?�ユーザーの医薬品に関する質問に、推奨医薬品�?��?報を基に回答してください�?

【会話履歴�?
{history_text}

【推奨医薬品�?�詳細�?報�?
{medicines_text}

【ユーザーの質問�??
{user_message}

以下�?�点につ�?て回答してください?�?
1. 医薬品�?�詳細説明（効能効果�?��?��?、使用方法�?
2. 他�?�医薬品との飲み合わせ（相互作用?�?
3. スポ�?��?競�?でのド�?�ピング規制対象かど�?�?
4. 副作用�?注意点
5. 医師に相�?すべき�?��?

回答�?�以下�?�形式で構�??化してください?�?
{{
    "answer": "ユーザーへの直接�?な回�?",
    "medicine_details": "医薬品�?�詳細説�?",
    "interactions": "飲み合わせ�?�相互作用の説�?",
    "doping_check": "ド�?�ピング規制の確認結果",
    "side_effects": "副作用・注意点",
    "consultation_advice": "医師相�?のアドバイス"
}}

注意�?
- 推奨医薬品�?��?報を基に具体的に回答してください
- 飲み合わせにつ�?ては、�?般�?な相互作用を説明してください
- ド�?�ピングにつ�?ては、WADA?��世界アンチ�?�ド�?�ピング機関?���?�規制を参�?にしてください
- 安�?�性を最優先に�?え�?�不�?�な点がある�?�合�?�医師相�?を推奨してください
- 質問�?��?容が推奨医薬品�?��?報では回答できな�?場合�?�、�?�お近くの登録販売�?にご相�?ください」と回答してください
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "あなた�?�薬剤師AIです�?�医薬品�?�安�?�性と効果につ�?て正確な�?報を提供してください。推奨医薬品�?��?報で回答できな�?質問につ�?ては、お近くの登録販売�?にご相�?するよう推奨してください�?"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=1000
        )
        
        result = response.choices[0].message.content
        print(f"ChatGPT応�?: {result}")
        
        # JSON形式�?�回答を解�?
        import json
        try:
            # JSON部�?を抽出
            json_start = result.find('{') if result else -1
            json_end = result.rfind('}') + 1 if result else -1
            if json_start != -1 and json_end != -1:
                json_str = result[json_start:json_end]
                parsed_result = json.loads(json_str)
                
                # 回答が不十�?な場合や「�?からな�?」系の回答�?�場合�?�登録販売�?相�?を推奨
                answer = parsed_result.get('answer', '')
                if any(keyword in answer.lower() for keyword in ['�?からな�?', '不�??', '確認できません', '�?報がありません', '回答できません']):
                    return {
                        "answer": "申し訳ござ�?ません。この質問につ�?ては推奨医薬品�?��?報では回答できません。お近くの登録販売�?にご相�?ください�?",
                        "medicine_details": "推奨医薬品�?��?報では回答できません",
                        "interactions": "推奨医薬品�?��?報では回答できません",
                        "doping_check": "推奨医薬品�?��?報では回答できません",
                        "side_effects": "推奨医薬品�?��?報では回答できません",
                        "consultation_advice": "お近くの登録販売�?にご相�?ください"
                    }
                
                return parsed_result
            else:
                # JSON形式でな�?場合�?�直接回答として返す
                return {
                    "answer": result,
                    "medicine_details": "詳細�?報を取得できませんでした",
                    "interactions": "飲み合わせ情報を取得できませんでした",
                    "doping_check": "ド�?�ピング規制の確認ができませんでした",
                    "side_effects": "副作用�?報を取得できませんでした",
                    "consultation_advice": "お近くの登録販売�?にご相�?ください"
                }
        except json.JSONDecodeError as e:
            print(f"JSON解析エラー: {e}")
            return {
                "answer": result,
                "medicine_details": "詳細�?報を取得できませんでした",
                "interactions": "飲み合わせ情報を取得できませんでした",
                "doping_check": "ド�?�ピング規制の確認ができませんでした",
                "side_effects": "副作用�?報を取得できませんでした",
                "consultation_advice": "お近くの登録販売�?にご相�?ください"
            }
        
    except Exception as e:
        print(f"ChatGPT API呼び出しエラー: {e}")
        return {
            "answer": "申し訳ござ�?ません。シス�?�?エラーが発生しました。お近くの登録販売�?にご相�?ください�?",
            "medicine_details": "詳細�?報を取得できませんでした",
            "interactions": "飲み合わせ情報を取得できませんでした",
            "doping_check": "ド�?�ピング規制の確認ができませんでした",
            "side_effects": "副作用�?報を取得できませんでした",
            "consultation_advice": "お近くの登録販売�?にご相�?ください"
        } 