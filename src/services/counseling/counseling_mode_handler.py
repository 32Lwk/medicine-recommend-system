"""
カウンセリングモードの制御（start_counseling_mode, handle_user_input_in_counseling_mode）
format_conversation_history は counseling_format から re-export
"""
import logging
import re
from datetime import datetime
from typing import Dict, List
from openai import OpenAI

from src.services.counseling.counseling_format import format_conversation_history
from src.services.counseling.counseling_logger import log_counseling_response
from src.services.counseling.counseling_topic_shift import detect_topic_shift
from src.services.counseling.counseling_processor import process_counseling_answer

logger = logging.getLogger(__name__)

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
    collected_info = counseling_mode.get('collected_info', {})
    
    # 期間や妊娠/授乳の情報をチェック（不眠カウンセリングの場合）
    if current_topic == "insomnia":
        # 妊娠/授乳の情報をチェック（期間のチェックより優先）
        user_text_lower = user_text.lower()
        pregnancy_keywords = ['妊娠', '妊娠中', '妊婦', '妊娠しています', '妊娠してます', '妊娠してる', '妊娠です']
        breastfeeding_keywords = ['授乳', '授乳中', '授乳しています', '授乳してます', '授乳してる', '母乳', '母乳育児', '授乳です']
        
        is_pregnant = any(keyword in user_text_lower for keyword in pregnancy_keywords)
        is_breastfeeding = any(keyword in user_text_lower for keyword in breastfeeding_keywords)
        
        if is_pregnant or is_breastfeeding:
            # 妊娠/授乳中の場合、カウンセリングを中止して受診勧告
            counseling_mode['active'] = False
            session['counseling_mode'] = counseling_mode
            session.modified = True
            
            if is_pregnant:
                consultation_message = """
妊娠中とのことですね。

妊娠中は、市販の睡眠改善薬の使用は避けるべきです。
胎児への影響を考慮し、必ず医師にご相談の上、適切な対処法を受けることをお勧めします。

お近くの産婦人科や、かかりつけの医師にご相談されることをお勧めします。
"""
                reason = 'pregnant'
            else:
                consultation_message = """
授乳中とのことですね。

授乳中は、市販の睡眠改善薬の使用は避けるべきです。
母乳を通じて赤ちゃんに影響を与える可能性があるため、必ず医師にご相談の上、適切な対処法を受けることをお勧めします。

お近くの産婦人科や、かかりつけの医師にご相談されることをお勧めします。
"""
                reason = 'breastfeeding'
            
            logger.info(f"🚨 カウンセリング中止: 理由={'妊娠中' if is_pregnant else '授乳中'}, "
                      f"質問回数={len(counseling_mode.get('question_history', []))}, "
                      f"収集情報数={len(collected_info)}")
            
            if session_id:
                # ログ記録（通常時は会話履歴なし）
                log_counseling_response(
                    session_id=session_id,
                    response_content=consultation_message.strip(),
                    response_type="counseling_summary_medical_consultation",
                    category=None,
                    confidence=None,
                    counseling_mode=counseling_mode,
                    user_input=user_text,
                    conversation_history=None
                )
            
            return {
                'type': 'counseling_summary',
                'content': consultation_message.strip(),
                'continue_counseling': False,
                'recommendation': 'medical_consultation',
                'completion_reason': reason
            }
        
        # 期間のチェック（2週間（14日）を超えている場合）
        # まず、collected_infoから期間を取得
        duration = collected_info.get('duration', '')
        # ユーザーの入力からも期間を抽出（collected_infoにない場合、または最新の入力から確認）
        import re
        if not duration or '日' in user_text or '週間' in user_text or '週' in user_text:
            # 「14日」「2,3日」「2〜3日」「2-3日」「2週間」「14日ほどです」などのパターンを抽出
            if '週間' in user_text or '週' in user_text:
                weeks_match = re.search(r'(\d+)', user_text)
                if weeks_match:
                    weeks = int(weeks_match.group(1))
                    duration = f"{weeks}週間"
            elif '日' in user_text:
                # 範囲表現を検出（「2,3日」「2〜3日」「2-3日」など）
                # カンマ、全角チルダ、ハイフンで区切られた範囲表現を検出
                range_patterns = [
                    r'(\d+)[,、](\d+)日',  # 「2,3日」「2、3日」
                    r'(\d+)[〜～](\d+)日',  # 「2〜3日」「2～3日」
                    r'(\d+)[-－](\d+)日',  # 「2-3日」「2－3日」
                ]
                days = None
                for pattern in range_patterns:
                    range_match = re.search(pattern, user_text)
                    if range_match:
                        # 範囲表現の場合は最大値（後ろの数値）を取る
                        days = max(int(range_match.group(1)), int(range_match.group(2)))
                        logger.info(f"📅 範囲表現を検出: {user_text} → {days}日（最大値）")
                        break
                
                if days is None:
                    # 範囲表現でない場合は通常の数値抽出
                    # カンマや全角カンマを削除してから数値を抽出
                    cleaned_text = user_text.replace(',', '').replace('、', '')
                    days_match = re.search(r'(\d+)', cleaned_text)
                    if days_match:
                        days = int(days_match.group(1))
                
                if days is not None:
                    duration = f"{days}日"
        
        if duration:
            # 期間の文字列から日数を抽出
            duration_days = None
            # 「14日」「2,3日」「2週間」などのパターンを抽出
            if '週間' in duration or '週' in duration:
                # 週間の場合は日数に変換
                weeks_match = re.search(r'(\d+)', duration)
                if weeks_match:
                    weeks = int(weeks_match.group(1))
                    duration_days = weeks * 7
            elif '日' in duration:
                # 日数の場合は数値を抽出
                # 範囲表現を検出（「2,3日」「2〜3日」「2-3日」など）
                range_patterns = [
                    r'(\d+)[,、](\d+)日',  # 「2,3日」「2、3日」
                    r'(\d+)[〜～](\d+)日',  # 「2〜3日」「2～3日」
                    r'(\d+)[-－](\d+)日',  # 「2-3日」「2－3日」
                ]
                days = None
                for pattern in range_patterns:
                    range_match = re.search(pattern, duration)
                    if range_match:
                        # 範囲表現の場合は最大値（後ろの数値）を取る
                        days = max(int(range_match.group(1)), int(range_match.group(2)))
                        logger.info(f"📅 範囲表現を検出（duration）: {duration} → {days}日（最大値）")
                        break
                
                if days is None:
                    # 範囲表現でない場合は通常の数値抽出
                    cleaned_duration = duration.replace(',', '').replace('、', '')
                    days_match = re.search(r'(\d+)', cleaned_duration)
                    if days_match:
                        days = int(days_match.group(1))
                
                if days is not None:
                    duration_days = days
            
            if duration_days and duration_days > 14:
                # 2週間を超えている場合、カウンセリングを中止して受診勧告
                counseling_mode['active'] = False
                session['counseling_mode'] = counseling_mode
                session.modified = True
                
                consultation_message = f"""
不眠の症状が{duration_days}日間続いているとのことですね。

2週間以上続く不眠は、一時的なものではなく、慢性的な不眠の可能性があります。
市販薬での対処には限界があるため、一度お近くの医療機関（内科、精神科、心療内科など）にご相談されることをお勧めします。

医療機関では、より適切な診断と治療を受けることができます。
"""
                
                logger.info(f"🚨 カウンセリング中止: 理由=期間が2週間を超えている（{duration_days}日）, "
                          f"質問回数={len(counseling_mode.get('question_history', []))}, "
                          f"収集情報数={len(collected_info)}")
                
                if session_id:
                    # ログ記録（通常時は会話履歴なし）
                    log_counseling_response(
                        session_id=session_id,
                        response_content=consultation_message.strip(),
                        response_type="counseling_summary_medical_consultation",
                        category=None,
                        confidence=None,
                        counseling_mode=counseling_mode,
                        user_input=user_text,
                        conversation_history=None
                    )
                
                return {
                    'type': 'counseling_summary',
                    'content': consultation_message.strip(),
                    'continue_counseling': False,
                    'recommendation': 'medical_consultation',
                    'completion_reason': 'duration_exceeded_2weeks'
                }
    
    # 不眠・眠気カウンセリング中に薬を希望した場合の検出
    if current_topic == "insomnia" or current_topic == "drowsiness":
        user_text_lower = user_text.lower()
        
        # 直前のメッセージを確認（医薬品情報メッセージに対する回答かどうか）
        messages = session.get('messages', [])
        is_medicine_info_response = False
        if messages:
            # 直前のbotメッセージを確認
            for msg in reversed(messages[-5:]):  # 直近5件を確認
                if msg.get('type') == 'bot' and msg.get('counseling_medicine_info'):
                    # 医薬品情報メッセージに対する回答
                    is_medicine_info_response = True
                    logger.info(f"✅ {current_topic}カウンセリング中の医薬品情報メッセージへの回答を検出")
                    break
        
        medicine_request_keywords = [
            "薬を教えて", "睡眠薬を教えて", "医薬品を知りたい", "薬を知りたい",
            "睡眠薬", "薬を", "医薬品を", "薬を教えて下さい", "薬を教えてください",
            "睡眠薬を教えて下さい", "睡眠薬を教えてください", "医薬品を教えて",
            "薬を推奨", "睡眠薬を推奨", "医薬品を推奨",
            "教えて欲しい", "教えてください", "教えて下さい", "教えて",
            "おしえてほしい","おしえて",
            "知りたい", "知りたいです", "知りたいです。", "知りたい。",
            "しりたい", "しりたいです", "しりたいです。", "しりたい。",
            "推奨して", "推奨してください", "推奨して下さい", "推奨して欲しい",
            "カフェイン", "カフェイン剤", "カフェイン剤を教えて", "眠気覚まし"
        ]
        
        # 「知りたい」「しりたい」系のキーワードは、直前のメッセージが医薬品情報メッセージの場合のみ検出
        simple_knowledge_keywords = ["知りたい", "知りたいです", "知りたいです。", "知りたい。", "しりたい", "しりたいです", "しりたいです。", "しりたい。"]
        has_simple_knowledge_keyword = any(keyword in user_text_lower for keyword in simple_knowledge_keywords)
        
        if has_simple_knowledge_keyword and not is_medicine_info_response:
            # 直前のメッセージが医薬品情報メッセージでない場合、薬推奨リクエストとして扱わない
            logger.info(f"⏭️ 「知りたい」系キーワードを検出しましたが、直前のメッセージが医薬品情報メッセージではないため、薬推奨リクエストとして扱いません")
        elif any(keyword in user_text_lower for keyword in medicine_request_keywords) or (has_simple_knowledge_keyword and is_medicine_info_response):
            # カウンセリングモードを終了し、Physicalカテゴリの処理に移行
            counseling_mode['active'] = False
            session['counseling_mode'] = counseling_mode
            session.modified = True
            
            logger.info(f"{current_topic}カウンセリングから薬推奨への切り替え: ユーザーが薬を希望")
            
            return {
                'type': 'topic_shift',
                'new_category': 'Physical',
                'topic_shift_result': {
                    'is_topic_shift': True,
                    'new_topic_category': 'Physical',
                    'relation_to_current_topic': 0.0,
                    'reasoning': f'ユーザーが薬を希望したため、{current_topic}カウンセリングから薬推奨に切り替え'
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
    return process_counseling_answer(
        user_text,
        session,
        session.get("messages", []),
        client,
        session_id=session_id,
    )
