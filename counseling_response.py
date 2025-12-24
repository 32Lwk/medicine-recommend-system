"""
カウンセリング的返信モジュール
感情的症状に対するカウンセリング的返信とフォローアップ質問を生成
"""

import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional
from openai import OpenAI

logger = logging.getLogger(__name__)


def log_counseling_response(
    session_id: str,
    response_content: str,
    response_type: str,
    category: str = None,
    confidence: float = None,
    counseling_mode: Dict = None
) -> None:
    """
    カウンセリング返信をログに記録
    
    Args:
        session_id: セッションID
        response_content: 返信内容
        response_type: 返信タイプ（counseling_question, counseling_summary, counseling_response等）
        category: トリアージカテゴリ（オプション）
        confidence: トリアージconfidence（オプション）
        counseling_mode: カウンセリングモード状態（オプション）
    """
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "session_id": session_id,
        "response_type": response_type,
        "response_content": response_content[:200] + "..." if len(response_content) > 200 else response_content,
        "response_length": len(response_content)
    }
    
    if category is not None:
        log_entry["category"] = category
    if confidence is not None:
        log_entry["confidence"] = confidence
    if counseling_mode:
        log_entry["counseling_mode"] = {
            "symptom_type": counseling_mode.get('symptom_type'),
            "active": counseling_mode.get('active'),
            "question_count": len(counseling_mode.get('question_history', [])),
            "collected_info_count": len(counseling_mode.get('collected_info', {}))
        }
    
    # ログディレクトリの作成
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'log')
    os.makedirs(log_dir, exist_ok=True)
    
    # ログファイルに保存
    log_file = os.path.join(log_dir, 'counseling_responses.jsonl')
    try:
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
        logger.info(f"📝 カウンセリング返信ログ記録: {response_type} (session_id: {session_id})")
    except Exception as e:
        logger.error(f"❌ カウンセリング返信ログ記録エラー: {e}")


def detect_emotional_symptom_type(user_text: str, triage_result: Dict) -> str:
    """
    感情的症状のタイプを判定
    
    Args:
        user_text: ユーザーの入力テキスト
        triage_result: トリアージ結果
    
    Returns:
        感情的症状タイプ（"heart_pain", "anxiety", "romantic_concern", "stress", "depression_like", "insomnia"）
    """
    subcategory = triage_result.get("subcategory", "").lower()
    user_text_lower = user_text.lower()
    
    # 不眠の検出（最優先）
    insomnia_keywords = [
        "不眠", "眠れない", "睡眠不足", "寝つきが悪い", "眠れません", "眠れないです", 
        "眠れない", "睡眠", "夜眠れない", "最近眠れない", "最近眠れません", "夜眠れません",
        "寝れない", "寝れません", "寝れないです", "夜寝れない", "最近寝れない",
        "眠れなくて", "眠れなく", "寝つけない", "寝つけません", "寝つけないです",
        "不眠症", "不眠で", "不眠です", "不眠の", "不眠が"
    ]
    if any(keyword in user_text_lower for keyword in insomnia_keywords):
        return "insomnia"
    
    if "heart" in subcategory or "心" in user_text:
        return "heart_pain"
    elif "anxiety" in subcategory or "緊張" in user_text or "不安" in user_text:
        return "anxiety"
    elif "romantic" in subcategory or "恋" in user_text:
        return "romantic_concern"
    elif "stress" in subcategory or "ストレス" in user_text:
        return "stress"
    else:
        return "general_emotional"


def get_counseling_prompt_template(symptom_type: str) -> Dict[str, str]:
    """
    症状タイプに応じたプロンプトテンプレートを取得
    
    Returns:
        {
            "system_message": str,
            "user_prompt_template": str,
            "response_requirements": str,
            "max_length": int
        }
    """
    # 不眠専用のプロンプトテンプレート
    if symptom_type == "insomnia":
        return {
            "system_message": "あなたは薬剤師兼カウンセラーです。不眠に関するカウンセリングを行い、代替療法を推奨し、薬のリスクを説明してください。「一時的な不眠で推奨される医薬品を知りたい場合は教えて下さい」というメッセージは含めないでください（別途送信されます）。",
            "user_prompt_template": """
あなたは薬剤師兼カウンセラーです。不眠で悩むユーザーに対して、
共感的で実践的なアドバイスを含む返信を生成してください。
{history_context}
【ユーザーの入力】
{user_text}

【症状タイプ】
不眠

【返信の要件】
- **共感的なメッセージ**: 不眠で悩む気持ちに寄り添う（1-2文）
- **代替療法の具体的な推奨**: 以下の方法を具体的に説明してください（必須）
  * ハーブティー（カモミール、バレリアンなど）を就寝前に飲む
  * ラベンダーのアロマオイルを枕元に置く、またはアロマディフューザーを使用
  * 軽いストレッチや深呼吸を行う
  * リラックスできる音楽を聴く
  * 睡眠環境の改善（室温、照明、騒音対策など）
- **薬のリスク説明**: 簡潔に説明してください（必須）
  * 睡眠改善薬は一時的な不眠にのみ効果がある
  * 常用化のリスクがある
  * 不眠症と診断されている場合は医師にご相談ください
- **応答長さ**: 200-300文字程度（簡潔に要点を押さえる）
- **質問は最小限に**: 不必要な質問は避け、代替療法の推奨と薬のリスク説明を優先する
- **重要**: 「一時的な不眠で推奨される医薬品を知りたい場合は教えて下さい」というメッセージは含めないでください（別途送信されます）
""",
            "response_requirements": "代替療法の推奨と薬のリスク説明を含む、共感的で実践的な返信（200-300文字程度）。簡潔に要点を押さえる。",
            "max_length": 300
        }
    
    # 医療関連の症状タイプ
    MEDICAL_SYMPTOM_TYPES = {'heart_pain', 'anxiety', 'depression_like'}
    
    if symptom_type in MEDICAL_SYMPTOM_TYPES:
        # 医療関連: 従来のプロンプト（詳細な情報収集を重視）
        return {
            "system_message": "あなたは薬剤師兼カウンセラーです。共感的でバランスの取れた返信を生成してください。",
            "user_prompt_template": """
あなたは薬剤師兼カウンセラーです。ユーザーの感情的症状に対して、
共感的でバランスの取れた返信を生成してください。
{history_context}
【ユーザーの入力】
{user_text}

【症状タイプ】
{symptom_type}

【返信の要件】
- 共感的で理解を示す
- 医療的なアドバイスと心理的なサポートのバランスを取る
- 必要に応じて医療機関受診を推奨する
- 市販薬の推奨は慎重に行う（感情的症状の場合、薬だけでは解決しないことが多い）
- 会話履歴がある場合は、文脈を考慮した返信を生成する
""",
            "response_requirements": "医療的な観点も含めたバランスの取れた返信",
            "max_length": 200
        }
    else:
        # 非医療関連: 応援を重視したプロンプト
        return {
            "system_message": "あなたは薬剤師兼カウンセラーです。医療的アドバイスよりも心理的サポートを優先し、ユーザーを応援し、励まします。",
            "user_prompt_template": """
あなたは薬剤師兼カウンセラーです。ユーザーの悩みや感情に対して、
温かく支援的で前向きな応援メッセージを生成してください。
{history_context}
【ユーザーの入力】
{user_text}

【症状タイプ】
{symptom_type}

【返信の要件】
- **温かく支援的なトーン**: 「大丈夫ですよ」「応援しています」などの温かいメッセージ
- **前向きでエネルギッシュなトーン**: 「頑張って！」「きっと大丈夫！」などの前向きなメッセージ
- **優しく理解を示すトーン**: 「お気持ちよく分かります」「無理しなくて大丈夫です」などの優しいメッセージ
- **バランスの取れたトーン**: 上記を組み合わせた自然な応援メッセージ
- **質問は最小限に**: 不必要な質問は避け、応援メッセージを優先する
- **短めで簡潔に**: 100-150文字程度で簡潔に応援メッセージを生成
- **パーソナライズ**: 会話履歴からユーザーの状況を理解し、それに合わせた応援メッセージを生成
- **共感レベルは適度に**: 過度な共感を避け、自然な応援メッセージを生成
- **会話の流れを自然に**: 機械的な質問を避け、自然な会話の流れを保つ
- **医療的アドバイスは最小限に**: 必要最小限の医療的アドバイスのみ（主に応援メッセージ）
""",
            "response_requirements": "応援と励ましを重視した温かく支援的な返信（100-150文字程度）",
            "max_length": 150
        }


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
        symptom_type: 感情的症状タイプ
        user_text: ユーザーの入力テキスト
        client: OpenAIクライアントインスタンス
        conversation_history: 会話履歴（直近10件まで使用）
        session_id: セッションID（ログ記録用）
    
    Returns:
        カウンセリング的返信テキスト
    """
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
        # 不眠の場合は長めの応答を許可（max_tokensを増やす）
        max_tokens_value = max_length * 2 if symptom_type == "insomnia" else max_length
        
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
        
        # 文字数制限を超える場合は切り詰める（不眠の場合は400文字まで許可）
        if len(response_text) > max_length:
            # 文の途中で切らないように、最後の文を削除
            if symptom_type == "insomnia" and max_length >= 300:
                # 不眠の場合は、文の区切りで切る
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
        
        # ログ記録
        if session_id:
            log_counseling_response(
                session_id=session_id,
                response_content=response_text,
                response_type="counseling_response",
                category=None,
                confidence=None,
                counseling_mode=None
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

一時的な不眠で推奨される医薬品を知りたい場合は教えて下さい。"""
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
                    counseling_mode=None
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


def generate_follow_up_questions(
    symptom_type: str,
    collected_info: Dict,
    client: OpenAI
) -> List[str]:
    """
    フォローアップ質問を生成
    
    Args:
        symptom_type: 感情的症状タイプ
        collected_info: 既に収集済みの情報
        client: OpenAIクライアントインスタンス
    
    Returns:
        フォローアップ質問のリスト
    """
    # 不眠専用の質問生成
    if symptom_type == "insomnia":
        # 既に収集済みの情報を確認
        has_duration = "duration" in collected_info or "期間" in str(collected_info)
        has_cause = "cause" in collected_info or "原因" in str(collected_info)
        has_relaxation = "relaxation" in collected_info or "リラックス" in str(collected_info)
        
        questions = []
        
        # 期間に関する質問（未収集の場合）
        if not has_duration:
            questions.append("どのくらいの期間、眠れない状態が続いていますか？")
        
        # 原因に関する質問（未収集の場合）
        if not has_cause and len(questions) < 3:
            questions.append("不眠の原因として、何か心配事やストレスがありますか？")
        
        # リラックス習慣に関する質問（未収集の場合）
        if not has_relaxation and len(questions) < 3:
            questions.append("就寝前に何かリラックスできる習慣はありますか？")
        
        # 質問が不足している場合、追加の質問を生成
        if len(questions) < 2:
            additional_questions = [
                "どのような時間帯に眠れないことが多いですか？",
                "不眠の影響で、日中の生活に支障はありますか？"
            ]
            for q in additional_questions:
                if len(questions) < 3:
                    questions.append(q)
        
        # 最低1つは質問を返す
        if not questions:
            questions = ["どのくらいの期間、眠れない状態が続いていますか？"]
        
        return questions[:3]  # 最大3つまで
    
    # その他の症状タイプの処理
    prompt = f"""
    あなたは薬剤師兼カウンセラーです。感情的症状について、より詳しい情報を収集するための
    フォローアップ質問を生成してください。
    
    【症状タイプ】
    {symptom_type}
    
    【既に収集済みの情報】
    {json.dumps(collected_info, ensure_ascii=False, indent=2)}
    
    【質問生成の要件】
    - 開かれた質問（Yes/Noで答えられない質問）を優先する
    - ユーザーが話しやすい質問にする
    - 3つ程度の質問を生成する
    - 質問は自然な会話形式で
    - 「もう少し詳しく教えていただけますか？」という質問は生成しない
    
    【回答形式】
    JSON形式で回答してください：
    {{
        "questions": ["質問1", "質問2", "質問3"]
    }}
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "あなたは薬剤師兼カウンセラーです。自然な会話形式のフォローアップ質問を生成してください。「もう少し詳しく教えていただけますか？」という質問は生成しないでください。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=200,
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        result = json.loads(content)
        
        # 質問リストを取得（"questions"キーまたは配列として直接返される場合に対応）
        if "questions" in result:
            questions = result["questions"]
        elif isinstance(result, list):
            questions = result
        else:
            # フォールバック: 症状タイプに応じたデフォルト質問を返す
            if symptom_type == "anxiety":
                questions = ["どのような場面で不安を感じることが多いですか？"]
            elif symptom_type == "stress":
                questions = ["どのようなストレスを感じていますか？"]
            elif symptom_type == "heart_pain":
                questions = ["どのような状況で心の痛みを感じますか？"]
            else:
                questions = ["もう少し詳しく教えていただけますか？"]
        
        # 「もう少し詳しく教えていただけますか？」を除外
        questions = [q for q in questions if "もう少し詳しく教えていただけますか？" not in q]
        
        # 質問が空の場合は、症状タイプに応じたデフォルト質問を返す
        if not questions:
            if symptom_type == "anxiety":
                questions = ["どのような場面で不安を感じることが多いですか？"]
            elif symptom_type == "stress":
                questions = ["どのようなストレスを感じていますか？"]
            elif symptom_type == "heart_pain":
                questions = ["どのような状況で心の痛みを感じますか？"]
            else:
                questions = ["具体的にどのような症状がありますか？"]
        
        return questions if isinstance(questions, list) else [questions]
    except Exception as e:
        logger.error(f"フォローアップ質問生成エラー: {e}")
        # エラー時のフォールバックも症状タイプに応じた質問を返す
        if symptom_type == "insomnia":
            return ["どのくらいの期間、眠れない状態が続いていますか？"]
        elif symptom_type == "anxiety":
            return ["どのような場面で不安を感じることが多いですか？"]
        elif symptom_type == "stress":
            return ["どのようなストレスを感じていますか？"]
        elif symptom_type == "heart_pain":
            return ["どのような状況で心の痛みを感じますか？"]
        else:
            return ["具体的にどのような症状がありますか？"]


def start_counseling_mode(
    session: Dict,
    symptom_type: str,
    initial_questions: List[str]
) -> None:
    """
    カウンセリングモードを開始し、セッション状態を更新
    
    Args:
        session: Flaskセッションオブジェクト
        symptom_type: 症状タイプ
        initial_questions: 初期質問リスト
    """
    session['counseling_mode'] = {
        'active': True,
        'started_at': datetime.now().isoformat(),
        'symptom_type': symptom_type,
        'question_history': [],
        'collected_info': {},
        'current_question_index': 0,
        'total_questions': len(initial_questions)
    }
    session.modified = True


def format_conversation_history(messages: List[Dict]) -> str:
    """
    会話履歴をテキスト形式に整形
    
    Args:
        messages: メッセージリスト
    
    Returns:
        整形された会話履歴テキスト
    """
    history_text = ""
    for msg in messages:
        role = msg.get('type', 'user')
        content = msg.get('content', '')
        if role == 'user':
            history_text += f"ユーザー: {content}\n"
        elif role == 'bot':
            history_text += f"ボット: {content}\n"
    return history_text


def calculate_adaptive_question_limit(
    symptom_type: str,
    collected_info: Dict,
    question_count: int
) -> int:
    """
    適応的な質問上限を計算
    
    Args:
        symptom_type: 症状タイプ
        collected_info: 収集済み情報
        question_count: 現在の質問回数
    
    Returns:
        質問上限（最大質問回数）
    """
    # 医療関連の症状タイプの場合、より多くの質問を許可
    medical_symptom_types = ['heart_pain', 'anxiety', 'depression_like']
    if symptom_type in medical_symptom_types:
        # 医療関連: 最大7問
        base_limit = 7
    else:
        # 非医療関連（恋愛、ストレスなど）: 最大4問（実際は2-3問で終了を推奨）
        base_limit = 4
    
    # 収集済み情報の量に応じて調整
    info_count = len(collected_info)
    if info_count >= 3:
        # 十分な情報が収集できている場合、上限を下げる
        return min(base_limit, question_count + 2)
    
    return base_limit


def should_ask_question(
    user_response: str,
    collected_info: Dict,
    question_count: int,
    symptom_type: str
) -> Dict:
    """
    質問を返すべきかどうかを判断
    
    Returns:
        {
            "should_ask": bool,
            "reason": str,
            "response_first": bool  # 返信を先に返すべきか
        }
    """
    # 十分な情報が収集できている場合、質問をスキップ
    if len(collected_info) >= 3:
        return {
            "should_ask": False,
            "reason": "sufficient_info",
            "response_first": True
        }
    
    # 質問回数が上限に達している場合、質問をスキップ
    adaptive_limit = calculate_adaptive_question_limit(
        symptom_type, collected_info, question_count
    )
    if question_count >= adaptive_limit:
        return {
            "should_ask": False,
            "reason": "question_limit_reached",
            "response_first": True
        }
    
    # ユーザーの回答が短い場合、返信を先に返してから質問
    if len(user_response) < 20:
        return {
            "should_ask": True,
            "reason": "short_response",
            "response_first": True
        }
    
    # 通常の場合、返信を先に返してから質問
    return {
        "should_ask": True,
        "reason": "normal",
        "response_first": True
    }


def should_generate_question_non_medical(
    user_response: str,
    collected_info: Dict,
    question_count: int,
    conversation_history: List[Dict],
    client: OpenAI
) -> Dict:
    """
    医療関連以外のカウンセリングで質問を生成すべきか判断
    
    Returns:
        {
            "should_ask": bool,
            "question_type": str,  # "supportive" | "none"
            "reason": str
        }
    """
    # 質問回数が既に2回以上の場合、質問をスキップ
    if question_count >= 2:
        return {
            "should_ask": False,
            "question_type": "none",
            "reason": "question_limit_reached"
        }
    
    # ユーザーが詳しく話したい場合のみ、支援的な質問を生成
    if len(user_response) > 50 and question_count < 2:
        return {
            "should_ask": True,
            "question_type": "supportive",
            "reason": "user_wants_to_talk"
        }
    
    # デフォルト: 質問をスキップ
    return {
        "should_ask": False,
        "question_type": "none",
        "reason": "default_no_question"
    }


def generate_supportive_question(
    symptom_type: str,
    user_response: str,
    conversation_history: List[Dict],
    client: OpenAI
) -> str:
    """
    支援的な質問を生成（医療関連以外のみ）
    
    例:
    - "何か手助けできることはありますか？"
    - "もっと詳しく聞かせてくれますか？"
    - "他に気になることはありますか？"
    """
    history_text = format_conversation_history(conversation_history[-5:])
    
    prompt = f"""
あなたは薬剤師兼カウンセラーです。ユーザーを応援し、支援するための
自然で親しみやすい質問を1つ生成してください。

【会話履歴】
{history_text}

【ユーザーの最新の回答】
{user_response}

【症状タイプ】
{symptom_type}

【質問の要件】
- 支援的で親しみやすいトーン
- 開かれた質問（Yes/Noで答えられない質問）
- ユーザーが話しやすい質問
- 1つだけ生成
- 50文字以内

【質問を生成してください】
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "あなたは薬剤師兼カウンセラーです。支援的で親しみやすい質問を生成してください。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=100
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"支援的質問生成エラー: {e}")
        return "何か手助けできることはありますか？"


def analyze_user_satisfaction(
    user_response: str,
    conversation_history: List[Dict],
    client: OpenAI
) -> Dict:
    """
    ユーザーの満足度を分析
    
    Returns:
        {
            "satisfaction_score": float,  # 0.0-1.0
            "wants_to_continue": bool,
            "is_frustrated": bool,
            "reasoning": str
        }
    """
    history_text = format_conversation_history(conversation_history[-5:])
    
    prompt = f"""
あなたは薬剤師兼カウンセラーです。ユーザーの最新の回答から満足度を分析してください。

【会話履歴】
{history_text}

【ユーザーの最新の回答】
{user_response}

【分析すべき内容】
1. ユーザーの満足度（0.0-1.0）
2. 会話を続けたいかどうか
3. フラストレーションを感じているかどうか

【満足度の指標】
- 「ありがとう」「大丈夫」「解決した」など → 満足度高（0.7以上）
- 「わからない」「別に」「特にない」など → 満足度低（0.3以下）
- 通常の回答 → 満足度中（0.4-0.6）

【回答形式】
JSON形式で回答してください：
{{
    "satisfaction_score": 0.0-1.0,
    "wants_to_continue": true/false,
    "is_frustrated": true/false,
    "reasoning": "分析理由"
}}
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "あなたは薬剤師兼カウンセラーです。ユーザーの満足度を正確に分析してください。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=200,
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        logger.error(f"満足度分析エラー: {e}")
        return {
            "satisfaction_score": 0.5,
            "wants_to_continue": True,
            "is_frustrated": False,
            "reasoning": f"エラー: {str(e)}"
        }


def process_counseling_answer(
    user_text: str,
    session: Dict,
    conversation_history: List[Dict],
    client: OpenAI,
    session_id: str = None
) -> Dict:
    """
    カウンセリングモード中にユーザーが回答した場合の処理（改善版）
    
    処理フロー:
    1. 会話履歴全体をChatGPTに渡して文脈理解
    2. 直前の質問に対する回答を抽出
    3. **文脈を考慮した返信を生成（新規追加）**
    4. 返信を返す
    5. 収集済み情報を更新
    6. 必要に応じて次の質問を生成、またはカウンセリングを完了
    
    Args:
        user_text: ユーザーの回答テキスト
        session: Flaskセッションオブジェクト
        conversation_history: 会話履歴
        client: OpenAIクライアントインスタンス
    
    Returns:
        処理結果の辞書（返信と質問を含む）
    """
    # 会話履歴を整形
    history_text = format_conversation_history(conversation_history)
    
    counseling_mode = session.get('counseling_mode', {})
    question_history = counseling_mode.get('question_history', [])
    
    last_question = ""
    if question_history:
        last_question = question_history[-1].get('question', '')
    
    # ChatGPTで回答を解釈（終了条件を明記）
    # 会話履歴から文脈をより詳細に理解するための情報を追加
    recent_messages = conversation_history[-10:] if len(conversation_history) > 10 else conversation_history
    context_summary = ""
    if len(recent_messages) > 1:
        # 直前の質問とその前の会話の流れを要約
        context_summary = "\n".join([
            f"{'ユーザー' if msg.get('type') == 'user' else 'ボット'}: {msg.get('content', '')[:100]}"
            for msg in recent_messages[-5:]  # 直近5件の要約
        ])
    
    prompt = f"""
    あなたは薬剤師兼カウンセラーです。以下の会話履歴を基に、ユーザーの最新の回答を解釈してください。
    
    【会話履歴（全文）】
    {history_text}
    
    【直近の会話の流れ】
    {context_summary if context_summary else "（会話履歴が短いため、上記の会話履歴を参照してください）"}
    
    【直前の質問】
    {last_question if last_question else "（質問履歴がありません）"}
    
    【ユーザーの回答】
    {user_text}
    
    【解釈すべき内容】
    1. 直前の質問に対する回答内容（質問への回答として解釈できるか）
    2. 回答から抽出できる情報（場所、程度、期間など）
    3. 次の質問が必要かどうか
    4. 「勉強中」「英語の勉強中」のような短い入力も、文脈から質問への回答として解釈できるか判断する
    5. 会話の流れから、ユーザーが何を伝えようとしているかを推測する
    
    【カウンセリング終了条件】
    以下のいずれかの場合、next_actionを"complete"に設定してください：
    
    【通常の終了条件】
    - ユーザーが「ありがとう」「もう大丈夫」「解決した」など、終了の意思を示している
    - ユーザーが「バイバイ」「さようなら」など、会話を終える意思を示している
    - 十分な情報が収集できた（3つ以上の質問に回答済み）
    - ユーザーが明確に「もう聞かないで」「終了」「終わり」「もういい」「やめる」などと拒否している
    - ユーザーが満足していると判断される場合（「大丈夫です」「問題ありません」など）
    
    【緊急終了条件（即座に終了）】
    - 希死念慮・自傷他害の示唆:
      **明示的な希死念慮の表現のみ**を検出してください：
      - 「死にたい」「消えたい」「自殺したい」「生きていても仕方ない」などの明示的な表現
      - 「リストカット」「自傷行為」などの自傷行為の明示的な表現
      - **重要**: 「失恋して胸が苦しい」「恋愛で悩んでいる」などの感情的な表現は、希死念慮ではありません
      - **重要**: 身体的症状（「胸が苦しい」「心臓が痛い」など）のみでは、希死念慮とは判定しないでください
      - 希死念慮が検出された場合のみ、next_actionを"complete"に設定し、completion_reasonに"crisis_detected"を設定してください
      カウンセリングを即時中止し、専門機関案内フローへ強制移行が必要です。
    
    - 停滞・ループ:
      ユーザーが「わからない」「別に」「特にない」などを繰り返し、
      情報収集が進まない場合（例: 3回連続で有意な情報が得られない）、
      next_actionを"complete"に設定し、completion_reasonに"no_progress"を設定してください。
    
    【回答形式】
    JSON形式で回答してください：
    {{
        "answer_extracted": {{
            "question_type": "直前の質問タイプ",
            "answer": "抽出された回答内容",
            "info_key": "収集済み情報のキー（location, severity, durationなど）",
            "info_value": "収集された情報の値"
        }},
        "next_action": "continue" | "complete",
        "completion_reason": "終了理由（completeの場合のみ）",
        "reasoning": "解釈理由"
    }}
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "あなたは薬剤師兼カウンセラーです。会話の文脈を理解し、ユーザーの回答を正確に解釈してください。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=500,
            response_format={"type": "json_object"}
        )
        
        # 回答を解釈
        interpretation = json.loads(response.choices[0].message.content)
        
        # ユーザー明示的終了キーワードの検知（最優先）
        explicit_end_keywords = ['終了', '終わり', 'もういい', 'やめる', 'もう聞かないで', '終わりたい']
        if any(keyword in user_text for keyword in explicit_end_keywords):
            counseling_mode['active'] = False
            session['counseling_mode'] = counseling_mode
            session.modified = True
            
            end_message = '承知いたしました。お役に立てて嬉しいです。何か他に気になることがあれば、いつでもお聞かせください。'
            
            # ログ記録（カウンセリング中断理由を記録）
            if session_id:
                log_counseling_response(
                    session_id=session_id,
                    response_content=end_message,
                    response_type="counseling_summary",
                    category=None,
                    confidence=None,
                    counseling_mode=counseling_mode
                )
                logger.info(f"📊 カウンセリング中断: 理由=ユーザー明示的終了, "
                          f"質問回数={len(question_history)}, "
                          f"収集情報数={len(counseling_mode.get('collected_info', {}))}")
            
            return {
                'type': 'counseling_summary',
                'content': end_message,
                'continue_counseling': False,
                'completion_reason': 'user_explicit_end'
            }
        
        # 収集済み情報を更新
        answer_extracted = interpretation.get('answer_extracted', {})
        if answer_extracted.get('info_key'):
            counseling_mode['collected_info'][answer_extracted['info_key']] = answer_extracted.get('info_value', '')
        
        # 終了条件のチェック（希死念慮・ループ）
        completion_reason = interpretation.get('completion_reason', '')
        
        if completion_reason == 'crisis_detected':
            # 希死念慮が検出された場合、即座に専門機関案内へ
            from medicine_logic import get_crisis_support_resources
            try:
                crisis_resources = get_crisis_support_resources('ja')
            except:
                crisis_resources = {
                    'message': '専門機関への相談をお勧めします。',
                    'resources': [],
                    'emergency_message': '緊急の場合は119番（救急）に連絡してください。'
                }
            
            counseling_mode['active'] = False
            session['counseling_mode'] = counseling_mode
            session.modified = True
            
            crisis_content = crisis_resources.get('message', '専門機関への相談をお勧めします。')
            
            # ログ記録（カウンセリング中断理由を記録）
            if session_id:
                log_counseling_response(
                    session_id=session_id,
                    response_content=crisis_content,
                    response_type="crisis_support",
                    category="Emergency",
                    confidence=None,
                    counseling_mode=counseling_mode
                )
                logger.warning(f"🚨 カウンセリング中断: 理由=危機検出（希死念慮・自傷他害の示唆）, "
                             f"質問回数={len(question_history)}, "
                             f"収集情報数={len(counseling_mode.get('collected_info', {}))}")
            
            return {
                'type': 'crisis_support',
                'content': crisis_content,
                'resources': crisis_resources.get('resources', []),
                'emergency_message': crisis_resources.get('emergency_message', '緊急の場合は119番（救急）に連絡してください。'),
                'continue_counseling': False,
                'crisis_detected': True,
                'completion_reason': 'crisis_detected'
            }
        elif completion_reason == 'no_progress':
            # 情報収集が進まない場合、医療機関受診を推奨
            counseling_mode['active'] = False
            session['counseling_mode'] = counseling_mode
            session.modified = True
            
            no_progress_content = '詳しい症状が分からないため、一度お近くの医療機関にご相談されることをお勧めします。'
            
            # ログ記録（カウンセリング中断理由を記録）
            if session_id:
                log_counseling_response(
                    session_id=session_id,
                    response_content=no_progress_content,
                    response_type="counseling_summary_no_progress",
                    category=None,
                    confidence=None,
                    counseling_mode=counseling_mode
                )
                logger.info(f"📊 カウンセリング中断: 理由=情報収集停滞（LLM判定）, "
                          f"質問回数={len(question_history)}, "
                          f"収集情報数={len(counseling_mode.get('collected_info', {}))}")
            
            return {
                'type': 'counseling_summary',
                'content': no_progress_content,
                'continue_counseling': False,
                'recommendation': 'medical_consultation',
                'completion_reason': 'no_progress'
            }
        
        # ステップ1: 文脈を考慮した返信を生成（不眠の場合は特別処理）
        symptom_type = counseling_mode.get('symptom_type', 'general_emotional')
        
        if symptom_type == "insomnia":
            # 不眠の場合、ユーザーの回答に応じた簡潔な返信を生成
            # 会話履歴を考慮して、既に説明した内容は繰り返さない
            history_text = format_conversation_history(conversation_history[-10:])
            
            # ユーザーの回答から情報を抽出
            answer_info = answer_extracted.get('info_value', '')
            info_key = answer_extracted.get('info_key', '')
            
            # 不眠専用の簡潔な返信を生成
            prompt = f"""
あなたは薬剤師兼カウンセラーです。不眠で悩むユーザーに対して、会話の流れを考慮した簡潔な返信を生成してください。

【会話履歴】
{history_text}

【直前の質問】
{last_question}

【ユーザーの回答】
{user_text}

【抽出された情報】
{info_key}: {answer_info}

【返信の要件】
- **会話の流れを考慮**: 既に説明した代替療法や薬のリスクについては、繰り返さないでください
- **ユーザーの回答に応じた返信**: ユーザーの回答（例：「昨日からです」）に応じた簡潔な返信を生成してください
- **簡潔に**: 100-150文字程度で簡潔に返信してください
- **共感的に**: ユーザーの状況に寄り添う返信をしてください
- **重要**: 代替療法や薬のリスクの詳細な説明は既に最初の応答で説明済みなので、繰り返さないでください

【返信を生成してください】
"""
            try:
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "あなたは薬剤師兼カウンセラーです。会話の流れを考慮した簡潔な返信を生成してください。"},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=200
                )
                counseling_response_text = response.choices[0].message.content.strip()
            except Exception as e:
                logger.error(f"不眠カウンセリング返信生成エラー: {e}")
                # フォールバック: 簡潔な返信
                counseling_response_text = f"了解しました。{user_text}とのことですね。"
        else:
            # その他の症状タイプは従来通り
            counseling_response_text = generate_counseling_response(
                symptom_type,
                user_text,
                client,
                conversation_history=conversation_history,
                session_id=session_id
            )
        
        # ステップ2: 次のアクションを決定
        if interpretation.get('next_action') == 'continue':
            # ユーザーの満足度を分析（非医療関連の場合）
            MEDICAL_SYMPTOM_TYPES = {'heart_pain', 'anxiety', 'depression_like'}
            satisfaction = None
            if symptom_type not in MEDICAL_SYMPTOM_TYPES:
                satisfaction = analyze_user_satisfaction(user_text, conversation_history, client)
                # 満足度が高い場合、カウンセリングを終了
                if satisfaction.get('satisfaction_score', 0.0) >= 0.7:
                    counseling_mode['active'] = False
                    session['counseling_mode'] = counseling_mode
                    session.modified = True
                    
                    summary_content = counseling_response_text + "\n\nお役に立てて嬉しいです。何か他に気になることがあれば、いつでもお聞かせください。"
                    
                    # ログ記録（カウンセリング中断理由を記録）
                    if session_id:
                        log_counseling_response(
                            session_id=session_id,
                            response_content=summary_content,
                            response_type="counseling_summary",
                            category=None,
                            confidence=None,
                            counseling_mode=counseling_mode
                        )
                        logger.info(f"📊 カウンセリング中断: 理由=ユーザー満足度高（満足度スコア={satisfaction.get('satisfaction_score', 0.0):.2f}）, "
                                  f"質問回数={len(question_history)}, "
                                  f"収集情報数={len(counseling_mode.get('collected_info', {}))}")
                    
                    return {
                        'type': 'counseling_summary',
                        'content': summary_content,
                        'continue_counseling': False,
                        'counseling_response': counseling_response_text,
                        'completion_reason': 'user_satisfied'
                    }
            
            # 停滞チェック: 3回連続で有意な情報が得られない場合は終了
            recent_answers = question_history[-3:] if len(question_history) >= 3 else question_history
            if len(recent_answers) >= 3:
                no_progress_count = sum(
                    1 for q in recent_answers 
                    if answer_extracted.get('info_value') in ['わからない', '別に', '特にない', 'なし']
                )
                if no_progress_count >= 3:
                    counseling_mode['active'] = False
                    session['counseling_mode'] = counseling_mode
                    session.modified = True
                    
                    no_progress_content = counseling_response_text + "\n\n詳しい症状が分からないため、一度お近くの医療機関にご相談されることをお勧めします。"
                    
                    # ログ記録（カウンセリング中断理由を記録）
                    if session_id:
                        log_counseling_response(
                            session_id=session_id,
                            response_content=no_progress_content,
                            response_type="counseling_summary_no_progress",
                            category=None,
                            confidence=None,
                            counseling_mode=counseling_mode
                        )
                        logger.info(f"📊 カウンセリング中断: 理由=情報収集停滞, "
                                  f"質問回数={len(question_history)}, "
                                  f"収集情報数={len(counseling_mode.get('collected_info', {}))}")
                    
                    return {
                        'type': 'counseling_summary',
                        'content': no_progress_content,
                        'continue_counseling': False,
                        'recommendation': 'medical_consultation',
                        'counseling_response': counseling_response_text
                    }
            
            # 質問を返すべきか判断
            question_count = len(question_history)
            question_decision = should_ask_question(
                user_text,
                counseling_mode.get('collected_info', {}),
                question_count,
                symptom_type
            )
            
            # 非医療関連の場合は特別な判定
            if symptom_type not in MEDICAL_SYMPTOM_TYPES:
                question_decision = should_generate_question_non_medical(
                    user_text,
                    counseling_mode.get('collected_info', {}),
                    question_count,
                    conversation_history,
                    client
                )
            
            if question_decision.get('should_ask'):
                # 次の質問を生成
                if symptom_type not in MEDICAL_SYMPTOM_TYPES and question_decision.get('question_type') == 'supportive':
                    # 非医療関連: 支援的な質問を生成
                    next_question = generate_supportive_question(
                        symptom_type,
                        user_text,
                        conversation_history,
                        client
                    )
                else:
                    # 医療関連: 通常のフォローアップ質問を生成
                    next_questions = generate_follow_up_questions(
                        symptom_type,
                        counseling_mode.get('collected_info', {}),
                        client
                    )
                    next_question = next_questions[0] if next_questions else None
                
                if next_question:
                    # 質問履歴に追加
                    counseling_mode['question_history'].append({
                        'question': next_question,
                        'asked_at': datetime.now().isoformat(),
                        'question_type': answer_extracted.get('question_type', 'general')
                    })
                    counseling_mode['current_question_index'] += 1
                    session['counseling_mode'] = counseling_mode
                    session.modified = True
                    
                    result = {
                        'type': 'counseling_response_with_question',
                        'counseling_response': counseling_response_text,
                        'question': next_question,
                        'continue_counseling': True
                    }
                    
                    # ログ記録
                    if session_id:
                        log_counseling_response(
                            session_id=session_id,
                            response_content=f"返信: {counseling_response_text[:100]}... | 質問: {next_question}",
                            response_type="counseling_response_with_question",
                            category=None,
                            confidence=None,
                            counseling_mode=counseling_mode
                        )
                    
                    return result
                else:
                    # 質問が生成できない場合は完了
                    counseling_mode['active'] = False
                    session['counseling_mode'] = counseling_mode
                    session.modified = True
                    
                    summary_content = counseling_response_text + "\n\nお話を伺えました。ありがとうございます。"
                    
                    # ログ記録
                    if session_id:
                        log_counseling_response(
                            session_id=session_id,
                            response_content=summary_content,
                            response_type="counseling_summary",
                            category=None,
                            confidence=None,
                            counseling_mode=counseling_mode
                        )
                    
                    return {
                        'type': 'counseling_summary',
                        'content': summary_content,
                        'continue_counseling': False,
                        'counseling_response': counseling_response_text
                    }
            else:
                # 質問をスキップして返信のみ返す
                return {
                    'type': 'counseling_response',
                    'content': counseling_response_text,
                    'continue_counseling': True,
                    'skip_question': True,
                    'reason': question_decision.get('reason', 'unknown')
                }
        else:
            # カウンセリングを完了し、総合的な返信を生成
            # 返信を先に生成済みの場合は、それを使用してサマリーを生成
            if counseling_response_text:
                # 既に返信がある場合は、それにサマリーを追加
                summary = generate_counseling_summary(
                    counseling_mode, 
                    interpretation, 
                    client,
                    conversation_history=conversation_history,
                    session_id=session_id
                )
                final_content = counseling_response_text + "\n\n" + summary
            else:
                summary = generate_counseling_summary(
                    counseling_mode, 
                    interpretation, 
                    client,
                    conversation_history=conversation_history,
                    session_id=session_id
                )
                final_content = summary
            
            # カウンセリングモードを終了
            counseling_mode['active'] = False
            session['counseling_mode'] = counseling_mode
            session.modified = True
            
            return {
                'type': 'counseling_summary',
                'content': final_content,
                'continue_counseling': False,
                'counseling_response': counseling_response_text if counseling_response_text else final_content
            }
            
    except Exception as e:
        logger.error(f"カウンセリング回答処理エラー: {e}")
        import traceback
        traceback.print_exc()
        
        # エラーメッセージも症状タイプに応じて変更
        counseling_mode = session.get('counseling_mode', {})
        symptom_type = counseling_mode.get('symptom_type', 'general_emotional')
        MEDICAL_SYMPTOM_TYPES = {'heart_pain', 'anxiety', 'depression_like'}
        
        if symptom_type in MEDICAL_SYMPTOM_TYPES:
            error_content = 'エラーが発生しました。もう一度お試しください。'
        else:
            error_content = '申し訳ございません。エラーが発生しました。応援しています。'
        
        # エラー時もログ記録を試みる
        if session_id:
            try:
                log_counseling_response(
                    session_id=session_id,
                    response_content=error_content,
                    response_type="counseling_error",
                    category=None,
                    confidence=None,
                    counseling_mode=counseling_mode
                )
            except:
                pass
        
        return {
            'type': 'error',
            'content': error_content,
            'continue_counseling': False
        }


def generate_counseling_summary(
    counseling_mode: Dict,
    interpretation: Dict,
    client: OpenAI,
    conversation_history: List[Dict] = None,
    session_id: str = None
) -> str:
    """
    カウンセリングの総合的な返信を生成
    
    Args:
        counseling_mode: カウンセリングモードの状態
        interpretation: 解釈結果
        client: OpenAIクライアントインスタンス
        conversation_history: 会話履歴（直近10件まで使用）
        session_id: セッションID（ログ記録用）
    
    Returns:
        総合的な返信テキスト
    """
    collected_info = counseling_mode.get('collected_info', {})
    symptom_type = counseling_mode.get('symptom_type', 'general_emotional')
    
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
    
    prompt = f"""
    あなたは薬剤師兼カウンセラーです。カウンセリングで収集した情報を基に、
    総合的な返信を生成してください。
    {history_context}
    【収集した情報】
    {json.dumps(collected_info, ensure_ascii=False, indent=2)}
    
    【症状タイプ】
    {symptom_type}
    
    【返信の要件】
    - 収集した情報を要約する
    - 適切なアドバイスを提供する
    - 必要に応じて医療機関受診を推奨する
    - 共感的で温かいトーンを保つ
    - 会話履歴がある場合は、文脈を考慮した返信を生成する
    
    【返信を生成してください】
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "あなたは薬剤師兼カウンセラーです。総合的な返信を生成してください。返信は200文字以内に収めてください。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=200  # 200文字に制限（日本語は1文字≈1トークン）
        )
        
        response_text = response.choices[0].message.content.strip()
        
        # 200文字を超える場合は切り詰める
        if len(response_text) > 200:
            response_text = response_text[:200] + "..."
        
        # ログ記録
        if session_id:
            log_counseling_response(
                session_id=session_id,
                response_content=response_text,
                response_type="counseling_summary",
                category=None,
                confidence=None,
                counseling_mode=counseling_mode
            )
        
        return response_text
    except Exception as e:
        logger.error(f"カウンセリング要約生成エラー: {e}")
        error_response = "お話を伺えました。ありがとうございます。必要に応じて医療機関にご相談されることをお勧めします。"
        
        # エラー時もログ記録を試みる
        if session_id:
            try:
                log_counseling_response(
                    session_id=session_id,
                    response_content=error_response,
                    response_type="counseling_summary_error",
                    category=None,
                    confidence=None,
                    counseling_mode=counseling_mode
                )
            except:
                pass
        
        return error_response


def detect_topic_shift(
    user_text: str,
    conversation_history: List[Dict],
    current_counseling_topic: str,
    client: OpenAI
) -> Dict:
    """
    カウンセリングモード中に話題が転換されたかを自動検知
    
    Args:
        user_text: ユーザーの入力テキスト
        conversation_history: 会話履歴
        current_counseling_topic: 現在のカウンセリングトピック
        client: OpenAIクライアントインスタンス
    
    Returns:
        {
            "is_topic_shift": bool,  # 話題転換があったか
            "new_topic_category": str,  # 新しい話題のカテゴリ（Physical/Emotional/etc.）
            "relation_to_current_topic": float,  # 現在のトピックとの関連性スコア（0.0-1.0）
            "confidence": float,  # 確信度
            "reasoning": str  # 判定理由
        }
    """
    # 会話履歴を整形
    history_text = format_conversation_history(conversation_history[-10:])  # 直近10件
    
    prompt = f"""
    あなたは薬剤師です。カウンセリング中の会話で、ユーザーが話題を転換したかを判定してください。
    
    【会話履歴】
    {history_text}
    
    【現在のカウンセリングトピック】
    {current_counseling_topic}
    
    【ユーザーの最新入力】
    {user_text}
    
    【判定すべき内容】
    1. ユーザーの最新入力は、現在のカウンセリングトピックの続きか？
    2. それとも、新しい症状や話題について話し始めたか？
    3. 現在のトピックとの関連性はどの程度か？
    
    【話題転換の例】
    - 「あ、そういえば頭も痛くて」→ 話題転換（新しい症状：頭痛）
    - 「左側です」→ カウンセリングの続き（質問への回答）
    - 「ありがとう、もう大丈夫」→ カウンセリング終了の意思表示
    
    【誤検知防止のための判定基準】
    - 文脈の連続性を考慮してください
    - 例: 「（恋の悩みで考えすぎて）頭が痛い」→ カウンセリングの続き（関連性高い）
    - 例: 「（殴られて）頭が痛い」→ 話題転換（新しい身体的症状、関連性低い）
    
    【回答形式】
    JSON形式で回答してください：
    {{
        "is_topic_shift": true/false,
        "new_topic_category": "Physical" | "Emotional" | "Emergency" | null,
        "relation_to_current_topic": 0.0-1.0,
        "confidence": 0.0-1.0,
        "reasoning": "判定理由"
    }}
    
    【重要な判定ルール】
    - relation_to_current_topicが0.5以上の場合、話題転換と判定しない（カウンセリングの続きとして処理）
    - カウンセリング中の質問への回答として解釈しやすい入力（「勉強中」「英語の勉強中」など）は、話題転換と判定しない
    - 新しいカテゴリがPhysical/Emergency かつ relation_to_current_topicが0.5未満の場合のみ、話題転換と判定
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "あなたは薬剤師です。会話の文脈を理解し、話題転換を正確に検知してください。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=300,
            response_format={"type": "json_object"}
        )
        
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        logger.error(f"話題転換検知エラー: {e}")
        import traceback
        traceback.print_exc()
        # エラー時は安全側に倒して話題転換なしと判定
        return {
            "is_topic_shift": False,
            "new_topic_category": None,
            "relation_to_current_topic": 1.0,
            "confidence": 0.0,
            "reasoning": f"エラーが発生しました: {str(e)}"
        }


def handle_user_input_in_counseling_mode(
    user_text: str,
    session: Dict,
    client: OpenAI,
    session_id: str = None
) -> Dict:
    """
    カウンセリングモード中にユーザーが入力した場合の処理（改善版）
    
    【改善点】: ユーザーに確認を求めず、自動的に話題転換を検知
    
    Args:
        user_text: ユーザーの入力テキスト
        session: Flaskセッションオブジェクト
        client: OpenAIクライアントインスタンス
    
    Returns:
        処理結果の辞書
    """
    counseling_mode = session.get('counseling_mode', {})
    current_topic = counseling_mode.get('symptom_type', '')
    
    # 不眠カウンセリング中に薬を希望した場合の検出
    if current_topic == "insomnia":
        user_text_lower = user_text.lower()
        medicine_request_keywords = [
            "薬を教えて", "睡眠薬を教えて", "医薬品を知りたい", "薬を知りたい",
            "睡眠薬", "薬を", "医薬品を", "薬を教えて下さい", "薬を教えてください",
            "睡眠薬を教えて下さい", "睡眠薬を教えてください", "医薬品を教えて",
            "薬を推奨", "睡眠薬を推奨", "医薬品を推奨",
            "教えて欲しい", "教えてください", "教えて下さい", "教えて",
            "知りたい", "知りたいです", "知りたいです。", "知りたい。",
            "推奨して", "推奨してください", "推奨して下さい", "推奨して欲しい"
        ]
        
        if any(keyword in user_text_lower for keyword in medicine_request_keywords):
            # カウンセリングモードを終了し、Physicalカテゴリの処理に移行
            counseling_mode['active'] = False
            session['counseling_mode'] = counseling_mode
            session.modified = True
            
            logger.info(f"不眠カウンセリングから薬推奨への切り替え: ユーザーが薬を希望")
            
            return {
                'type': 'topic_shift',
                'new_category': 'Physical',
                'topic_shift_result': {
                    'is_topic_shift': True,
                    'new_topic_category': 'Physical',
                    'relation_to_current_topic': 0.0,
                    'reasoning': 'ユーザーが薬を希望したため、カウンセリングから薬推奨に切り替え'
                },
                'continue_counseling': False,
                'medicine_request': True
            }
    
    # 話題転換を自動検知
    topic_shift_result = detect_topic_shift(
        user_text,
        session.get('messages', []),
        current_topic,
        client
    )
    
    # 誤検知防止: 関連性スコアをチェック
    relation_score = topic_shift_result.get('relation_to_current_topic', 0.0)
    is_topic_shift = topic_shift_result.get('is_topic_shift', False)
    new_category = topic_shift_result.get('new_topic_category')
    
    # 話題転換の判定条件を調整（閾値を0.3から0.5に緩和）
    if (is_topic_shift and 
        relation_score < 0.5 and 
        new_category in ['Physical', 'Emergency']):
        # 話題転換が検知され、関連性が低く、新しいカテゴリがPhysical/Emergencyの場合のみ転換
        # カウンセリングを一時中断し、新しい話題を処理
        counseling_mode['active'] = False  # カウンセリングモードを一時中断
        session['counseling_mode'] = counseling_mode
        session.modified = True
        
        # 新しい話題のカテゴリに応じて処理を分岐
        # この処理はapp.pyで実装される（ここではフラグを返す）
        return {
            'type': 'topic_shift',
            'new_category': new_category,
            'topic_shift_result': topic_shift_result,
            'continue_counseling': False
        }
    
    # 話題転換がない場合、カウンセリングの続きとして処理
    return process_counseling_answer(user_text, session, session.get('messages', []), client, session_id=session_id)

