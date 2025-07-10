from flask import Flask, render_template, request, session, jsonify
from medicine_logic import get_medicines_by_symptom, csv_load_status
from medicine_logic import select_symptoms_via_gpt, comprehensive_medicine_recommendation, chat_with_medicine_context
from debug_logger import performance_stats, network_logs, add_network_log
import json
import time
from datetime import datetime
import random
import logging

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # ターミナルに出力
        logging.FileHandler('app.log', encoding='utf-8')  # ファイルにも出力
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # セッション管理用

# キャッシュバスティング用のバージョン番号
VERSION = str(int(time.time()))

# AI自動応答制御用のグローバル変数
AI_AUTO_REPLY = True
ADMIN_MODE = False
MANUAL_REPLY_QUEUE = []  # 手動返信待ちのメッセージ

ALL_SESSIONS = {}  # {session_id: {'username': str, 'messages': list, 'last_activity': timestamp}}
USER_COUNTER = 1  # ユーザー名の連番
MAX_SESSIONS = 50  # 最大セッション数
SESSION_TIMEOUT = 3600  # セッションタイムアウト（秒）

def log_network_request(method, endpoint, request_data, response_data, response_time, status):
    """ネットワークリクエストをログ出力"""
    logger.info(f"🌐 NETWORK REQUEST:")
    logger.info(f"   Method: {method}")
    logger.info(f"   Endpoint: {endpoint}")
    logger.info(f"   Request Data: {request_data}")
    logger.info(f"   Response Time: {response_time}s")
    logger.info(f"   Status: {status}")
    if response_data:
        logger.info(f"   Response Data: {response_data}")

def log_medicine_logic_call(function_name, input_data, output_data, execution_time=None):
    """medicine_logic.pyの関数呼び出しをログ出力"""
    logger.info(f"💊 MEDICINE_LOGIC CALL:")
    logger.info(f"   Function: {function_name}")
    logger.info(f"   Input: {input_data}")
    if execution_time:
        logger.info(f"   Execution Time: {execution_time}s")
    logger.info(f"   Output: {output_data}")

def log_user_interaction(user_message, response_type, session_id, username):
    """ユーザーインタラクションをログ出力"""
    logger.info(f"👤 USER INTERACTION:")
    logger.info(f"   Session ID: {session_id}")
    logger.info(f"   Username: {username}")
    logger.info(f"   User Message: {user_message}")
    logger.info(f"   Response Type: {response_type}")

def log_system_status():
    """システムステータスをログ出力"""
    logger.info(f"📊 SYSTEM STATUS:")
    logger.info(f"   Active Sessions: {len(ALL_SESSIONS)}")
    logger.info(f"   AI Auto Reply: {AI_AUTO_REPLY}")
    logger.info(f"   Admin Mode: {ADMIN_MODE}")
    logger.info(f"   Manual Reply Queue: {len(MANUAL_REPLY_QUEUE)}")

def cleanup_old_sessions():
    """古いセッションをクリーンアップ"""
    global ALL_SESSIONS, USER_COUNTER
    current_time = time.time()
    expired_sessions = []
    
    for sid, info in ALL_SESSIONS.items():
        last_activity = info.get('last_activity', 0)
        if current_time - last_activity > SESSION_TIMEOUT:
            expired_sessions.append(sid)
    
    # 期限切れセッションを削除
    for sid in expired_sessions:
        del ALL_SESSIONS[sid]
        logger.info(f"🗑️ Expired session removed: {sid}")
    
    # セッション数が上限を超えた場合、最も古いセッションを削除
    if len(ALL_SESSIONS) > MAX_SESSIONS:
        oldest_sessions = sorted(ALL_SESSIONS.items(), key=lambda x: x[1].get('last_activity', 0))
        sessions_to_remove = len(ALL_SESSIONS) - MAX_SESSIONS
        for i in range(sessions_to_remove):
            sid = oldest_sessions[i][0]
            del ALL_SESSIONS[sid]
            logger.info(f"🗑️ Old session removed due to limit: {sid}")

def get_next_user_number():
    """次のユーザー番号を取得（既存の番号を再利用）"""
    global USER_COUNTER
    used_numbers = set()
    
    # 既存のセッションで使用されている番号を収集
    for info in ALL_SESSIONS.values():
        username = info.get('username', '')
        if username.startswith('ユーザー'):
            try:
                number = int(username.replace('ユーザー', ''))
                used_numbers.add(number)
            except ValueError:
                pass
    
    # 使用されていない最小の番号を見つける
    next_number = 1
    while next_number in used_numbers:
        next_number += 1
    
    # USER_COUNTERを更新（次回の効率化のため）
    USER_COUNTER = max(USER_COUNTER, next_number + 1)
    
    return next_number

def find_existing_session(client_ip, user_agent):
    """既存のセッションを検索（同じ人からのアクセスのみ）"""
    current_time = time.time()
    
    for existing_sid, info in ALL_SESSIONS.items():
        # IPアドレスとUser-Agentの両方が一致し、かつ30分以内のアクセス
        if (info.get('client_ip') == client_ip and 
            info.get('user_agent') == user_agent and 
            current_time - info.get('last_activity', 0) < 1800):  # 30分以内
            return existing_sid
    
    return None

def update_session_activity(sid):
    """セッションの最終アクティビティを更新"""
    if sid in ALL_SESSIONS:
        ALL_SESSIONS[sid]['last_activity'] = time.time()

@app.route('/', methods=['GET', 'POST'])
def index():
    # 古いセッションをクリーンアップ
    cleanup_old_sessions()
    
    current_time = time.time()
    client_ip = request.remote_addr
    user_agent = request.headers.get('User-Agent', '')
    
    # セッションIDの取得または作成
    sid = session.get('_id')
    if not sid:
        sid = str(int(time.time() * 1000)) + str(id(session))
        session['_id'] = sid
    
    # ユーザー名の設定
    if 'username' not in session:
        # 既存のセッションを検索（同じ人からのアクセスのみ）
        existing_session = find_existing_session(client_ip, user_agent)
        
        if existing_session:
            # 既存のセッションを再利用
            session['username'] = ALL_SESSIONS[existing_session]['username']
            session['messages'] = ALL_SESSIONS[existing_session]['messages'].copy()
            logger.info(f"🔄 Reusing existing session: {existing_session} for IP: {client_ip}, User: {session['username']}")
        else:
            # 新しいユーザー番号を取得
            user_number = get_next_user_number()
            session['username'] = f'ユーザー{user_number}'
            session['messages'] = []
            logger.info(f"👤 New user created: {session['username']} for IP: {client_ip}, User-Agent: {user_agent[:50]}...")
    else:
        logger.info(f"👤 Existing session accessed: {session['username']} for IP: {client_ip}")
    
    # メッセージの初期化
    if 'messages' not in session:
        session['messages'] = []
    
    if request.method == 'POST':
        user_message = request.form.get('message', '').strip()
        if user_message:
            # ユーザーインタラクションをログ出力
            log_user_interaction(user_message, "POST", session.get('_id', 'unknown'), session.get('username', 'unknown'))
            
            # 「終了」ワード検知
            if user_message in ['終了', 'end', 'おわり', '終わり', 'quit', 'exit']:
                logger.info(f"🔚 CHAT ENDED by user: {session.get('username', 'unknown')}")
                session.modified = True
                bot_response = {
                    'type': 'bot',
                    'content': 'チャットを終了しました。不明点がございましたら、お気軽にお近くの登録販売者にご相談ください。',
                    'diagnosis': None,
                    'chat_ended': True
                }
                session['messages'].append(bot_response)
                return render_template('index.html', messages=session.get('messages', []), version=VERSION, username=session['username'])
            if not AI_AUTO_REPLY:
                if ADMIN_MODE:
                    bot_response = None  # 管理者対応モード時は何も返さない
                else:
                    pending_message = {
                        'session_id': session.get('_id', 'unknown'),
                        'user_message': user_message,
                        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'status': 'pending'
                    }
                    MANUAL_REPLY_QUEUE.append(pending_message)
                    add_network_log(
                        'POST',
                        'メインサイト - 手動返信待ち',
                        {'symptom': user_message},
                        {'status': 'pending_manual_reply'},
                        0,
                        'pending'
                    )
                    bot_response = {
                        'type': 'bot',
                        'content': '申し訳ございません。現在、AI自動応答が一時停止されています。担当者が確認次第、回答いたします。',
                        'diagnosis': None
                    }
                if bot_response:
                    session['messages'].append(bot_response)
                session.modified = True
                return render_template('index.html', messages=session.get('messages', []), version=VERSION, username=session['username'])
            session['messages'].append({
                'type': 'user',
                'content': user_message
            })
            # AI自動応答がOFFの場合は手動返信待ちにする
            if not AI_AUTO_REPLY:
                pending_message = {
                    'session_id': session.get('_id', 'unknown'),
                    'user_message': user_message,
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'status': 'pending'
                }
                MANUAL_REPLY_QUEUE.append(pending_message)
                add_network_log(
                    'POST',
                    'メインサイト - 手動返信待ち',
                    {'symptom': user_message},
                    {'status': 'pending_manual_reply'},
                    0,
                    'pending'
                )
                bot_response = {
                    'type': 'bot',
                    'content': '申し訳ございません。現在、AI自動応答が一時停止されています。担当者が確認次第、回答いたします。',
                    'diagnosis': None
                }
            else:
                # 質問か症状入力かを判定
                is_question = not is_symptom_input(user_message)
                
                if is_question:
                    # 質問の場合：会話履歴と推奨医薬品の情報をChatGPTに渡す
                    logger.info(f"❓ QUESTION DETECTED: {user_message}")
                    try:
                        # 最新の推奨医薬品を取得
                        latest_recommended_medicines = []
                        for msg in reversed(session.get('messages', [])):
                            if msg.get('type') == 'bot' and msg.get('diagnosis'):
                                diagnosis = msg.get('diagnosis', {})
                                for msg in reversed(session.get('messages', [])):
                                    if msg.get('type') == 'bot' and msg.get('diagnosis'):
                                        diagnosis = msg.get('diagnosis', {})
                                        if diagnosis.get('recommended_medicines'):
                                            latest_recommended_medicines = diagnosis.get('recommended_medicines', [])
                                            break
                                
                                logger.info(f"📋 Latest recommended medicines: {len(latest_recommended_medicines)} items")
                                
                                # 会話履歴を取得（最新の10件程度）
                        conversation_history = session.get('messages', [])[-10:]
                        logger.info(f"💬 Conversation history: {len(conversation_history)} messages")
                        
                        # ChatGPTに質問を送信
                        start_time = time.time()
                        chat_response = chat_with_medicine_context(
                            user_message, 
                            conversation_history, 
                            latest_recommended_medicines
                        )
                        end_time = time.time()
                        execution_time = round(end_time - start_time, 3)
                        
                        # medicine_logic.pyの呼び出しをログ出力
                        log_medicine_logic_call(
                            "chat_with_medicine_context",
                            {
                                "user_message": user_message,
                                "conversation_history_length": len(conversation_history),
                                "recommended_medicines_count": len(latest_recommended_medicines)
                            },
                            chat_response,
                            execution_time
                        )
                        
                        # 回答をHTML形式で整形
                        bot_content = f"""
<div class="chat-response">
    <h4>💬 医薬品相談回答</h4>
    <div class="answer-section">
        <strong>回答:</strong><br>
        {chat_response.get('answer', '回答を取得できませんでした')}
    </div>
    
    <div class="details-section">
        <h5>📋 医薬品詳細</h5>
        <p>{chat_response.get('medicine_details', '詳細情報を取得できませんでした')}</p>
        
        <h5>💊 飲み合わせ・相互作用</h5>
        <p>{chat_response.get('interactions', '飲み合わせ情報を取得できませんでした')}</p>
        
        <h5>🏃 ドーピング規制チェック</h5>
        <p>{chat_response.get('doping_check', 'ドーピング規制の確認ができませんでした')}</p>
        
        <h5>⚠️ 副作用・注意点</h5>
        <p>{chat_response.get('side_effects', '副作用情報を取得できませんでした')}</p>
        
        <h5>🏥 医師相談のアドバイス</h5>
        <p>{chat_response.get('consultation_advice', '医師にご相談ください')}</p>
    </div>
</div>
"""
                        
                        bot_response = {
                            'type': 'bot',
                            'content': bot_content,
                            'diagnosis': {
                                'chat_response': chat_response,
                                'is_question': True
                            }
                        }
                        
                    except Exception as e:
                        logger.error(f"❌ 医薬品相談機能実行時エラー: {e}")
                        bot_content = f"申し訳ございません。システムエラーが発生しました: {str(e)}"
                    bot_response = {
                        'type': 'bot',
                            'content': bot_content,
                        'diagnosis': None
                    }
                else:
                    # 症状入力の場合：従来の医薬品推奨システムを使用
                    logger.info(f"🏥 SYMPTOM INPUT DETECTED: {user_message}")
                    last_diagnosis = None
                    
                    # ユーザー症状文をselect_symptoms_via_gptに渡してChatGPT返答をターミナルに表示
                    try:
                        logger.info(f"🔍 Calling select_symptoms_via_gpt...")
                        start_time = time.time()
                        matched_symptoms = select_symptoms_via_gpt(user_message)
                        end_time = time.time()
                        execution_time = round(end_time - start_time, 3)
                        
                        # medicine_logic.pyの呼び出しをログ出力
                        log_medicine_logic_call(
                            "select_symptoms_via_gpt",
                            {"user_message": user_message},
                            {"matched_symptoms": matched_symptoms},
                            execution_time
                        )
                    except Exception as e:
                        logger.error(f"❌ select_symptoms_via_gpt実行時エラー: {e}")
                    
                    # 包括的な医薬品推奨システムを使用
                    logger.info(f"💊 Calling comprehensive_medicine_recommendation...")
                    start_time = time.time()
                    try:
                        recommendation_result = comprehensive_medicine_recommendation(user_message)
                        end_time = time.time()
                        response_time = round(end_time - start_time, 3)
                        
                        # medicine_logic.pyの呼び出しをログ出力
                        log_medicine_logic_call(
                            "comprehensive_medicine_recommendation",
                            {"user_message": user_message},
                            {
                                "symptoms": recommendation_result.get('symptoms', []),
                                "medicine_type": recommendation_result.get('medicine_type', ''),
                                "recommended_medicines_count": len(recommendation_result.get('recommended_medicines', []))
                            },
                            response_time
                        )
                        
                        # ネットワークリクエストをログ出力
                        log_network_request(
                            'POST',
                            'メインサイト - 包括的医薬品推奨',
                            {'symptom': user_message},
                            {'recommendation': recommendation_result},
                            response_time,
                            'success'
                        )
                        
                        add_network_log(
                            'POST',
                            'メインサイト - 包括的医薬品推奨',
                            {'symptom': user_message},
                            {'recommendation': recommendation_result},
                            response_time,
                            'success'
                        )
                        
                        # 推奨結果を整形して表示
                        symptoms = recommendation_result.get('symptoms', [])
                        medicine_type = recommendation_result.get('medicine_type', '')
                        recommended_medicines = recommendation_result.get('recommended_medicines', [])
                        usage_notes = recommendation_result.get('usage_notes', '')
                        doctor_consultation = recommendation_result.get('doctor_consultation', '')
                        
                        # 結果をHTML形式で整形
                        bot_content = f"""
<div class="recommendation-result">
    <h4>🔍 症状分析結果</h4>
    <p><strong>推測される症状:</strong> {', '.join(symptoms) if symptoms else '特定できませんでした'}</p>
    <p><strong>医薬品の種類:</strong> {medicine_type}</p>
    
    <h4>💊 推奨医薬品</h4>
"""
                        
                        if recommended_medicines:
                            for medicine in recommended_medicines:
                                # 効能効果と成分が長すぎる場合は省略
                                efficacy = medicine.get('efficacy', '')
                                ingredients = medicine.get('ingredients', '')
                                
                                # 長いテキストを省略
                                if len(efficacy) > 200:
                                    efficacy = efficacy[:200] + "..."
                                if len(ingredients) > 200:
                                    ingredients = ingredients[:200] + "..."
                                
                                bot_content += f"""
    <div class="medicine-item">
        <h5>🏆 {medicine.get('number', '')}位: {medicine.get('product_name', '')}</h5>
        <p><strong>メーカー:</strong> {medicine.get('manufacturer', '')}</p>
        <p><strong>推奨理由:</strong> {medicine.get('reason', '')}</p>
        <p><strong>効能効果:</strong> {efficacy}</p>
        <p><strong>成分:</strong> {ingredients}</p>
    </div>
"""
                        else:
                            bot_content += "<p>適切な医薬品が見つかりませんでした。</p>"
                        
                        bot_content += f"""
    <h4>⚠️ 使用上の注意</h4>
    <p>{usage_notes}</p>
    
    <h4>🏥 医師の受診が必要な場合</h4>
    <p>{doctor_consultation}</p>
</div>
"""
                        
                        bot_diag = recommendation_result
                        
                    except Exception as e:
                        logger.error(f"❌ 包括的医薬品推奨システム実行時エラー: {e}")
                        bot_content = f"申し訳ございません。システムエラーが発生しました: {str(e)}"
                        bot_diag = None
                    
                    bot_response = {
                        'type': 'bot',
                        'content': bot_content,
                        'diagnosis': bot_diag
                    }
            session['messages'].append(bot_response)
            session.modified = True
    
    # ALL_SESSIONSにセッション情報を保存/更新
    # 既存のALL_SESSIONSエントリがある場合は、手動返信メッセージを保持
    if sid in ALL_SESSIONS:
        existing_session = ALL_SESSIONS[sid]
        existing_messages = existing_session.get('messages', [])
        
        # 手動返信メッセージを保持
        manual_replies = [msg for msg in existing_messages if msg.get('manual_reply')]
        
        # 現在のセッションメッセージに手動返信を追加
        current_messages = session['messages'].copy()
        for manual_reply in manual_replies:
            # 既に同じ内容の手動返信が含まれていないかチェック
            if not any(msg.get('manual_reply') and msg.get('content') == manual_reply.get('content') for msg in current_messages):
                current_messages.append(manual_reply)
        
        # ALL_SESSIONSを更新
        ALL_SESSIONS[sid] = {
            'username': session['username'],
            'messages': current_messages,
            'last_activity': current_time,
            'client_ip': client_ip,
            'user_agent': user_agent
        }
        
        # セッションをALL_SESSIONSの内容で更新
        session['messages'] = current_messages
        session.modified = True
        
        logger.info(f"📝 Session {sid} updated with manual replies: {len(current_messages)} messages")
        if manual_replies:
            logger.info(f"📝 Manual replies preserved: {len(manual_replies)} messages")
    else:
        # 新しいセッションの場合
        ALL_SESSIONS[sid] = {
            'username': session['username'],
            'messages': session['messages'].copy(),
            'last_activity': current_time,
            'client_ip': client_ip,
            'user_agent': user_agent
        }
    
    # 手動返信メッセージがあるかチェック
    manual_replies = [msg for msg in session['messages'] if msg.get('manual_reply')]
    if manual_replies:
        print(f"Manual replies found in session {sid}: {len(manual_replies)} messages")
        for i, reply in enumerate(manual_replies):
            print(f"  Manual reply {i+1}: {reply.get('content', '')[:50]}...")
    
    return render_template('index.html', messages=session.get('messages', []), version=VERSION, username=session['username'])

def is_symptom_input(message):
    """メッセージが症状入力かどうかを判定"""
    # 症状を示すキーワード
    symptom_keywords = [
        '痛い', '痛み', '熱', '咳', '鼻水', '頭痛', '腹痛', '吐き気', '下痢', '便秘',
        '痒い', '腫れ', '炎症', '発疹', 'めまい', 'だるい', '疲れ', '不調', '症状',
        '喉', '胃', '腸', '目', '耳', '鼻', '皮膚', '関節', '筋肉', '風邪', 'インフルエンザ'
    ]
    
    # 質問を示すキーワード
    question_keywords = [
        'ですか', 'でしょうか', 'ですか？', 'でしょうか？', 'どう', '何', 'なぜ', 'いつ',
        '副作用', '飲み方', '注意', '効果', '効き目', '時間', '回数', '量', '併用',
        '一緒に', '同時に', '飲んで', '使って', '服用', '投与', '飲み合わせ', 'ドーピング',
        'スポーツ', '競技', '運動', 'トレーニング', '試合', '大会', '検査', '陽性',
        '禁止', '規制', '成分', '効能', '効果', '作用', 'メカニズム', '仕組み',
        '飲む', '使う', '服用', '投与', '摂取', '飲むタイミング', '飲む時間',
        '食前', '食後', '食間', '空腹時', '満腹時', '就寝前', '起床時',
        '他の薬', '併用', '同時', '一緒', '組み合わせ', '飲み合わせ',
        '注意点', '気をつける', '避ける', '控える', '中止', '停止',
        '効果', '効き目', '効く', '効かない', '効果的', '効果的でない',
        '副作用', '副作用が出る', '副作用がある', '副作用がない',
        '安全', '危険', 'リスク', '危険性', '安全性'
    ]
    
    # 質問キーワードが含まれている場合は質問と判定
    for keyword in question_keywords:
        if keyword in message:
            return False
    
    # 症状キーワードが含まれている場合は症状入力と判定
    for keyword in symptom_keywords:
        if keyword in message:
            return True
    
    # 文末が「？」の場合は質問と判定
    if message.strip().endswith('？') or message.strip().endswith('?'):
        return False
    
    # デフォルトは症状入力として扱う
    return True

@app.route('/clear', methods=['POST'])
def clear_chat():
    """チャット履歴をクリア"""
    session['messages'] = []
    session.modified = True
    sid = session.get('_id')
    if sid and sid in ALL_SESSIONS:
        ALL_SESSIONS[sid]['messages'] = []
    # 「チャットを終了しました。」フラグも消す
    session.pop('chat_ended', None)
    return '', 204

@app.route('/api/status')
def api_status():
    """システム状況を返す"""
    try:
        # csv_load_statusのpathを文字列として確実に返す
        csv_path = csv_load_status.get('path')
        if csv_path is not None:
            csv_path_str = str(csv_path)
        else:
            csv_path_str = None
            
        status_data = {
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'csv_load_status': {
                'success': csv_load_status.get('success', False),
                'encoding': csv_load_status.get('encoding'),
                'error': csv_load_status.get('error'),
                'row_count': csv_load_status.get('row_count', 0),
                'col_count': csv_load_status.get('col_count', 0),
                'columns': csv_load_status.get('columns', []),
                'path': csv_path_str
            },
            'session_active': 'messages' in session,
            'message_count': len(session.get('messages', [])),
            'version': VERSION
        }
        return jsonify(status_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/performance')
def api_performance():
    """パフォーマンス統計を返す"""
    try:
        return jsonify(performance_stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/logs')
def api_logs():
    """通信ログを返す"""
    try:
        # network_logsが配列でない場合は空配列を返す
        if not isinstance(network_logs, list):
            return jsonify([])
        return jsonify(network_logs)
    except Exception as e:
        # エラーの場合も空配列を返す
        return jsonify([])

@app.route('/api/sessions')
def api_sessions():
    """セッション情報を返す"""
    try:
        # 現在のセッション情報を取得
        session_data = {
            'session_id': session.get('_id', 'unknown'),
            'messages_count': len(session.get('messages', [])),
            'last_activity': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'session_active': 'messages' in session,
            'messages': session.get('messages', [])
        }
        # usage_notesを直近のbotレスポンスから抽出
        latest_usage_notes = None
        messages = session.get('messages', [])
        for msg in reversed(messages):
            if msg.get('type') == 'bot':
                # diagnosisにusage_notesがあれば優先
                diagnosis = msg.get('diagnosis')
                if isinstance(diagnosis, dict) and 'usage_notes' in diagnosis:
                    latest_usage_notes = diagnosis['usage_notes']
                # content直下にusage_notesがあればそれも考慮
                if not latest_usage_notes and 'usage_notes' in msg:
                    latest_usage_notes = msg['usage_notes']
                break
        session_data['latest_usage_notes'] = latest_usage_notes
        return jsonify(session_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ai_control', methods=['GET', 'POST'])
def api_ai_control():
    """AI自動応答の制御"""
    global AI_AUTO_REPLY
    
    if request.method == 'GET':
        return jsonify({
            'ai_auto_reply': AI_AUTO_REPLY,
            'manual_reply_queue_count': len(MANUAL_REPLY_QUEUE)
        })
    
    elif request.method == 'POST':
        data = request.get_json()
        mode = data.get('mode')
        
        if mode in ['on', 'off']:
            AI_AUTO_REPLY = (mode == 'on')
            return jsonify({
                'ai_auto_reply': AI_AUTO_REPLY,
                'message': f'AI自動応答を{"ON" if AI_AUTO_REPLY else "OFF"}にしました'
            })
        else:
            return jsonify({'error': 'Invalid mode. Use "on" or "off"'}), 400
    
    return jsonify({'error': 'Method not allowed'}), 405

@app.route('/api/manual_reply_queue', methods=['GET', 'POST'])
def api_manual_reply_queue():
    """手動返信待ちキュー"""
    global MANUAL_REPLY_QUEUE, ALL_SESSIONS
    
    if request.method == 'GET':
        return jsonify(MANUAL_REPLY_QUEUE)
    
    elif request.method == 'POST':
        data = request.get_json()
        session_id = data.get('session_id')
        reply_message = data.get('reply_message')
        
        print(f"Manual reply request received: session_id={session_id}, message={reply_message}")
        print(f"Current ALL_SESSIONS keys: {list(ALL_SESSIONS.keys())}")
        
        if not session_id or not reply_message:
            return jsonify({'error': 'session_id and reply_message are required'}), 400
        
        # キューから該当するメッセージを削除
        for i, pending in enumerate(MANUAL_REPLY_QUEUE):
            if pending['session_id'] == session_id:
                MANUAL_REPLY_QUEUE.pop(i)
                print(f"Removed pending message from queue for session {session_id}")
                break
        
        # 指定されたセッションIDのユーザーセッションに返信メッセージを追加
        if session_id in ALL_SESSIONS:
            # ALL_SESSIONSから対象セッションを取得
            target_session = ALL_SESSIONS[session_id]
            print(f"Found target session: {target_session}")
            
            # 返信メッセージを追加
            manual_reply_message = {
                'type': 'bot',
                'content': reply_message,
                'diagnosis': None,
                'manual_reply': True  # 手動返信のフラグ
            }
            
            target_session['messages'].append(manual_reply_message)
            target_session['last_activity'] = time.time()  # 最終アクティビティを更新
            
            # ALL_SESSIONSを更新
            ALL_SESSIONS[session_id] = target_session
            
            # ログに記録
            add_network_log(
                'POST',
                'メインサイト - 手動返信',
                {'session_id': session_id, 'reply': reply_message},
                {'status': 'manual_reply_sent'},
                0,
                'success'
            )
            
            logger.info(f"📝 Manual reply sent to session {session_id}: {reply_message}")
            logger.info(f"📝 ALL_SESSIONS updated: {len(ALL_SESSIONS[session_id]['messages'])} messages")
            logger.info(f"📝 Target session info: {target_session}")
            logger.info(f"📝 Updated ALL_SESSIONS for {session_id}: {ALL_SESSIONS[session_id]}")
            logger.info(f"📝 Manual reply message added: {manual_reply_message}")
            
            # メインサイトでの反映確認用ログ
            logger.info(f"=== Manual Reply Summary ===")
            logger.info(f"Session ID: {session_id}")
            logger.info(f"Total messages in ALL_SESSIONS: {len(ALL_SESSIONS[session_id]['messages'])}")
            logger.info(f"Manual reply messages: {len([msg for msg in ALL_SESSIONS[session_id]['messages'] if msg.get('manual_reply')])}")
            logger.info(f"Latest message: {ALL_SESSIONS[session_id]['messages'][-1] if ALL_SESSIONS[session_id]['messages'] else 'None'}")
            logger.info(f"===========================")
            
            return jsonify({
                'message': '手動返信を送信しました',
                'remaining_queue': len(MANUAL_REPLY_QUEUE),
                'target_session_id': session_id,
                'messages_count': len(target_session['messages']),
                'session_updated': True
            })
        else:
            logger.error(f"❌ Session {session_id} not found in ALL_SESSIONS")
            logger.error(f"❌ Available sessions: {list(ALL_SESSIONS.keys())}")
            logger.error(f"❌ ALL_SESSIONS content: {ALL_SESSIONS}")
            return jsonify({'error': f'Session {session_id} not found'}), 404
    
    return jsonify({'error': 'Method not allowed'}), 405

@app.route('/api/all_sessions')
def api_all_sessions():
    result = []
    for sid, info in ALL_SESSIONS.items():
        result.append({
            'session_id': sid,
            'username': info.get('username', ''),
            'messages': info.get('messages', []),
            'messages_count': len(info.get('messages', []))
        })
    
    # デバッグ用ログ
    logger.info(f"📊 ALL_SESSIONS API called: {len(result)} sessions")
    for session_info in result:
        logger.info(f"📊 Session {session_info['session_id']}: {session_info['messages_count']} messages")
    
    return jsonify(result)

@app.route('/api/session_stats')
def api_session_stats():
    """セッション管理の統計情報を返す"""
    try:
        current_time = time.time()
        active_sessions = 0
        expired_sessions = 0
        used_user_numbers = set()
        session_details = []
        
        for sid, info in ALL_SESSIONS.items():
            last_activity = info.get('last_activity', 0)
            if current_time - last_activity < SESSION_TIMEOUT:
                active_sessions += 1
                # ユーザー番号を収集
                username = info.get('username', '')
                if username.startswith('ユーザー'):
                    try:
                        number = int(username.replace('ユーザー', ''))
                        used_user_numbers.add(number)
                    except ValueError:
                        pass
                
                # セッション詳細情報を収集
                session_details.append({
                    'session_id': sid,
                    'username': username,
                    'client_ip': info.get('client_ip', ''),
                    'user_agent': info.get('user_agent', '')[:50] + '...' if len(info.get('user_agent', '')) > 50 else info.get('user_agent', ''),
                    'messages_count': len(info.get('messages', [])),
                    'last_activity': datetime.fromtimestamp(last_activity).strftime("%Y-%m-%d %H:%M:%S"),
                    'age_minutes': int((current_time - last_activity) / 60)
                })
            else:
                expired_sessions += 1
        
        stats = {
            'total_sessions': len(ALL_SESSIONS),
            'active_sessions': active_sessions,
            'expired_sessions': expired_sessions,
            'max_sessions': MAX_SESSIONS,
            'session_timeout': SESSION_TIMEOUT,
            'current_user_counter': USER_COUNTER,
            'used_user_numbers': sorted(list(used_user_numbers)),
            'next_available_number': get_next_user_number(),
            'session_details': session_details,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/debug_manual_replies')
def api_debug_manual_replies():
    """手動返信のデバッグ情報を返す"""
    try:
        debug_info = {
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'total_sessions': len(ALL_SESSIONS),
            'sessions_with_manual_replies': [],
            'manual_reply_queue': MANUAL_REPLY_QUEUE
        }
        
        for sid, info in ALL_SESSIONS.items():
            manual_replies = [msg for msg in info.get('messages', []) if msg.get('manual_reply')]
            if manual_replies:
                debug_info['sessions_with_manual_replies'].append({
                    'session_id': sid,
                    'username': info.get('username', ''),
                    'manual_replies_count': len(manual_replies),
                    'manual_replies': manual_replies,
                    'total_messages': len(info.get('messages', []))
                })
        
        return jsonify(debug_info)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/new_session', methods=['POST'])
def new_session():
    """新しいセッションを開始"""
    global ALL_SESSIONS
    session.clear()  # 現在のセッション情報をクリア

    # 新しいセッションIDとユーザー名を割り当て
    sid = str(int(time.time() * 1000)) + str(id(session))
    session['_id'] = sid
    user_number = get_next_user_number()
    session['username'] = f'ユーザー{user_number}'
    session['messages'] = []
    session.modified = True

    # ALL_SESSIONSにも新規登録
    current_time = time.time()
    client_ip = request.remote_addr
    user_agent = request.headers.get('User-Agent', '')
    ALL_SESSIONS[sid] = {
        'username': session['username'],
        'messages': [],
        'last_activity': current_time,
        'client_ip': client_ip,
        'user_agent': user_agent
    }

    return jsonify({'message': '新しいセッションを開始しました', 'username': session['username']}), 200

@app.route('/api/request_admin', methods=['POST'])
def request_admin():
    """管理者対応要請を受け付ける"""
    global AI_AUTO_REPLY
    sid = session.get('_id')
    username = session.get('username', 'unknown')
    if sid:
        # セッションに要請フラグを追加
        if sid in ALL_SESSIONS:
            ALL_SESSIONS[sid]['admin_request'] = True
        session['admin_request'] = True
        # メッセージ履歴にも記録
        session['messages'].append({
            'type': 'system',
            'content': '薬剤師を要請しました。しばらくお待ちください。',
            'admin_request': True
        })
        session.modified = True
        # MANUAL_REPLY_QUEUEに同じセッションIDのadmin_requestがなければ追加
        already_exists = any(item.get('session_id') == sid and item.get('admin_request') for item in MANUAL_REPLY_QUEUE)
        if not already_exists:
            MANUAL_REPLY_QUEUE.append({
                'session_id': sid,
                'user_message': '薬剤師を要請しました。しばらくお待ちください。',
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'status': 'admin_requested',
                'admin_request': True
            })
        # AI自動応答をOFFにする
        AI_AUTO_REPLY = False
        return jsonify({'status': 'ok'})
    return jsonify({'status': 'error', 'message': 'No session'}), 400

@app.route('/api/admin_mode', methods=['POST'])
def api_admin_mode():
    global ADMIN_MODE, AI_AUTO_REPLY
    ADMIN_MODE = True
    AI_AUTO_REPLY = False
    return jsonify({'admin_mode': ADMIN_MODE, 'ai_auto_reply': AI_AUTO_REPLY, 'message': '管理者対応モードに切り替えました'})

if __name__ == '__main__':
    logger.info("🚀 Starting Medicine Recommendation System...")
    logger.info(f"📁 CSVファイル絶対パス: {csv_load_status['path']}")
    logger.info("🔑 環境変数からAPIキーを取得できませんでした。直接設定されたAPIキーを使用します。")
    logger.info("✅ OpenAI client initialized successfully.")
    logger.info("✅ CSVファイルを正常に読み込みました（エンコーディング: utf-8）。")
    
    # システムステータスをログ出力
    log_system_status()
    
    logger.info("🌐 Starting Flask development server...")
    app.run(debug=True, port=5000) 