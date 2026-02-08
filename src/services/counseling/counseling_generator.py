"""
カウンセリング返信の生成
"""
import logging
from typing import Dict, List
from openai import OpenAI

from src.services.counseling.counseling_templates import generate_illegal_drug_rejection_message
from src.services.counseling.counseling_logger import log_counseling_response
from src.services.counseling.counseling_prompts import get_counseling_prompt_template
from src.services.counseling.counseling_format import format_conversation_history
from src.services.counseling_triage import detect_app_specification_question

logger = logging.getLogger(__name__)

def generate_counseling_response(
    symptom_type: str,
    user_text: str,
    client: OpenAI,
    conversation_history: List[Dict] = None,
    session_id: str = None
) -> str:
    """
    カウンセリング的返信を生成
    
    Args:
        symptom_type: 感情的症状タイプまたは不適切な要求タイプ
        user_text: ユーザーの入力テキスト
        client: OpenAIクライアントインスタンス
        conversation_history: 会話履歴（直近10件まで使用）
        session_id: セッションID（ログ記録用）
    
    Returns:
        カウンセリング的返信テキスト
    """
    # 違法薬物・規制薬物の場合は、テンプレートベースのメッセージを返す
    if symptom_type.startswith("inappropriate_request/"):
        request_type = symptom_type.split("/")[1]
        if request_type in ["illegal", "controlled"]:
            return generate_illegal_drug_rejection_message(request_type)
        
        # 緊急避妊薬に関する質問を検出（処方薬の要求の場合）
        if request_type == "prescription":
            # 性被害の検出
            sexual_assault_keywords = [
                "レイプ", "れいぷ", "rape", "強姦", "ごうかん", "性被害", "せいひがい", 
                "性的被害", "せいてきひがい", "性暴力", "せいぼうりょく", "性的暴力", "せいてきぼうりょく"
            ]
            
            user_text_lower = user_text.lower()
            is_sexual_assault = any(keyword.lower() in user_text_lower for keyword in sexual_assault_keywords)
            
            emergency_contraception_keywords = [
                "アフターピル", "あふたーぴる", "afterpill", "after pill",
                "ノルレボ", "のるれぼ", "norlevo",
                "レボノルゲストレル", "れぼのるげすとれる", "levonorgestrel",
                "緊急避妊", "きんきゅうひにん", "緊急避妊薬", "きんきゅうひにんやく",
                "緊急避妊ピル", "きんきゅうひにんぴる",
                "避妊に失敗", "ひにんにしっぱい", "避妊失敗", "ひにんしっぱい",
                "避妊できません", "ひにんできません", "避妊できなかった", "ひにんできなかった",
                "避妊出来なかった", "ひにんできなかった", "避妊出来ません", "ひにんできません",
                "コンドームが破れ", "こんどむが破れ", "コンドーム破れ", "こんどむ破れ",
                "コンドームが破れた", "こんどむが破れた", "コンドーム破れた", "こんどむ破れた"
            ]
            
            is_emergency_contraception = any(keyword.lower() in user_text_lower for keyword in emergency_contraception_keywords)
            
            if is_sexual_assault:
                # 性被害の場合の専用プロンプト
                history_text = ""
                if conversation_history:
                    try:
                        recent_history = conversation_history[-5:]
                        history_lines = []
                        for msg in recent_history:
                            role = msg.get('type', 'unknown')
                            content = msg.get('content', '')
                            if role == 'user':
                                history_lines.append(f"ユーザー: {content}")
                            elif role == 'bot':
                                history_lines.append(f"アシスタント: {content}")
                        history_text = "\n".join(history_lines)
                    except Exception:
                        history_text = ""
                
                sexual_assault_prompt = f"""
あなたは医薬品相談AIアシスタントです。性被害を受けた方に対して、親身で適切な情報とサポートを提供してください。

【ユーザーの状況】
{user_text}

【会話履歴】
{history_text if history_text else "（会話履歴がありません）"}

【性被害を受けた方への重要な情報】

1. **緊急避妊薬（アフターピル）について**
   - 性行為から72時間（3日）以内に服用することで、高い確率で妊娠を避けることが期待できます
   - できるだけ早く服用することが効果的です
   - 日本で認可されている緊急避妊薬は「ノルレボ」「レボノルゲストレル」で、性行為から72時間以内に1錠服用します
   - 必ず医療機関で発行される処方箋が必要です

2. **医療機関への相談**
   - 産婦人科を受診し、緊急避妊薬の処方を受けることができます
   - 性感染症の検査も受けることをお勧めします
   - 2019年より、オンライン診療も可能です（産婦人科医または必要な研修を受けた医師が初診からオンライン診療を行うことができます）

3. **心理的サポート**
   - 性暴力被害者支援センターや相談窓口があります
   - 一人で抱え込まず、信頼できる人や専門家に相談することが大切です

4. **警察への相談**
   - 希望する場合は、警察への相談も可能です
   - 証拠保全のため、できるだけ早く相談することが重要です

5. **その他の支援**
   - 性暴力被害者支援センター（全国共通ダイヤル：#8103）
   - 各都道府県の相談窓口

【返信の要件】
- **親身で共感的なトーン**: ユーザーの状況に寄り添い、理解を示す（1-2文）
- **時間の重要性を強調**: 72時間以内の緊急避妊薬の服用の重要性を説明
- **医療機関への相談を促す**: 産婦人科への相談を案内し、性感染症の検査も受けることを推奨
- **心理的サポートの案内**: 性暴力被害者支援センターなどの相談窓口を案内
- **警察への相談の案内**: 希望する場合は警察への相談も可能であることを伝える
- **システムの制限の説明**: 当システムは市販薬（OTC医薬品）の相談を承っており、処方薬の処方はできないことを説明
- **安心感を与える**: ユーザーが適切な支援を受けられるよう、親身にサポートする
- **応答長さ**: 400-500文字程度（重要な情報を含めるため、やや長めでも可）
- **マークダウン記号の使用禁止**: **や*などのマークダウン記号は使用せず、通常のテキストで返信してください

【返信を生成してください】
"""
                try:
                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": "あなたは医薬品相談AIアシスタントです。性被害を受けた方に対して、親身で適切な情報とサポートを提供してください。"},
                            {"role": "user", "content": sexual_assault_prompt}
                        ],
                        temperature=0.7,
                        max_tokens=600
                    )
                    # マークダウン記号を削除
                    response_text = response.choices[0].message.content.strip()
                    response_text = response_text.replace('**', '').replace('*', '').replace('__', '').replace('_', '')
                    return response_text
                except Exception as e:
                    logger.error(f"性被害応答生成エラー: {e}")
                    # フォールバック: 一般的な処方薬の応答を返す（後続処理で実行される）
            elif is_emergency_contraception:
                # 緊急避妊薬専用のプロンプトを使用
                history_text = ""
                if conversation_history:
                    # format_conversation_historyは同じファイル内にあるため、直接呼び出し
                    # 関数が定義される前に呼び出される可能性があるため、後で定義を確認
                    try:
                        recent_history = conversation_history[-5:]
                        history_lines = []
                        for msg in recent_history:
                            role = msg.get('type', 'unknown')
                            content = msg.get('content', '')
                            if role == 'user':
                                history_lines.append(f"ユーザー: {content}")
                            elif role == 'bot':
                                history_lines.append(f"アシスタント: {content}")
                        history_text = "\n".join(history_lines)
                    except Exception:
                        history_text = ""
                
                emergency_contraception_prompt = f"""
あなたは医薬品相談AIアシスタントです。緊急避妊薬に関する質問に対して、親身で適切な情報を提供してください。

【ユーザーの質問】
{user_text}

【会話履歴】
{history_text if history_text else "（会話履歴がありません）"}

【緊急避妊薬に関する重要な情報】
- **名称**: アフターピル、緊急避妊ピルとも呼ばれます
- **目的**: 望まない妊娠の可能性がある場合（性行為や性被害など）に使用
- **有効性**: 性行為から72時間（3日）以内に服用することで、高い確率で妊娠を避けることが期待できます
- **効果**: 主に排卵を遅らせるなどの作用により緊急的に妊娠の成立を防ぎます
- **時間の重要性**: 性交からできるだけ早く服用することが効果的で、早く服用した方が効果が高いことがわかっています。72時間を超えてから服用すると効果は大きく落ちますが、効果が全く得られないわけではありません
- **認可されている薬**: 日本で認可されている緊急避妊薬は「ノルレボ」「レボノルゲストレル（ノルレボのジェネリック医薬品）」で、性行為から72時間以内に1錠服用します

【取得方法】
緊急避妊薬は必ず医療機関で発行される処方箋が必要です。以下の2つの方法があります：

1. **対面診療**
   - 産婦人科及び必要な研修を受けた医師に診察を受ける
   - 処方箋原本を薬局に持参
   - 薬局で必要な研修を受けた薬剤師との対面服用（処方は1錠のみ）

2. **オンライン診療（緊急避妊に関するオンライン診療）**
   - 2019年より、産婦人科医又は厚生労働省が指定する研修を受講した医師が、初診からオンライン診療を行うことができるようになりました
   - 産婦人科及び必要な研修を受けた医師に診察を受ける
   - 医療機関から薬局へ処方箋情報の送付・情報提供
   - 薬局において、必要な研修を受けた薬剤師との対面服用（処方は1錠のみ）
   - 薬局から処方医へ、服用したことを情報提供

**重要**: いずれの場合も、3週間後に産婦人科医による対面診療を受けてください。

【返信の要件】
- **親身で共感的なトーン**: ユーザーの状況に寄り添い、理解を示す（1-2文）
- **時間の重要性を強調**: 72時間以内の服用の重要性、できるだけ早く服用することが効果的であることを説明
- **具体的な取得方法の案内**: 対面診療とオンライン診療の両方の選択肢を説明
- **システムの制限の説明**: 当システムは市販薬（OTC医薬品）の相談を承っており、処方薬の処方はできないことを説明
- **専門家への相談を促す**: 産婦人科医への相談を案内し、3週間後の対面診療の重要性も伝える
- **安心感を与える**: ユーザーが適切な医療機関にアクセスできるよう、親身にサポートする
- **応答長さ**: 300-400文字程度（重要な情報を含めるため、やや長めでも可）
- **マークダウン記号の使用禁止**: **や*などのマークダウン記号は使用せず、通常のテキストで返信してください

【返信を生成してください】
"""
                try:
                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": "あなたは医薬品相談AIアシスタントです。緊急避妊薬に関する質問に対して、親身で適切な情報を提供してください。"},
                            {"role": "user", "content": emergency_contraception_prompt}
                        ],
                        temperature=0.7,
                        max_tokens=500
                    )
                    # マークダウン記号を削除
                    response_text = response.choices[0].message.content.strip()
                    response_text = response_text.replace('**', '').replace('*', '').replace('__', '').replace('_', '')
                    return response_text
                except Exception as e:
                    logger.error(f"緊急避妊薬応答生成エラー: {e}")
                    # フォールバック: 一般的な処方薬の応答を返す（後続処理で実行される）
    
    # 緊急避妊薬に関する質問を検出（general_otherまたはinappropriate_request/unknownの場合も）
    # 性被害の検出
    sexual_assault_keywords = [
        "レイプ", "れいぷ", "rape", "強姦", "ごうかん", "性被害", "せいひがい", 
        "性的被害", "せいてきひがい", "性暴力", "せいぼうりょく", "性的暴力", "せいてきぼうりょく"
    ]
    
    user_text_lower = user_text.lower()
    is_sexual_assault_general = any(keyword.lower() in user_text_lower for keyword in sexual_assault_keywords)
    
    emergency_contraception_keywords = [
        "アフターピル", "あふたーぴる", "afterpill", "after pill",
        "ノルレボ", "のるれぼ", "norlevo",
        "レボノルゲストレル", "れぼのるげすとれる", "levonorgestrel",
        "緊急避妊", "きんきゅうひにん", "緊急避妊薬", "きんきゅうひにんやく",
        "緊急避妊ピル", "きんきゅうひにんぴる",
        "避妊に失敗", "ひにんにしっぱい", "避妊失敗", "ひにんしっぱい",
        "避妊できません", "ひにんできません", "避妊できなかった", "ひにんできなかった",
        "避妊出来なかった", "ひにんできなかった", "避妊出来ません", "ひにんできません",
        "コンドームが破れ", "こんどむが破れ", "コンドーム破れ", "こんどむ破れ",
        "コンドームが破れた", "こんどむが破れた", "コンドーム破れた", "こんどむ破れた"
    ]
    
    is_emergency_contraception_general = any(keyword.lower() in user_text_lower for keyword in emergency_contraception_keywords)
    
    # general_otherまたはinappropriate_request/unknownの場合に性被害または緊急避妊薬の質問をチェック
    if (symptom_type == "general_other" or symptom_type == "inappropriate_request/unknown") and (is_sexual_assault_general or is_emergency_contraception_general):
        if is_sexual_assault_general:
            # 性被害の場合の専用プロンプト
            history_text = ""
            if conversation_history:
                try:
                    recent_history = conversation_history[-5:]
                    history_lines = []
                    for msg in recent_history:
                        role = msg.get('type', 'unknown')
                        content = msg.get('content', '')
                        if role == 'user':
                            history_lines.append(f"ユーザー: {content}")
                        elif role == 'bot':
                            history_lines.append(f"アシスタント: {content}")
                    history_text = "\n".join(history_lines)
                except Exception:
                    history_text = ""
            
            sexual_assault_prompt = f"""
あなたは医薬品相談AIアシスタントです。性被害を受けた方に対して、親身で適切な情報とサポートを提供してください。

【ユーザーの状況】
{user_text}

【会話履歴】
{history_text if history_text else "（会話履歴がありません）"}

【性被害を受けた方への重要な情報】

1. **緊急避妊薬（アフターピル）について**
   - 性行為から72時間（3日）以内に服用することで、高い確率で妊娠を避けることが期待できます
   - できるだけ早く服用することが効果的です
   - 日本で認可されている緊急避妊薬は「ノルレボ」「レボノルゲストレル」で、性行為から72時間以内に1錠服用します
   - 必ず医療機関で発行される処方箋が必要です

2. **医療機関への相談**
   - 産婦人科を受診し、緊急避妊薬の処方を受けることができます
   - 性感染症の検査も受けることをお勧めします
   - 2019年より、オンライン診療も可能です（産婦人科医または必要な研修を受けた医師が初診からオンライン診療を行うことができます）

3. **心理的サポート**
   - 性暴力被害者支援センターや相談窓口があります
   - 一人で抱え込まず、信頼できる人や専門家に相談することが大切です

4. **警察への相談**
   - 希望する場合は、警察への相談も可能です
   - 証拠保全のため、できるだけ早く相談することが重要です

5. **その他の支援**
   - 性暴力被害者支援センター（全国共通ダイヤル：#8103）
   - 各都道府県の相談窓口

【返信の要件】
- **親身で共感的なトーン**: ユーザーの状況に寄り添い、理解を示す（1-2文）
- **時間の重要性を強調**: 72時間以内の緊急避妊薬の服用の重要性を説明
- **医療機関への相談を促す**: 産婦人科への相談を案内し、性感染症の検査も受けることを推奨
- **心理的サポートの案内**: 性暴力被害者支援センターなどの相談窓口を案内
- **警察への相談の案内**: 希望する場合は警察への相談も可能であることを伝える
- **システムの制限の説明**: 当システムは市販薬（OTC医薬品）の相談を承っており、処方薬の処方はできないことを説明
- **安心感を与える**: ユーザーが適切な支援を受けられるよう、親身にサポートする
- **応答長さ**: 400-500文字程度（重要な情報を含めるため、やや長めでも可）
- **マークダウン記号の使用禁止**: **や*などのマークダウン記号は使用せず、通常のテキストで返信してください

【返信を生成してください】
"""
            try:
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "あなたは医薬品相談AIアシスタントです。性被害を受けた方に対して、親身で適切な情報とサポートを提供してください。"},
                        {"role": "user", "content": sexual_assault_prompt}
                    ],
                    temperature=0.7,
                    max_tokens=600
                )
                # マークダウン記号を削除
                response_text = response.choices[0].message.content.strip()
                response_text = response_text.replace('**', '').replace('*', '').replace('__', '').replace('_', '')
                return response_text
            except Exception as e:
                logger.error(f"性被害応答生成エラー: {e}")
                # フォールバック: 一般的な応答を返す（後続処理で実行される）
        elif is_emergency_contraception_general:
            # 緊急避妊薬専用のプロンプトを使用
            history_text = ""
            if conversation_history:
                try:
                    recent_history = conversation_history[-5:]
                    history_lines = []
                    for msg in recent_history:
                        role = msg.get('type', 'unknown')
                        content = msg.get('content', '')
                        if role == 'user':
                            history_lines.append(f"ユーザー: {content}")
                        elif role == 'bot':
                            history_lines.append(f"アシスタント: {content}")
                    history_text = "\n".join(history_lines)
                except Exception:
                    history_text = ""
            
            emergency_contraception_prompt = f"""
あなたは医薬品相談AIアシスタントです。緊急避妊薬に関する質問に対して、親身で適切な情報を提供してください。

【ユーザーの質問】
{user_text}

【会話履歴】
{history_text if history_text else "（会話履歴がありません）"}

【緊急避妊薬に関する重要な情報】
- **名称**: アフターピル、緊急避妊ピルとも呼ばれます
- **目的**: 望まない妊娠の可能性がある場合（性行為や性被害など）に使用
- **有効性**: 性行為から72時間（3日）以内に服用することで、高い確率で妊娠を避けることが期待できます
- **効果**: 主に排卵を遅らせるなどの作用により緊急的に妊娠の成立を防ぎます
- **時間の重要性**: 性交からできるだけ早く服用することが効果的で、早く服用した方が効果が高いことがわかっています。72時間を超えてから服用すると効果は大きく落ちますが、効果が全く得られないわけではありません
- **認可されている薬**: 日本で認可されている緊急避妊薬は「ノルレボ」「レボノルゲストレル（ノルレボのジェネリック医薬品）」で、性行為から72時間以内に1錠服用します

【取得方法】
緊急避妊薬は必ず医療機関で発行される処方箋が必要です。以下の2つの方法があります：

1. **対面診療**
   - 産婦人科及び必要な研修を受けた医師に診察を受ける
   - 処方箋原本を薬局に持参
   - 薬局で必要な研修を受けた薬剤師との対面服用（処方は1錠のみ）

2. **オンライン診療（緊急避妊に関するオンライン診療）**
   - 2019年より、産婦人科医又は厚生労働省が指定する研修を受講した医師が、初診からオンライン診療を行うことができるようになりました
   - 産婦人科及び必要な研修を受けた医師に診察を受ける
   - 医療機関から薬局へ処方箋情報の送付・情報提供
   - 薬局において、必要な研修を受けた薬剤師との対面服用（処方は1錠のみ）
   - 薬局から処方医へ、服用したことを情報提供

**重要**: いずれの場合も、3週間後に産婦人科医による対面診療を受けてください。

【返信の要件】
- **親身で共感的なトーン**: ユーザーの状況に寄り添い、理解を示す（1-2文）
- **時間の重要性を強調**: 72時間以内の服用の重要性、できるだけ早く服用することが効果的であることを説明
- **具体的な取得方法の案内**: 対面診療とオンライン診療の両方の選択肢を説明
- **システムの制限の説明**: 当システムは市販薬（OTC医薬品）の相談を承っており、処方薬の処方はできないことを説明
- **専門家への相談を促す**: 産婦人科医への相談を案内し、3週間後の対面診療の重要性も伝える
- **安心感を与える**: ユーザーが適切な医療機関にアクセスできるよう、親身にサポートする
- **応答長さ**: 300-400文字程度（重要な情報を含めるため、やや長めでも可）
- **マークダウン記号の使用禁止**: **や*などのマークダウン記号は使用せず、通常のテキストで返信してください

【返信を生成してください】
"""
            try:
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "あなたは医薬品相談AIアシスタントです。緊急避妊薬に関する質問に対して、親身で適切な情報を提供してください。"},
                        {"role": "user", "content": emergency_contraception_prompt}
                    ],
                    temperature=0.7,
                    max_tokens=500
                )
                # マークダウン記号を削除
                response_text = response.choices[0].message.content.strip()
                response_text = response_text.replace('**', '').replace('*', '').replace('__', '').replace('_', '')
                return response_text
            except Exception as e:
                logger.error(f"緊急避妊薬応答生成エラー: {e}")
                # フォールバック: 一般的な応答を返す（後続処理で実行される）
    
    # アプリケーションの技術仕様に関する質問を検出
    # general_otherまたはinappropriate_request/unknownの場合に技術仕様質問をチェック
    if (symptom_type == "general_other" or symptom_type == "inappropriate_request/unknown") and detect_app_specification_question(user_text):
        # アプリケーションの技術仕様に関する質問に特化したプロンプトを使用
        app_spec_prompt = f"""
あなたは医薬品相談AIアシスタントです。ユーザーからのアプリケーションの技術仕様や対応内容に関する質問に対して、正確で分かりやすい説明を提供してください。

【ユーザーの質問】
{user_text}

【アプリケーションの基本情報】
- 名称: チャット型医薬品相談ツール（β版）
- 目的: 症状に基づいて一般用医薬品（OTC薬）をチャット形式で安全かつ柔軟に提案
- 対象: 企業・行政関係者・薬剤師・登録販売者など、限られた専門関係者（β版）

【主な機能】
1. 自然なチャット形式での相談
2. AI × 薬学知識による安全性の担保
3. 受診勧奨システムの導入
4. 多言語・多環境対応（日本語・英語・中国語・韓国語）
5. データの安全管理

【技術仕様】
- バックエンド: Python 3.9+, Flask 3.0.0, Jinja2
- AI/NLP: OpenAI GPT-4o-mini, ルールベースNLU（ハイブリッド推奨システム）
- 翻訳API: DeepL API（多言語対応：日本語・英語・中国語・韓国語、高速翻訳）
- データベース: PostgreSQL（フィードバック永続化・セッション管理・マルチインスタンス対応）
- データ処理: Pandas 2.2.3, NumPy
- フロントエンド: HTML5, CSS3, JavaScript（ES6+）、バニラJavaScript（フレームワーク不使用）、レスポンシブデザイン
- デプロイ環境: Render（本番環境）、Gunicorn（WSGIサーバー）
- 監視・ログ: psutil, JSONL形式記録（構造化ログ）、アクセス分析、パフォーマンス監視
- バージョン管理: Git（GitHub）

【独自のアルゴリズム】
本アプリの心臓部となる「医薬品選定アルゴリズム」は、大規模言語モデルによる柔軟な言語理解と、薬効・禁忌・ユーザー属性情報・症状などの要素を統合的に評価する独自のアルゴリズムで構成されています。これにより、単なるAI応答ではなく、根拠に基づいた薬選びを実現しています。

【対応内容】
- 一般用医薬品（OTC薬）の相談・推奨
- 症状に基づいた医薬品選定
- 医薬品の相互作用チェック
- アレルギー対応
- 受診勧奨（重篤な症状が疑われる場合）
- 多言語対応（日本語・英語・中国語・韓国語）

【対応できない内容】
- 処方薬の推奨・処方
- 診断・治療行為
- 違法薬物・規制薬物に関する相談
- 重篤な疾患の完治・予防を目的とした薬の要求

【返信の要件】
- **正確性**: アプリケーションの技術仕様や対応内容について、正確な情報を提供してください
- **分かりやすさ**: 専門用語を使う場合は、分かりやすく説明してください
- **簡潔さ**: 200-300文字程度で簡潔に説明してください
- **丁寧さ**: ユーザーの質問に対して、丁寧に回答してください

【返信を生成してください】
"""
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "あなたは医薬品相談AIアシスタントです。アプリケーションの技術仕様や対応内容に関する質問に対して、正確で分かりやすい説明を提供してください。"},
                    {"role": "user", "content": app_spec_prompt}
                ],
                temperature=0.7,
                max_tokens=400
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"アプリケーション仕様質問応答生成エラー: {e}")
            return "申し訳ございませんが、システムエラーが発生しました。アプリケーションの技術仕様については、右上のℹ️ボタンから「アプリ概要・運営者情報」をご確認ください。"
    
    # プロンプトテンプレートを取得
    template = get_counseling_prompt_template(symptom_type)
    
    # 会話履歴の準備（直近10件）
    history_context = ""
    if conversation_history:
        recent_history = conversation_history[-10:]  # 直近10件
        history_text = format_conversation_history(recent_history)
        if history_text.strip():
            history_context = f"""
    
    【会話履歴（文脈理解のため）】
    {history_text}
    """
    
    prompt = template["user_prompt_template"].format(
        history_context=history_context,
        user_text=user_text,
        symptom_type=symptom_type
    )
    
    max_length = template.get("max_length", 200)
    
    try:
        # 不眠と眠気の場合は長めの応答を許可（max_tokensを増やす）
        max_tokens_value = max_length * 2 if symptom_type in ["insomnia", "drowsiness"] else max_length
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": f"{template['system_message']} 返信は{max_length}文字以内に収めてください。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=max_tokens_value
        )
        
        response_text = response.choices[0].message.content.strip()
        
        # 不眠の場合、カウンセリング応答から「一時的な不眠で推奨される医薬品を知りたい場合は教えて下さい」を削除
        # （別途app.pyで送信されるため）
        if symptom_type == "insomnia":
            # 切り替え案内のメッセージを削除
            switch_patterns = [
                "一時的な不眠で推奨される医薬品を知りたい場合は教えて下さい",
                "一時的な不眠で推奨される医薬品を知りたい場合は教えてください",
                "医薬品を知りたい場合は教えて下さい",
                "医薬品を知りたい場合は教えてください"
            ]
            for pattern in switch_patterns:
                if pattern in response_text:
                    # パターンを含む行を削除
                    lines = response_text.split('\n')
                    response_text = '\n'.join([line for line in lines if pattern not in line])
                    break
        
        # 文字数制限を超える場合は切り詰める（不眠と眠気の場合は400文字まで許可）
        if len(response_text) > max_length:
            # 文の途中で切らないように、最後の文を削除
            if symptom_type in ["insomnia", "drowsiness"] and max_length >= 300:
                # 不眠と眠気の場合は、文の区切りで切る
                sentences = response_text.split('。')
                trimmed_text = ""
                for sentence in sentences:
                    if len(trimmed_text) + len(sentence) + 1 <= max_length:
                        trimmed_text += sentence + "。"
                    else:
                        break
                # 最後の「。」が重複しないように調整
                if trimmed_text.endswith("。。"):
                    trimmed_text = trimmed_text[:-1]
                response_text = trimmed_text
            else:
                response_text = response_text[:max_length] + "..."
        
        # ログ記録（通常時は会話履歴なし）
        if session_id:
            log_counseling_response(
                session_id=session_id,
                response_content=response_text,
                response_type="counseling_response",
                category=None,
                confidence=None,
                counseling_mode=None,
                user_input=user_text,
                conversation_history=None
            )
        
        return response_text
    except Exception as e:
        logger.error(f"カウンセリング返信生成エラー: {e}")
        # エラーメッセージも症状タイプに応じて変更
        if symptom_type == "insomnia":
            error_response = """不眠でお悩みですね。お気持ちお察しします。

【代替療法の推奨】
- ハーブティー（カモミール、バレリアンなど）を就寝前に飲む
- ラベンダーのアロマオイルを枕元に置く、またはアロマディフューザーを使用
- 軽いストレッチや深呼吸を行う
- リラックスできる音楽を聴く
- 睡眠環境の改善（室温、照明、騒音対策など）

【薬について】
睡眠改善薬は一時的な不眠にのみ効果があり、常用化のリスクがあります。不眠症と診断されている場合は医師にご相談ください。

一時的な不眠で、推奨される医薬品を知りたい場合は教えて下さい。"""
        else:
            MEDICAL_SYMPTOM_TYPES = {'heart_pain', 'anxiety', 'depression_like'}
            if symptom_type in MEDICAL_SYMPTOM_TYPES:
                error_response = "お気持ちをお聞かせいただき、ありがとうございます。詳しくお話を伺いたいので、もう少し詳しく教えていただけますか？"
            else:
                error_response = "お気持ちをお聞かせいただき、ありがとうございます。応援しています。"
        
        # エラー時もログ記録を試みる
        if session_id:
            try:
                log_counseling_response(
                    session_id=session_id,
                    response_content=error_response,
                    response_type="counseling_response_error",
                    category=None,
                    confidence=None,
                    counseling_mode=None,
                    user_input=user_text,
                    conversation_history=conversation_history if 'conversation_history' in locals() else None
                )
            except:
                pass
        
        return error_response


def personalize_response(
    response: str,
    user_name: str = None,
    conversation_history: List[Dict] = None
) -> str:
    """
    応援メッセージをパーソナライズ
    
    - ユーザー名がある場合、名前を使用
    - 会話履歴からユーザーの状況を参照
    - 自然なパーソナライズ（過度にならないように）
    
    Args:
        response: 元の応援メッセージ
        user_name: ユーザー名（オプション）
        conversation_history: 会話履歴（オプション）
    
    Returns:
        パーソナライズされた応援メッセージ
    """
    # ユーザー名がある場合、自然に名前を使用
    if user_name and user_name != 'Unknown':
        # メッセージの最初に名前を追加（自然な形で）
        if not response.startswith(user_name):
            # 「[名前]さん、」のような形で追加
            response = f"{user_name}さん、{response}"
    
    # 会話履歴から状況を参照してパーソナライズ（簡易版）
    # より高度なパーソナライズが必要な場合は、LLMを使用
    if conversation_history:
        # 会話履歴から特定の状況を検出してパーソナライズ
        # 例: 恋愛関連の話題がある場合、それに合わせた表現を使用
        pass
    
    return response
