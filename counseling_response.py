"""
カウンセリング的返信モジュール
感情的症状に対するカウンセリング的返信とフォローアップ質問を生成
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
from openai import OpenAI

logger = logging.getLogger(__name__)


def detect_emotional_symptom_type(user_text: str, triage_result: Dict) -> str:
    """
    感情的症状のタイプを判定
    
    Args:
        user_text: ユーザーの入力テキスト
        triage_result: トリアージ結果
    
    Returns:
        感情的症状タイプ（"heart_pain", "anxiety", "romantic_concern", "stress", "depression_like"）
    """
    subcategory = triage_result.get("subcategory", "").lower()
    
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


def generate_counseling_response(
    symptom_type: str,
    user_text: str,
    client: OpenAI
) -> str:
    """
    カウンセリング的返信を生成
    
    Args:
        symptom_type: 感情的症状タイプ
        user_text: ユーザーの入力テキスト
        client: OpenAIクライアントインスタンス
    
    Returns:
        カウンセリング的返信テキスト
    """
    prompt = f"""
    あなたは薬剤師兼カウンセラーです。ユーザーの感情的症状に対して、
    共感的でバランスの取れた返信を生成してください。
    
    【ユーザーの入力】
    {user_text}
    
    【症状タイプ】
    {symptom_type}
    
    【返信の要件】
    - 共感的で理解を示す
    - 医療的なアドバイスと心理的なサポートのバランスを取る
    - 必要に応じて医療機関受診を推奨する
    - 市販薬の推奨は慎重に行う（感情的症状の場合、薬だけでは解決しないことが多い）
    
    【返信を生成してください】
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "あなたは薬剤師兼カウンセラーです。共感的でバランスの取れた返信を生成してください。返信は100文字以内に収めてください。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=100  # 100文字に制限（日本語は1文字≈1トークン）
        )
        
        response_text = response.choices[0].message.content.strip()
        
        # 100文字を超える場合は切り詰める
        if len(response_text) > 100:
            response_text = response_text[:100] + "..."
        
        return response_text
    except Exception as e:
        logger.error(f"カウンセリング返信生成エラー: {e}")
        return "お気持ちをお聞かせいただき、ありがとうございます。詳しくお話を伺いたいので、もう少し詳しく教えていただけますか？"


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
    
    【回答形式】
    JSON配列形式で質問を返してください：
    ["質問1", "質問2", "質問3"]
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "あなたは薬剤師兼カウンセラーです。自然な会話形式のフォローアップ質問を生成してください。"},
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
            # フォールバック: デフォルトの質問を返す
            questions = ["もう少し詳しく教えていただけますか？"]
        
        return questions if isinstance(questions, list) else [questions]
    except Exception as e:
        logger.error(f"フォローアップ質問生成エラー: {e}")
        return ["もう少し詳しく教えていただけますか？"]


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


def process_counseling_answer(
    user_text: str,
    session: Dict,
    conversation_history: List[Dict],
    client: OpenAI
) -> Dict:
    """
    カウンセリングモード中にユーザーが回答した場合の処理
    
    処理フロー:
    1. 会話履歴全体をChatGPTに渡して文脈理解
    2. 直前の質問に対する回答を抽出
    3. 収集済み情報を更新
    4. 次の質問を生成、またはカウンセリングを完了
    
    Args:
        user_text: ユーザーの回答テキスト
        session: Flaskセッションオブジェクト
        conversation_history: 会話履歴
        client: OpenAIクライアントインスタンス
    
    Returns:
        処理結果の辞書
    """
    # 会話履歴を整形
    history_text = format_conversation_history(conversation_history)
    
    counseling_mode = session.get('counseling_mode', {})
    question_history = counseling_mode.get('question_history', [])
    
    last_question = ""
    if question_history:
        last_question = question_history[-1].get('question', '')
    
    # ChatGPTで回答を解釈（終了条件を明記）
    prompt = f"""
    あなたは薬剤師兼カウンセラーです。以下の会話履歴を基に、ユーザーの最新の回答を解釈してください。
    
    【会話履歴】
    {history_text}
    
    【直前の質問】
    {last_question}
    
    【ユーザーの回答】
    {user_text}
    
    【解釈すべき内容】
    1. 直前の質問に対する回答内容
    2. 回答から抽出できる情報（場所、程度、期間など）
    3. 次の質問が必要かどうか
    
    【カウンセリング終了条件】
    以下のいずれかの場合、next_actionを"complete"に設定してください：
    
    【通常の終了条件】
    - ユーザーが「ありがとう」「もう大丈夫」「解決した」など、終了の意思を示している
    - ユーザーが「バイバイ」「さようなら」など、会話を終える意思を示している
    - 十分な情報が収集できた（3つ以上の質問に回答済み）
    - ユーザーが明確に「もう聞かないで」などと拒否している
    
    【緊急終了条件（即座に終了）】
    - 希死念慮・自傷他害の示唆:
      「死にたい」「消えたい」「リストカット」などのワードが出た場合、
      next_actionを"complete"に設定し、completion_reasonに"crisis_detected"を設定してください。
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
            
            return {
                'type': 'crisis_support',
                'content': crisis_resources.get('message', '専門機関への相談をお勧めします。'),
                'resources': crisis_resources.get('resources', []),
                'emergency_message': crisis_resources.get('emergency_message', '緊急の場合は119番（救急）に連絡してください。'),
                'continue_counseling': False,
                'crisis_detected': True
            }
        elif completion_reason == 'no_progress':
            # 情報収集が進まない場合、医療機関受診を推奨
            counseling_mode['active'] = False
            session['counseling_mode'] = counseling_mode
            session.modified = True
            
            return {
                'type': 'counseling_summary',
                'content': '詳しい症状が分からないため、一度お近くの医療機関にご相談されることをお勧めします。',
                'continue_counseling': False,
                'recommendation': 'medical_consultation'
            }
        
        # 次のアクションを決定
        if interpretation.get('next_action') == 'continue':
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
                    
                    return {
                        'type': 'counseling_summary',
                        'content': '詳しい症状が分からないため、一度お近くの医療機関にご相談されることをお勧めします。',
                        'continue_counseling': False,
                        'recommendation': 'medical_consultation'
                    }
            
            # 次の質問を生成
            symptom_type = counseling_mode.get('symptom_type', 'general_emotional')
            next_questions = generate_follow_up_questions(
                symptom_type,
                counseling_mode.get('collected_info', {}),
                client
            )
            
            if next_questions:
                next_question = next_questions[0]
                # 質問履歴に追加
                counseling_mode['question_history'].append({
                    'question': next_question,
                    'asked_at': datetime.now().isoformat(),
                    'question_type': answer_extracted.get('question_type', 'general')
                })
                counseling_mode['current_question_index'] += 1
                session['counseling_mode'] = counseling_mode
                session.modified = True
                
                return {
                    'type': 'counseling_question',
                    'content': next_question,
                    'continue_counseling': True
                }
            else:
                # 質問が生成できない場合は完了
                counseling_mode['active'] = False
                session['counseling_mode'] = counseling_mode
                session.modified = True
                
                return {
                    'type': 'counseling_summary',
                    'content': 'お話を伺えました。ありがとうございます。',
                    'continue_counseling': False
                }
        else:
            # カウンセリングを完了し、総合的な返信を生成
            summary = generate_counseling_summary(counseling_mode, interpretation, client)
            # カウンセリングモードを終了
            counseling_mode['active'] = False
            session['counseling_mode'] = counseling_mode
            session.modified = True
            
            return {
                'type': 'counseling_summary',
                'content': summary,
                'continue_counseling': False
            }
            
    except Exception as e:
        logger.error(f"カウンセリング回答処理エラー: {e}")
        import traceback
        traceback.print_exc()
        return {
            'type': 'error',
            'content': 'エラーが発生しました。もう一度お試しください。',
            'continue_counseling': False
        }


def generate_counseling_summary(
    counseling_mode: Dict,
    interpretation: Dict,
    client: OpenAI
) -> str:
    """
    カウンセリングの総合的な返信を生成
    
    Args:
        counseling_mode: カウンセリングモードの状態
        interpretation: 解釈結果
        client: OpenAIクライアントインスタンス
    
    Returns:
        総合的な返信テキスト
    """
    collected_info = counseling_mode.get('collected_info', {})
    symptom_type = counseling_mode.get('symptom_type', 'general_emotional')
    
    prompt = f"""
    あなたは薬剤師兼カウンセラーです。カウンセリングで収集した情報を基に、
    総合的な返信を生成してください。
    
    【収集した情報】
    {json.dumps(collected_info, ensure_ascii=False, indent=2)}
    
    【症状タイプ】
    {symptom_type}
    
    【返信の要件】
    - 収集した情報を要約する
    - 適切なアドバイスを提供する
    - 必要に応じて医療機関受診を推奨する
    - 共感的で温かいトーンを保つ
    
    【返信を生成してください】
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "あなたは薬剤師兼カウンセラーです。総合的な返信を生成してください。返信は100文字以内に収めてください。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=100  # 100文字に制限（日本語は1文字≈1トークン）
        )
        
        response_text = response.choices[0].message.content.strip()
        
        # 100文字を超える場合は切り詰める
        if len(response_text) > 100:
            response_text = response_text[:100] + "..."
        
        return response_text
    except Exception as e:
        logger.error(f"カウンセリング要約生成エラー: {e}")
        return "お話を伺えました。ありがとうございます。必要に応じて医療機関にご相談されることをお勧めします。"


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
    - relation_to_current_topicが0.5以上の場合、話題転換と判定しない
    - 新しいカテゴリがPhysical/Emergency かつ relation_to_current_topicが0.3未満の場合のみ、話題転換と判定
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
    client: OpenAI
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
    
    # 話題転換の判定条件を厳格化
    if (is_topic_shift and 
        relation_score < 0.3 and 
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
    return process_counseling_answer(user_text, session, session.get('messages', []), client)

