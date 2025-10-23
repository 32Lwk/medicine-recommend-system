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
                {"role": "system", "content": "あなたは薬剤師です。医薬品の使用上の注意を専門的で分かりやすく説明してください。特に年齢制限とドーピング禁止物質については詳細に説明してください。"},
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
    load_dotenv()
    print("dotenvを使用して.envファイルから環境変数を読み込みました。")
except ImportError:
    print("python-dotenvがインストールされていません。環境変数のみを使用します。")

# --- OpenAI APIキー設定 ---
# 環境変数からAPIキーを取得
api_key = os.getenv('OPENAI_API_KEY')

# 環境変数が設定されていない場合のエラー表示
if not api_key:
    print("⚠️ 警告: OpenAI API keyが環境変数に設定されていません。")
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
        "あなたは薬剤師AIです。以下は症状リストです。\n"
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
        f"あなたは薬剤師AIです。ユーザーの症状「{user_text}」に最も適した市販薬を3つ選び、理由も簡単に説明してください。(市販薬の重複は避けてください)\n\n"
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
        f"あなたは薬剤師AIです。ユーザーの症状:『{user_text}』\n"
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
        f"あなたは薬剤師AIです。下記は市販薬の効能効果リストです。\n"
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
        "口内炎", "目の疲れ", "耳鳴り", "動悸"
    ]
    
    # 症状抽出のプロンプトを改善
    prompt = f"""
あなたは薬剤師AIです。ユーザーの症状文から該当する症状を正確に抽出してください。

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
        {"role": "system", "content": "あなたは薬剤師AIです。ユーザーの症状文から正確に症状を抽出してください。"},
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
        "解熱鎮痛薬", "外用薬（皮膚）", "抗アレルギー薬", "殺虫剤", 
        "鼻炎用薬", "風邪薬", "目薬"
    ]
    
    # 症状リスト（包括的なリストを使用）
    symptoms_list = [
        "頭痛", "発熱", "咳", "鼻水", "鼻づまり", "のどの痛み", "くしゃみ", "寒気", "悪寒",
        "腹痛", "下痢", "便秘", "吐き気", "嘔吐", "胃痛", "胸やけ", "胃もたれ",
        "めまい", "疲労感", "倦怠感", "筋肉痛", "関節痛", "肩こり", "腰痛",
        "かゆみ", "発疹", "湿疹", "蕁麻疹", "皮膚の乾燥",
        "不眠", "眠気", "イライラ", "不安", "ストレス",
        "生理痛", "月経不順", "更年期症状",
        "口内炎", "目の疲れ", "耳鳴り", "動悸"
    ]
    
    prompt = f"""
あなたは薬剤師AIです。ユーザーの症状文を分析して、該当する症状と適する医薬品の種類を選択してください。

【ユーザーの症状文】
{user_text}

【選択可能な症状リスト】
{', '.join(symptoms_list)}

【医薬品の種類】
{', '.join(medicine_types)}

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
                {"role": "system", "content": "あなたは医薬品の専門家です。症状文を分析して適切な症状と医薬品の種類を選択してください。"},
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
    
    # 症状キーワードマッピング
    symptom_keywords = {
        "頭痛": ["頭痛", "頭が痛い", "ズキズキ", "偏頭痛"],
        "発熱": ["熱", "発熱", "熱っぽい", "高熱"],
        "のどの痛み": ["喉", "のど", "咽頭痛"],
        "咳": ["咳", "せき"],
        "鼻水": ["鼻水", "鼻みず", "鼻汁"],
        "鼻づまり": ["鼻づまり", "鼻詰まり"],
        "くしゃみ": ["くしゃみ", "クシャミ"],
        "生理痛": ["生理痛", "月経痛", "生理"],
        "胃痛": ["胃痛", "胃が痛い"],
        "吐き気": ["吐き気", "嘔吐"],
    }
    
    detected_symptoms = []
    for symptom, keywords in symptom_keywords.items():
        for keyword in keywords:
            if keyword in user_text:
                detected_symptoms.append(symptom)
                break
    
    # 医薬品種類の推定
    medicine_type = "その他"
    
    # 鼻炎用薬の判定（鼻症状のみで発熱・喉・咳がない場合）
    nose_symptoms = ["鼻水", "鼻づまり", "くしゃみ"]
    other_cold_symptoms = ["発熱", "のどの痛み", "咳"]
    
    if any(s in detected_symptoms for s in nose_symptoms):
        # 鼻症状のみで他の風邪症状がない場合は鼻炎用薬
        if not any(s in detected_symptoms for s in other_cold_symptoms):
            medicine_type = "鼻炎用薬"
        # 鼻症状+他の風邪症状がある場合は風邪薬
        else:
            medicine_type = "風邪薬"
    # 風邪薬の判定（鼻症状以外の風邪症状）
    elif any(s in detected_symptoms for s in other_cold_symptoms):
        medicine_type = "風邪薬"
    
    # 解熱鎮痛薬の判定
    elif any(s in detected_symptoms for s in ["頭痛", "生理痛"]):
        medicine_type = "解熱鎮痛薬"
    
    # 胃腸薬の判定
    elif any(s in detected_symptoms for s in ["胃痛", "吐き気"]):
        medicine_type = "胃腸薬"
    
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
"""

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "あなたは医薬品の専門家です。症状に適した医薬品を推奨し、使用上の注意を説明してください。"},
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
                'score': medicine_score  # スコアリング情報を追加
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
                'score': fallback_score  # スコアリング情報を追加
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
    
    # 推奨医薬品がない場合は登録販売者相談を推奨
    if not recommended_medicines:
        return {
            "answer": "申し訳ございません。推奨医薬品の情報がないため、具体的な回答ができません。お近くの登録販売者にご相談ください。",
            "medicine_details": "推奨医薬品の情報がありません",
            "interactions": "推奨医薬品の情報がありません",
            "doping_check": "推奨医薬品の情報がありません",
            "side_effects": "推奨医薬品の情報がありません",
            "consultation_advice": "お近くの登録販売者にご相談ください"
        }
    
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
あなたは薬剤師AIです。ユーザーの医薬品に関する質問に、推奨医薬品の情報を基に回答してください。

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
                {"role": "system", "content": "あなたは薬剤師AIです。医薬品の安全性と効果について正確な情報を提供してください。推奨医薬品の情報で回答できない質問については、お近くの登録販売者にご相談するよう推奨してください。"},
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