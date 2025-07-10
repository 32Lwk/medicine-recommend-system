import pandas as pd
from openai import OpenAI
import os

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

# 環境変数が設定されていない場合のフォールバック
if not api_key:
    # 直接APIキーを設定（開発・テスト用）
    api_key = "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"
    print("環境変数からAPIキーを取得できませんでした。直接設定されたAPIキーを使用します。")

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
encodings = ['utf-8', 'shift_jis', 'cp932', 'euc-jp']

for encoding in encodings:
    try:
        df = pd.read_csv("症状-薬.csv", encoding=encoding)
        print(f"CSVファイルを正常に読み込みました（エンコーディング: {encoding}）。")
        break
    except UnicodeDecodeError:
        print(f"エンコーディング {encoding} で読み込みに失敗しました。")
        continue
    except FileNotFoundError:
        print("エラー: 症状-薬.csvファイルが見つかりません。")
        print("ファイルが正しい場所にあることを確認してください。")
        break
    except Exception as e:
        print(f"CSVファイルの読み込みエラー: {e}")
        break

if df is None:
    print("すべてのエンコーディングでCSVファイルの読み込みに失敗しました。")

#ChatGPTを用いた症状に合う組み合わせの推定 (複数対応)
def match_symptom_pairs(symptom_text, df):
    if client is None:
        return ["APIキーが設定されていません。"] # Return as a list

    prompt_data = "\n".join(
        f"{row['部位']} - {row['症状']}" for _, row in df.iterrows()
    )

    messages = [
        {
            "role": "system",
            "content": (
                "以下は体の部位と関連する症状の対応です。\n"
                "ユーザーの症状文から、該当する症状をすべて日本語で返してください。\n"
                "見つからなければ「該当なし」とだけ返してください。\n"
                f"データ:\n{prompt_data}\n\n"
                "出力は「部位 - 症状」の形式でカンマで区切ってください。"
            )
        },
        {"role": "user", "content": f"症状: {symptom_text}"}
    ]

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0
        )
        result_str = response.choices[0].message.content
        if result_str:
            result_str = result_str.strip()
        else:
            result_str = "該当なし"
            
        if result_str == "該当なし":
            return [] # Return an empty list for no match
        elif "登録販売者に問い合わせください" in result_str: # Handle the previous "登録販売者に問い合わせください" case if it appears
             return ["登録販売者に問い合わせください"] # Return a specific list for this case
        else:
            # Split by comma and strip whitespace, returning a list
            # Further filter to ensure returned pairs are in the original data if necessary, though prompt tries to enforce this
            valid_pairs = set(df['部位'] + ' - ' + df['症状'])
            returned_pairs = [pair.strip() for pair in result_str.split(",") if pair.strip()]
            # Optional: Filter out pairs not exactly matching the CSV data
            # filtered_pairs = [pair for pair in returned_pairs if pair in valid_pairs]
            # if not filtered_pairs and returned_pairs: # If filtering removed everything but GPT returned something
            #     return ["該当なし"] # Treat as no valid match
            # return filtered_pairs
            return returned_pairs # Return all pairs returned by GPT based on the prompt instruction

    except Exception as e:
        print(f"An API error occurred during symptom matching: {e}")
        return ["APIエラー"] # Indicate an API error as a list


#薬の取得 (症状の組み合わせからDataFrameを検索)
def get_medicines(symptom_pair, df):
    # Find the row in the DataFrame that matches the symptom pair
    matched_row = df[(df['部位'] + ' - ' + df['症状']) == symptom_pair]

    if not matched_row.empty:
        # Get the first three medicine columns, filtering out NaNs
        medicines_list = [med for med in matched_row.iloc[0][['医薬品1', '医薬品2', '医薬品3']].dropna().tolist()]
        return medicines_list if medicines_list else ["該当する市販薬情報が見つかりませんでした。"]
    else:
        return ["該当する市販薬情報が見つかりませんでした。"]

#注意点の生成 (症状の組み合わせに基づきChatGPTに問い合わせ)
def generate_cautions(symptom_pair):
    if client is None:
        return "APIキーが設定されていません。" # Return an error message if client is not initialized

    if symptom_pair in ["該当なし", "APIエラー", "APIキーが設定されていません。", "登録販売者に問い合わせください"]:
        return ("申し訳ありませんが、入力された症状に合致する情報が見つかりませんでした。"
                "具体的な症状を詳しく教えていただくか、登録販売者にご相談ください。")


    messages = [
        {"role": "system", "content": (
            "あなたは日本の登録販売者AIです。\n"
            "以下の症状の組み合わせに対し、専門家として、以下の3点を具体的に、かつ分かりやすく記述してください。\n"
            "① 考えられる病気の候補（1〜2個）：登録販売者の視点から、可能性のある病名を挙げてください。\n"
            "② 使用上の一般的な注意点：市販薬を使う場合の一般的な注意や、日常生活でのケアについて簡潔に説明してください。\n"
            "③ 医師の受診が必要な場合：どのような症状が出たら、すぐに医師に相談すべきか、簡潔に兆候を明確に示してください。\n"
            "市販薬の具体的な商品名は含めないでください。専門用語は避け、一般の方にも理解できるように平易な言葉遣いを心がけてください。"
        )},
        {"role": "user", "content": f"症状の組み合わせ：{symptom_pair}"}
    ]
    try:
        res = client.chat.completions.create(model="gpt-4o", messages=messages)
        result_content = res.choices[0].message.content
        if result_content:
            return result_content.strip()
        else:
            return "注意点の生成中にエラーが発生しました。"
    except Exception as e:
        print(f"An API error occurred during caution generation: {e}")
        return "注意点の生成中にAPIエラーが発生しました。"


# --- 重複・飲み合わせ確認とアドバイス ---
# This function is designed to take a list of medicine names and provide advice
def check_combination_advice(all_medicine_list):
    if client is None:
        return "APIキーが設定されていないため、薬の選び方アドバイスを提供できません。"

    if not all_medicine_list:
        return "提案できる市販薬がありません。"

    prompt = (
        "あなたは日本の薬剤師または登録販売者AIです。\n"
        "以下の市販薬リストに含まれるすべての薬について、成分の重複や一般的な併用禁忌がないか詳細に判断してください。\n"
        "症状に対して適した医薬品候補群の中から一つだけ選んで服用し、成分が異なっていても、一つの症状から複数の医薬品を使うことは推奨しないでください\n"
        "もし症状をまたいで薬の成分に重複や併用注意がある場合(例:総合感冒薬＋解熱薬など)は具体的な成分名に言及し、どちらか一方を選ぶべきか、あるいはどのような症状に注意すべきかなど、実践的で具体的な判断基準やアドバイスを提供した上で、「登録販売者にお問い合わせください。」を加えてください。\n"
        "体力の低下などが見られる場合は必要に応じて食事療法や栄養ドリンクを進めるようにしてください。\n"
        "薬の名前だけでなく、なぜそのアドバイスが必要なのか、理由も簡潔に説明してください。\n"
        "個別の医薬品の説明どのよう主成分と効果のみ説明してください。\n"
        "症状に対しては○○が原因の場合という風に伝えてください。\n\n"
        "すべての内容は簡潔に伝えるようにしてください。\n\n\n"
        "リストに挙げられた薬全体として特に大きな問題がなければ、「症状ごとの医薬品の飲み合わせに特に問題ありません。ただし、体調に変化があった場合は専門家にご相談ください。」のように、安全に関する注意を添えて返してください。\n\n"
        f"市販薬リスト: {', '.join(all_medicine_list)}"
    )

    messages = [
        {"role": "system", "content": prompt}, # Use the detailed prompt as the system message
        {"role": "user", "content": f"以下の市販薬についてアドバイスをください: {', '.join(all_medicine_list)}"}
    ]

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.2
        )
        result_content = response.choices[0].message.content
        if result_content:
            return result_content.strip()
        else:
            return "薬の選び方アドバイスの生成中にエラーが発生しました。"
    except Exception as e:
        print(f"An API error occurred during combination check: {e}")
        return "薬の選び方アドバイスの生成中にAPIエラーが発生しました。"


def continue_conversation(symptom_pairs, question, all_medicine_list):
    if client is None:
        return "APIキーが設定されていないため、質問にお答えできません。"

    if not symptom_pairs or "APIエラー" in symptom_pairs or "APIキーが設定されていません。" in symptom_pairs or "登録販売者に問い合わせください" in symptom_pairs:
        return "診断された症状の組み合わせがない、またはエラーが発生したため、具体的な質問にお答えできません。再度症状を入力してください。"

    context_symptom = symptom_pairs[0] if len(symptom_pairs) == 1 else ", ".join(symptom_pairs)

    # プロンプトの組み立て
    prompt = (
        "あなたは日本の薬剤師または登録販売者AIです。\n"
        "医薬品や病気に関する質問にのみ解答するようにして、関係のない質問に関しては「病気や医薬品以外の質問には回答する事ができません。詳しくはお近くのスタッフにお問い合わせください」と返信してください。\n"
        "すべての質問に簡潔に解答し、最後には必ず「詳しくは登録販売者にお声掛けください」と付け加えてください。\n"
        "また、「体調に変化があった場合は専門家にご相談ください。」という注意書きを添えてください。\n"
        f"現在の症状の組み合わせ: {context_symptom}\n"
        f"市販薬リスト: {', '.join(all_medicine_list) if all_medicine_list else 'なし'}"
    )

    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": f"質問: {question}"}
    ]

    try:
        res = client.chat.completions.create(model="gpt-4o", messages=messages)
        result_content = res.choices[0].message.content
        if result_content:
            return result_content.strip()
        else:
            return "質問への回答中にエラーが発生しました。"
    except Exception as e:
        print(f"An API error occurred during conversation: {e}")
        return "質問への回答中にAPIエラーが発生しました。"

# --- 実行ブロック ---
# Initialize symptom_pairs to an empty list before the loop
symptom_pairs = []
all_suggested_medicines = []

if df is not None:
    symptom = input("症状を入力してください（例：喉が痛くて熱がある）\n> ")

    # --- 診断 ---
    symptom_pairs = match_symptom_pairs(symptom, df)

    if not symptom_pairs or "APIエラー" in symptom_pairs or "APIキーが設定されていません。" in symptom_pairs or "登録販売者に問い合わせください" in symptom_pairs:
        print("\n❗", ", ".join(symptom_pairs) if symptom_pairs else "該当する症状の組み合わせが見つかりませんでした。")
        # Provide a general caution if no specific pair is found or an error occurred
        print(generate_cautions(symptom_pairs[0] if symptom_pairs else "該当なし")) # Pass first element or "該当なし"
    else:
        print("\n✅ 推定された症状の組み合わせ:", ", ".join(symptom_pairs))

        print("\n💊 市販薬候補と注意点:")
        for pair in symptom_pairs:
            print(f"\n--- {pair} ---")
            medicine_list = get_medicines(pair, df)
            print(f"市販薬候補: {', '.join(medicine_list)}")
            all_suggested_medicines.extend([med for med in medicine_list if med != "該当する市販薬情報が見つかりませんでした。"])

            cautions = generate_cautions(pair)
            print(f"注意点:\n{cautions}")

        # 成分の重複・組み合わせアドバイス (すべての候補薬を考慮)
        print("\n🤖 薬の選び方全体アドバイス:")
        print("\n症状に対して適した医薬品候補群の中から一つだけ選んで服用してください。")
        print("\n不明点がありましたら、お気軽に登録販売者にお問い合わせください。")
        print(check_combination_advice(all_suggested_medicines))

    while True:
        follow = input("\nご質問があれば入力してください（終了するには '終了'）\n> ")
        if follow == "終了":
            print("ご利用ありがとうございました。")
            break
        else:
            # Pass the list of symptom pairs to the conversation function
            print(continue_conversation(symptom_pairs, follow, all_suggested_medicines))
else:
    print("\nエラー: CSVファイルが読み込めませんでした。プログラムを終了します。")