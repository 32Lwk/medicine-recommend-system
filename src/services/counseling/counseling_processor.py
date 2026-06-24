"""
カウンセリング回答の統合処理（process_counseling_answer）
"""
import json
import logging
from typing import Dict, List
from openai import OpenAI

from src.services.counseling.counseling_format import format_conversation_history
from src.services.counseling.counseling_logger import log_counseling_response
from src.services.counseling.counseling_summary import generate_counseling_summary
from src.services.counseling.counseling_questions import (
    should_generate_question_non_medical,
    generate_supportive_question,
)
from src.services.counseling.counseling_satisfaction import analyze_user_satisfaction
from src.services.counseling.counseling_generator import generate_counseling_response

logger = logging.getLogger(__name__)

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
    あなたは医薬品相談AIアシスタントです。以下の会話履歴を基に、ユーザーの最新の回答を解釈してください。
    
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
        from src.services.counseling.counseling_llm import counseling_chat
        response = counseling_chat(
            client,
            "counseling_processor",
            [
                {"role": "system", "content": "あなたは医薬品相談AIアシスタントです。会話の文脈を理解し、ユーザーの回答を正確に解釈してください。"},
                {"role": "user", "content": prompt},
            ],
            max_tokens=500,
            temperature=0.1,
            response_format={"type": "json_object"},
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
            
            # ログ記録（カウンセリング中断理由を記録、通常時は会話履歴なし）
            if session_id:
                log_counseling_response(
                    session_id=session_id,
                    response_content=end_message,
                    response_type="counseling_summary",
                    category=None,
                    confidence=None,
                    counseling_mode=counseling_mode,
                    user_input=user_text,
                    conversation_history=conversation_history
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
            from src.core.crisis_detection import get_crisis_support_resources
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
            
            # ログ記録（カウンセリング中断理由を記録、通常時は会話履歴なし）
            if session_id:
                log_counseling_response(
                    session_id=session_id,
                    response_content=crisis_content,
                    response_type="crisis_support",
                    category="Emergency",
                    confidence=None,
                    counseling_mode=counseling_mode,
                    user_input=user_text,
                    conversation_history=conversation_history
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
            
            # ログ記録（カウンセリング中断理由を記録、通常時は会話履歴なし）
            if session_id:
                log_counseling_response(
                    session_id=session_id,
                    response_content=no_progress_content,
                    response_type="counseling_summary_no_progress",
                    category=None,
                    confidence=None,
                    counseling_mode=counseling_mode,
                    user_input=user_text,
                    conversation_history=conversation_history
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
あなたは医薬品相談AIアシスタントです。不眠で悩むユーザーに対して、会話の流れを考慮した簡潔な返信を生成してください。

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
                from src.services.counseling.counseling_llm import counseling_chat
                response = counseling_chat(
                    client,
                    "counseling_processor.insomnia_reply",
                    [
                        {"role": "system", "content": "あなたは医薬品相談AIアシスタントです。会話の流れを考慮した簡潔な返信を生成してください。"},
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=200,
                    session_id=session_id,
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
                    
                    # ログ記録（カウンセリング中断理由を記録、通常時は会話履歴なし）
                    if session_id:
                        log_counseling_response(
                            session_id=session_id,
                            response_content=summary_content,
                            response_type="counseling_summary",
                            category=None,
                            confidence=None,
                            counseling_mode=counseling_mode,
                            user_input=user_text,
                            conversation_history=conversation_history
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
                    
                    # ログ記録（カウンセリング中断理由を記録、通常時は会話履歴なし）
                    if session_id:
                        log_counseling_response(
                            session_id=session_id,
                            response_content=no_progress_content,
                            response_type="counseling_summary_no_progress",
                            category=None,
                            confidence=None,
                            counseling_mode=counseling_mode,
                            user_input=user_text,
                            conversation_history=conversation_history
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
                    
                    # ログ記録（通常時は会話履歴なし）
                    if session_id:
                        log_counseling_response(
                            session_id=session_id,
                            response_content=f"返信: {counseling_response_text[:100]}... | 質問: {next_question}",
                            response_type="counseling_response_with_question",
                            category=None,
                            confidence=None,
                            counseling_mode=counseling_mode,
                            user_input=user_text,
                            conversation_history=conversation_history
                        )
                    
                    return result
                else:
                    # 質問が生成できない場合は完了
                    counseling_mode['active'] = False
                    session['counseling_mode'] = counseling_mode
                    session.modified = True
                    
                    summary_content = counseling_response_text + "\n\nお話を伺えました。ありがとうございます。"
                    
                    # ログ記録（通常時は会話履歴なし）
                    if session_id:
                        log_counseling_response(
                            session_id=session_id,
                            response_content=summary_content,
                            response_type="counseling_summary",
                            category=None,
                            confidence=None,
                            counseling_mode=counseling_mode,
                            user_input=user_text,
                            conversation_history=conversation_history
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
                    session_id=session_id,
                    user_text=user_text
                )
                final_content = counseling_response_text + "\n\n" + summary
            else:
                summary = generate_counseling_summary(
                    counseling_mode, 
                    interpretation, 
                    client,
                    conversation_history=conversation_history,
                    session_id=session_id,
                    user_text=user_text
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
                    counseling_mode=counseling_mode,
                    user_input=user_text,
                    conversation_history=conversation_history
                )
            except:
                pass
        
        return {
            'type': 'error',
            'content': error_content,
            'continue_counseling': False
        }

