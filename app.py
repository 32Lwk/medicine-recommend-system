from flask import Flask, render_template, request, session, jsonify
from medicine_logic import get_medicines_by_symptom, csv_load_status
from medicine_logic import select_symptoms_via_gpt, comprehensive_medicine_recommendation, chat_with_medicine_context
from medicine_logic import rule_based_medicine_recommendation, analyze_symptoms_and_medicine_type, client
from debug_logger import performance_stats, network_logs, add_network_log
from typing import Dict, List
import json
import time
import os
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
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')  # セッション管理用

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

# グローバルエラーハンドラー
@app.errorhandler(500)
def handle_500_error(e):
    """500エラーのハンドラー"""
    logger.error(f"❌ 500 Internal Server Error: {str(e)}")
    logger.error(f"❌ エラータイプ: {type(e).__name__}")
    
    import traceback
    logger.error(f"❌ トレースバック:\n{traceback.format_exc()}")
    
    # APIキーのチェック
    if not os.getenv('OPENAI_API_KEY'):
        logger.error("❌ OPENAI_API_KEY が環境変数に設定されていません！")
        error_msg = "⚠️ OpenAI APIキーが設定されていません。Renderの環境変数を確認してください。"
    else:
        error_msg = "申し訳ございません。システムエラーが発生しました。管理者に連絡してください。"
    
    # JSONリクエストの場合
    if request.is_json or request.method == 'POST':
        return jsonify({
            'error': True,
            'response': error_msg,
            'error_type': type(e).__name__ if os.getenv('FLASK_ENV') != 'production' else None
        }), 500
    
    # HTMLリクエストの場合
    return f"<h1>エラー</h1><p>{error_msg}</p>", 500

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
    """古いセッションをクリーンアップ（無効化）"""
    # セッションの自動削除を無効化
    # 管理者が手動でセッションを管理できるようにする
    pass

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
    # ALL_SESSIONSから復元（Cookieサイズ削減のため）
    if sid and sid in ALL_SESSIONS:
        session['messages'] = ALL_SESSIONS[sid].get('messages', []).copy()
        logger.info(f"📥 Session messages restored from ALL_SESSIONS: {len(session['messages'])} messages")
    elif 'messages' not in session:
        session['messages'] = []
    
    # ユーザー属性データの初期化（セッション管理）
    if 'user_attributes' not in session:
        session['user_attributes'] = {
            'age': None,
            'gender': None,
            'pregnant': None,
            'breastfeeding': None,
            'current_medications': [],
            'allergies': [],
            'medical_history': [],
            'symptom_duration_days': None,
            'other_info': None
        }
    
    if request.method == 'POST':
        logger.info(f"📨 POST処理開始")
        user_message = request.form.get('message', '').strip()
        logger.info(f"📝 受信メッセージ: {user_message}")
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
                # ALL_SESSIONSを更新
                if sid and sid in ALL_SESSIONS:
                    ALL_SESSIONS[sid]['messages'] = session['messages'].copy()
                message_count = len(session['messages'])
                logger.info(f"✅ POST処理完了（チャット終了） - JSON返却: {message_count} messages")
                return jsonify({'status': 'ok', 'message_count': message_count})
            
            # ユーザーメッセージを追加（AI自動応答ON/OFF問わず）
            session['messages'].append({
                'type': 'user',
                'content': user_message
            })
            
            # 個別チャット単位でAI自動応答のON/OFFを確認（デフォルトはTrue）
            chat_ai_auto_reply = ALL_SESSIONS.get(sid, {}).get('ai_auto_reply', True)
            
            # AI自動応答がOFFの場合は手動返信待ちにする
            if not chat_ai_auto_reply:
                if ADMIN_MODE:
                    # 管理者対応モード時は自動返信せず、ユーザーメッセージのみ保存
                    session.modified = True
                    
                    # ALL_SESSIONSを更新
                    if sid and sid in ALL_SESSIONS:
                        ALL_SESSIONS[sid]['messages'] = session['messages'].copy()
                    
                    message_count = len(session['messages'])
                    logger.info(f"✅ POST処理完了（管理者対応モード） - JSON返却: {message_count} messages")
                    return jsonify({'status': 'ok', 'message_count': message_count})
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
                    session['messages'].append(bot_response)
                    session.modified = True
                    
                    # ALL_SESSIONSを更新
                    if sid and sid in ALL_SESSIONS:
                        ALL_SESSIONS[sid]['messages'] = session['messages'].copy()
                    
                    message_count = len(session['messages'])
                    logger.info(f"✅ POST処理完了（手動返信待ち） - JSON返却: {message_count} messages")
                    return jsonify({'status': 'ok', 'message_count': message_count})
            
            # AI自動応答がONの場合の通常処理
            # 質問か症状入力かを判定
            is_question = not is_symptom_input(user_message)
            add_reanalysis_message = False  # 再分析メッセージフラグ
            original_user_message = None  # 元のユーザーメッセージ
            
            if is_question:
                # 質問の場合：ChatGPTで属性データを抽出し、必要なら再分析
                logger.info(f"❓ QUESTION/ATTRIBUTE RESPONSE DETECTED: {user_message}")
                
                # ステップ1: ユーザー属性を抽出・更新
                user_attributes = session.get('user_attributes', {
                    'age': None,
                    'gender': None,
                    'pregnant': None,
                    'breastfeeding': None,
                    'current_medications': [],
                    'allergies': [],
                    'medical_history': [],
                    'symptom_duration_days': None,
                    'other_info': None
                })
                
                # ChatGPTを使用して属性情報を抽出
                import re
                import json
                from openai import OpenAI
                
                updated = False
                
                # OpenAI clientを初期化
                api_key = os.getenv('OPENAI_API_KEY')
                if not api_key:
                    return jsonify({
                        'error': True,
                        'response': '⚠️ システムエラー: OpenAI APIキーが設定されていません。管理者に連絡してください。'
                    })
                client = OpenAI(api_key=api_key)
                
                # ChatGPTによる属性抽出
                try:
                    prompt = f"""
ユーザーのメッセージから以下の属性情報を抽出してください：

【ユーザーメッセージ】
{user_message}

【抽出すべき情報】
1. 年齢（数値のみ）
2. 性別（男性/女性）
3. 妊娠状態（true/false/null）
4. 授乳状態（true/false/null）
5. アレルギー（配列形式、なしの場合は["なし"]）
6. 現在服用中の薬（配列形式、なしの場合は[]）
7. 既往症（配列形式、なしの場合は[]）
8. 症状の持続期間（日数、不明の場合はnull）
9. その他伝えたいこと（文字列、なしの場合はnull）

【回答形式】
以下のJSON形式で回答してください：
{{
    "age": 数値またはnull,
    "gender": "男性"または"女性"またはnull,
    "pregnant": true/false/null,
    "breastfeeding": true/false/null,
    "allergies": ["アレルギー1", "アレルギー2"]または["なし"]または[],
    "current_medications": ["薬1", "薬2"]または[],
    "medical_history": ["既往症1", "既往症2"]または[],
    "symptom_duration_days": 数値またはnull,
    "other_info": "文字列"またはnull
}}

注意：
- 情報が明示されていない場合はnullを使用
- アレルギーがない場合は["なし"]
- 薬や既往症がない場合は空配列[]
- 症状期間は日数で回答（例：3日前から → 3）
"""

                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": "あなたは医療情報抽出システムです。ユーザーのメッセージから正確に属性情報を抽出してください。"},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.1,
                        max_tokens=500
                    )
                    
                    result = response.choices[0].message.content
                    
                    # JSON解析
                    json_start = result.find('{')
                    json_end = result.rfind('}') + 1
                    
                    if json_start != -1 and json_end != -1:
                        json_str = result[json_start:json_end]
                        extracted_attrs = json.loads(json_str)
                        
                        logger.info(f"🤖 ChatGPT抽出結果: {extracted_attrs}")
                        
                        # 抽出された情報をセッションに保存
                        for key, value in extracted_attrs.items():
                            if value is not None and value != [] and value != "":
                                if key == 'age' and isinstance(value, (int, float)):
                                    user_attributes['age'] = int(value)
                                    logger.info(f"📝 年齢を更新: {user_attributes['age']}")
                                    updated = True
                                elif key == 'gender' and value in ['男性', '女性']:
                                    user_attributes['gender'] = value
                                    logger.info(f"📝 性別を更新: {user_attributes['gender']}")
                                    updated = True
                                elif key == 'pregnant' and isinstance(value, bool):
                                    user_attributes['pregnant'] = value
                                    logger.info(f"📝 妊娠状態を更新: {user_attributes['pregnant']}")
                                    updated = True
                                elif key == 'breastfeeding' and isinstance(value, bool):
                                    user_attributes['breastfeeding'] = value
                                    logger.info(f"📝 授乳状態を更新: {user_attributes['breastfeeding']}")
                                    updated = True
                                elif key == 'allergies' and isinstance(value, list):
                                    user_attributes['allergies'] = value
                                    logger.info(f"📝 アレルギーを更新: {user_attributes['allergies']}")
                                    updated = True
                                elif key == 'current_medications' and isinstance(value, list):
                                    user_attributes['current_medications'] = value
                                    logger.info(f"📝 服用中の薬を更新: {user_attributes['current_medications']}")
                                    updated = True
                                elif key == 'medical_history' and isinstance(value, list):
                                    user_attributes['medical_history'] = value
                                    logger.info(f"📝 既往症を更新: {user_attributes['medical_history']}")
                                    updated = True
                                elif key == 'symptom_duration_days' and isinstance(value, (int, float)):
                                    user_attributes['symptom_duration_days'] = int(value)
                                    logger.info(f"📝 症状期間を更新: {user_attributes['symptom_duration_days']}日")
                                    updated = True
                                elif key == 'other_info' and isinstance(value, str):
                                    user_attributes['other_info'] = value
                                    logger.info(f"📝 その他情報を更新: {user_attributes['other_info']}")
                                    updated = True
                    
                except Exception as e:
                    logger.error(f"ChatGPT属性抽出エラー: {e}")
                    logger.info("フォールバック: 正規表現による抽出に切り替えます")
                    
                    # フォールバック: 正規表現による抽出
                    # 年齢（日本語と英語）
                    age_match = re.search(r'(\d+)歳', user_message)
                    if age_match:
                        user_attributes['age'] = int(age_match.group(1))
                        logger.info(f"📝 年齢を更新: {user_attributes['age']}")
                        updated = True
                    else:
                        # 英語の年齢パターン
                        age_match_en = re.search(r'(\d+)\s*years?\s*old', user_message, re.IGNORECASE)
                        if age_match_en:
                            user_attributes['age'] = int(age_match_en.group(1))
                            logger.info(f"📝 年齢を更新: {user_attributes['age']}")
                            updated = True
                    
                    # 性別（日本語と英語）
                    if '男性' in user_message or '男' in user_message or 'male' in user_message.lower():
                        user_attributes['gender'] = '男性'
                        logger.info(f"📝 性別を更新: 男性")
                        updated = True
                    elif '女性' in user_message or '女' in user_message or 'female' in user_message.lower():
                        user_attributes['gender'] = '女性'
                        logger.info(f"📝 性別を更新: 女性")
                        updated = True
                    
                    # 妊娠・授乳（フォールバック処理）
                    if '妊娠' in user_message:
                        if '妊娠していません' in user_message or '妊娠中ではありません' in user_message or '妊娠していない' in user_message:
                            user_attributes['pregnant'] = False
                            logger.info(f"📝 妊娠状態を更新: False（妊娠していない）")
                        elif '妊娠中です' in user_message or '妊娠中' in user_message or '妊娠しています' in user_message:
                            user_attributes['pregnant'] = True
                            logger.info(f"📝 妊娠状態を更新: True（妊娠中）")
                        updated = True
                    
                    if '授乳' in user_message:
                        if '授乳していません' in user_message or '授乳中ではありません' in user_message or '授乳していない' in user_message:
                            user_attributes['breastfeeding'] = False
                            logger.info(f"📝 授乳状態を更新: False（授乳していない）")
                        elif '授乳中です' in user_message or '授乳中' in user_message or '授乳しています' in user_message:
                            user_attributes['breastfeeding'] = True
                            logger.info(f"📝 授乳状態を更新: True（授乳中）")
                        updated = True
                
                # アレルギー（日本語と英語）
                if 'アレルギー' in user_message or 'allergy' in user_message.lower() or 'allergies' in user_message.lower():
                    if ('ない' in user_message or 'いいえ' in user_message or 'ありません' in user_message or 'なし' in user_message or 
                        'no allergy' in user_message.lower() or 'no allergies' in user_message.lower()):
                        user_attributes['allergies'] = ['なし']
                    else:
                        # 日本語のアレルギー抽出
                        allergens = re.findall(r'([ぁ-んァ-ヶー]+)アレルギー', user_message)
                        if allergens:
                            user_attributes['allergies'] = allergens
                        else:
                            # 英語のアレルギー抽出
                            allergy_match = re.search(r'have\s+([^,\s]+)\s+allergy', user_message, re.IGNORECASE)
                            if allergy_match:
                                user_attributes['allergies'] = [allergy_match.group(1)]
                    logger.info(f"📝 アレルギーを更新: {user_attributes['allergies']}")
                    updated = True
                
                # 症状期間（日本語と英語）
                if ('続いています' in user_message or 'から' in user_message or 
                    'started' in user_message.lower() or 'ago' in user_message.lower()):
                    duration_patterns = [
                        (r'(今日|きょう)から', 0),
                        (r'(昨日|きのう)から', 1),
                        (r'(\d+)日前から', None),
                        (r'(\d+)週間前から', None),
                        # 英語のパターン
                        (r'(\d+)\s*days?\s*ago', None),
                        (r'(\d+)\s*weeks?\s*ago', None),
                        (r'(\d+)\s*months?\s*ago', None)
                    ]
                    for pattern, days in duration_patterns:
                        match = re.search(pattern, user_message)
                        if match:
                            if days is not None:
                                user_attributes['symptom_duration_days'] = days
                            else:
                                # 数値を抽出
                                if '日前' in user_message:
                                    num_match = re.search(r'(\d+)日前', user_message)
                                    if num_match:
                                        user_attributes['symptom_duration_days'] = int(num_match.group(1))
                                elif '週間前' in user_message:
                                    num_match = re.search(r'(\d+)週間前', user_message)
                                    if num_match:
                                        user_attributes['symptom_duration_days'] = int(num_match.group(1)) * 7
                                elif 'days ago' in user_message.lower():
                                    num_match = re.search(r'(\d+)\s*days?\s*ago', user_message, re.IGNORECASE)
                                    if num_match:
                                        user_attributes['symptom_duration_days'] = int(num_match.group(1))
                                elif 'weeks ago' in user_message.lower():
                                    num_match = re.search(r'(\d+)\s*weeks?\s*ago', user_message, re.IGNORECASE)
                                    if num_match:
                                        user_attributes['symptom_duration_days'] = int(num_match.group(1)) * 7
                                elif 'months ago' in user_message.lower():
                                    num_match = re.search(r'(\d+)\s*months?\s*ago', user_message, re.IGNORECASE)
                                    if num_match:
                                        user_attributes['symptom_duration_days'] = int(num_match.group(1)) * 30
                            logger.info(f"📝 症状期間を更新: {user_attributes.get('symptom_duration_days')}日前から")
                            updated = True
                            break
                
                # 服用中の薬（日本語と英語）
                if ('服用している薬はありません' in user_message or '他に服用している薬はありません' in user_message or '薬は飲んでいません' in user_message or
                    'not taking' in user_message.lower() or 'no medication' in user_message.lower()):
                    user_attributes['current_medications'] = []
                    logger.info(f"📝 服用中の薬なしを確認")
                    updated = True
                elif ('服用している' in user_message or '飲んでいる' in user_message or '薬を' in user_message or
                      'taking' in user_message.lower() or 'medication' in user_message.lower() or 'medicine' in user_message.lower()):
                    # 薬の名前を抽出（日本語と英語）
                    medication_patterns = [
                        r'服用している薬[はが]?([^。、\n]+)',
                        r'飲んでいる薬[はが]?([^。、\n]+)',
                        r'薬[はが]?([^。、\n]+)',
                        r'([^。、\n]*薬[^。、\n]*)',
                        # 英語のパターン
                        r'taking\s+([^,\s]+(?:\s+[^,\s]+)*)',
                        r'medication[:\s]+([^,\n]+)',
                        r'medicine[:\s]+([^,\n]+)'
                    ]
                    
                    for pattern in medication_patterns:
                        match = re.search(pattern, user_message)
                        if match:
                            medication_name = match.group(1).strip()
                            if medication_name and medication_name not in user_attributes['current_medications']:
                                user_attributes['current_medications'].append(medication_name)
                                logger.info(f"📝 服用中の薬を抽出: {medication_name}")
                                updated = True
                                break
                
                # 既往症の抽出（日本語と英語）
                if ('既往症' in user_message or '病気' in user_message or '疾患' in user_message or
                    'history' in user_message.lower() or 'disease' in user_message.lower() or 'condition' in user_message.lower()):
                    # 既往症のパターンを抽出
                    history_patterns = [
                        r'既往症[はが]?([^。、\n]+)',
                        r'病気[はが]?([^。、\n]+)',
                        r'疾患[はが]?([^。、\n]+)',
                        r'([^。、\n]*病[^。、\n]*)',
                        # 英語のパターン
                        r'have\s+([^,\s]+(?:\s+[^,\s]+)*)\s+history',
                        r'history\s+of\s+([^,\n]+)',
                        r'disease[:\s]+([^,\n]+)',
                        r'condition[:\s]+([^,\n]+)'
                    ]
                    
                    for pattern in history_patterns:
                        match = re.search(pattern, user_message)
                        if match:
                            history_name = match.group(1).strip()
                            if history_name and history_name not in user_attributes['medical_history']:
                                user_attributes['medical_history'].append(history_name)
                                logger.info(f"📝 既往症を抽出: {history_name}")
                                updated = True
                                break
                
                # その他伝えたいことの抽出（日本語と英語）
                if ('その他' in user_message or '伝えたい' in user_message or '他に' in user_message or
                    'want to know' in user_message.lower() or 'ask about' in user_message.lower() or 'tell you' in user_message.lower()):
                    # その他の情報を抽出
                    other_patterns = [
                        r'その他[はが]?([^。、\n]+)',
                        r'伝えたいこと[はが]?([^。、\n]+)',
                        r'他に[はが]?([^。、\n]+)',
                        # 英語のパターン
                        r'want to know about\s+([^,\n]+)',
                        r'ask about\s+([^,\n]+)',
                        r'tell you\s+([^,\n]+)'
                    ]
                    
                    for pattern in other_patterns:
                        match = re.search(pattern, user_message)
                        if match:
                            other_info = match.group(1).strip()
                            if other_info:
                                user_attributes['other_info'] = other_info
                                logger.info(f"📝 その他情報を抽出: {other_info}")
                                updated = True
                                break
                
                # セッションに保存
                session['user_attributes'] = user_attributes
                session.modified = True
                
                # ALL_SESSIONSも更新
                sid = session.get('_id')
                if sid and sid in ALL_SESSIONS:
                    ALL_SESSIONS[sid]['user_attributes'] = user_attributes
                
                # ステップ2: 属性が更新された場合、最後の症状で再分析
                last_symptom_message = None
                if updated:
                    logger.info(f"✅ 属性データが更新されました。再分析を実行します。")
                    
                    # 最後の症状入力を取得
                    for msg in reversed(session.get('messages', [])):
                        if msg.get('type') == 'user' and is_symptom_input(msg.get('content', '')):
                            last_symptom_message = msg.get('content', '')
                            break
                    
                    if last_symptom_message:
                        logger.info(f"🔄 最後の症状で再分析: {last_symptom_message}")
                        # 再分析フラグを立てる
                        session['is_reanalysis'] = True
                        session['reanalysis_attributes'] = user_attributes.copy()
                        # 症状分析処理に進む（is_questionをFalseにして症状分析を強制実行）
                        is_question = False
                        user_message = last_symptom_message  # 症状メッセージで再分析
                    else:
                        # 症状が見つからない場合は、属性更新のみの確認メッセージ
                        bot_response = {
                            'type': 'bot',
                            'content': f'情報を更新しました。ありがとうございます。',
                            'diagnosis': None
                        }
                else:
                    # 属性が更新されていない場合は通常の質問応答
                    logger.info(f"❓ 通常の質問として処理します")
                    try:
                        # 最新の推奨医薬品を取得
                        latest_recommended_medicines = []
                        for msg in reversed(session.get('messages', [])):
                            if msg.get('type') == 'bot' and msg.get('diagnosis'):
                                diagnosis = msg.get('diagnosis', {})
                                if diagnosis.get('recommended_medicines'):
                                    latest_recommended_medicines = diagnosis.get('recommended_medicines', [])
                                    break
                        
                        logger.info(f"📋 Latest recommended medicines: {len(latest_recommended_medicines)} items")
                        
                        # 会話履歴を取得
                        conversation_history = session.get('messages', [])[-10:]
                        
                        # ChatGPTに質問を送信
                        chat_response = chat_with_medicine_context(
                            user_message, 
                            conversation_history, 
                            latest_recommended_medicines
                        )
                        
                        # 回答をHTML形式で整形
                        bot_content = f"""
<div class="chat-response">
    <h4>💬 医薬品相談回答</h4>
    <p>{chat_response.get('answer', '回答を取得できませんでした')}</p>
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
                        bot_response = {
                            'type': 'bot',
                            'content': f"申し訳ございません。システムエラーが発生しました: {str(e)}",
                            'diagnosis': None
                        }
                
            # 症状入力の場合のみ医薬品推奨を実行
            # 質問の場合は属性抽出のみ行い、医薬品推奨は行わない
            if not is_question:
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
                
                # ハイブリッド医薬品推奨システム（ルールベース + ChatGPT）
                logger.info(f"💊 Hybrid medicine recommendation system starting...")
                
                # OpenAI clientを初期化（推奨システム用）
                from openai import OpenAI
                api_key = os.getenv('OPENAI_API_KEY')
                if not api_key:
                    return jsonify({
                        'error': True,
                        'response': '⚠️ システムエラー: OpenAI APIキーが設定されていません。管理者に連絡してください。'
                    })
                recommendation_client = OpenAI(api_key=api_key)
                
                # ステップ1: ChatGPTで医薬品の種類を判定
                start_time = time.time()
                try:
                    logger.info(f"🔍 Step 1: Analyzing medicine type with ChatGPT...")
                    analysis_result = analyze_symptoms_and_medicine_type(user_message, recommendation_client)
                    medicine_type = analysis_result.get('medicine_type', 'その他')
                    symptoms = analysis_result.get('symptoms', [])
                    
                    logger.info(f"📋 Detected medicine type: {medicine_type}")
                    logger.info(f"📋 Detected symptoms: {symptoms}")
                    
                    # ステップ2: 医薬品の種類に応じて推奨アルゴリズムを選択
                    target_types = ['風邪薬', '解熱鎮痛薬', '鼻炎用薬']
                    
                    if medicine_type in target_types:
                        # ルールベースアルゴリズムを使用
                        logger.info(f"✅ Using RULE-BASED algorithm for {medicine_type}")
                        
                        # ユーザー属性データをセッションから取得
                        user_attributes = session.get('user_attributes', {
                            'age': None,
                            'gender': None,
                            'pregnant': None,
                            'breastfeeding': None,
                            'current_medications': [],
                            'allergies': [],
                            'medical_history': [],
                            'symptom_duration_days': None,
                            'other_info': None
                        })
                        
                        # メッセージから属性情報を抽出してセッションに保存
                        import re
                        
                        # 年齢の抽出
                        age_match = re.search(r'(\d+)\s*歳', user_message)
                        if age_match:
                            extracted_age = int(age_match.group(1))
                            user_attributes['age'] = extracted_age
                            logger.info(f"📋 Extracted age from message: {extracted_age}")
                        
                        # 性別の抽出
                        if '女性' in user_message or '女' in user_message:
                            user_attributes['gender'] = '女性'
                            logger.info(f"📋 Detected gender: 女性")
                        elif '男性' in user_message or '男' in user_message:
                            user_attributes['gender'] = '男性'
                            logger.info(f"📋 Detected gender: 男性")
                        
                        # 妊娠・授乳の検出
                        if '妊娠' in user_message or '妊婦' in user_message:
                            user_attributes['pregnant'] = True
                            logger.info(f"📋 Detected pregnancy status from message")
                        elif '妊娠していない' in user_message or '妊娠してない' in user_message:
                            user_attributes['pregnant'] = False
                            logger.info(f"📋 Detected not pregnant from message")
                        
                        if '授乳' in user_message:
                            user_attributes['breastfeeding'] = True
                            logger.info(f"📋 Detected breastfeeding status from message")
                        elif '授乳していない' in user_message or '授乳してない' in user_message:
                            user_attributes['breastfeeding'] = False
                            logger.info(f"📋 Detected not breastfeeding from message")
                        
                        # アレルギーの抽出
                        if 'アレルギー' in user_message:
                            if 'ない' in user_message or 'なし' in user_message:
                                user_attributes['allergies'] = ['なし']
                                logger.info(f"📋 No allergies detected")
                            else:
                                # アレルギー情報を追加（簡易的）
                                allergy_match = re.search(r'アレルギー[：:](.*?)(?:[。、]|$)', user_message)
                                if allergy_match:
                                    allergy_info = allergy_match.group(1).strip()
                                    if allergy_info and allergy_info not in user_attributes['allergies']:
                                        user_attributes['allergies'].append(allergy_info)
                                        logger.info(f"📋 Extracted allergy: {allergy_info}")
                        
                        # セッションに保存
                        session['user_attributes'] = user_attributes
                        session.modified = True
                        
                        # ALL_SESSIONSも更新
                        sid = session.get('_id')
                        if sid and sid in ALL_SESSIONS:
                            ALL_SESSIONS[sid]['user_attributes'] = user_attributes
                        
                        # ルールベース推奨用のuser_infoを構築（デフォルト値は使用しない）
                        user_info = {
                            'age': user_attributes.get('age'),  # Noneのまま渡す
                            'gender': user_attributes.get('gender'),
                            'pregnant': user_attributes.get('pregnant'),  # Noneのまま渡す
                            'breastfeeding': user_attributes.get('breastfeeding'),  # Noneのまま渡す
                            'current_medications': user_attributes.get('current_medications', []),
                            'allergies': user_attributes.get('allergies', []),
                            'symptom_duration_days': user_attributes.get('symptom_duration_days')  # 症状期間を追加
                        }
                        
                        logger.info(f"📋 User info for recommendation: age={user_info.get('age')}, gender={user_info.get('gender')}, pregnant={user_info.get('pregnant')}, allergies={user_info.get('allergies')}")
                        
                        recommendation_result = rule_based_medicine_recommendation(
                            user_message, 
                            user_info, 
                            recommendation_client
                        )
                        
                        # ルールベース結果を従来の形式に変換
                        if recommendation_result.get('status') == 'success':
                            recommended_medicines = recommendation_result.get('recommended_medicines', [])
                            usage_notes = recommendation_result.get('usage_notes', '添付文書をよく読んでご使用ください。')
                            doctor_consultation = recommendation_result.get('doctor_consultation', '症状が改善しない場合は医師にご相談ください。')
                            additional_questions = recommendation_result.get('additional_questions', [])
                            
                            recommendation_result = {
                                'symptoms': symptoms,
                                'medicine_type': medicine_type,
                                'recommended_medicines': recommended_medicines,
                                'usage_notes': usage_notes,
                                'doctor_consultation': doctor_consultation,
                                'additional_questions': additional_questions,
                                'algorithm': 'rule_based'
                            }
                        elif recommendation_result.get('status') == 'escalation_required':
                            # エスカレーションが必要な場合
                            recommendation_result = {
                                'symptoms': symptoms,
                                'medicine_type': medicine_type,
                                'recommended_medicines': [],
                                'usage_notes': '',
                                'doctor_consultation': recommendation_result.get('reason', ''),
                                'escalation': True,
                                'algorithm': 'rule_based'
                            }
                        else:
                            # エラーの場合はChatGPTベースにフォールバック
                            logger.warning(f"⚠️ Rule-based algorithm failed, falling back to ChatGPT")
                            recommendation_result = comprehensive_medicine_recommendation(user_message)
                            recommendation_result['algorithm'] = 'chatgpt_fallback'
                    else:
                        # ChatGPTベースのアルゴリズムを使用
                        logger.info(f"✅ Using ChatGPT-BASED algorithm for {medicine_type}")
                        recommendation_result = comprehensive_medicine_recommendation(user_message)
                        recommendation_result['algorithm'] = 'chatgpt'
                    
                    end_time = time.time()
                    response_time = round(end_time - start_time, 3)
                    
                    # medicine_logic.pyの呼び出しをログ出力
                    log_medicine_logic_call(
                        f"hybrid_recommendation ({recommendation_result.get('algorithm', 'unknown')})",
                        {"user_message": user_message},
                        {
                            "symptoms": recommendation_result.get('symptoms', []),
                            "medicine_type": recommendation_result.get('medicine_type', medicine_type),
                            "recommended_medicines_count": len(recommendation_result.get('recommended_medicines', [])),
                            "algorithm": recommendation_result.get('algorithm', 'unknown')
                        },
                        response_time
                    )
                    
                    # ネットワークリクエストをログ出力
                    log_network_request(
                        'POST',
                        f'メインサイト - ハイブリッド医薬品推奨 ({recommendation_result.get("algorithm", "unknown")})',
                        {'symptom': user_message},
                        {'recommendation': recommendation_result},
                        response_time,
                        'success'
                    )
                    
                    add_network_log(
                        'POST',
                        f'メインサイト - ハイブリッド医薬品推奨 ({recommendation_result.get("algorithm", "unknown")})',
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
                    
                    # エスカレーションが必要な場合の特別処理
                    if recommendation_result.get('escalation'):
                        bot_content = f"""
<div class="recommendation-result escalation">
    <h4>⚠️ 重要な注意事項</h4>
    <p class="escalation-warning"><strong>{doctor_consultation}</strong></p>
    <p><strong>医薬品の種類:</strong> {medicine_type}</p>
    <p><strong>アルゴリズム:</strong> {recommendation_result.get('algorithm', 'unknown')}</p>
    
    <h4>🏥 推奨される対応</h4>
    <ul>
        <li>速やかに医師の診察を受けてください</li>
        <li>市販薬での自己治療は推奨されません</li>
        <li>症状が悪化する場合は救急医療機関へ</li>
    </ul>
</div>
"""
                    else:
                        # 通常の推奨結果の表示
                        algorithm_label = {
                            'rule_based': 'ルールベースアルゴリズム（安全性重視）',
                            'chatgpt': 'ChatGPTベースアルゴリズム',
                            'chatgpt_fallback': 'ChatGPTベースアルゴリズム（フォールバック）'
                        }.get(recommendation_result.get('algorithm', 'unknown'), '不明')
                        
                        # 再分析の場合、個別アドバイスを最初に表示
                        personalized_section = ""
                        if session.get('is_reanalysis'):
                            reanalysis_attrs = session.get('reanalysis_attributes', {})
                            
                            try:
                                personalized_advice = generate_personalized_advice(
                                    reanalysis_attrs,
                                    recommended_medicines,
                                    symptoms,
                                    recommendation_client
                                )
                                
                                personalized_section = f"""
    <div style="background: #e3f2fd; padding: 20px; margin: 15px 0; border-radius: 8px; border-left: 4px solid #2196f3;">
        <h4 style="color: #1976d2; margin-top: 0;">💡 あなたに合わせたアドバイス</h4>
        <p style="margin: 5px 0; line-height: 1.6; white-space: pre-wrap;">{personalized_advice}</p>
    </div>
"""
                            except Exception as e:
                                logger.error(f"❌ 個別説明生成エラー: {e}")
                            
                            # 再分析フラグをリセット
                            session.pop('is_reanalysis', None)
                            session.pop('reanalysis_attributes', None)
                        
                        bot_content = f"""
<div class="recommendation-result">
{personalized_section}
    <h4 style="color: #1976d2; border-bottom: 2px solid #1976d2; padding-bottom: 8px;">🔍 症状分析結果</h4>
    <p><strong>推測される症状:</strong> {', '.join(symptoms) if symptoms else '特定できませんでした'}</p>
    <p><strong>医薬品の種類:</strong> {medicine_type}</p>
    
    <div style="background: #e8f5e9; padding: 20px; margin: 15px 0; border-radius: 8px; border-left: 4px solid #4caf50;">
        <h4 style="color: #2e7d32; margin-top: 0;">💊 推奨医薬品</h4>
"""
                        
                        if recommended_medicines:
                            for medicine in recommended_medicines:
                                # ルールベース結果の場合
                                if 'rank' in medicine:
                                    explanation = medicine.get('explanation', '')
                                    score = medicine.get('score', 0)
                                    
                                    # 年齢制限の取得と表示
                                    age_restriction = medicine.get('age_restriction', '')
                                    age_restriction_display = ''
                                    
                                    import math
                                    if isinstance(age_restriction, float) and math.isnan(age_restriction):
                                        age_restriction = ''
                                    
                                    if age_restriction and isinstance(age_restriction, str) and age_restriction.strip():
                                        if '15歳未満' in age_restriction:
                                            age_restriction_display = '<p><strong>年齢制限:</strong> <span style="color: #d32f2f;">15歳未満の方は使用しないでください。</span></p>'
                                        elif '7歳未満' in age_restriction:
                                            age_restriction_display = '<p><strong>年齢制限:</strong> <span style="color: #d32f2f;">7歳未満の方は使用しないでください。</span></p>'
                                        elif '12歳未満' in age_restriction:
                                            age_restriction_display = '<p><strong>年齢制限:</strong> <span style="color: #d32f2f;">12歳未満の方は使用しないでください。</span></p>'
                                        else:
                                            # その他の年齢制限がある場合
                                            import re
                                            match = re.search(r'(\d+)歳', age_restriction)
                                            if match:
                                                age_restriction_display = f'<p><strong>年齢制限:</strong> {age_restriction}</p>'
                                    elif isinstance(age_restriction, (int, float)):
                                        try:
                                            age_val = int(age_restriction)
                                            age_restriction_display = f'<p><strong>年齢制限:</strong> {age_val}歳以上の方が対象です。</p>'
                                        except (ValueError, OverflowError):
                                            pass
                                    
                                    rank = medicine.get('rank', 1)
                                    
                                    bot_content += f"""
        <div class="medicine-item" style="padding: 10px 0; margin: 10px 0; border-bottom: 1px solid #ddd;">
            <h5 style="margin: 0 0 10px 0;">🏆 {rank}位: {medicine.get('product_name', '')} <span style="color: #666; font-size: 0.9em;">({medicine.get('manufacturer', '')})</span></h5>
            <p style="margin: 5px 0;"><strong>推奨理由:</strong> {explanation}</p>
            {age_restriction_display}
            <p style="margin: 5px 0;"><strong>効能効果:</strong> {medicine.get('efficacy', '')}</p>
        </div>
"""
                                else:
                                    # ChatGPTベース結果の場合
                                    efficacy = medicine.get('efficacy', '')
                                    ingredients = medicine.get('ingredients', '')
                                    
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
                            bot_content += "        <p>適切な医薬品が見つかりませんでした。</p>"
                        
                        # 推奨医薬品セクションを閉じる
                        bot_content += """
    </div>
"""
                        
                        if usage_notes or doctor_consultation:
                            # 使用上の注意を整形（セクションごとに色分け）
                            formatted_usage_notes = ""
                            if usage_notes:
                                lines = usage_notes.split('\n')
                                current_section = None
                                current_html = ""
                                
                                # 年齢制限の重複チェック用
                                age_restriction_added = False
                                
                                for line in lines:
                                    line = line.strip()
                                    if not line:
                                        continue
                                        
                                    if line.startswith('1つ目：') or line.startswith('2つ目：') or line.startswith('3つ目：'):
                                        # 前のセクションを閉じる
                                        if current_section and current_html:
                                            formatted_usage_notes += current_html + '</div>'
                                        
                                        # 新しい医薬品セクション開始（シンプルな区切り）
                                        current_html = f'<div style="padding: 10px 0; margin: 10px 0; border-bottom: 1px solid #ddd;"><h5 style="margin: 0 0 8px 0;">💊 {line}</h5>'
                                        current_section = 'individual'
                                        age_restriction_added = False  # 新しい医薬品セクションでリセット
                                    elif line.startswith('【使ってはいけない人】'):
                                        # 個別セクションを閉じる
                                        if current_section == 'individual' and current_html:
                                            formatted_usage_notes += current_html + '</div>'
                                            current_html = ""
                                        # 禁忌セクション
                                        current_html = f'<div style="padding: 10px 0; margin: 10px 0; border-bottom: 1px solid #ddd;"><h5 style="color: #d32f2f; margin: 0 0 8px 0;">⚠️ {line}</h5>'
                                        current_section = 'caution'
                                    elif line.startswith('【服用時の注意】'):
                                        # 禁忌セクションを閉じる
                                        if current_section == 'caution' and current_html:
                                            formatted_usage_notes += current_html + '</div>'
                                            current_html = ""
                                        # 服用注意セクション
                                        current_html = f'<div style="padding: 10px 0; margin: 10px 0;"><h5 style="color: #f57c00; margin: 0 0 8px 0;">📌 {line}</h5>'
                                        current_section = 'usage'
                                    elif line.startswith('年齢制限:'):
                                        # 年齢制限の処理（重複を避けるため）
                                        if not age_restriction_added:
                                            age_restriction = line.replace('年齢制限:', '').strip()
                                            if age_restriction and age_restriction != 'なし':
                                                # 年齢制限がある場合のみ表示（重複を避けるため）
                                                if '未満の方は使用しないでください' in age_restriction or '未満は服用しないこと' in age_restriction:
                                                    # 既に適切な形式になっている場合はそのまま表示
                                                    current_html += f'<p style="margin: 3px 0;"><strong>年齢制限:</strong> {age_restriction}</p>'
                                                elif '歳以上の方が対象です' in age_restriction:
                                                    # 「歳以上の方が対象です」の場合は「歳未満の方は使用しないでください」に変換
                                                    age_num = age_restriction.replace('歳以上の方が対象です', '').strip()
                                                    current_html += f'<p style="margin: 3px 0;"><strong>年齢制限:</strong> {age_num}歳未満の方は使用しないでください。</p>'
                                                else:
                                                    # その他の場合は「未満の方は使用しないでください」を追加
                                                    current_html += f'<p style="margin: 3px 0;"><strong>年齢制限:</strong> {age_restriction}未満の方は使用しないでください。</p>'
                                                age_restriction_added = True
                                    elif line.startswith('ドーピング:'):
                                        # ドーピングの処理
                                        doping_info = line.replace('ドーピング:', '').strip()
                                        if doping_info and doping_info != 'なし':
                                            # ドーピング情報がある場合のみ表示
                                            current_html += f'<p style="margin: 3px 0;"><strong>ドーピング:</strong> {doping_info}</p>'
                                    elif line.startswith('・'):
                                        # リストアイテム
                                        current_html += f'<p style="margin: 3px 0; padding-left: 10px;">{line}</p>'
                                    else:
                                        # 通常のテキスト（年齢制限とドーピング以外）
                                        if not line.startswith('年齢制限:') and not line.startswith('ドーピング:'):
                                            current_html += f'<p style="margin: 3px 0;">{line}</p>'
                                
                                # 最後のセクションを閉じる
                                if current_section and current_html:
                                    formatted_usage_notes += current_html + '</div>'
                            
                            bot_content += f"""
    <div style="background: #fff3e0; padding: 20px; margin: 15px 0; border-radius: 8px; border-left: 4px solid #ff9800;">
        <h4 style="color: #e65100; margin-top: 0;">⚠️ 使用上の注意</h4>
        {formatted_usage_notes if formatted_usage_notes else '<p>特になし</p>'}
    </div>
    
    <div style="background: #ffebee; padding: 20px; margin: 15px 0; border-radius: 8px; border-left: 4px solid #f44336;">
        <h4 style="color: #c62828; margin-top: 0;">🏥 医師の受診が必要な場合</h4>
        <p style="margin: 5px 0;">{doctor_consultation if doctor_consultation else '症状が改善しない場合は医師にご相談ください。'}</p>
    </div>
"""
                        
                        # 追加質問がある場合（すべての優先度で表示）
                        additional_questions = recommendation_result.get('additional_questions', [])
                        missing_priority = recommendation_result.get('missing_priority')
                        
                        if additional_questions:
                            priority_label = {
                                'critical': '必須',
                                'important': '重要',
                                'optional': '任意'
                            }.get(missing_priority, '任意')
                            
                            priority_message = {
                                'critical': 'より適切な医薬品をご提案するため、以下の情報を教えてください：',
                                'important': '安全のため、以下の情報を教えてください：',
                                'optional': 'より安全な使用のため、可能であれば以下の情報を教えてください：'
                            }.get(missing_priority, 'より安全な使用のため、可能であれば以下の情報を教えてください：')
                            
                            # 優先度に応じた色
                            if missing_priority == 'critical':
                                question_bg = '#ffebee'
                                question_border = '#f44336'
                                question_title = '#c62828'
                            elif missing_priority == 'important':
                                question_bg = '#fff3e0'
                                question_border = '#ff9800'
                                question_title = '#f57c00'
                            else:
                                question_bg = '#e8f5e9'
                                question_border = '#4caf50'
                                question_title = '#388e3c'
                            
                            bot_content += f"""
    <div style="background: {question_bg}; padding: 15px; margin: 15px 0; border-radius: 8px; border-left: 4px solid {question_border};">
        <h4 style="color: {question_title}; margin-top: 0;">❓ 追加でお伺いしたいこと <span style="font-size: 0.9em;">（優先度: {priority_label}）</span></h4>
        <p style="margin: 10px 0;">{priority_message}</p>
        <ul style="margin: 10px 0; padding-left: 20px;">
"""
                            for question in additional_questions:
                                bot_content += f"            <li style='margin: 5px 0;'>{question}</li>\n"
                            bot_content += """
        </ul>
        <button onclick="openAttributeModal()" class="answer-questions-btn">📝 回答する</button>
    </div>
"""
                        
                        bot_content += "</div>"
                    
                    bot_diag = recommendation_result
                    
                except Exception as e:
                    logger.error(f"❌ 包括的医薬品推奨システム実行時エラー: {e}")
                    bot_content = f"申し訳ございません。システムエラーが発生しました: {str(e)}"
                    bot_diag = None
                
                # 個別アドバイスは既にbot_contentの最初に追加済み（重複削除）
                
                bot_response = {
                    'type': 'bot',
                    'content': bot_content,
                    'diagnosis': bot_diag
                }
            if 'bot_response' in locals():
                session['messages'].append(bot_response)
                session.modified = True
                logger.info(f"💾 メッセージ保存完了: {len(session['messages'])} messages")
            else:
                logger.error(f"❌ bot_responseが定義されていません")
                # フォールバック
                bot_response = {
                'type': 'bot',
                'content': '処理中にエラーが発生しました。',
                'diagnosis': None
                }
                session['messages'].append(bot_response)
                session.modified = True
            
            # POST処理完了 - 次のセクションに進む
        else:
            # user_messageが空の場合
            logger.warning(f"⚠️ 空のメッセージを受信")
    
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
            'user_agent': user_agent,
            'user_attributes': session.get('user_attributes', {})
        }
        
        # セッションには最小限のデータのみ保存（Cookieサイズ削減）
        # messagesはALL_SESSIONSのみに保存
        session.modified = True
        
        logger.info(f"📝 Session {sid} updated: {len(current_messages)} messages (ALL_SESSIONS保存完了)")
        logger.info(f"📝 Session cookie size reduced - messages only in ALL_SESSIONS")
        if manual_replies:
            logger.info(f"📝 Manual replies preserved: {len(manual_replies)} messages")
    else:
        # 新しいセッションの場合
        ALL_SESSIONS[sid] = {
            'username': session['username'],
            'messages': session['messages'].copy(),
            'last_activity': current_time,
            'client_ip': client_ip,
            'user_agent': user_agent,
            'user_attributes': session.get('user_attributes', {})
        }
        logger.info(f"🆕 New session {sid} created: {len(session['messages'])} messages (ALL_SESSIONS保存完了)")
    
    # 手動返信メッセージがあるかチェック
    manual_replies = [msg for msg in session['messages'] if msg.get('manual_reply')]
    if manual_replies:
        print(f"Manual replies found in session {sid}: {len(manual_replies)} messages")
        for i, reply in enumerate(manual_replies):
            print(f"  Manual reply {i+1}: {reply.get('content', '')[:50]}...")
    
    # POSTリクエストの場合はJSON形式で成功を返す
    if request.method == 'POST':
        message_count = len(ALL_SESSIONS.get(sid, {}).get('messages', []))
        logger.info(f"✅ POST処理完了 - JSON返却: {message_count} messages")
        return jsonify({'status': 'ok', 'message_count': message_count})
    
    # GET処理（初期表示）
    messages = ALL_SESSIONS.get(sid, {}).get('messages', [])
    logger.info(f"✅ GET処理完了 - HTML返却: {len(messages)} messages")
    return render_template('index.html', messages=messages, version=VERSION, username=session['username'])

def generate_personalized_advice(user_attrs: Dict, medicines: List[Dict], symptoms: List[str], client) -> str:
    """
    ユーザー属性に基づいた個別アドバイスをChatGPTで生成
    """
    # ユーザー属性を文章化
    attr_text = []
    if user_attrs.get('age'):
        attr_text.append(f"年齢: {user_attrs['age']}歳")
    if user_attrs.get('gender'):
        attr_text.append(f"性別: {user_attrs['gender']}")
    if user_attrs.get('pregnant'):
        attr_text.append("妊娠中")
    if user_attrs.get('breastfeeding'):
        attr_text.append("授乳中")
    if user_attrs.get('allergies'):
        allergy_list = user_attrs['allergies']
        if allergy_list and allergy_list != ['なし']:
            attr_text.append(f"アレルギー: {', '.join(allergy_list)}")
    if user_attrs.get('symptom_duration_days') is not None:
        days = user_attrs['symptom_duration_days']
        if days == 0:
            attr_text.append("症状開始: 今日から")
        elif days == 1:
            attr_text.append("症状開始: 昨日から")
        else:
            attr_text.append(f"症状開始: {days}日前から")
    
    attr_summary = '、'.join(attr_text) if attr_text else '情報なし'
    
    # 推奨医薬品の名前リスト
    medicine_names = [m.get('product_name', '') for m in medicines[:3]]
    
    prompt = f"""
あなたは登録販売者です。以下のユーザー情報と推奨医薬品を基に、このユーザーに合わせた個別のアドバイスを100字程度で生成してください。

【ユーザー情報】
{attr_summary}

【症状】
{', '.join(symptoms)}

【推奨医薬品】
{', '.join(medicine_names)}

【生成するアドバイス】
- ユーザーの年齢、性別、妊娠状態などを考慮
- 推奨医薬品がこのユーザーに適している理由
- 特に注意すべきポイント
- 温かく、分かりやすい言葉で

例：
「19歳女性で妊娠中とのこと。妊娠中は薬の選択に特に注意が必要です。推奨した医薬品は妊娠中でも安全に使用できるものを選んでいます。服用前に必ず添付文書を確認し、不安な点があれば医師にご相談ください。」

100字程度で、このユーザーに合わせた温かいアドバイスを生成してください。
"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "あなたは親切な登録販売者です。ユーザーに寄り添った温かいアドバイスを提供してください。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=200
        )
        
        advice = response.choices[0].message.content.strip()
        logger.info(f"✅ 個別アドバイス生成完了: {len(advice)}字")
        return advice
        
    except Exception as e:
        logger.error(f"❌ 個別アドバイス生成エラー: {e}")
        logger.error(f"エラー詳細: {str(e)}")
        # フォールバック
        age = user_attrs.get('age')
        pregnant = user_attrs.get('pregnant')
        breastfeeding = user_attrs.get('breastfeeding')
        
        duration_days = user_attrs.get('symptom_duration_days')
        
        logger.info(f"フォールバック: age={age}, pregnant={pregnant}, breastfeeding={breastfeeding}, duration={duration_days}")
        
        # 症状期間の警告
        duration_warning = ""
        if duration_days and duration_days >= 3:
            if duration_days >= 7:
                duration_warning = f"症状が{duration_days}日間続いているとのこと、1週間以上症状が続く場合は早めに医師の診察を受けることをお勧めします。"
            else:
                duration_warning = f"症状が{duration_days}日間続いているとのこと、"
        
        if pregnant == True or pregnant == 'True':
            base_msg = "妊娠中のためご連絡ありがとうございます。推奨した医薬品は妊娠中でも使用可能なものを選んでいますが、服用前に必ず医師にご相談いただくとより安心です。お大事になさってください。"
            return f"{duration_warning}{base_msg}"
        elif breastfeeding == True or breastfeeding == 'True':
            base_msg = "授乳中のためご連絡ありがとうございます。推奨した医薬品は授乳中でも使用可能なものを選んでいますが、服用前に医師にご相談いただくとより安心です。"
            return f"{duration_warning}{base_msg}"
        elif age and age < 15:
            base_msg = f"{age}歳のお子様への服用となります。推奨医薬品は年齢に適したものを選んでいますが、必ず保護者の方が用法用量を確認し、監督のもとで服用してください。"
            return f"{duration_warning}{base_msg}"
        elif age and age >= 65:
            base_msg = "ご高齢の方への推奨となります。推奨医薬品は適切なものを選んでいますが、持病をお持ちの場合や他のお薬を服用されている場合は、飲み合わせにご注意ください。"
            return f"{duration_warning}{base_msg}"
        else:
            # 属性情報があればそれを含める
            info_parts = []
            if age:
                info_parts.append(f"{age}歳")
            if user_attrs.get('gender'):
                info_parts.append(user_attrs['gender'])
            
            if info_parts:
                info_str = '、'.join(info_parts)
                return f"{info_str}の方への推奨です。あなたの情報を考慮して最適な医薬品を選んでいます。服用前に添付文書をよく読み、用法用量を守ってご使用ください。お大事にしてください。"
            else:
                return "あなたの情報を考慮して、最適な医薬品を推奨しています。服用前に添付文書をよく読み、用法用量を守ってご使用ください。お大事にしてください。"

def is_symptom_input(message):
    """メッセージが症状入力かどうかを判定"""
    # 属性応答を示すキーワード（質問への回答）
    attribute_keywords = [
        '歳です', '歳、', '男性です', '女性です', '男です', '女です',
        'いいえ', 'はい', 'ありません', 'ないです', 'なしです',
        '妊娠', '授乳', 'アレルギー',
        '昨日から', '今日から', 'きのうから', 'きょうから', '日前から', '週間前から',
        '服用している', '飲んでいる', '続いています',
        # 英語の属性キーワード
        'years old', 'male', 'female', 'man', 'woman', 'allergy', 'allergies',
        'pregnant', 'breastfeeding', 'taking', 'medication', 'medicine',
        'started', 'days ago', 'weeks ago', 'months ago', 'yesterday', 'today'
    ]
    
    # 属性応答の場合は質問（症状入力ではない）
    for keyword in attribute_keywords:
        if keyword in message:
            return False
    
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
        sid = session.get('_id', 'unknown')
        logger.info(f"🔍 /api/sessions called - Session ID: {sid}")
        logger.info(f"🔍 ALL_SESSIONS keys: {list(ALL_SESSIONS.keys())}")
        
        # ALL_SESSIONSから取得（セッションCookieの肥大化を防ぐ）
        messages = []
        if sid in ALL_SESSIONS:
            messages = ALL_SESSIONS[sid].get('messages', [])
            logger.info(f"📦 /api/sessions - ALL_SESSIONSから取得: {len(messages)} messages (sid={sid})")
        else:
            # フォールバック: セッションから取得
            messages = session.get('messages', [])
            logger.warning(f"⚠️ /api/sessions - セッションIDがALL_SESSIONSに存在しません (sid={sid})")
            logger.info(f"📦 /api/sessions - セッションから取得: {len(messages)} messages")
        
        session_data = {
            'session_id': sid,
            'messages_count': len(messages),
            'last_activity': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'session_active': len(messages) > 0,
            'messages': messages
        }
        
        # usage_notesを直近のbotレスポンスから抽出
        latest_usage_notes = None
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
        
        # NaN値をnullに変換（JSONシリアライズ対応）
        import math
        import json
        
        def convert_nan_to_null(obj):
            """NaN値をnullに変換する再帰関数"""
            if isinstance(obj, dict):
                return {k: convert_nan_to_null(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_nan_to_null(item) for item in obj]
            elif isinstance(obj, float) and math.isnan(obj):
                return None
            else:
                return obj
        
        session_data = convert_nan_to_null(session_data)
        
        logger.info(f"✅ /api/sessions レスポンス: {len(messages)} messages")
        return jsonify(session_data)
    except Exception as e:
        logger.error(f"❌ /api/sessions エラー: {e}")
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
        'user_agent': user_agent,
        'user_attributes': session.get('user_attributes', {})
    }

    return jsonify({'message': '新しいセッションを開始しました', 'username': session['username']}), 200

@app.route('/api/request_admin', methods=['POST'])
def request_admin():
    """管理者対応要請を受け付ける（個別チャット単位）"""
    sid = session.get('_id')
    username = session.get('username', 'unknown')
    if sid:
        # セッションに要請フラグとAI自動応答OFFフラグを追加（個別チャット単位）
        if sid in ALL_SESSIONS:
            ALL_SESSIONS[sid]['admin_request'] = True
            ALL_SESSIONS[sid]['ai_auto_reply'] = False  # このチャットのみAI自動応答OFF
        
        session['admin_request'] = True
        session['ai_auto_reply'] = False  # このチャットのみAI自動応答OFF
        
        # システムメッセージを追加
        system_message = {
            'type': 'system',
            'content': '薬剤師対応を要請しました。しばらくお待ちください。',
            'admin_request': True
        }
        session['messages'].append(system_message)
        
        # ALL_SESSIONSにも保存（ページ更新後も表示されるように）
        if sid in ALL_SESSIONS:
            ALL_SESSIONS[sid]['messages'].append(system_message)
        
        session.modified = True
        
        # MANUAL_REPLY_QUEUEに同じセッションIDのadmin_requestがなければ追加
        already_exists = any(item.get('session_id') == sid and item.get('admin_request') for item in MANUAL_REPLY_QUEUE)
        if not already_exists:
            MANUAL_REPLY_QUEUE.append({
                'session_id': sid,
                'username': username,
                'user_message': '【薬剤師要請】' + username,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'status': 'admin_requested',
                'admin_request': True
            })
        
        logger.info(f"💊 薬剤師要請: {username} (Session: {sid}) - このチャットのみAI自動応答OFF")
        return jsonify({'status': 'ok'})
    return jsonify({'status': 'error', 'message': 'No session'}), 400

@app.route('/api/admin_mode', methods=['POST'])
def api_admin_mode():
    global ADMIN_MODE, AI_AUTO_REPLY
    ADMIN_MODE = True
    AI_AUTO_REPLY = False
    return jsonify({'admin_mode': ADMIN_MODE, 'ai_auto_reply': AI_AUTO_REPLY, 'message': '管理者対応モードに切り替えました'})

@app.route('/admin')
def admin():
    """管理画面（パスワード認証付き）"""
    # Basic認証のチェック
    auth = request.authorization
    admin_password = os.getenv('ADMIN_PASSWORD', 'admin123')  # デフォルトパスワード
    
    if not auth or auth.username != 'admin' or auth.password != admin_password:
        # 認証が必要
        return ('認証が必要です', 401, {
            'WWW-Authenticate': 'Basic realm="Admin Area"'
        })
    
    return render_template('admin_chat.html')

@app.route('/admin/system_status', methods=['GET'])
def admin_system_status():
    """システム状況を取得"""
    return jsonify({
        'status': 'ok',
        'csv_load_status': csv_load_status,
        'total_sessions': len(ALL_SESSIONS),
        'active_sessions': len([s for s in ALL_SESSIONS.values() if time.time() - s.get('last_activity', 0) < SESSION_TIMEOUT]),
        'manual_reply_queue': len(MANUAL_REPLY_QUEUE),
        'ai_auto_reply': AI_AUTO_REPLY,
        'admin_mode': ADMIN_MODE,
        'performance_stats': performance_stats
    })

@app.route('/clear_logs', methods=['POST'])
def clear_logs():
    """ログをクリア"""
    global network_logs
    network_logs.clear()
    
    # ログファイルもクリア
    log_file = 'log/recommendation_log.jsonl'
    if os.path.exists(log_file):
        try:
            with open(log_file, 'w', encoding='utf-8') as f:
                pass  # ファイルを空にする
            logger.info("📝 ログファイルをクリアしました")
        except Exception as e:
            logger.error(f"❌ ログファイルのクリアに失敗: {e}")
    
    return jsonify({'status': 'ok', 'message': 'ログをクリアしました'})

@app.route('/admin/ai_control', methods=['POST'])
def admin_ai_control():
    """AI自動応答の制御（管理画面用）"""
    global AI_AUTO_REPLY
    
    data = request.get_json()
    mode = data.get('mode')
    
    if mode == 'on':
        AI_AUTO_REPLY = True
        message = 'AI自動応答をONにしました'
    elif mode == 'off':
        AI_AUTO_REPLY = False
        message = 'AI自動応答をOFFにしました'
    else:
        return jsonify({'status': 'error', 'message': '無効なモード'}), 400
    
    logger.info(f"🤖 AI自動応答: {mode.upper()} (グローバル設定)")
    
    return jsonify({
        'status': 'ok',
        'message': message,
        'ai_auto_reply': AI_AUTO_REPLY
    })

@app.route('/admin/medicine_chat', methods=['POST'])
def admin_medicine_chat():
    """医薬品相談テスト（管理画面用）"""
    data = request.get_json()
    user_message = data.get('message', '').strip()
    
    if not user_message:
        return jsonify({'status': 'error', 'message': 'メッセージが空です'}), 400
    
    try:
        # medicine_logic.pyで初期化されたclientをインポート
        from medicine_logic import client, select_symptoms_via_gpt
        
        # 症状抽出を実行
        symptoms_result = select_symptoms_via_gpt(user_message)
        
        # 医薬品推奨を実行
        if symptoms_result and symptoms_result.get('status') == 'success':
            symptoms = symptoms_result.get('symptoms', [])
            
            # ルールベース推奨を試行
            from medicine_logic import analyze_symptoms_and_medicine_type
            medicine_type_result = analyze_symptoms_and_medicine_type(user_message, client)
            
            if medicine_type_result and medicine_type_result.get('medicine_type'):
                medicine_type = medicine_type_result['medicine_type']
                
                # ルールベース推奨
                from medicine_logic import rule_based_medicine_recommendation
                recommendation = rule_based_medicine_recommendation(
                    user_text=user_message,
                    user_info={},
                    client=client
                )
                
                return jsonify({
                    'status': 'ok',
                    'message': '医薬品推奨を実行しました',
                    'symptoms': symptoms,
                    'medicine_type': medicine_type,
                    'recommendation': recommendation
                })
            else:
                # AI推奨
                from medicine_logic import comprehensive_medicine_recommendation
                recommendation = comprehensive_medicine_recommendation(
                    user_text=user_message,
                    client=client
                )
                
                return jsonify({
                    'status': 'ok',
                    'message': '医薬品推奨を実行しました（AI）',
                    'symptoms': symptoms,
                    'recommendation': recommendation
                })
        else:
            return jsonify({
                'status': 'error',
                'message': '症状抽出に失敗しました',
                'details': symptoms_result
            }), 500
            
    except Exception as e:
        logger.error(f"❌ 医薬品相談テストエラー: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': 'エラーが発生しました',
            'error': str(e)
        }), 500

@app.route('/api/admin/sessions', methods=['GET'])
def get_all_sessions():
    """全セッション情報を取得"""
    cleanup_old_sessions()
    
    sessions_data = []
    for sid, info in ALL_SESSIONS.items():
        sessions_data.append({
            'session_id': sid,
            'username': info.get('username', 'Unknown'),
            'messages': info.get('messages', []),
            'last_activity': info.get('last_activity', 0)
        })
    
    return jsonify({
        'sessions': sessions_data,
        'admin_mode': ADMIN_MODE,
        'ai_auto_reply': AI_AUTO_REPLY
    })

@app.route('/api/admin/send_message', methods=['POST'])
def admin_send_message():
    """管理者からのメッセージ送信"""
    data = request.json
    session_id = data.get('session_id')
    message = data.get('message')
    
    if not session_id or not message:
        return jsonify({'status': 'error', 'message': 'session_idとmessageが必要です'}), 400
    
    if session_id not in ALL_SESSIONS:
        return jsonify({'status': 'error', 'message': 'セッションが見つかりません'}), 404
    
    # 管理者メッセージを追加
    ai_response = {
        'role': 'ai',
        'content': message,
        'timestamp': datetime.now().isoformat(),
        'from_admin': True
    }
    
    ALL_SESSIONS[session_id]['messages'].append(ai_response)
    ALL_SESSIONS[session_id]['last_activity'] = time.time()
    
    return jsonify({'status': 'success', 'message': 'メッセージを送信しました'})

@app.route('/api/main_sessions', methods=['GET'])
def api_main_sessions():
    """全セッション情報を取得（admin_chat.html用）"""
    cleanup_old_sessions()
    
    sessions_list = []
    for sid, info in ALL_SESSIONS.items():
        sessions_list.append({
            'session_id': sid,
            'username': info.get('username', 'Unknown'),
            'messages': info.get('messages', []),
            'last_activity': info.get('last_activity', 0),
            'message_count': len(info.get('messages', [])),
            'user_info': info.get('user_attributes', {}),
            'attributes': info.get('user_attributes', {})
        })
    
    # NaN値をnullに変換（JSONシリアライズ対応）
    import math
    import json
    
    def convert_nan_to_null(obj):
        """NaN値をnullに変換する再帰関数"""
        if isinstance(obj, dict):
            return {k: convert_nan_to_null(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_nan_to_null(item) for item in obj]
        elif isinstance(obj, float) and math.isnan(obj):
            return None
        else:
            return obj
    
    sessions_list = convert_nan_to_null(sessions_list)
    
    return jsonify(sessions_list)

@app.route('/api/main_manual_reply_queue', methods=['GET', 'POST'])
def api_main_manual_reply_queue():
    """手動返信キューの管理"""
    global MANUAL_REPLY_QUEUE
    
    if request.method == 'GET':
        return jsonify(MANUAL_REPLY_QUEUE)
    
    elif request.method == 'POST':
        data = request.json
        action = data.get('action')
        session_id = data.get('session_id')
        
        logger.info(f"📥 Manual reply queue POST request: action={action}, session_id={session_id}, data_keys={list(data.keys())}")
        
        # actionが指定されていない場合は、reply_messageの有無で判断
        if not action:
            if data.get('reply_message'):
                action = 'reply'
                logger.info(f"🔄 Action auto-detected as 'reply' from reply_message")
        
        if action == 'add':
            session_id = data.get('session_id')
            if session_id and session_id in ALL_SESSIONS:
                if session_id not in MANUAL_REPLY_QUEUE:
                    MANUAL_REPLY_QUEUE.append(session_id)
                return jsonify({'status': 'success', 'queue': MANUAL_REPLY_QUEUE})
        
        elif action == 'remove':
            session_id = data.get('session_id')
            if session_id in MANUAL_REPLY_QUEUE:
                MANUAL_REPLY_QUEUE.remove(session_id)
            return jsonify({'status': 'success', 'queue': MANUAL_REPLY_QUEUE})
        
        elif action == 'reply':
            # reply_messageとmessageの両方をサポート
            message = data.get('reply_message') or data.get('message')
            
            if session_id and message and session_id in ALL_SESSIONS:
                # 管理者メッセージを追加（manual_replyフラグを使用）
                manual_reply = {
                    'type': 'bot',
                    'content': message,
                    'timestamp': datetime.now().isoformat(),
                    'manual_reply': True
                }
                
                ALL_SESSIONS[session_id]['messages'].append(manual_reply)
                ALL_SESSIONS[session_id]['last_activity'] = time.time()
                
                logger.info(f"💬 Manual reply sent to session {session_id}: {message[:50]}...")
                
                # キューから削除
                if session_id in MANUAL_REPLY_QUEUE:
                    MANUAL_REPLY_QUEUE.remove(session_id)
                
                return jsonify({'status': 'success', 'message': 'メッセージを送信しました'})
        
        return jsonify({'status': 'error', 'message': '無効なアクションです'}), 400

@app.route('/api/main_ai_control', methods=['GET', 'POST'])
def api_main_ai_control():
    """AI自動応答の制御"""
    global AI_AUTO_REPLY, ADMIN_MODE
    
    if request.method == 'GET':
        return jsonify({
            'ai_auto_reply': AI_AUTO_REPLY,
            'admin_mode': ADMIN_MODE
        })
    
    elif request.method == 'POST':
        data = request.json
        action = data.get('action')
        
        if action == 'enable':
            AI_AUTO_REPLY = True
            ADMIN_MODE = False
        elif action == 'disable':
            AI_AUTO_REPLY = False
            ADMIN_MODE = True
        
        return jsonify({
            'ai_auto_reply': AI_AUTO_REPLY,
            'admin_mode': ADMIN_MODE,
            'message': 'AI自動応答を' + ('有効化' if AI_AUTO_REPLY else '無効化') + 'しました'
        })

@app.route('/api/user_attributes', methods=['GET', 'POST'])
def api_user_attributes():
    """ユーザー属性情報の取得と保存"""
    if request.method == 'GET':
        # 現在のセッションのユーザー属性を返す
        user_attributes = session.get('user_attributes', {
            'age': None,
            'gender': None,
            'pregnant': None,
            'breastfeeding': None,
            'current_medications': [],
            'allergies': [],
            'medical_history': [],
            'symptom_duration_days': None,
            'other_info': None
        })
        logger.info(f"📊 GET /api/user_attributes: {user_attributes}")
        return jsonify(user_attributes)
    
    elif request.method == 'POST':
        # ユーザー属性を保存
        data = request.json
        logger.info(f"💾 POST /api/user_attributes: {data}")
        
        sid = session.get('_id')
        
        # セッションに保存
        session['user_attributes'] = {
            'age': data.get('age'),
            'gender': data.get('gender'),
            'pregnant': data.get('pregnant'),
            'breastfeeding': data.get('breastfeeding'),
            'current_medications': data.get('current_medications', []),
            'allergies': data.get('allergies', []),
            'medical_history': data.get('medical_history', []),
            'symptom_duration_days': data.get('symptom_duration_days'),
            'other_info': data.get('other_info')
        }
        session.modified = True
        
        # ALL_SESSIONSにも保存
        if sid and sid in ALL_SESSIONS:
            ALL_SESSIONS[sid]['user_attributes'] = session['user_attributes'].copy()
            logger.info(f"✅ User attributes saved to session {sid}")
        
        return jsonify({'status': 'success', 'message': 'ユーザー属性を保存しました'})

if __name__ == '__main__':
    logger.info("🚀 Starting Medicine Recommendation System...")
    logger.info(f"📁 CSVファイル絶対パス: {csv_load_status['path']}")
    logger.info("🔑 環境変数からAPIキーを取得できませんでした。直接設定されたAPIキーを使用します。")
    logger.info("✅ OpenAI client initialized successfully.")
    logger.info("✅ CSVファイルを正常に読み込みました（エンコーディング: utf-8）。")
    
    # システムステータスをログ出力
    log_system_status()
    
    logger.info("🌐 Starting Flask development server...")
    port = int(os.getenv('PORT', 5000))
    app.run(debug=True, port=port, host='0.0.0.0') 