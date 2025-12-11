from flask import Flask, render_template, request, session as flask_session, jsonify, has_request_context
from flask_cors import CORS
from typing import Dict, List
import json
import time
import os
from datetime import datetime
import random
import logging
import re
import socket
from collections.abc import MutableMapping
from threading import local

# ログ設定（早期に設定）
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # ターミナルに出力
        logging.FileHandler('app.log', encoding='utf-8')  # ファイルにも出力
    ]
)
logger = logging.getLogger(__name__)

# .envファイルから環境変数を読み込み（medicine_logic.pyより前に実行）
try:
    from dotenv import load_dotenv
    # 明示的なパスを指定（app.pyと同じディレクトリの.envファイル）
    base_dir = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(base_dir, '.env')
    
    # デバッグ情報（DEBUG_MODE時のみ）
    if os.getenv('DEBUG_MODE', 'false').lower() == 'true':
        logger.debug(f"[DEBUG app.py] base_dir: {base_dir}")
        logger.debug(f"[DEBUG app.py] .envファイルのパス: {env_path}")
        logger.debug(f"[DEBUG app.py] .envファイル存在確認: {os.path.exists(env_path)}")
    
    # まず明示的なパスで読み込む（存在する場合）
    loaded = False
    if os.path.exists(env_path):
        loaded = load_dotenv(env_path, override=True)  # override=Trueで確実に読み込む
        if os.getenv('DEBUG_MODE', 'false').lower() == 'true':
            logger.debug(f"[DEBUG app.py] load_dotenv({env_path}) 結果: {loaded}")
    
    # 引数なしでも試す（自動検索、override=Trueで上書き）
    if not loaded:
        loaded = load_dotenv(override=True)
        if os.getenv('DEBUG_MODE', 'false').lower() == 'true':
            logger.debug(f"[DEBUG app.py] load_dotenv() (引数なし) 結果: {loaded}")
    
    # 環境変数の確認
    api_key_check = os.getenv('OPENAI_API_KEY')
    if api_key_check:
        if os.getenv('DEBUG_MODE', 'false').lower() == 'true':
            logger.debug(f"[DEBUG app.py] OPENAI_API_KEY読み込み成功（長さ: {len(api_key_check)}文字）")
    else:
        logger.warning("[DEBUG app.py] WARNING: OPENAI_API_KEYが環境変数に設定されていません")
    
    logger.info("app.py: .envファイルから環境変数を読み込みました。")
except ImportError:
    logger.info("app.py: python-dotenvがインストールされていません。環境変数のみを使用します。")
except Exception as e:
    logger.warning(f"app.py: .envファイル読み込みエラー: {e}")
    import traceback
    traceback.print_exc()

from medicine_logic import get_medicines_by_symptom, csv_load_status
from medicine_logic import select_symptoms_via_gpt, comprehensive_medicine_recommendation, chat_with_medicine_context
from medicine_logic import rule_based_medicine_recommendation, analyze_symptoms_and_medicine_type, client
from medicine_logic import detect_language, extract_user_attributes_multilingual, translate_medicine_recommendation
from debug_logger import performance_stats, network_logs, add_network_log
from analytics import log_access_analytics, get_access_statistics
from performance_monitor import get_global_monitor, log_performance_metrics, check_performance_alerts
from database import init_database, get_database


class RequestSafeSession(MutableMapping):
    """Flaskセッションをリクエストコンテキスト外でも安全に扱うためのラッパー"""

    def __init__(self):
        self._storage = local()

    def _use_real_session(self) -> bool:
        return has_request_context()

    def _fallback_store(self):
        if not hasattr(self._storage, 'data'):
            self._storage.data = {}
            self._storage.modified = False
        return self._storage

    def __getitem__(self, key):
        if self._use_real_session():
            return flask_session[key]
        store = self._fallback_store()
        return store.data[key]

    def __setitem__(self, key, value):
        if self._use_real_session():
            flask_session[key] = value
        else:
            store = self._fallback_store()
            store.data[key] = value
            store.modified = True

    def __delitem__(self, key):
        if self._use_real_session():
            del flask_session[key]
        else:
            store = self._fallback_store()
            del store.data[key]
            store.modified = True

    def __iter__(self):
        if self._use_real_session():
            return iter(flask_session)
        return iter(self._fallback_store().data)

    def __len__(self):
        if self._use_real_session():
            return len(flask_session)
        return len(self._fallback_store().data)

    def get(self, key, default=None):
        if self._use_real_session():
            return flask_session.get(key, default)
        return self._fallback_store().data.get(key, default)

    def setdefault(self, key, default=None):
        if self._use_real_session():
            return flask_session.setdefault(key, default)
        store = self._fallback_store()
        if key not in store.data:
            store.data[key] = default
            store.modified = True
        return store.data[key]

    def pop(self, key, default=None):
        if self._use_real_session():
            return flask_session.pop(key, default)
        store = self._fallback_store()
        store.modified = True
        return store.data.pop(key, default)

    def clear(self):
        if self._use_real_session():
            flask_session.clear()
        else:
            store = self._fallback_store()
            store.data.clear()
            store.modified = True

    @property
    def modified(self):
        if self._use_real_session():
            return flask_session.modified
        return self._fallback_store().modified

    @modified.setter
    def modified(self, value: bool):
        if self._use_real_session():
            flask_session.modified = value
        else:
            store = self._fallback_store()
            store.modified = bool(value)


session = RequestSafeSession()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')  # セッション管理用

# CORS設定（Render環境対応）
CORS(app, 
     supports_credentials=True, 
     origins=["https://medicine-recommend-system.onrender.com", "http://localhost:5000", "http://127.0.0.1:5000"],
     allow_headers=["Content-Type", "Authorization"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])

# セッション設定（環境に応じて自動調整）
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_TYPE'] = 'filesystem'

# 本番環境（FLASK_ENV=production）では Secure/None、開発では非Secure/Lax
env = os.getenv('FLASK_ENV', 'development').lower()
is_prod = (env == 'production')
secure_override = os.getenv('SESSION_COOKIE_SECURE')
if secure_override is not None:
    secure_flag = secure_override.lower() == 'true'
else:
    secure_flag = is_prod

samesite_value = 'None' if secure_flag else 'Lax'

app.config['SESSION_COOKIE_SECURE'] = secure_flag
app.config['SESSION_COOKIE_SAMESITE'] = samesite_value
app.config['SESSION_COOKIE_HTTPONLY'] = False  # 既存挙動を維持
app.config['SESSION_COOKIE_DOMAIN'] = None  # ドメイン制限を解除

# データベース初期化（非同期化）
try:
    if not init_database():
        logger.warning("⚠️ Database initialization failed. Feedback features will be disabled.")
    else:
        logger.info("✅ Database initialized successfully.")
except Exception as e:
    logger.warning(f"⚠️ Database initialization error: {e}. Feedback features will be disabled.")

# キャッシュバスティング用のバージョン番号
VERSION = str(int(time.time()))

# AI自動応答制御用のグローバル変数（DBから取得、フォールバック用にメモリにも保持）
def get_ai_auto_reply():
    """AI自動応答設定をDBから取得"""
    db = get_database()
    if db and (db.connection or db.connection_pool):
        return db.get_global_state('AI_AUTO_REPLY', default_value=True)
    return AI_AUTO_REPLY

def set_ai_auto_reply(value):
    """AI自動応答設定をDBに保存"""
    db = get_database()
    if db and (db.connection or db.connection_pool):
        db.set_global_state('AI_AUTO_REPLY', value)
    global AI_AUTO_REPLY
    AI_AUTO_REPLY = value

def get_admin_mode():
    """管理者モード設定をDBから取得"""
    db = get_database()
    if db and (db.connection or db.connection_pool):
        return db.get_global_state('ADMIN_MODE', default_value=False)
    return ADMIN_MODE

def set_admin_mode(value):
    """管理者モード設定をDBに保存"""
    db = get_database()
    if db and (db.connection or db.connection_pool):
        db.set_global_state('ADMIN_MODE', value)
    global ADMIN_MODE
    ADMIN_MODE = value

def get_manual_reply_queue():
    """手動返信キューをDBから取得"""
    db = get_database()
    if db and (db.connection or db.connection_pool):
        return db.get_global_state('MANUAL_REPLY_QUEUE', default_value=[])
    return MANUAL_REPLY_QUEUE

def get_manual_reply_message():
    """手動返信時の自動メッセージを取得"""
    default_message = '申し訳ございません。現在、AI自動応答が一時停止されています。担当者が確認次第、回答いたします。'
    
    # globals()に保存されている場合はそれを優先（最新の値が確実に取得できる）
    if hasattr(globals(), 'MANUAL_REPLY_MESSAGE'):
        return globals()['MANUAL_REPLY_MESSAGE']
    
    # データベースから読み込み（データベース接続がある場合）
    db = get_database()
    if db and (db.connection or db.connection_pool):
        db_value = db.get_global_state('MANUAL_REPLY_MESSAGE', default_value=None)
        if db_value is not None:
            # データベースから取得した値をglobals()にも保存（次回のアクセスを高速化）
            globals()['MANUAL_REPLY_MESSAGE'] = db_value
            return db_value
    
    # デフォルト値を返す
    return default_message

def set_manual_reply_message(value):
    """手動返信時の自動メッセージを保存"""
    db = get_database()
    if db and (db.connection or db.connection_pool):
        db.set_global_state('MANUAL_REPLY_MESSAGE', value)
    globals()['MANUAL_REPLY_MESSAGE'] = value

def set_manual_reply_queue(value):
    """手動返信キューをDBに保存"""
    db = get_database()
    if db and (db.connection or db.connection_pool):
        db.set_global_state('MANUAL_REPLY_QUEUE', value)
    global MANUAL_REPLY_QUEUE
    MANUAL_REPLY_QUEUE = value

# フォールバック用のメモリ変数
AI_AUTO_REPLY = True
ADMIN_MODE = False
MANUAL_REPLY_QUEUE = []  # 手動返信待ちのメッセージ

# 後方互換性のため、ALL_SESSIONSは残すが、DBアクセスを優先
ALL_SESSIONS = {}  # フォールバック用（DB接続失敗時のみ使用）
ADMIN_SESSIONS = {}  # 管理者専用のセッション情報
USER_COUNTER = 1  # ユーザー名の連番
MAX_SESSIONS = 50  # 最大セッション数（メモリ制約を考慮した適切な値）
SESSION_TIMEOUT = 600  # セッションタイムアウト（秒）- 10分に短縮
CHAT_END_TIMEOUT = 300  # チャット終了後の削除タイムアウト（秒）- 5分
LAST_CLEANUP_TIME = 0  # 最後にクリーンアップを実行した時刻（タイムスタンプ）
CLEANUP_INTERVAL = 60  # クリーンアップ実行間隔（秒）- 1分ごとに実行
MAX_CLEANUP_DELAY = 300  # 高負荷時のクリーンアップ遅延（秒）- 5分

# セッション管理ヘルパー関数（DBアクセス優先）
def get_session_from_db(session_id):
    """セッションをDBから取得、失敗時はフォールバック"""
    db = get_database()
    if db and (db.connection or db.connection_pool):
        session_data = db.get_session(session_id)
        if session_data:
            return session_data
    # フォールバック: メモリから取得
    return ALL_SESSIONS.get(session_id)

def save_session_to_db(session_id, data):
    """セッションをDBに保存、失敗時はメモリに保存"""
    db = get_database()
    if db and (db.connection or db.connection_pool):
        success = db.save_session(session_id, data)
        if success:
            return True
    # フォールバック: メモリに保存
    ALL_SESSIONS[session_id] = data
    logger.warning(f"⚠️ DB save failed, using memory fallback for session {session_id}")
    return True

def get_all_sessions_from_db():
    """全セッションをDBから取得、失敗時はフォールバック"""
    db = get_database()
    if db and (db.connection or db.connection_pool):
        sessions = db.get_all_sessions()
        if sessions is not None:
            return {s['session_id']: s for s in sessions}
    # フォールバック: メモリから取得
    return ALL_SESSIONS

# グローバルエラーハンドラー
@app.errorhandler(404)
def handle_404_error(e):
    """404エラーのハンドラー"""
    logger.warning(f"⚠️ 404 Not Found: {request.url}")
    return render_template('index.html', messages=[], version=VERSION), 404

@app.errorhandler(502)
def handle_502_error(e):
    """502エラーのハンドラー"""
    logger.error(f"❌ 502 Bad Gateway Error: {str(e)}")
    logger.error(f"❌ エラータイプ: {type(e).__name__}")
    
    # JSONリクエストの場合
    if request.is_json or request.method == 'POST':
        return jsonify({
            'error': True,
            'response': 'サーバーエラーが発生しました。しばらく時間をおいてから再度お試しください。'
        }), 502
    else:
        return render_template('index.html', messages=[], version=VERSION), 502

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

def remove_duplicate_user_messages_after_ai_response(sid):
    """AI応答後に重複するユーザーメッセージを削除"""
    if not sid:
        return False
    
    session_data = get_session_from_db(sid)
    if not session_data:
        return False
    
    messages = session_data.get('messages', [])
    original_count = len(messages)
    
    # 重複するユーザーメッセージを特定
    user_messages = [msg for msg in messages if msg.get('type') == 'user']
    seen_contents = set()
    unique_messages = []
    
    for msg in messages:
        if msg.get('type') == 'user':
            content = msg.get('content', '')
            if content not in seen_contents:
                seen_contents.add(content)
                unique_messages.append(msg)
            else:
                logger.info(f"⏭️ 重複ユーザーメッセージを削除: {content[:50]}...")
        else:
            unique_messages.append(msg)
    
    # 重複が削除された場合のみ更新
    if len(unique_messages) < original_count:
        session_data['messages'] = unique_messages
        save_session_to_db(sid, session_data)
        logger.info(f"✅ 重複削除完了: {original_count} → {len(unique_messages)} messages")
        return True
    
    return False

def log_system_status():
    """システムステータスをログ出力"""
    all_sessions = get_all_sessions_from_db()
    logger.info(f"📊 SYSTEM STATUS:")
    logger.info(f"   Active Sessions: {len(all_sessions)}")
    logger.info(f"   AI Auto Reply: {AI_AUTO_REPLY}")
    logger.info(f"   Admin Mode: {ADMIN_MODE}")
    logger.info(f"   Manual Reply Queue: {len(MANUAL_REPLY_QUEUE)}")


def get_next_user_number():
    """次のユーザー番号を取得（既存の番号を再利用）"""
    global USER_COUNTER
    used_numbers = set()
    
    # 既存のセッションで使用されている番号を収集
    all_sessions = get_all_sessions_from_db()
    for info in all_sessions.values():
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
    all_sessions = get_all_sessions_from_db()
    
    for existing_sid, info in all_sessions.items():
        # IPアドレスとUser-Agentの両方が一致し、かつ30分以内のアクセス
        last_activity = info.get('last_activity')
        if isinstance(last_activity, datetime):
            last_activity = last_activity.timestamp()
        elif isinstance(last_activity, str):
            try:
                last_activity = datetime.fromisoformat(last_activity.replace('Z', '+00:00')).timestamp()
            except:
                last_activity = 0
        
        if (info.get('client_ip') == client_ip and 
            info.get('user_agent') == user_agent and 
            current_time - (last_activity or 0) < 1800):  # 30分以内
            return existing_sid
    
    return None

def update_session_activity(sid):
    """セッションの最終アクティビティを更新"""
    if not sid:
        return
    
    session_data = get_session_from_db(sid)
    if session_data:
        session_data['last_activity'] = datetime.now()
        save_session_to_db(sid, session_data)

def cleanup_old_sessions(force=False, exclude_current_session=True):
    """古いセッションをクリーンアップ（メモリ最適化）
    
    Args:
        force: Trueの場合、間隔を無視して強制実行
        exclude_current_session: Trueの場合、現在のセッションを削除から除外
    """
    global LAST_CLEANUP_TIME
    # datetimeをグローバルスコープから明示的に使用
    from datetime import datetime
    
    current_time = time.time()
    
    # 強制実行でない場合、実行間隔をチェック
    if not force:
        if (current_time - LAST_CLEANUP_TIME) < CLEANUP_INTERVAL:
            return  # 実行間隔が経過していない場合はスキップ
        
        # 高負荷時のチェック（簡易版：CPU使用率の代わりにリクエスト頻度を推測）
        # クリーンアップ間隔が短すぎる場合は遅延させる
        if (current_time - LAST_CLEANUP_TIME) < MAX_CLEANUP_DELAY:
            # 高負荷時はクリーンアップをスキップ（負荷軽減）
            return
    
    db = get_database()
    current_sid = None
    if exclude_current_session and has_request_context():
        current_sid = session.get('_id')

    if db and (db.connection or db.connection_pool) and hasattr(db, 'cleanup_expired_sessions'):
        # 現在のセッションIDを取得（削除から除外するため）
        exclude_session_ids = []
        if current_sid:
            exclude_session_ids.append(current_sid)
        
        try:
            # DBから期限切れセッションを削除
            # - アクティブなセッション: SESSION_TIMEOUT秒以上アクティブでない場合
            # - チャット終了済みセッション: CHAT_END_TIMEOUT秒以上経過した場合
            deleted_count = db.cleanup_expired_sessions(
                SESSION_TIMEOUT, 
                exclude_session_ids=exclude_session_ids if exclude_session_ids else None,
                chat_end_timeout_seconds=CHAT_END_TIMEOUT
            )
            # deleted_countが整数の場合のみチェック
            if isinstance(deleted_count, int) and deleted_count > 0:
                logger.info(f"🧹 セッションクリーンアップ完了: {deleted_count}件削除")
            LAST_CLEANUP_TIME = current_time
            return
        except AttributeError as e:
            logger.warning(f"⚠️ cleanup_expired_sessions メソッドが利用できません: {e}。フォールバック処理に進みます。")
        except Exception as e:
            logger.error(f"❌ セッションクリーンアップ中にエラーが発生しました: {e}。フォールバック処理に進みます。")
    
    # フォールバック: メモリベースのクリーンアップ
    current_time = time.time()
    sessions_to_remove = []
    
    # タイムアウトしたセッションを特定（現在のセッションは除外）
    current_sid = session.get('_id') if has_request_context() else None
    all_sessions = get_all_sessions_from_db()
    for sid, session_info in all_sessions.items():
        # 現在のセッションは削除しない
        if sid == current_sid:
            continue
            
        last_activity = session_info.get('last_activity', 0)
        
        # last_activityがdatetimeオブジェクトの場合はtimestampに変換
        if isinstance(last_activity, datetime):
            last_activity = last_activity.timestamp()
        # last_activityが文字列の場合は数値に変換
        elif isinstance(last_activity, str):
            try:
                # ISO形式の文字列をパース
                last_activity_dt = datetime.fromisoformat(last_activity.replace('Z', '+00:00'))
                last_activity = last_activity_dt.timestamp()
            except (ValueError, AttributeError):
                # パースに失敗した場合は0（古いセッションとして扱う）
                last_activity = 0
        
        if current_time - last_activity > SESSION_TIMEOUT:
            sessions_to_remove.append(sid)
    
    # セッション数が上限を超えている場合、古いものから削除（現在のセッションは除外）
    all_sessions = get_all_sessions_from_db()
    if len(all_sessions) > MAX_SESSIONS:
        # 現在のセッションを除外してソート
        other_sessions = {k: v for k, v in all_sessions.items() if k != current_sid}
        if len(other_sessions) > 0:
            sorted_sessions = sorted(
                other_sessions.items(), 
                key=lambda x: x[1].get('last_activity', 0)
            )
            excess_count = len(all_sessions) - MAX_SESSIONS
            for i in range(min(excess_count, len(sorted_sessions))):
                sessions_to_remove.append(sorted_sessions[i][0])
    
    # セッションを削除
    db = get_database()
    for sid in sessions_to_remove:
        if sid != current_sid:
            if db and (db.connection or db.connection_pool):
                db.delete_session(sid)
            elif sid in ALL_SESSIONS:
                del ALL_SESSIONS[sid]
            logger.info(f"🗑️ 古いセッションを削除: {sid}")
    
    if sessions_to_remove:
        remaining = len(get_all_sessions_from_db())
        logger.info(f"🧹 セッションクリーンアップ完了: {len(sessions_to_remove)}件削除, 残り: {remaining}件")

@app.route('/favicon.ico')
def favicon():
    """favicon.icoの404エラーを防ぐ"""
    return '', 204

@app.route('/', methods=['GET', 'POST'])
def index():
    # datetimeを明示的にインポート（UnboundLocalError対策）
    from datetime import datetime
    
    # パフォーマンス監視開始
    monitor = get_global_monitor()
    monitor.start_monitoring()
    monitor.increment_request()
    
    # 古いセッションをクリーンアップ（定期的に実行）
    cleanup_old_sessions()
    
    current_time = time.time()
    client_ip = request.remote_addr
    user_agent = request.headers.get('User-Agent', '')
    
    # セッション初期化（最優先・KeyError対策）
    session.setdefault('messages', [])
    session.setdefault('user_attributes', {
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
    
    # セッションIDの取得または作成
    sid = session.get('_id')
    if not sid:
        # より安定したセッションID生成（マイクロ秒 + ランダム）
        # randomモジュールは15行目でグローバルにインポート済み
        sid = str(int(time.time() * 1000000)) + str(random.randint(100000, 999999))
        session['_id'] = sid
        # 言語設定を初期化
        session['ui_language'] = 'ja'  # UI言語（デフォルトは日本語）
        session['detected_language'] = 'ja'  # 検出された言語（デフォルトは日本語）
        logger.info(f"🆕 新しいセッションIDを作成: {sid}")
    
    # セッションIDの整合性を確認
    all_sessions = get_all_sessions_from_db()
    logger.info(f"🔍 Current session ID: {sid}")
    logger.info(f"🔍 ALL_SESSIONS keys: {list(all_sessions.keys())}")
    
    # ユーザー名の設定
    if 'username' not in session:
        # 既存のセッションを検索（同じ人からのアクセスのみ）
        existing_session = find_existing_session(client_ip, user_agent)
        
        if existing_session:
            # 既存のセッションを再利用
            existing_session_data = get_session_from_db(existing_session)
            if existing_session_data:
                session['username'] = existing_session_data.get('username', '')
                session['messages'] = existing_session_data.get('messages', []).copy()
                logger.info(f"🔄 Reusing existing session: {existing_session} for IP: {client_ip}, User: {session['username']}")
        else:
            # 新しいユーザー番号を取得
            user_number = get_next_user_number()
            session['username'] = f'ユーザー{user_number}'
            session['messages'] = []
            logger.info(f"👤 New user created: {session['username']} for IP: {client_ip}, User-Agent: {user_agent[:50]}...")
    else:
        logger.info(f"👤 Existing session accessed: {session['username']} for IP: {client_ip}")
    
    # DBからセッションを復元（Cookieサイズ削減のため）
    if sid:
        session_data = get_session_from_db(sid)
        if session_data:
            # 会話履歴は常に完全な履歴を復元する（管理者要請メッセージのみで上書きしない）
            session['messages'] = session_data.get('messages', []).copy()
            logger.info(f"📥 Session messages restored from DB: {len(session['messages'])} messages (full history)")
    
    # current_messagesは安全に取得
    current_messages = session.get('messages', []).copy()
    
    if request.method == 'POST':
        logger.info(f"📨 POST処理開始")
        user_message = request.form.get('message', '').strip()
        logger.info(f"📝 受信メッセージ: {user_message}")
        if user_message:
            # セキュリティ検証を一時的に無効化（デプロイメント問題のため）
            try:
                from security_validator import validate_user_input
                from security_config import should_block_input
                from security_logger import log_input_validation
                
                # 入力検証
                is_safe, risk_score, warnings, sanitized_message = validate_user_input(
                    user_message, context='chat'
                )
                
                # ログ記録
                log_input_validation(
                    user_id=session.get('username', 'unknown'),
                    input_text=user_message,
                    risk_score=risk_score,
                    is_safe=is_safe,
                    warnings=warnings,
                    sanitized_text=sanitized_message
                )
                
                # ブロック判定（Phase 1でも高リスクは警告表示）
                if should_block_input(risk_score):
                    logger.warning(f"⚠️ 入力がブロックされました: リスクスコア {risk_score}")
                    return jsonify({
                        'error': True,
                        'response': '入力内容に問題が検出されました。症状や質問を自然な文章で入力してください。'
                    })
                
                # Phase 1でも高リスクの場合は警告表示
                if risk_score >= 80:
                    logger.warning(f"⚠️ 高リスク入力検出: リスクスコア {risk_score}")
                    return jsonify({
                        'warning': True,
                        'response': '入力内容に不審なパターンが検出されました。症状や質問を自然な文章で入力してください。'
                    })
                
                # ユーザーインタラクションをログ出力
                log_user_interaction(sanitized_message, "POST", session.get('_id', 'unknown'), session.get('username', 'unknown'))
            except ImportError as e:
                logger.warning(f"⚠️ セキュリティモジュールのインポートに失敗: {e}")
                logger.info("🔓 セキュリティ機能をスキップして続行します")
                # セキュリティ機能をスキップして通常の処理を続行
                sanitized_message = user_message
                log_user_interaction(sanitized_message, "POST", session.get('_id', 'unknown'), session.get('username', 'unknown'))
            except Exception as e:
                logger.error(f"❌ セキュリティ検証でエラー: {e}")
                logger.info("🔓 セキュリティ機能をスキップして続行します")
                # セキュリティ機能をスキップして通常の処理を続行
                sanitized_message = user_message
                log_user_interaction(sanitized_message, "POST", session.get('_id', 'unknown'), session.get('username', 'unknown'))
            
            # 危機関連ワード検出（「終了」ワード検知の前）
            try:
                from medicine_logic import detect_crisis_keywords, get_crisis_support_resources
                from security_logger import log_crisis_keyword_detection
                
                # 危機関連ワードをチェック
                has_crisis_keywords, detected_keywords = detect_crisis_keywords(sanitized_message)
                
                if has_crisis_keywords:
                    logger.warning(f"🚨 危機関連ワード検出: {detected_keywords}")
                    
                    # ユーザーメッセージをセッションに追加
                    if 'messages' not in session:
                        session['messages'] = []
                    
                    from datetime import datetime
                    import uuid
                    
                    # 重複チェック
                    user_message_exists = any(
                        msg.get('type') == 'user' and 
                        msg.get('content') == sanitized_message and
                        msg.get('uuid')
                        for msg in session.get('messages', [])
                    )
                    
                    if not user_message_exists:
                        session['messages'].append({
                            'type': 'user',
                            'content': sanitized_message,
                            'timestamp': datetime.now().isoformat(),
                            'uuid': str(uuid.uuid4())
                        })
                    
                    # 言語設定を取得（デフォルトは日本語）
                    user_language = session.get('language', 'ja')
                    crisis_resources = get_crisis_support_resources(user_language)
                    
                    # 危機対応の特別な応答メッセージを作成
                    bot_response = {
                        'type': 'bot',
                        'content': crisis_resources['message'],
                        'crisis_support': True,
                        'crisis_title': crisis_resources['title'],
                        'resources': crisis_resources['resources'],
                        'emergency_message': crisis_resources['emergency_message'],
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    # セッションに追加
                    session['messages'].append(bot_response)
                    session.modified = True
                    
                    # セッションに危機検出フラグを設定
                    session['crisis_detected'] = True
                    
                    # DBを更新
                    if sid:
                        session_data = get_session_from_db(sid)
                        if not session_data:
                            session_data = {
                                'session_id': sid,
                                'username': session.get('username', 'Unknown'),
                                'messages': session['messages'].copy(),
                                'last_activity': datetime.now(),
                                'client_ip': request.remote_addr,
                                'user_agent': request.headers.get('User-Agent', ''),
                                'user_attributes': session.get('user_attributes', {}),
                                'session_active': True,
                                'crisis_detected': True
                            }
                        else:
                            session_data['messages'] = session['messages'].copy()
                            session_data['crisis_detected'] = True
                            session_data['last_activity'] = datetime.now()
                        save_session_to_db(sid, session_data)
                    
                    # セキュリティログに記録
                    log_crisis_keyword_detection(
                        user_id=session.get('username', 'unknown'),
                        input_text=sanitized_message,
                        detected_keywords=detected_keywords,
                        session_id=sid
                    )
                    
                    # 危機対応セッションを手動返信キューに追加
                    crisis_queue_item = {
                        'session_id': sid,
                        'user_message': sanitized_message,
                        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'status': 'crisis_detected',
                        'crisis_keywords': detected_keywords,
                        'priority': 'high'
                    }
                    queue = get_manual_reply_queue()
                    queue.append(crisis_queue_item)
                    set_manual_reply_queue(queue)
                    logger.info(f"🚨 危機対応セッションを手動返信キューに追加: {sid}")
                    
                    message_count = len(session['messages'])
                    logger.info(f"✅ 危機対応完了: {message_count} messages")
                    return jsonify({
                        'status': 'ok', 
                        'message_count': message_count, 
                        'crisis_support': True
                    })
                    
            except ImportError as e:
                logger.warning(f"⚠️ 危機対応機能のインポートに失敗: {e}")
                # 機能をスキップして通常処理を続行
            except Exception as e:
                logger.error(f"❌ 危機対応機能でエラー: {e}")
                # 機能をスキップして通常処理を続行

            # 「終了」ワード検知（サニタイズされたメッセージでチェック）
            if sanitized_message in ['終了', 'end', 'おわり', '終わり', 'quit', 'exit']:
                logger.info(f"🔚 CHAT ENDED by user: {session.get('username', 'unknown')}")
                session.modified = True
                bot_response = {
                    'type': 'bot',
                    'content': 'チャットを終了しました。不明点がございましたら、お気軽にお近くの登録販売者にご相談ください。',
                    'diagnosis': None,
                    'chat_ended': True
                }
                session['messages'].append(bot_response)
                # DBを更新（チャット終了フラグを設定）
                if sid:
                    session_data = get_session_from_db(sid)
                    if session_data:
                        session_data['messages'] = session['messages'].copy()
                        session_data['last_activity'] = datetime.now()
                        session_data['session_active'] = False  # チャット終了フラグ
                        save_session_to_db(sid, session_data)
                message_count = len(session['messages'])
                logger.info(f"✅ POST処理完了（チャット終了） - JSON返却: {message_count} messages")
                return jsonify({'status': 'ok', 'message_count': message_count})
            
            # ユーザーメッセージを追加（AI自動応答ON/OFF問わず）
            if 'messages' not in session:
                session['messages'] = []
            
            from datetime import datetime
            import uuid
            
            # 重複チェック：同じ内容のユーザーメッセージが既に存在するかチェック
            user_message_exists = any(
                msg.get('type') == 'user' and 
                msg.get('content') == sanitized_message and
                msg.get('uuid')  # UUIDが存在する場合は既存メッセージ
                for msg in session.get('messages', [])
            )
            
            if not user_message_exists:
                session['messages'].append({
                    'type': 'user',
                    'content': sanitized_message,  # サニタイズされたメッセージを使用
                    'timestamp': datetime.now().isoformat(),  # タイムスタンプを追加
                    'uuid': str(uuid.uuid4())  # 一意な識別子を追加（将来のtemp_idフローに統合可能）
                })
                logger.info(f"✅ ユーザーメッセージ追加: {sanitized_message[:50]}...")
            else:
                logger.info(f"⏭️ 重複ユーザーメッセージをスキップ: {sanitized_message[:50]}...")
            # 管理画面表示用にDBへも即時反映（ユーザーメッセージが見えるように）
            if sid:
                session_data = get_session_from_db(sid)
                if not session_data:
                    session_data = {
                        'session_id': sid,
                        'username': session.get('username', 'Unknown'),
                        'messages': session['messages'].copy(),
                        'last_activity': datetime.now(),
                        'client_ip': request.remote_addr,
                        'user_agent': request.headers.get('User-Agent', ''),
                        'user_attributes': session.get('user_attributes', {}),
                        'session_active': True
                    }
                    save_session_to_db(sid, session_data)
                else:
                    # 医薬品相談回答処理中は即時反映を完全にスキップ（重複を根本的に防止）
                    if not session.get('is_medicine_consultation', False):
                        # 既存のDBメッセージと重複チェック
                        existing_messages = session_data.get('messages', [])
                        new_user_messages = [msg for msg in session['messages'] if msg.get('type') == 'user']
                        
                        # 新しいユーザーメッセージのみを追加
                        for new_msg in new_user_messages:
                            if not any(
                                existing_msg.get('type') == 'user' and 
                                existing_msg.get('content') == new_msg.get('content') and
                                existing_msg.get('uuid') == new_msg.get('uuid')
                                for existing_msg in existing_messages
                            ):
                                existing_messages.append(new_msg)
                        
                        session_data['messages'] = existing_messages
                        session_data['last_activity'] = datetime.now()
                        save_session_to_db(sid, session_data)
                    else:
                        logger.info(f"📝 医薬品相談回答処理中のため、DB即時反映を完全にスキップ")
            
            # 個別チャット単位でAI自動応答のON/OFFを確認（デフォルトはTrue）
            session_data_for_ai = get_session_from_db(sid) if sid else {}

            chat_ai_auto_reply = session_data_for_ai.get('ai_auto_reply') if session_data_for_ai else None
            if chat_ai_auto_reply is None:
                chat_ai_auto_reply = session.get('ai_auto_reply')
            if chat_ai_auto_reply is None:
                chat_ai_auto_reply = get_ai_auto_reply()

            if isinstance(chat_ai_auto_reply, str):
                chat_ai_auto_reply = chat_ai_auto_reply.lower() == 'true'
            else:
                chat_ai_auto_reply = bool(chat_ai_auto_reply)
            
            # AI自動応答がOFFの場合は手動返信待ちにする
            if not chat_ai_auto_reply:
                logger.info(f"⚠️ AI自動応答OFF検出 - セッションID: {sid}, 管理者モード: {get_admin_mode()}")
                
                # 管理者モードでない場合のみ手動返信待ちキューに追加
                if not get_admin_mode():
                    # 手動返信待ちキューに追加
                    pending_message = {
                        'session_id': session.get('_id', 'unknown'),
                        'user_message': user_message,
                        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'status': 'pending'
                    }
                    queue = get_manual_reply_queue()
                    queue.append(pending_message)
                    set_manual_reply_queue(queue)
                    logger.info(f"📋 手動返信キューに追加: セッションID {session.get('_id', 'unknown')}")
                    
                    add_network_log(
                        'POST',
                        'メインサイト - 手動返信待ち',
                        {'symptom': user_message},
                        {'status': 'pending_manual_reply'},
                        0,
                        'pending'
                    )
                
                # 管理者モードでもカスタムメッセージを送信する（ユーザーに通知するため）
                # 最新のメッセージがユーザーメッセージかどうかを確認
                # ユーザーメッセージの直後にbotメッセージがない場合のみ追加
                session_messages = session.get('messages', [])
                last_message = session_messages[-1] if session_messages else None
                should_add_custom_message = False
                
                # 最新のメッセージがユーザーメッセージで、その直前にbotメッセージがない場合は追加
                if last_message and last_message.get('type') == 'user':
                    # 最新のbotメッセージを確認（最後から逆順に検索）
                    has_recent_bot_message = False
                    for msg in reversed(session_messages[:-1]):  # 最後のユーザーメッセージは除外
                        if msg.get('type') == 'bot':
                            has_recent_bot_message = True
                            break
                    should_add_custom_message = not has_recent_bot_message
                elif not last_message or last_message.get('type') != 'bot':
                    # メッセージがない、または最後がbotメッセージでない場合
                    should_add_custom_message = True
                
                if should_add_custom_message:
                    # カスタムメッセージを取得
                    custom_message = get_manual_reply_message()
                    admin_mode_status = "管理者モード" if get_admin_mode() else "通常モード"
                    logger.info(f"💬 カスタムメッセージ送信（{admin_mode_status}）: {custom_message[:50]}...")
                    
                    bot_response = {
                        'type': 'bot',
                        'content': custom_message,
                        'admin_request': True,  # 管理者対応フラグ
                        'diagnosis': None,
                        'timestamp': datetime.now().isoformat()
                    }
                    if 'messages' not in session:
                        session['messages'] = []
                    session['messages'].append(bot_response)
                    session.modified = True
                    
                    # DBを更新（確実に反映させるため）
                    if sid:
                        session_data = get_session_from_db(sid)
                        if session_data:
                            session_data['messages'] = session['messages'].copy()
                            session_data['last_activity'] = datetime.now()
                            session_data['ai_auto_reply'] = False  # セッションにも設定を反映
                            save_session_to_db(sid, session_data)
                            logger.info(f"💾 DB更新完了（{admin_mode_status}）: セッションID {sid}, メッセージ数 {len(session_data['messages'])}")
                    else:
                        logger.warning(f"⚠️ セッションIDが取得できませんでした")
                else:
                    # 既にbotメッセージが存在する場合はスキップ
                    logger.info(f"💊 既にbotメッセージが存在するため、追加のメッセージをスキップします")
                    
                    # sessionとDBを同期（メッセージがsessionにない場合はDBから復元）
                    if sid:
                        session_data = get_session_from_db(sid)
                        if session_data:
                            # sessionのメッセージ数がDBより少ない場合はDBから復元
                            if len(session_messages) < len(session_data.get('messages', [])):
                                session['messages'] = session_data['messages'].copy()
                                session.modified = True
                                logger.info(f"💊 メッセージをDBから復元しました（{len(session['messages'])} messages）")
                            else:
                                # DBを更新
                                session_data['messages'] = session['messages'].copy()
                                session_data['last_activity'] = datetime.now()
                                save_session_to_db(sid, session_data)
                
                message_count = len(session['messages'])
                admin_mode_status = "管理者モード" if get_admin_mode() else "手動返信待ち"
                logger.info(f"✅ POST処理完了（AI自動応答OFF - {admin_mode_status}） - JSON返却: {message_count} messages")
                return jsonify({'status': 'ok', 'message_count': message_count})
            
            # AI自動応答がONの場合の通常処理
            # まず挨拶を検出（症状検出の前に実行）
            greeting_keywords = [
                'こんにちは', 'こんばんは', 'おはよう', 'おはようございます',
                'はじめまして', '初めまして', 'よろしく', 'よろしくお願いします',
                'お疲れ様', 'おつかれさま', 'おつかれ', 'ご苦労様',
                'さようなら', 'さよなら', 'バイバイ', 'またね',
                'ありがとう', 'ありがとうございます', 'どうも', 'どうもありがとう',
                'すみません', 'すいません', 'ごめんなさい', 'ごめん',
                'hello', 'hi', 'good morning', 'good evening', 'good night',
                'thanks', 'thank you', 'bye', 'goodbye'
            ]
            
            # 症状キーワード（is_symptom_input関数と同じリストを使用）
            symptom_keywords = [
                '痛い', '痛み', '熱', '発熱', '咳', '鼻水', '頭痛', '腹痛', '吐き気', '嘔吐', '下痢', '便秘',
                '痒い', 'かゆい', '腫れ', '炎症', '発疹', '湿疹', 'めまい', 'だるい', '倦怠感', '疲れ', '不調', '症状',
                '喉', 'のど', '胃', '腸', '目', '耳', '鼻', '皮膚', '関節', '筋肉', '肩こり', '腰痛', '風邪', 'インフルエンザ',
                '寒気', '寒気がする', '寒気がします', '寒気があります', '寒気があり', '寒気が',
                '痺れ', 'しびれ', 'むくみ', '倦怠', '倦怠感', 'だるさ'
            ]
            
            # 挨拶キーワードが含まれているかチェック
            has_greeting = any(greeting in user_message for greeting in greeting_keywords)
            # 症状キーワードが含まれているかチェック
            has_symptom = any(symptom in user_message for symptom in symptom_keywords)
            
            # 質問か症状入力かを判定
            is_question = not is_symptom_input(user_message)
            add_reanalysis_message = False  # 再分析メッセージフラグ
            original_user_message = None  # 元のユーザーメッセージ
            
            # 挨拶のみで症状キーワードが含まれていない場合は質問処理に進む
            if has_greeting and not has_symptom:
                is_question = True
            
            if is_question:
                # システム紹介質問を検出
                system_intro_keywords = ['あなたについて', 'あなたは', 'システムについて', 'どんなシステム', '何ができる', '機能', '自己紹介']
                is_system_intro = any(keyword in user_message for keyword in system_intro_keywords)
                
                # 医薬品名検索を検出
                medicine_search_keywords = ['の薬', '薬を', '医薬品', 'について教えて', 'を教えて', 'お勧め', 'おすすめ']
                is_medicine_search = any(keyword in user_message for keyword in medicine_search_keywords)
                
                # 質問かどうかを判定（質問キーワードがあるか確認）
                has_question_keyword = False
                question_keywords = [
                    'ですか', 'でしょうか', 'ですか？', 'でしょうか？',
                    'ますか', 'できますか', '利用できますか', '使用できますか', '使えますか',
                    '飲めますか', '飲んでも大丈夫ですか', '使用しても大丈夫ですか', '利用しても大丈夫ですか',
                    '服用できますか', '服用しても大丈夫ですか', '摂取できますか',
                    'ドーピング', '禁止', '禁止物質', '違反', '大丈夫', '安全', '危険',
                    '大会前', '競技', 'レース', '試合前', '試合で', 'アンチドーピング', '陽性',
                    '当たる', '当たります', '対象', '含まれる', '使える',
                    '副作用', '飲み方', '効果', '効き目',
                    '教えて', '教えてください', '知りたい', '聞きたい'
                ]
                question_suffixes = [
                    'ですか', 'でしょうか', 'ますか', 'できますか', '利用できますか',
                    '使用できますか', '使えますか', '飲めますか', '飲んでも大丈夫ですか',
                    '使用しても大丈夫ですか', '利用しても大丈夫ですか', '服用できますか',
                    '服用しても大丈夫ですか', '摂取できますか'
                ]
                message_stripped = user_message.strip()
                has_question_suffix = any(message_stripped.endswith(suffix) for suffix in question_suffixes)
                ends_with_question_mark = message_stripped.endswith('?') or message_stripped.endswith('？')
                for keyword in question_keywords:
                    if keyword in user_message:
                        has_question_keyword = True
                        break
                
                # 挨拶のみの場合は挨拶への返答を生成
                if has_greeting and not has_symptom and not (is_system_intro or is_medicine_search or has_question_keyword or
                    has_question_suffix or ends_with_question_mark):
                    logger.info(f"👋 GREETING DETECTED: {user_message}")
                    
                    # 挨拶への返答を生成
                    greeting_responses = {
                        'こんにちは': 'こんにちは！どのような症状でお困りですか？具体的な症状を教えていただければ、適切な市販薬をご提案いたします。',
                        'こんばんは': 'こんばんは！どのような症状でお困りですか？具体的な症状を教えていただければ、適切な市販薬をご提案いたします。',
                        'おはよう': 'おはようございます！どのような症状でお困りですか？具体的な症状を教えていただければ、適切な市販薬をご提案いたします。',
                        'おはようございます': 'おはようございます！どのような症状でお困りですか？具体的な症状を教えていただければ、適切な市販薬をご提案いたします。',
                        'はじめまして': 'はじめまして！医薬品相談ツールです。どのような症状でお困りですか？具体的な症状を教えていただければ、適切な市販薬をご提案いたします。',
                        '初めまして': '初めまして！医薬品相談ツールです。どのような症状でお困りですか？具体的な症状を教えていただければ、適切な市販薬をご提案いたします。',
                        'よろしく': 'よろしくお願いします！どのような症状でお困りですか？具体的な症状を教えていただければ、適切な市販薬をご提案いたします。',
                        'よろしくお願いします': 'よろしくお願いします！どのような症状でお困りですか？具体的な症状を教えていただければ、適切な市販薬をご提案いたします。',
                        'ありがとう': 'どういたしまして！他にご質問や症状がございましたら、お気軽にお聞かせください。',
                        'ありがとうございます': 'どういたしまして！他にご質問や症状がございましたら、お気軽にお聞かせください。',
                        'どうも': 'どういたしまして！他にご質問や症状がございましたら、お気軽にお聞かせください。',
                        'どうもありがとう': 'どういたしまして！他にご質問や症状がございましたら、お気軽にお聞かせください。',
                        'hello': 'Hello! What symptoms are you experiencing? Please tell me your specific symptoms, and I will recommend appropriate over-the-counter medicines.',
                        'hi': 'Hi! What symptoms are you experiencing? Please tell me your specific symptoms, and I will recommend appropriate over-the-counter medicines.',
                        'thanks': "You're welcome! If you have any other questions or symptoms, please feel free to let me know.",
                        'thank you': "You're welcome! If you have any other questions or symptoms, please feel free to let me know."
                    }
                    
                    # 挨拶に応じた返答を選択（デフォルトは汎用挨拶）
                    greeting_response = 'こんにちは！どのような症状でお困りですか？具体的な症状を教えていただければ、適切な市販薬をご提案いたします。'
                    for greeting_key, response in greeting_responses.items():
                        if greeting_key in user_message.lower():
                            greeting_response = response
                            break
                    
                    bot_response = {
                        'type': 'bot',
                        'content': greeting_response,
                        'diagnosis': None
                    }
                    session['messages'].append(bot_response)
                    session.modified = True
                    
                    # DB保存処理
                    if sid:
                        session_data = get_session_from_db(sid)
                        if not session_data:
                            session_data = {
                                'session_id': sid,
                                'username': session.get('username', 'Unknown'),
                                'messages': session['messages'].copy(),
                                'last_activity': datetime.now(),
                                'client_ip': request.remote_addr,
                                'user_agent': request.headers.get('User-Agent', ''),
                                'user_attributes': session.get('user_attributes', {}),
                                'session_active': True
                            }
                            save_session_to_db(sid, session_data)
                        else:
                            session_data['messages'] = session['messages'].copy()
                            session_data['last_activity'] = datetime.now()
                            save_session_to_db(sid, session_data)
                    
                    message_count = len(session['messages'])
                    logger.info(f"✅ POST処理完了（挨拶返答） - JSON返却: {message_count} messages")
                    return jsonify({'status': 'ok', 'message_count': message_count})
                
                # システム紹介、医薬品検索、明確な質問、または語尾・記号から質問と判断できる場合は質問回答に進む
                if (is_system_intro or is_medicine_search or has_question_keyword or
                    has_question_suffix or ends_with_question_mark):
                    logger.info(f"❓ CLEAR QUESTION DETECTED: {user_message}")
                    
                    # ユーザーメッセージは既に1回目の保存処理で保存済み（重複を避けるため削除）
                    # import uuid
                    # user_response = {
                    #     'type': 'user',
                    #     'content': user_message,
                    #     'timestamp': datetime.now().isoformat(),
                    #     'uuid': str(uuid.uuid4())  # 一意な識別子を追加
                    # }
                    # ALL_SESSIONS[sid]['messages'].append(user_response)
                    # logger.info(f"💾 ユーザー質問を保存: {user_message}")
                    
                    # 質問回答に直接進む
                    try:
                        # 最新の推奨医薬品を取得
                        session_data_for_medicines = get_session_from_db(sid) if sid else {}
                        latest_recommended_medicines = []
                        for msg in reversed(session_data_for_medicines.get('messages', [])):
                            if msg.get('type') == 'bot' and msg.get('diagnosis'):
                                diagnosis = msg.get('diagnosis', {})
                                if diagnosis.get('recommended_medicines'):
                                    latest_recommended_medicines = diagnosis.get('recommended_medicines', [])
                                    break
                        
                        logger.info(f"📋 Latest recommended medicines: {len(latest_recommended_medicines)} items")
                        
                        # 会話履歴を取得
                        conversation_history = session_data_for_medicines.get('messages', [])[-10:]
                        
                        # ChatGPTに質問を送信
                        chat_response = chat_with_medicine_context(
                            user_message, 
                            conversation_history, 
                            latest_recommended_medicines
                        )
                        
                        # 評価ボタン用のデータを準備
                        import json
                        import html
                        
                        # HTML整形用ヘルパー関数
                        def safe_format(text):
                            """テキストを安全にHTML表示用に整形"""
                            if not text:
                                return ""
                            # XSSリスクを防ぐためにエスケープしてから改行を変換
                            escaped = html.escape(text)
                            return escaped.replace("\n", "<br>")
                        
                        # 回答の全文を作成（全項目を含める）
                        answer_text = safe_format(chat_response.get('answer', '回答を取得できませんでした'))
                        medicine_details = safe_format(chat_response.get('medicine_details', ''))
                        interactions = safe_format(chat_response.get('interactions', ''))
                        doping_check = safe_format(chat_response.get('doping_check', ''))
                        side_effects = safe_format(chat_response.get('side_effects', ''))
                        consultation_advice = safe_format(chat_response.get('consultation_advice', ''))
                        
                        full_response_html = f"""
<div class="chat-response">
    <h4>💬 医薬品相談回答</h4>
    <p><strong>回答:</strong><br>{answer_text}</p>
    
    {f'<div style="margin-top: 15px; padding: 10px; background: #e3f2fd; border-radius: 5px;"><strong>💊 医薬品の詳細:</strong><br>{medicine_details}</div>' if medicine_details else ''}
    
    {f'<div style="margin-top: 15px; padding: 10px; background: #fff3e0; border-radius: 5px;"><strong>⚠️ 相互作用の注意:</strong><br>{interactions}</div>' if interactions else ''}
    
    {f'<div style="margin-top: 15px; padding: 10px; background: #ffebee; border-radius: 5px;"><strong>🏃 ドーピングチェック:</strong><br>{doping_check}</div>' if doping_check else ''}
    
    {f'<div style="margin-top: 15px; padding: 10px; background: #fce4ec; border-radius: 5px;"><strong>⚕️ 副作用情報:</strong><br>{side_effects}</div>' if side_effects else ''}
    
    {f'<div style="margin-top: 15px; padding: 10px; background: #f1f8e9; border-radius: 5px;"><strong>🩺 相談アドバイス:</strong><br>{consultation_advice}</div>' if consultation_advice else ''}
</div>"""
                        
                        # デバッグログ：ChatGPT応答の内容確認
                        logger.info("-" * 40)
                        logger.info(f"[DEBUG] ChatGPT response fields:")
                        logger.info(f"  - answer: {'✓' if answer_text else '✗'} ({len(answer_text) if answer_text else 0} chars)")
                        logger.info(f"  - medicine_details: {'✓' if medicine_details else '✗'} ({len(medicine_details) if medicine_details else 0} chars)")
                        logger.info(f"  - interactions: {'✓' if interactions else '✗'} ({len(interactions) if interactions else 0} chars)")
                        logger.info(f"  - doping_check: {'✓' if doping_check else '✗'} ({len(doping_check) if doping_check else 0} chars)")
                        logger.info(f"  - side_effects: {'✓' if side_effects else '✗'} ({len(side_effects) if side_effects else 0} chars)")
                        logger.info(f"  - consultation_advice: {'✓' if consultation_advice else '✗'} ({len(consultation_advice) if consultation_advice else 0} chars)")
                        
                        # デバッグログ：HTML構造の整合性確認
                        opening_divs = full_response_html.count('<div')
                        closing_divs = full_response_html.count('</div>')
                        logger.info(f"[DEBUG] HTML structure: {opening_divs} opening divs, {closing_divs} closing divs {'✓' if opening_divs == closing_divs else '✗ MISMATCH'}")
                        logger.info("-" * 40)
                        
                        # メッセージIDを生成
                        message_id = f"msg_{int(time.time() * 1000)}_{random.randint(1000, 9999)}"
                        logger.info(f"[DEBUG] Generated message_id: {message_id}")
                        
                        # [SECURITY NOTE]: full_response_html is generated only from safe, pre-sanitized templates.
                        # All user input is escaped via safe_format (html.escape + newline conversion).
                        # Do not re-escape, otherwise structured HTML (icons, sections) will break.
                        
                        # 評価ボタンを追加（メッセージIDベース方式）
                        bot_content = full_response_html + f"""
<div class="feedback-buttons" style="margin-top: 20px; padding: 15px; background: #f8f9fa; border-radius: 8px; border: 1px solid #dee2e6;">
    <p style="margin: 0 0 10px 0; font-weight: bold; color: #495057;">この回答はいかがでしたか？</p>
    <button class="feedback-btn-positive" onclick="handlePositiveFeedback('{message_id}')" style="background: #28a745; color: white; border: none; padding: 8px 16px; margin-right: 10px; border-radius: 4px; cursor: pointer; font-size: 14px; min-width: 80px;">
        適切
    </button>
    <button class="feedback-btn-negative" onclick="handleNegativeFeedback('{message_id}')" style="background: #dc3545; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; font-size: 14px; min-width: 80px;">
        不適切
    </button>
</div>"""
                        
                        bot_response = {
                            'type': 'bot',
                            'content': bot_content,
                            'message_id': message_id,
                            'diagnosis': {
                                'chat_response': chat_response,
                                'is_question': True
                            },
                            'timestamp': datetime.now().isoformat()
                        }
                        
                        # 質問応答をDBに保存
                        if sid:
                            session_data = get_session_from_db(sid)
                            if not session_data:
                                session_data = {
                                    'session_id': sid,
                                    'username': session.get('username', 'Unknown'),
                                    'messages': [],
                                    'last_activity': datetime.now(),
                                    'client_ip': request.remote_addr,
                                    'user_agent': request.headers.get('User-Agent', ''),
                                    'user_attributes': session.get('user_attributes', {}),
                                    'session_active': True
                                }
                            if 'messages' not in session_data:
                                session_data['messages'] = []
                            session_data['messages'].append(bot_response)
                            session_data['last_activity'] = datetime.now()
                            save_session_to_db(sid, session_data)
                        
                        # セッションCookie肥大化を防ぐため、Flaskセッションからmessagesを削除
                        if 'messages' in session:
                            del session['messages']
                            session.modified = True
                        logger.info(f"✅ 質問応答完了: {user_message}")
                        
                        # 質問応答の場合は、user_attributesを初期化してセッションに保存
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
                        session['user_attributes'] = user_attributes
                        session.modified = True
                        
                        # JSONレスポンスを返す
                        updated_session = get_session_from_db(sid) if sid else {}
                        message_count = len(updated_session.get('messages', []))
                        return jsonify({'status': 'ok', 'message_count': message_count})
                        
                    except Exception as e:
                        logger.error(f"❌ 医薬品相談機能実行時エラー: {e}")
                        import traceback
                        logger.error(traceback.format_exc())
                        bot_response = {
                            'type': 'bot',
                            'content': f"申し訳ございません。システムエラーが発生しました: {str(e)}",
                            'diagnosis': None,
                            'timestamp': datetime.now().isoformat()
                        }
                        
                        # エラー応答をDBに保存
                        if sid:
                            session_data = get_session_from_db(sid)
                            if session_data:
                                if 'messages' not in session_data:
                                    session_data['messages'] = []
                                session_data['messages'].append(bot_response)
                                session_data['last_activity'] = datetime.now()
                                save_session_to_db(sid, session_data)
                        # セッションCookie肥大化を防ぐため、Flaskセッションからmessagesを削除
                        if 'messages' in session:
                            del session['messages']
                            session.modified = True
                        
                        # エラーの場合もuser_attributesを初期化
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
                        session['user_attributes'] = user_attributes
                        session.modified = True
                        
                        # JSONレスポンスを返す
                        updated_session = get_session_from_db(sid) if sid else {}
                        message_count = len(updated_session.get('messages', []))
                        return jsonify({'status': 'ok', 'message_count': message_count})
                else:
                    # 操作指示の検出（セキュリティ検証の後）
                    if is_operation_command(user_message):
                        logger.info(f"🔄 操作指示を検出: {user_message}")
                        
                        # セッションから過去の症状文を取得
                        session_messages = session.get('messages', [])
                        previous_symptom_text = None
                        
                        # 過去のメッセージから症状文を探す（最初のユーザーメッセージ）
                        for msg in session_messages:
                            if msg.get('type') == 'user':
                                previous_symptom_text = msg.get('content', '')
                                break
                        
                        # 症状文が見つからない場合は、現在のメッセージを症状として扱う
                        if not previous_symptom_text:
                            previous_symptom_text = user_message
                        
                        # ユーザー属性情報を取得
                        user_attributes = session.get('user_attributes', {})
                        
                        # 推奨医薬品の再分析を実行
                        # 既存の医薬品推奨処理を再利用するため、user_messageを一時的にprevious_symptom_textに置き換える
                        original_user_message = user_message
                        user_message = previous_symptom_text
                        # sanitized_messageも更新（再分析用）
                        sanitized_message = previous_symptom_text
                        
                        # 再分析フラグを設定
                        session['is_reanalysis'] = True
                        is_question = False  # 症状分析を強制実行
                        
                        logger.info(f"🔄 再分析を実行: 症状文={previous_symptom_text[:50]}...")
                    
                    # 属性応答の可能性がある場合のみ属性抽出を実行
                    logger.info(f"❓ POSSIBLE ATTRIBUTE RESPONSE DETECTED: {user_message}")
                    
                    # 言語を検出（すべての入力に対して実行）
                    detected_language = detect_language(user_message)
                    session['detected_language'] = detected_language
                    logger.info(f"🌍 検出された言語: {detected_language}")
                    
                    # 初回チャットで症状入力の場合は属性抽出をスキップして症状分析に進む
                    if len(session.get('messages', [])) <= 1 and is_symptom_input(user_message):
                        logger.info(f"🔄 初回症状入力のため属性抽出をスキップして症状分析に進みます")
                        is_question = False  # 症状分析を強制実行
                    else:
                        # ステップ1: 多言語対応ユーザー属性を抽出・更新
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
                        
                        # 多言語対応の属性抽出を実行（言語検出は既に上で実行済み）
                        try:
                            extracted_attrs = extract_user_attributes_multilingual(
                                user_message, 
                                client, 
                                user_attributes
                            )
                            
                            logger.info(f"🤖 多言語属性抽出結果: {extracted_attrs}")
                            
                            # 抽出された情報をセッションに保存
                            for key, value in extracted_attrs.items():
                                if value is not None and value != [] and value != "" and key != 'detected_language':
                                    if key == 'age' and isinstance(value, (int, float)):
                                        user_attributes['age'] = int(value)
                                        logger.info(f"📝 年齢を更新: {user_attributes['age']}")
                                        updated = True
                                    elif key == 'gender' and value in ['男性', '女性', 'Male', 'Female', '남성', '여성', '男性', '女性']:
                                        # 多言語の性別を日本語に統一
                                        if value in ['Male', '남성', '男性']:
                                            user_attributes['gender'] = '男性'
                                        elif value in ['Female', '여성', '女性']:
                                            user_attributes['gender'] = '女性'
                                        else:
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
                                        # 薬に関する情報はother_infoに入れない（current_medicationsに反映される）
                                        medication_patterns = [
                                            r'他に服用.*薬.*(?:あり|なし|ありません|ない)',
                                            r'服用.*薬.*(?:あり|なし|ありません|ない)',
                                            r'薬.*服用.*(?:あり|なし|ありません|ない)',
                                            r'服用.*(?:あり|なし|ありません|ない)',
                                            r'薬.*(?:あり|なし|ありません|ない)',
                                            r'服用している薬.*(?:あり|なし|ありません|ない)',
                                            r'他に服用.*(?:あり|なし|ありません|ない)'
                                        ]
                                        is_medication_info = any(re.search(pattern, value, re.IGNORECASE) for pattern in medication_patterns)
                                        
                                        if not is_medication_info:
                                            user_attributes['other_info'] = value
                                            logger.info(f"📝 その他情報を更新: {user_attributes['other_info']}")
                                            updated = True
                                        else:
                                            logger.info(f"📝 薬に関する情報のためother_infoには設定しません: {value}")
                        
                        except Exception as e:
                            logger.error(f"多言語属性抽出エラー: {e}")
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
                # 薬に関する情報（「他に服用している薬はありません」など）を除外
                medication_exclusion_patterns = [
                    r'他に服用.*薬.*(?:あり|なし|ありません|ない)',
                    r'服用.*薬.*(?:あり|なし|ありません|ない)',
                    r'薬.*服用.*(?:あり|なし|ありません|ない)',
                    r'服用.*(?:あり|なし|ありません|ない)',
                    r'薬.*(?:あり|なし|ありません|ない)'
                ]
                is_medication_message = any(re.search(pattern, user_message, re.IGNORECASE) for pattern in medication_exclusion_patterns)
                
                if not is_medication_message and ('その他' in user_message or '伝えたい' in user_message or 
                    'want to know' in user_message.lower() or 'ask about' in user_message.lower() or 'tell you' in user_message.lower()):
                    # その他の情報を抽出（「他に」は薬に関する情報の可能性があるため除外）
                    other_patterns = [
                        r'その他[はが]?([^。、\n]+)',
                        r'伝えたいこと[はが]?([^。、\n]+)',
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
                                # 薬に関する情報はother_infoに入れない（current_medicationsに反映される）
                                medication_patterns = [
                                    r'服用.*薬.*(?:あり|なし|ありません|ない)',
                                    r'薬.*服用.*(?:あり|なし|ありません|ない)',
                                    r'服用.*(?:あり|なし|ありません|ない)',
                                    r'薬.*(?:あり|なし|ありません|ない)'
                                ]
                                is_medication_info = any(re.search(pattern, other_info, re.IGNORECASE) for pattern in medication_patterns)
                                
                                if not is_medication_info:
                                    user_attributes['other_info'] = other_info
                                    logger.info(f"📝 その他情報を抽出: {other_info}")
                                    updated = True
                                    break
                                else:
                                    logger.info(f"📝 薬に関する情報のためother_infoには設定しません: {other_info}")
                                    break
                
                # セッションに保存
                session['user_attributes'] = user_attributes
                session.modified = True
                
                # DBも更新
                sid = session.get('_id')
                if sid:
                    session_data = get_session_from_db(sid)
                    if session_data:
                        session_data['user_attributes'] = user_attributes
                        session_data['last_activity'] = datetime.now()
                        save_session_to_db(sid, session_data)
                
                # ステップ2: 属性が更新された場合の追加処理
                if updated:
                    logger.info("✅ 属性データが更新されました。前回の症状に対して再推奨を実行します。")
                    session.pop('is_reanalysis', None)
                    session.pop('reanalysis_attributes', None)

                    # 症状期間が7日を超える場合の医療機関受診案内をチェック
                    symptom_duration = user_attributes.get('symptom_duration_days')
                    if symptom_duration and symptom_duration > 7:
                        logger.info(f"⚠️ 症状期間が7日を超えています: {symptom_duration}日")
                        
                        # ユーザーメッセージをDBに保存（症状期間チェック前に保存）
                        if sid:
                            session_data = get_session_from_db(sid)
                            if session_data:
                                session_data['messages'] = session['messages'].copy()
                                session_data['last_activity'] = datetime.now()
                                save_session_to_db(sid, session_data)
                            logger.info(f"💾 ユーザーメッセージをDBに保存: {len(session['messages'])} messages")
                        
                        # 医療機関受診案内を追加
                        medical_advice = {
                            'type': 'bot',
                            'content': '⚠️ 症状が7日を超えている場合は、市販薬での対応が困難な可能性があります。医療機関（病院・クリニック）での受診をお勧めします。',
                            'medical_advice': True
                        }
                        if 'messages' not in session:
                            session['messages'] = []
                        session['messages'].append(medical_advice)
                        if sid:
                            session_data = get_session_from_db(sid)
                            if session_data:
                                if 'messages' not in session_data:
                                    session_data['messages'] = []
                                session_data['messages'].append(medical_advice)
                                session_data['last_activity'] = datetime.now()
                                save_session_to_db(sid, session_data)
                        
                        # 症状期間が7日を超える場合は医薬品推奨を停止
                        logger.info(f"🚫 症状期間が7日を超えるため医薬品推奨を停止します")
                        session.modified = True
                        message_count = len(session['messages'])
                        return jsonify({'status': 'ok', 'message_count': message_count})
                    
                    # 属性更新後、前回の症状メッセージを取得して再推奨を実行
                    logger.info(f"🔄 属性更新後、前回の症状に対して再推奨を実行します")
                    
                    # セッションから前回の症状メッセージを取得
                    previous_symptom_message = None
                    if sid:
                        session_data = get_session_from_db(sid)
                        if session_data:
                            messages = session_data.get('messages', [])
                            # ユーザーメッセージの中で症状を述べているものを逆順で検索
                            for msg in reversed(messages):
                                if msg.get('type') == 'user':
                                    content = msg.get('content', '')
                                    # 症状キーワードを含むメッセージを探す（拡張版）
                                    symptom_keywords = [
                                        '痛い', '痛み', '熱', '咳', '鼻水', '頭痛', '発熱', 'のど', '喉', '寒気', 'だるい', '疲れ',
                                        'かゆい', 'かゆみ', '痒い', '痒み', 'かぶれ', '発疹', '湿疹', 'じんましん',
                                        '下痢', '便秘', '腹痛', '胃痛', '吐き気', '嘔吐', '胸やけ', '胃もたれ',
                                        'めまい', '不眠', '肩こり', '腰痛', '関節痛', '筋肉痛'
                                    ]
                                    if any(keyword in content for keyword in symptom_keywords):
                                        previous_symptom_message = content
                                        logger.info(f"📋 前回の症状メッセージを取得: {content[:50]}...")
                                        break
                    
                    # 前回の症状が見つかった場合、更新された属性情報で再推奨を実行
                    if previous_symptom_message:
                        logger.info(f"💊 更新された属性情報で再推奨を開始: {previous_symptom_message[:50]}...")
                        # 症状メッセージとして扱うため、is_questionをFalseに設定
                        user_message = previous_symptom_message
                        is_question = False
                        # 医薬品相談処理を実行するためにフラグを設定
                        session['is_medicine_consultation'] = True
                        session['is_reanalysis_with_updated_attributes'] = True
                    else:
                        # 前回の症状が見つからない場合、属性更新の確認メッセージのみ返す
                        logger.warning(f"⚠️ 前回の症状メッセージが見つかりません。属性更新の確認のみ返します。")
                        bot_response = {
                            'type': 'bot',
                            'content': f"✅ 属性情報を更新しました。\n\n年齢: {user_attributes.get('age', '未入力')}\n性別: {user_attributes.get('gender', '未入力')}\nアレルギー: {', '.join(user_attributes.get('allergies', [])) if user_attributes.get('allergies') else 'なし'}\n服用中の薬: {', '.join(user_attributes.get('current_medications', [])) if user_attributes.get('current_medications') else 'なし'}\n\n症状について教えていただければ、更新された情報をもとに適切な医薬品をご提案いたします。",
                            'diagnosis': None,
                            'attribute_update_confirmation': True
                        }
                        
                        # ユーザーメッセージをDBに保存
                        if sid:
                            session_data = get_session_from_db(sid)
                            if not session_data:
                                session_data = {
                                    'session_id': sid,
                                    'username': session.get('username', 'Unknown'),
                                    'messages': [],
                                    'last_activity': datetime.now(),
                                    'client_ip': request.remote_addr,
                                    'user_agent': request.headers.get('User-Agent', ''),
                                    'user_attributes': user_attributes,
                                    'session_active': True
                                }
                            if 'messages' not in session_data:
                                session_data['messages'] = []
                            session_data['messages'].append(bot_response)
                            session_data['last_activity'] = datetime.now()
                            save_session_to_db(sid, session_data)
                            logger.info(f"💾 属性更新確認メッセージを保存: {len(session_data.get('messages', []))} messages")
                        
                        # Cookieサイズ削減（メッセージはDBのみに保存）
                        if 'messages' in session:
                            del session['messages']
                            session.modified = True
                            logger.info(f"📝 Session cookie size reduced - messages only in DB")
                        
                        # セッションの他の大きなデータも最小限に
                        if sid:
                            session_data = get_session_from_db(sid)
                            if session_data:
                                session_data['last_activity'] = datetime.now()
                                save_session_to_db(sid, session_data)
                        
                        message_count = len(session_data.get('messages', [])) if sid and session_data else 0
                        logger.info(f"✅ POST処理完了 - 属性更新確認メッセージ返却: {message_count} messages")
                        return jsonify({'status': 'ok', 'message_count': message_count})
                else:
                    # 属性が更新されていない場合は通常の質問応答
                    logger.info(f"❓ 通常の質問として処理します")
                    try:
                        # 最新の推奨医薬品を取得（DBを参照）
                        session_data_for_medicines2 = get_session_from_db(sid) if sid else {}
                        latest_recommended_medicines = []
                        for msg in reversed(session_data_for_medicines2.get('messages', [])):
                            if msg.get('type') == 'bot' and msg.get('diagnosis'):
                                diagnosis = msg.get('diagnosis', {})
                                if diagnosis.get('recommended_medicines'):
                                    latest_recommended_medicines = diagnosis.get('recommended_medicines', [])
                                    break

                        logger.info(f"📋 Latest recommended medicines: {len(latest_recommended_medicines)} items")

                        # 会話履歴を取得（DBから直近10件）
                        conversation_history = session_data_for_medicines2.get('messages', [])[-10:]

                        # ChatGPTに質問を送信
                        chat_response = chat_with_medicine_context(
                            user_message,
                            conversation_history,
                            latest_recommended_medicines
                        )

                        # 医薬品相談回答の処理は既に上記で実装済み
                        # 重複コードを削除

                    except Exception as e:
                        logger.error(f"❌ 医薬品相談機能実行時エラー: {e}")
                        bot_response = {
                            'type': 'bot',
                            'content': f"申し訳ございません。システムエラーが発生しました: {str(e)}",
                            'diagnosis': None
                        }

                        # エラー応答をDBに保存
                        if sid:
                            session_data = get_session_from_db(sid)
                            if session_data:
                                if 'messages' not in session_data:
                                    session_data['messages'] = []
                                session_data['messages'].append(bot_response)
                                session_data['last_activity'] = datetime.now()
                                save_session_to_db(sid, session_data)
                        # セッションCookie肥大化を防ぐため、Flaskセッションからmessagesを削除
                        if 'messages' in session:
                            del session['messages']
                            session.modified = True
                
            # 症状入力の場合のみ医薬品推奨を実行
            # 質問の場合は属性抽出のみ行い、医薬品推奨は行わない
            if not is_question:
                # 言語を検出（症状入力時にも実行）
                detected_language = detect_language(user_message)
                session['detected_language'] = detected_language
                logger.info(f"🌍 検出された言語: {detected_language}")
                
                # 医薬品相談回答処理の開始時にフラグを設定
                session['is_medicine_consultation'] = True
                logger.info(f"🏥 SYMPTOM INPUT DETECTED: {user_message}")
                logger.info(f"💊 医薬品相談回答処理開始 - フラグ設定完了")
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
                    
                    # No symptoms detectedの場合は早期リターン
                    if matched_symptoms.get('status') == 'success' and matched_symptoms.get('message') == 'No symptoms detected':
                        logger.warning(f"⚠️ 症状が検出できませんでした: {user_message}")
                        bot_response = {
                            'type': 'bot',
                            'content': '申し訳ございませんが、入力いただいた内容から症状を分析することができませんでした。もう少し詳しく症状を教えていただけますか？例えば「頭痛がします」「熱があります」など、具体的な症状を入力してください。',
                            'diagnosis': None
                        }
                        session['messages'].append(bot_response)
                        session.modified = True
                        
                        # DB保存処理
                        if sid:
                            session_data = get_session_from_db(sid)
                            if not session_data:
                                session_data = {
                                    'session_id': sid,
                                    'username': session.get('username', 'Unknown'),
                                    'messages': session['messages'].copy(),
                                    'last_activity': datetime.now(),
                                    'client_ip': request.remote_addr,
                                    'user_agent': request.headers.get('User-Agent', ''),
                                    'user_attributes': session.get('user_attributes', {}),
                                    'session_active': True
                                }
                                save_session_to_db(sid, session_data)
                            else:
                                session_data['messages'] = session['messages'].copy()
                                session_data['last_activity'] = datetime.now()
                                save_session_to_db(sid, session_data)
                        
                        message_count = len(session['messages'])
                        logger.info(f"✅ POST処理完了（症状検出失敗） - JSON返却: {message_count} messages")
                        return jsonify({'status': 'ok', 'message_count': message_count})
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
                    medicine_type = analysis_result.get('medicine_type')
                    symptoms = analysis_result.get('symptoms', [])
                    
                    # 医薬品種類が判定できない場合（Noneまたは「その他」）はエラーメッセージを返す
                    if not medicine_type or medicine_type == 'その他':
                        logger.warning(f"⚠️ 医薬品種類が判定できませんでした: {medicine_type}")
                        
                        # エラーメッセージの内容
                        error_message = '正常に処理が行われなかったので改めて送信してください。'
                        
                        # 評価ボタン用のデータを準備（HTMLエスケープ処理）
                        import json
                        import html
                        
                        # HTMLエスケープ処理
                        escaped_user_message = html.escape(user_message)
                        escaped_error_message = html.escape(error_message)
                        
                        feedback_data = {
                            'user_message': escaped_user_message,
                            'ai_response': escaped_error_message,
                            'security_score': None,
                            'error_type': 'medicine_type_detection_failed'
                        }
                        
                        # JSONエンコードしてHTMLエスケープ
                        feedback_json = html.escape(json.dumps(feedback_data, ensure_ascii=False))
                        
                        # 不具合報告用のデータ属性を準備
                        bug_report_data_attrs = f'data-user-message="{escaped_user_message}" data-ai-response="{escaped_error_message}" data-security-score=""'
                        
                        # エラーメッセージに評価ボタンと不具合報告ボタンを追加
                        bot_content = f"""
<div class="chat-response" style="padding: 15px; background: #fff3cd; border-radius: 8px; border: 1px solid #ffc107;">
    <h4 style="margin: 0 0 10px 0; color: #856404;">⚠️ エラー</h4>
    <p style="margin: 0; color: #856404;">{escaped_error_message}</p>
    <div class="feedback-buttons" style="margin-top: 20px; padding: 15px; background: #f8f9fa; border-radius: 8px; border: 1px solid #dee2e6;">
        <p style="margin: 0 0 10px 0; font-weight: bold; color: #495057;">このエラーメッセージはいかがでしたか？</p>
        <div style="display: flex; gap: 10px; flex-wrap: wrap;">
            <button class="feedback-btn-positive" onclick="handlePositiveFeedback({feedback_json})" style="background: #28a745; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; font-size: 14px;">
                適切
            </button>
            <button class="feedback-btn-negative" onclick="handleNegativeFeedback({feedback_json})" style="background: #dc3545; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; font-size: 14px;">
                不適切
            </button>
            <button class="bug-report-btn" onclick="handleSecurityReportFromButton(this)" {bug_report_data_attrs} style="background: #6c757d; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; font-size: 14px;">
                🐛 不具合報告
            </button>
        </div>
    </div>
</div>"""
                        
                        bot_response = {
                            'type': 'bot',
                            'content': bot_content,
                            'diagnosis': None,
                            'timestamp': datetime.now().isoformat()
                        }
                        if 'messages' not in session:
                            session['messages'] = []
                        session['messages'].append(bot_response)
                        session.modified = True
                        
                        # DBにも保存
                        sid = session.get('_id')
                        if sid:
                            session_data = get_session_from_db(sid)
                            if not session_data:
                                session_data = {
                                    'session_id': sid,
                                    'username': session.get('username', 'Unknown'),
                                    'messages': [],
                                    'last_activity': datetime.now(),
                                    'client_ip': request.remote_addr,
                                    'user_agent': request.headers.get('User-Agent', ''),
                                    'user_attributes': session.get('user_attributes', {}),
                                    'session_active': True
                                }
                            if 'messages' not in session_data:
                                session_data['messages'] = []
                            session_data['messages'].append(bot_response)
                            session_data['last_activity'] = datetime.now()
                            save_session_to_db(sid, session_data)
                        
                        message_count = len(session['messages'])
                        return jsonify({'status': 'ok', 'message_count': message_count})
                    
                    logger.info(f"📋 Detected medicine type: {medicine_type}")
                    logger.info(f"📋 Detected symptoms: {symptoms}")
                    
                    # ステップ2: 医薬品の種類に応じて推奨アルゴリズムを選択
                    # SYMPTOM_DICTIONARYから動的に対応種類を判定
                    from rule_based_recommendation import SYMPTOM_DICTIONARY
                    
                    # SYMPTOM_DICTIONARYに含まれる全てのmedicine_typesを取得
                    supported_types = set()
                    for symptom_data in SYMPTOM_DICTIONARY.values():
                        supported_types.update(symptom_data.get('medicine_types', []))
                    
                    # 全ての医薬品種類でルールベース推奨を使用
                    # confidence < 0.4 の場合のみGPTフォールバック
                    if medicine_type in supported_types:
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
                        
                        # DBも更新
                        sid = session.get('_id')
                        if sid:
                            session_data = get_session_from_db(sid)
                            if session_data:
                                session_data['user_attributes'] = user_attributes
                                session_data['last_activity'] = datetime.now()
                                save_session_to_db(sid, session_data)
                        
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
                        
                        # ルールベース結果のデバッグログ
                        logger.info(f"🔍 Rule-based result: {recommendation_result.get('status', 'unknown')}")
                        logger.info(f"🔍 Rule-based medicines count: {len(recommendation_result.get('recommended_medicines', []))}")
                        
                        # ルールベース結果を従来の形式に変換
                        if recommendation_result.get('status') == 'success':
                            # API呼び出し回数を記録
                            monitor.increment_api_calls()
                            
                            recommended_medicines = recommendation_result.get('recommended_medicines', [])
                            
                            # 使用上の注意をChatGPTで自動生成（最適化版）
                            usage_notes = recommendation_result.get('usage_notes', '')
                            if not usage_notes or usage_notes == '添付文書をよく読んでご使用ください。':
                                # 推奨された医薬品の使用上の注意を一括生成
                                try:
                                    from medicine_logic import generate_usage_notes
                                    
                                    # 上位3つの医薬品の使用上の注意を並列処理で生成
                                    generated_notes = []
                                    for medicine in recommended_medicines[:3]:  # 上位3つのみ
                                        try:
                                            # CSVデータから追加情報を取得
                                            medicine_with_details = medicine.copy()
                                            # 年齢制限とドーピング情報を追加
                                            if 'age_restriction' not in medicine_with_details:
                                                medicine_with_details['age_restriction'] = medicine.get('age_restriction', '情報なし')
                                            if 'doping_prohibited' not in medicine_with_details:
                                                medicine_with_details['doping_prohibited'] = medicine.get('doping_prohibited', 'なし')
                                            if 'competition_category' not in medicine_with_details:
                                                medicine_with_details['competition_category'] = medicine.get('competition_category', '情報なし')
                                            if 'conditions' not in medicine_with_details:
                                                medicine_with_details['conditions'] = medicine.get('conditions', '情報なし')
                                            
                                            # 使用上の注意を生成（キャッシュ機能付き）
                                            medicine_notes = generate_usage_notes(
                                                medicine.get('name', ''),
                                                medicine_with_details,
                                                user_info
                                            )
                                            if medicine_notes and medicine_notes != "使用上の注意の生成に失敗しました。薬剤師または登録販売者にご相談ください。":
                                                generated_notes.append(f"<strong>{medicine.get('name', '')}:</strong><br>{medicine_notes}")
                                        except Exception as e:
                                            logger.warning(f"使用上の注意生成エラー: {e}")
                                            continue
                                    
                                    if generated_notes:
                                        usage_notes = '<br><br>'.join(generated_notes)
                                    else:
                                        usage_notes = '添付文書をよく読んでご使用ください。'
                                        
                                except Exception as e:
                                    logger.warning(f"使用上の注意一括生成エラー: {e}")
                                    usage_notes = '添付文書をよく読んでご使用ください。'
                            
                            doctor_consultation = recommendation_result.get('doctor_consultation', '症状が改善しない場合は医師にご相談ください。')
                            additional_questions = recommendation_result.get('additional_questions', [])
                            critical_questions = recommendation_result.get('critical_questions', [])
                            influenza_risk = recommendation_result.get('influenza_risk', False)
                            influenza_reason = recommendation_result.get('influenza_reason', '')
                            
                            recommendation_result = {
                                'symptoms': symptoms,
                                'medicine_type': medicine_type,
                                'recommended_medicines': recommended_medicines,
                                'usage_notes': usage_notes,
                                'doctor_consultation': doctor_consultation,
                                'additional_questions': additional_questions,
                                'critical_questions': critical_questions,  # 新規追加
                                'influenza_risk': influenza_risk,  # 新規追加
                                'influenza_reason': influenza_reason,  # 新規追加
                                'algorithm': 'rule_based'
                            }
                        elif recommendation_result.get('status') == 'escalation_required':
                            # エスカレーションが必要な場合
                            monitor.increment_error()
                            recommendation_result = {
                                'symptoms': symptoms,
                                'medicine_type': medicine_type,
                                'recommended_medicines': [],
                                'usage_notes': '',
                                'doctor_consultation': recommendation_result.get('reason', ''),
                                'escalation': True,
                                'algorithm': 'rule_based'
                            }
                        elif recommendation_result.get('status') == 'no_candidates':
                            # 候補医薬品が見つからない場合 - エラーメッセージを表示
                            monitor.increment_error()
                            confidence_score = recommendation_result.get('confidence_score', 0.0)
                            logger.warning(f"⚠️ Rule-based algorithm: no candidates found (confidence: {confidence_score:.2f})")
                            # エラー情報を保持して後続のエラー表示処理で使用
                            recommendation_result['error'] = True
                            recommendation_result['error_type'] = 'no_candidates'
                            recommendation_result['error_details'] = {
                                'confidence_score': confidence_score,
                                'reason': recommendation_result.get('reason', '該当する医薬品が見つかりませんでした'),
                                'technical_details': f"信頼度スコア: {confidence_score:.2f}, 症状: {symptoms}, 医薬品の種類: {medicine_type}"
                            }
                        elif recommendation_result.get('status') == 'error':
                            # ルールベース推奨エラー - エラーメッセージを表示
                            monitor.increment_error()
                            logger.warning(f"⚠️ Rule-based algorithm error: {recommendation_result.get('reason', 'unknown error')}")
                            recommendation_result['error'] = True
                            recommendation_result['error_type'] = 'rule_based_error'
                            recommendation_result['error_details'] = {
                                'reason': recommendation_result.get('reason', 'ルールベース推奨でエラーが発生しました'),
                                'error_message': recommendation_result.get('error_message', ''),
                                'technical_details': f"ステータス: error, 症状: {symptoms}, 医薬品の種類: {medicine_type}"
                            }
                        elif recommendation_result.get('status') == 'missing_critical_info':
                            # 必須情報不足 - エラーメッセージを表示
                            monitor.increment_error()
                            logger.warning(f"⚠️ Rule-based algorithm: missing critical information")
                            recommendation_result['error'] = True
                            recommendation_result['error_type'] = 'missing_critical_info'
                            recommendation_result['error_details'] = {
                                'reason': recommendation_result.get('reason', '症状が検出されていません'),
                                'missing_fields': recommendation_result.get('missing_fields', []),
                                'technical_details': f"ステータス: missing_critical_info, 症状: {symptoms}, 医薬品の種類: {medicine_type}"
                            }
                        else:
                            # その他のエラーの場合 - エラーメッセージを表示
                            monitor.increment_error()
                            status = recommendation_result.get('status', 'unknown')
                            logger.warning(f"⚠️ Rule-based algorithm failed (status: {status})")
                            recommendation_result['error'] = True
                            recommendation_result['error_type'] = 'unknown_error'
                            recommendation_result['error_details'] = {
                                'reason': recommendation_result.get('reason', f'ルールベース推奨でエラーが発生しました（ステータス: {status}）'),
                                'status': status,
                                'technical_details': f"ステータス: {status}, 症状: {symptoms}, 医薬品の種類: {medicine_type}"
                            }
                    else:
                        # ChatGPTベースのアルゴリズムを使用
                        logger.info(f"✅ Using ChatGPT-BASED algorithm for {medicine_type}")
                        
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
                        
                        # ChatGPTベース推奨用のuser_infoを構築
                        user_info = {
                            'age': user_attributes.get('age'),
                            'gender': user_attributes.get('gender'),
                            'pregnant': user_attributes.get('pregnant'),
                            'breastfeeding': user_attributes.get('breastfeeding'),
                            'current_medications': user_attributes.get('current_medications', []),
                            'allergies': user_attributes.get('allergies', []),
                            'symptom_duration_days': user_attributes.get('symptom_duration_days')
                        }
                        
                        recommendation_result = comprehensive_medicine_recommendation(user_message)
                        recommendation_result['algorithm'] = 'chatgpt'
                        # API呼び出し回数を記録
                        monitor.increment_api_calls()
                        
                        # ChatGPTベースでも個別の医薬品の使用上の注意を表示
                        recommended_medicines = recommendation_result.get('recommended_medicines', [])
                        if recommended_medicines:
                            # 個別の医薬品の使用上の注意を収集
                            individual_notes = []
                            for medicine in recommended_medicines:
                                if medicine.get('usage_notes') and medicine.get('usage_notes') != '添付文書をよく読んでご使用ください。':
                                    individual_notes.append(f"<strong>{medicine.get('product_name', '')}:</strong><br>{medicine.get('usage_notes', '')}")
                            
                            if individual_notes:
                                # 個別の使用上の注意がある場合はそれを使用
                                recommendation_result['usage_notes'] = '<br><br>'.join(individual_notes)
                            elif not recommendation_result.get('usage_notes'):
                                # 個別の使用上の注意がない場合のみ簡易的なものを設定
                                recommendation_result['usage_notes'] = '添付文書をよく読んでご使用ください。妊娠中・授乳中の方、アレルギー体質の方は医師にご相談ください。'
                    
                    end_time = time.time()
                    response_time = round(end_time - start_time, 3)
                    
                    # 属性情報の不足チェック
                    user_attributes = session.get('user_attributes', {})
                    missing_questions, missing_priority = check_missing_attributes(user_attributes)
                    
                    if missing_questions:
                        recommendation_result['additional_questions'] = missing_questions
                        recommendation_result['missing_priority'] = missing_priority
                        logger.info(f"❓ Missing attributes detected: {len(missing_questions)} questions, priority: {missing_priority}")
                    
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
                    
                    # ルールベース推奨失敗時のエラー表示処理
                    if recommendation_result.get('error'):
                        import json
                        import html
                        
                        error_type = recommendation_result.get('error_type', 'unknown')
                        error_details = recommendation_result.get('error_details', {})
                        reason = error_details.get('reason', 'ルールベース推奨でエラーが発生しました')
                        technical_details = error_details.get('technical_details', '')
                        
                        # エラータイプに応じたメッセージを生成
                        error_messages = {
                            'no_candidates': {
                                'title': '⚠️ 医薬品が見つかりませんでした',
                                'main_message': '入力された症状に対して、適切な市販薬が見つかりませんでした。',
                                'recommendations': [
                                    '症状をより具体的に記述してください（例：痛みの部位、程度、継続期間など）',
                                    '症状が1週間以上続いている場合は、医療機関を受診することをお勧めします',
                                    '重症の症状がある場合は、速やかに医師の診察を受けてください'
                                ]
                            },
                            'rule_based_error': {
                                'title': '⚠️ 推奨システムエラー',
                                'main_message': '症状の解析中にエラーが発生しました。',
                                'recommendations': [
                                    '症状を別の表現で入力し直してください',
                                    '具体的な症状名（例：頭痛、発熱、のどの痛みなど）を含めて記述してください',
                                    '症状が続く場合は、医療機関を受診することをお勧めします'
                                ]
                            },
                            'missing_critical_info': {
                                'title': '⚠️ 症状が検出されませんでした',
                                'main_message': '入力されたテキストから症状を検出できませんでした。',
                                'recommendations': [
                                    '具体的な症状名を含めて記述してください（例：「頭が痛い」「熱がある」など）',
                                    '症状の部位や程度も記述すると、より適切な推奨が可能です',
                                    '症状が続く場合は、医療機関を受診することをお勧めします'
                                ]
                            },
                            'unknown_error': {
                                'title': '⚠️ システムエラー',
                                'main_message': '推奨システムでエラーが発生しました。',
                                'recommendations': [
                                    '症状を再度入力してください',
                                    '症状が続く場合は、医療機関を受診することをお勧めします',
                                    '問題が解決しない場合は、薬剤師または登録販売者にご相談ください'
                                ]
                            }
                        }
                        
                        error_info = error_messages.get(error_type, error_messages['unknown_error'])
                        
                        # HTMLエスケープ処理
                        escaped_user_message = html.escape(user_message)
                        escaped_reason = html.escape(reason)
                        escaped_technical = html.escape(technical_details)
                        
                        error_content = f"""
<div class="recommendation-result error" style="background: #fff3cd; border: 2px solid #ffc107; border-radius: 8px; padding: 20px; margin: 15px 0;">
    <h4 style="color: #856404; margin-top: 0;">{error_info['title']}</h4>
    <p style="color: #856404; font-weight: bold; margin: 10px 0;">{error_info['main_message']}</p>
    <p style="color: #856404; margin: 10px 0;"><strong>エラー理由:</strong> {escaped_reason}</p>
    
    <h5 style="color: #856404; margin-top: 20px; margin-bottom: 10px;">📋 推奨される対応</h5>
    <ul style="color: #856404; margin: 10px 0; padding-left: 20px;">
"""
                        for rec in error_info['recommendations']:
                            error_content += f"        <li>{rec}</li>\n"
                        
                        error_content += f"""    </ul>
    
    <h5 style="color: #856404; margin-top: 20px; margin-bottom: 10px;">🏥 医師への相談をお勧めします</h5>
    <p style="color: #856404; margin: 10px 0;">
        以下の場合は、速やかに医療機関（病院・クリニック）を受診してください：
    </p>
    <ul style="color: #856404; margin: 10px 0; padding-left: 20px;">
        <li>症状が1週間以上続いている場合</li>
        <li>症状が悪化している場合</li>
        <li>高熱（38.5度以上）が続く場合</li>
        <li>重症の症状がある場合（激しい痛み、呼吸困難、意識障害など）</li>
        <li>妊娠中・授乳中の場合</li>
        <li>7歳未満のお子様の場合</li>
    </ul>
    
    <details style="margin-top: 20px; padding: 10px; background: #fff; border-radius: 4px; border: 1px solid #dee2e6;">
        <summary style="color: #856404; cursor: pointer; font-weight: bold;">技術的な詳細（デバッグ用）</summary>
        <pre style="color: #856404; margin: 10px 0; font-size: 0.9em; white-space: pre-wrap; word-wrap: break-word;">{escaped_technical}</pre>
    </details>
</div>"""
                        
                        error_data = {
                            'user_message': escaped_user_message,
                            'ai_response': error_content,
                            'security_score': None,
                            'error_type': error_type
                        }
                        
                        error_json = html.escape(json.dumps(error_data, ensure_ascii=False))
                        
                        bot_content = error_content + f"""
    <div class="feedback-buttons" style="margin-top: 20px; padding: 15px; background: #f8f9fa; border-radius: 8px; border: 1px solid #dee2e6;">
        <p style="margin: 0 0 10px 0; font-weight: bold; color: #495057;">このエラーメッセージはいかがでしたか？</p>
        <button class="feedback-btn-positive" onclick="handlePositiveFeedback({error_json})" style="background: #28a745; color: white; border: none; padding: 8px 16px; margin-right: 10px; border-radius: 4px; cursor: pointer; font-size: 14px;">
            適切
        </button>
        <button class="feedback-btn-negative" onclick="handleNegativeFeedback({error_json})" style="background: #dc3545; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; font-size: 14px;">
            不適切
        </button>
    </div>
"""
                    # エスカレーションが必要な場合の特別処理
                    elif recommendation_result.get('escalation'):
                        # 重要な注意事項用のデータを準備（HTMLエスケープ処理）
                        import json
                        import html
                        
                        # HTMLエスケープ処理
                        escaped_user_message = html.escape(user_message)
                        escalation_content = f"""
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
</div>"""
                        
                        escalation_data = {
                            'user_message': escaped_user_message,
                            'ai_response': escalation_content,
                            'security_score': None
                        }
                        
                        # JSONエンコードしてHTMLエスケープ
                        escalation_json = html.escape(json.dumps(escalation_data, ensure_ascii=False))
                        
                        bot_content = escalation_content + f"""
    <div class="feedback-buttons" style="margin-top: 20px; padding: 15px; background: #f8f9fa; border-radius: 8px; border: 1px solid #dee2e6;">
        <p style="margin: 0 0 10px 0; font-weight: bold; color: #495057;">この重要な注意事項はいかがでしたか？</p>
        <button class="feedback-btn-positive" onclick="handlePositiveFeedback({escalation_json})" style="background: #28a745; color: white; border: none; padding: 8px 16px; margin-right: 10px; border-radius: 4px; cursor: pointer; font-size: 14px;">
            適切
        </button>
        <button class="feedback-btn-negative" onclick="handleNegativeFeedback({escalation_json})" style="background: #dc3545; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; font-size: 14px;">
            不適切
        </button>
    </div>
</div>"""
                    else:
                        # 通常の推奨結果の表示
                        algorithm_label = {
                            'rule_based': 'ルールベースアルゴリズム（安全性重視）',
                            'chatgpt': 'ChatGPTベースアルゴリズム',
                            'chatgpt_fallback': 'ChatGPTベースアルゴリズム（フォールバック）'
                        }.get(recommendation_result.get('algorithm', 'unknown'), '不明')
                        
                        # 全ての推奨結果に対してアドバイスを生成（再分析時だけでなく常時）
                        personalized_section = ""
                        try:
                            # ユーザー属性を取得
                            user_attrs = session.get('user_attributes', {})
                            
                            # 再分析時はreanalysis_attributesを使用
                            if session.get('is_reanalysis'):
                                user_attrs = session.get('reanalysis_attributes', user_attrs)
                                session.pop('is_reanalysis', None)
                                session.pop('reanalysis_attributes', None)
                            
                            # インフルエンザリスク情報を追加
                            influenza_risk = recommendation_result.get('influenza_risk', False)
                            influenza_reason = recommendation_result.get('influenza_reason', '')
                            
                            personalized_advice = generate_personalized_advice(
                                user_attrs,
                                recommended_medicines,
                                symptoms,
                                recommendation_client,
                                influenza_risk=influenza_risk,
                                influenza_reason=influenza_reason
                            )
                            
                            personalized_section = f"""
    <div style="background: #e3f2fd; padding: 20px; margin: 15px 0; border-radius: 8px; border-left: 4px solid #2196f3;">
        <h4 style="color: #1976d2; margin-top: 0;">💡 あなたに合わせたアドバイス</h4>
        <p style="margin: 5px 0; line-height: 1.6; white-space: pre-wrap;">{personalized_advice}</p>
    </div>
"""
                        except Exception as e:
                            logger.error(f"❌ 個別説明生成エラー: {e}")
                            # エラー時はインフルエンザリスク情報のみ表示
                            influenza_risk = recommendation_result.get('influenza_risk', False)
                            influenza_reason = recommendation_result.get('influenza_reason', '')
                            if influenza_risk:
                                personalized_section = f"""
    <div style="background: #fff3e0; padding: 20px; margin: 15px 0; border-radius: 8px; border-left: 4px solid #ff9800;">
        <h4 style="color: #f57c00; margin-top: 0;">⚠️ インフルエンザの可能性について</h4>
        <p style="margin: 5px 0; line-height: 1.6;">{influenza_reason}。インフルエンザの可能性がある場合は、アスピリンを含む医薬品の使用を避け、早めに医療機関を受診することをお勧めします。</p>
    </div>
"""
                        
                        # critical_questionsとadditional_questionsを統合して推奨前に表示
                        critical_questions = recommendation_result.get('critical_questions', [])
                        additional_questions = recommendation_result.get('additional_questions', [])
                        missing_priority = recommendation_result.get('missing_priority')
                        
                        # すべての質問を統合（critical_questionsを先に）
                        all_questions_before = []
                        if critical_questions:
                            all_questions_before.extend(critical_questions)
                        if additional_questions:
                            for q in additional_questions:
                                if q not in all_questions_before:
                                    all_questions_before.append(q)
                        
                        # 推奨前の質問セクション（すべての質問を統合して表示）
                        questions_section_before = ""
                        if all_questions_before:
                            priority_label = {
                                'critical': '必須',
                                'important': '重要',
                                'optional': '任意'
                            }.get(missing_priority, '重要' if critical_questions else '任意')
                            
                            priority_message = {
                                'critical': 'より適切な医薬品をご提案するため、以下の情報を教えてください：',
                                'important': '安全のため、以下の情報を教えてください：',
                                'optional': 'より安全な使用のため、可能であれば以下の情報を教えてください：'
                            }.get(missing_priority, 'より適切な医薬品をご提案するため、以下の情報を教えてください：')
                            
                            # critical_questionsがある場合はcriticalスタイル、そうでない場合はimportantスタイル
                            if critical_questions:
                                question_bg = '#ffebee'
                                question_border = '#f44336'
                                question_title = '#c62828'
                                if missing_priority != 'critical':
                                    missing_priority = 'critical'
                                    priority_label = '必須'
                                    priority_message = 'より適切な医薬品をご提案するため、以下の情報を教えてください：'
                            elif missing_priority == 'critical':
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
                            
                            questions_section_before = f"""
    <div style="background: {question_bg}; padding: 15px; margin: 15px 0; border-radius: 8px; border-left: 4px solid {question_border};">
        <h4 style="color: {question_title}; margin-top: 0;">❓ 追加でお伺いしたいこと <span style="font-size: 0.9em;">（優先度: {priority_label}）</span></h4>
        <p style="margin: 10px 0;">{priority_message}</p>
        <ul style="margin: 10px 0; padding-left: 20px;">
"""
                            for question in all_questions_before:
                                questions_section_before += f"            <li style='margin: 5px 0;'>{question}</li>\n"
                            questions_section_before += """
        </ul>
        <button onclick="openAttributeModal()" class="answer-questions-btn">📝 回答する</button>
    </div>
"""
                        
                        # 属性更新による再推奨の場合、確認メッセージを追加
                        attribute_update_message = ""
                        if session.get('is_reanalysis_with_updated_attributes'):
                            user_attrs = session.get('user_attributes', {})
                            attribute_info = []
                            if user_attrs.get('age'):
                                attribute_info.append(f"年齢: {user_attrs['age']}歳")
                            if user_attrs.get('gender'):
                                attribute_info.append(f"性別: {user_attrs['gender']}")
                            if user_attrs.get('allergies'):
                                allergies_str = ', '.join(user_attrs['allergies']) if user_attrs['allergies'] else 'なし'
                                attribute_info.append(f"アレルギー: {allergies_str}")
                            if user_attrs.get('current_medications'):
                                meds_str = ', '.join(user_attrs['current_medications']) if user_attrs['current_medications'] else 'なし'
                                attribute_info.append(f"服用中の薬: {meds_str}")
                            
                            attribute_update_message = f"""
    <div style="background: #e1f5fe; padding: 15px; margin: 15px 0; border-radius: 8px; border-left: 4px solid #0277bd;">
        <h4 style="color: #01579b; margin-top: 0;">✅ 属性情報を更新しました</h4>
        <p style="margin: 5px 0; line-height: 1.6;">{' | '.join(attribute_info) if attribute_info else '属性情報が更新されました'}</p>
        <p style="margin: 5px 0; font-size: 0.9em; color: #666;">更新された情報をもとに、より適切な医薬品を再推奨いたします。</p>
    </div>
"""
                            # アレルギー警告を追加
                            if user_attrs.get('allergies') and user_attrs['allergies'] != ['なし']:
                                allergies_list = [a for a in user_attrs['allergies'] if a != 'なし']
                                if allergies_list:
                                    attribute_update_message += f"""
    <div style="background: #fff3e0; padding: 15px; margin: 15px 0; border-radius: 8px; border-left: 4px solid #ff9800;">
        <h4 style="color: #e65100; margin-top: 0;">⚠️ アレルギー情報について</h4>
        <p style="margin: 5px 0; line-height: 1.6;">アレルギー: <strong>{', '.join(allergies_list)}</strong></p>
        <p style="margin: 5px 0; font-size: 0.9em; color: #666;">アレルギーについて不明な点がある場合はお近くの薬剤師にご相談ください。</p>
    </div>
"""
                            session.pop('is_reanalysis_with_updated_attributes', None)
                        
                        bot_content = f"""
<div class="recommendation-result">
{attribute_update_message}
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
                                    
                                    # 年齢制限から数値のみを抽出（「15歳以上」→「15」）
                                    if age_restriction and isinstance(age_restriction, str):
                                        # 数値のみを抽出（例：「15歳以上」→「15」）
                                        age_match = re.search(r'(\d+)歳', age_restriction)
                                        if age_match:
                                            age_num = age_match.group(1)
                                            age_restriction = f"{age_num}歳以上"
                                    
                                    if age_restriction and isinstance(age_restriction, str) and age_restriction.strip():
                                        if '15歳未満' in age_restriction:
                                            age_restriction_display = '<p><strong>年齢制限:</strong> <span style="color: #d32f2f;">15歳以上の方が対象です。</span></p>'
                                        elif '7歳未満' in age_restriction:
                                            age_restriction_display = '<p><strong>年齢制限:</strong> <span style="color: #d32f2f;">7歳以上の方が対象です。</span></p>'
                                        elif '12歳未満' in age_restriction:
                                            age_restriction_display = '<p><strong>年齢制限:</strong> <span style="color: #d32f2f;">12歳以上の方が対象です。</span></p>'
                                        else:
                                            # その他の年齢制限がある場合
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
                                    
                                    # スコア表示の生成（相対スコアとスコア帯）
                                    score_display = ""
                                    relative_score = medicine.get('relative_score')
                                    score_level = medicine.get('score_level', '中')
                                    if relative_score is not None:
                                        score_percent = relative_score * 100
                                        score_display = f'<p style="margin: 5px 0;"><strong>📊 最適度:</strong> {score_percent:.1f}% <span style="color: #666;">({score_level})</span></p>'
                                    elif medicine.get('score') is not None:
                                        # 相対スコアがない場合は絶対スコアを表示（フォールバック）
                                        score_percent = medicine.get('score', 0) * 100
                                        score_display = f'<p style="margin: 5px 0;"><strong>📊 最適度:</strong> {score_percent:.1f}%</p>'
                                    
                                    # リスク警告の表示
                                    risk_warning_display = ""
                                    if medicine.get('risk_warning'):
                                        risk_warning_display = f'<p style="margin: 5px 0; color: #d32f2f;"><strong>⚠️ 注意:</strong> {medicine.get("risk_warning")}</p>'
                                    
                                    # 低スコア警告の表示
                                    low_score_warning_display = ""
                                    if medicine.get('low_score_warning'):
                                        low_score_warning_display = '<p style="margin: 5px 0; color: #f57c00;"><strong>⚠️ 推奨スコアが低めです。</strong> 使用前に薬剤師または登録販売者にご相談ください。</p>'
                                    
                                    bot_content += f"""
        <div class="medicine-item" style="padding: 10px 0; margin: 10px 0; border-bottom: 1px solid #ddd;">
            <h5 style="margin: 0 0 10px 0;">🏆 {rank}つ目: {medicine.get('product_name', '')} <span style="color: #666; font-size: 0.9em;">({medicine.get('manufacturer', '')})</span></h5>
            {score_display}
            <p style="margin: 5px 0;"><strong>推奨理由:</strong> {explanation}</p>
            {age_restriction_display}
            {risk_warning_display}
            {low_score_warning_display}
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
        <h5>🏆 {medicine.get('number', '')}つ目: {medicine.get('product_name', '')}</h5>
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
                                # ChatGPTベースの使用上の注意（HTML形式）をチェック
                                if '<strong>' in usage_notes and '<br>' in usage_notes:
                                    # ChatGPTベースの形式（HTML）の場合はそのまま表示
                                    formatted_usage_notes = usage_notes
                                else:
                                    # ルールベースの形式（テキスト）の場合は従来の処理
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
                                                        # 「歳以上の方が対象です」の場合はそのまま表示
                                                        current_html += f'<p style="margin: 3px 0;"><strong>年齢制限:</strong> {age_restriction}</p>'
                                                    else:
                                                        # その他の場合は「以上の方が対象です」を追加
                                                        current_html += f'<p style="margin: 3px 0;"><strong>年齢制限:</strong> {age_restriction}以上の方が対象です。</p>'
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
                        
                        # 表示順序: アドバイス → 推奨 → 質問（アドバイスを一番上に表示）
                        
                        # 多言語対応: 入力言語に応じて翻訳（フィードバックボタン追加前）
                        detected_language = session.get('detected_language', 'ja')
                        if detected_language != 'ja' and bot_content:
                            try:
                                logger.info(f"🌍 翻訳開始: {detected_language}")
                                translated_content = translate_medicine_recommendation(bot_content, detected_language, recommendation_client)
                                if translated_content and translated_content != bot_content:
                                    bot_content = translated_content
                                    logger.info(f"✅ 翻訳完了: {detected_language}")
                                else:
                                    logger.info(f"⚠️ 翻訳スキップ: 翻訳結果が空または同じ")
                            except Exception as e:
                                logger.error(f"❌ 翻訳エラー: {e}")
                                # 翻訳に失敗した場合は元のコンテンツを使用
                        
                        # 質問セクションを翻訳して追加（翻訳処理の後）
                        if questions_section_before:
                            if detected_language != 'ja':
                                try:
                                    logger.info(f"🌍 質問セクションの翻訳開始: {detected_language}")
                                    translated_questions_section = translate_medicine_recommendation(questions_section_before, detected_language, recommendation_client)
                                    if translated_questions_section and translated_questions_section != questions_section_before:
                                        questions_section_before = translated_questions_section
                                        logger.info(f"✅ 質問セクションの翻訳完了: {detected_language}")
                                    else:
                                        logger.info(f"⚠️ 質問セクションの翻訳スキップ: 翻訳結果が空または同じ")
                                except Exception as e:
                                    logger.warning(f"⚠️ 質問セクションの翻訳エラー: {e}")
                                    # 翻訳に失敗した場合は元のコンテンツを使用
                            bot_content += questions_section_before
                        
                        # 評価ボタン用のデータを準備（HTMLエスケープ処理）
                        import json
                        import html
                        
                        # HTMLエスケープ処理
                        escaped_user_message = html.escape(user_message)
                        escaped_ai_response = html.escape(bot_content)
                        
                        feedback_data = {
                            'user_message': escaped_user_message,
                            'ai_response': escaped_ai_response,
                            'security_score': None
                        }
                        
                        # JSONエンコードしてHTMLエスケープ
                        feedback_json = html.escape(json.dumps(feedback_data, ensure_ascii=False))
                        
                        # フィードバックボタンのテキストも翻訳
                        feedback_text = "この推奨結果はいかがでしたか？"
                        feedback_positive = "適切"
                        feedback_negative = "不適切"
                        if detected_language != 'ja':
                            try:
                                feedback_text_translated = translate_medicine_recommendation(feedback_text, detected_language, recommendation_client)
                                feedback_positive_translated = translate_medicine_recommendation(feedback_positive, detected_language, recommendation_client)
                                feedback_negative_translated = translate_medicine_recommendation(feedback_negative, detected_language, recommendation_client)
                                if feedback_text_translated and feedback_text_translated != feedback_text:
                                    feedback_text = feedback_text_translated
                                if feedback_positive_translated and feedback_positive_translated != feedback_positive:
                                    feedback_positive = feedback_positive_translated
                                if feedback_negative_translated and feedback_negative_translated != feedback_negative:
                                    feedback_negative = feedback_negative_translated
                            except Exception as e:
                                logger.warning(f"⚠️ フィードバックボタンの翻訳エラー: {e}")
                        
                        bot_content += f"""
    <div class="feedback-buttons" style="margin-top: 20px; padding: 15px; background: #f8f9fa; border-radius: 8px; border: 1px solid #dee2e6;">
        <p style="margin: 0 0 10px 0; font-weight: bold; color: #495057;">{feedback_text}</p>
        <button class="feedback-btn-positive" onclick="handlePositiveFeedback({feedback_json})" style="background: #28a745; color: white; border: none; padding: 8px 16px; margin-right: 10px; border-radius: 4px; cursor: pointer; font-size: 14px;">
            {feedback_positive}
        </button>
        <button class="feedback-btn-negative" onclick="handleNegativeFeedback({feedback_json})" style="background: #dc3545; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; font-size: 14px;">
            {feedback_negative}
        </button>
    </div>
</div>"""
                    
                        bot_diag = recommendation_result
                    
                except Exception as e:
                    logger.error(f"❌ 包括的医薬品推奨システム実行時エラー: {e}")
                    bot_content = f"申し訳ございません。システムエラーが発生しました: {str(e)}"
                    bot_diag = None
                
                # 個別アドバイスは既にbot_contentの最初に追加済み（重複削除）
                
                # bot_diagが未定義の場合はNoneに設定
                if 'bot_diag' not in locals():
                    bot_diag = None
                
                # ユーザー向け情報のサニタイズ
                def sanitize_for_user_storage(diagnosis_data):
                    """ユーザー向けに情報をサニタイズ"""
                    if not diagnosis_data:
                        return diagnosis_data
                    
                    sanitized = diagnosis_data.copy()
                    
                    # 推奨医薬品から管理者専用情報を除去（管理画面ではスコア情報を保持）
                    if 'recommended_medicines' in sanitized:
                        for medicine in sanitized['recommended_medicines']:
                            # 管理画面ではスコア情報を保持するため、削除しない
                            # medicine.pop('score', None)
                            # medicine.pop('scores', None)
                            # medicine.pop('score_breakdown', None)
                            
                            # 推奨理由を簡潔化
                            if 'reason' in medicine:
                                # 詳細なスコア情報を含む推奨理由を簡潔化
                                reason = medicine['reason']
                                if '✅' in reason or '⚠️' in reason or '|' in reason:
                                    medicine['reason'] = "症状に適した医薬品です"
                    
                    return sanitized
                
                # 診断結果をサニタイズ
                sanitized_diagnosis = sanitize_for_user_storage(bot_diag)
                
                # 管理者専用の詳細情報を別途保存（session_idを付与してフロントの一致判定を通す）
                if bot_diag and sid:
                    if sid not in ADMIN_SESSIONS:
                        ADMIN_SESSIONS[sid] = {}
                    try:
                        bot_diag_with_sid = dict(bot_diag)
                    except Exception:
                        # 念のためフォールバック
                        bot_diag_with_sid = bot_diag
                    # フロント側（admin_chat.html）は currentDetailedDiagnosis.session_id === currentSessionId を要求
                    # ここでセッションIDを埋め込むことでスコア付き詳細を確実に表示可能にする
                    if isinstance(bot_diag_with_sid, dict):
                        bot_diag_with_sid['session_id'] = sid
                    ADMIN_SESSIONS[sid]['detailed_diagnosis'] = bot_diag_with_sid
                    ADMIN_SESSIONS[sid]['last_updated'] = time.time()
                    logger.info(f"💾 管理者専用詳細情報を保存: {sid} (session_id付与済み)")
                
                bot_response = {
                    'type': 'bot',
                    'content': bot_content,
                    'diagnosis': sanitized_diagnosis
                }
            
            # bot_responseが定義されている場合の処理
            logger.info(f"🔍 bot_response check: in locals={('bot_response' in locals())}, bot_response={bot_response is not None if 'bot_response' in locals() else 'N/A'}")
            if 'bot_response' in locals() and bot_response is not None:
                logger.info(f"✅ bot_response found, content length: {len(bot_response.get('content', ''))}")
                # 重複チェック：同じ内容のメッセージが既に存在するかチェック
                existing_messages = session.get('messages', [])
                is_duplicate = False
                
                for existing_msg in existing_messages:
                    if (existing_msg.get('type') == 'bot' and 
                        existing_msg.get('content') == bot_response['content']):
                        is_duplicate = True
                        logger.warning(f"⚠️ 重複メッセージを検出、追加をスキップします")
                        break
                
                if not is_duplicate:
                    # DBに保存
                    if sid:
                        session_data = get_session_from_db(sid)
                        if not session_data:
                            # 新しいセッションを作成
                            session_data = {
                                'session_id': sid,
                                'username': session.get('username', 'Unknown'),
                                'messages': [],
                                'last_activity': datetime.now(),
                                'client_ip': request.remote_addr,
                                'user_agent': request.headers.get('User-Agent', ''),
                                'user_attributes': session.get('user_attributes', {}),
                                'session_active': True
                            }
                        
                        # メッセージを追加
                        if 'messages' not in session_data:
                            session_data['messages'] = []
                        session_data['messages'].append(bot_response)
                        session_data['last_activity'] = datetime.now()
                        
                        # DBに保存
                        save_session_to_db(sid, session_data)
                        logger.info(f"💾 メッセージ保存完了: {len(session_data.get('messages', []))} messages")
                        
                        # 医薬品相談回答処理後の重複削除を実行
                        if remove_duplicate_user_messages_after_ai_response(sid):
                            updated_session = get_session_from_db(sid)
                            if updated_session:
                                logger.info(f"✅ 重複削除完了: {len(updated_session.get('messages', []))} messages")
                        
                        # セッションCookie肥大化を防ぐためFlaskセッションからmessagesを削除
                        if 'messages' in session:
                            del session['messages']
                            session.modified = True
                            
                            # 医薬品相談回答処理の終了時にフラグをクリア
                            if session.get('is_medicine_consultation', False):
                                session['is_medicine_consultation'] = False
                                logger.info(f"💊 医薬品相談回答処理終了 - フラグクリア完了")
                else:
                    logger.info(f"⏭️ 重複メッセージのため追加をスキップしました")
            else:
                logger.error(f"❌ bot_responseが定義されていません - locals: {list(locals().keys())}")
                # フォールバック
                bot_response = {
                'type': 'bot',
                'content': '処理中にエラーが発生しました。',
                'diagnosis': None
                }
                if 'messages' not in session:
                    session['messages'] = []
                session['messages'].append(bot_response)
                session.modified = True
            
            # POST処理完了 - 次のセクションに進む
        else:
            # user_messageが空の場合
            logger.warning(f"⚠️ 空のメッセージを受信")
    
    # DBにセッション情報を保存/更新
    if sid:
        session_data = get_session_from_db(sid)
        
        if session_data:
            # 既存セッションの更新
            # 手動返信メッセージを保持
            existing_messages = session_data.get('messages', [])
            manual_replies = [msg for msg in existing_messages if msg.get('manual_reply')]
            
            # session['messages']が存在する場合のみマージ処理を実行（重複を避けるため）
            if 'messages' in session and session['messages']:
                session_messages = session['messages']
                
                # 重複を避けてメッセージをマージ
                for session_msg in session_messages:
                    if not any(
                        existing_msg.get('type') == session_msg.get('type') and 
                        existing_msg.get('content') == session_msg.get('content') and
                        existing_msg.get('uuid') == session_msg.get('uuid')
                        for existing_msg in existing_messages
                    ):
                        existing_messages.append(session_msg)
            
            # 手動返信メッセージを保持
            for manual_reply in manual_replies:
                if not any(msg.get('manual_reply') and msg.get('content') == manual_reply.get('content') for msg in existing_messages):
                    existing_messages.append(manual_reply)
            
            # セッション情報を更新（messagesは既に保存済みの場合があるため、既存のものを優先）
            session_data.update({
                'session_id': sid,
                'username': session.get('username', 'Unknown'),
                'last_activity': datetime.now(),
                'client_ip': client_ip,
                'user_agent': user_agent,
                'user_attributes': session.get('user_attributes', {}),
                'session_active': True
            })
            # messagesは既に更新されている場合はそのまま、そうでない場合は既存のものを維持
            if 'messages' not in session_data or not session_data.get('messages'):
                session_data['messages'] = existing_messages
            
            save_session_to_db(sid, session_data)
            logger.info(f"🔄 既存セッション更新: {sid} ({len(session_data.get('messages', []))} messages)")
        else:
            # 新しいセッションの場合
            existing_messages = []
            if 'messages' in session and session['messages']:
                existing_messages = session['messages'].copy()
            
            session_data = {
                'session_id': sid,
                'username': session.get('username', 'Unknown'),
                'messages': existing_messages,
                'last_activity': datetime.now(),
                'client_ip': client_ip,
                'user_agent': user_agent,
                'user_attributes': session.get('user_attributes', {}),
                'session_active': True
            }
            
            save_session_to_db(sid, session_data)
            logger.info(f"📝 新規セッション作成: {sid}")
        
        # セッションには最小限のデータのみ保存（Cookieサイズ削減）
        # messagesはDBのみに保存（永続化）
        if hasattr(session, 'modified'):
            session.modified = True
        
        # チャット履歴の永続化を強化（DBに保存済み）
        if sid:
            session_data = get_session_from_db(sid)
            if session_data:
                session_data['last_activity'] = datetime.now()
                save_session_to_db(sid, session_data)
            # メッセージは既に他の箇所で適切に保存済み（重複を避けるため更新しない）
        
        session_data_for_log = get_session_from_db(sid) if sid else None
        message_count_for_log = len(session_data_for_log.get('messages', [])) if session_data_for_log else 0
        logger.info(f"📝 Session {sid} updated: {message_count_for_log} messages (DB保存完了)")
        logger.info(f"📝 Session cookie size reduced - messages only in DB")
        logger.info(f"💾 チャット履歴永続化完了: {message_count_for_log} messages")
    
    # 手動返信メッセージがあるかチェック（安全な取得）
    manual_replies = [msg for msg in session.get('messages', []) if msg.get('manual_reply')]
    if manual_replies:
        logger.info(f"📝 Manual replies preserved: {len(manual_replies)} messages")
        if os.getenv('DEBUG_MODE', 'false').lower() == 'true':
            logger.debug(f"Manual replies found in session {sid}: {len(manual_replies)} messages")
            for i, reply in enumerate(manual_replies):
                logger.debug(f"  Manual reply {i+1}: {reply.get('content', '')[:50]}...")
    
    # POSTリクエストの場合はJSON形式で成功を返す
    if request.method == 'POST':
        # レスポンスを先に準備（最小限のDB読み取りのみ）
        # メッセージ数は既にsessionに保存されているため、DB読み取りを最小限に
        message_count = len(session.get('messages', []))
        response_data = {'status': 'ok', 'message_count': message_count}
        response = jsonify(response_data)
        
        # レスポンス返却後にログ出力（非同期化）
        try:
            # パフォーマンスメトリクスをログに記録
            metrics = monitor.get_metrics()
            log_performance_metrics(monitor, sid, 'POST_request', {
                'user_agent': user_agent,
                'client_ip': client_ip
            })
            
            # アクセス分析ログを記録（DB読み取りは最小限に）
            session_data = get_session_from_db(sid) if sid else None
            actual_message_count = len(session_data.get('messages', [])) if session_data else message_count
            log_access_analytics(sid, user_agent, client_ip, metrics['response_time_ms'], {
                'username': session.get('username', ''),
                'message_count': actual_message_count
            })
            
            logger.info(f"✅ POST処理完了 - JSON返却: {actual_message_count} messages")
        except Exception as e:
            logger.warning(f"ログ出力エラー（無視）: {e}")
        
        return response
    
    # GET処理（初期表示）
    # パフォーマンスメトリクスをログに記録
    metrics = monitor.get_metrics()
    log_performance_metrics(monitor, sid, 'GET_request', {
        'user_agent': user_agent,
        'client_ip': client_ip
    })
    
    # アクセス分析ログを記録
    session_data = get_session_from_db(sid) if sid else None
    message_count = len(session_data.get('messages', [])) if session_data else 0
    log_access_analytics(sid, user_agent, client_ip, metrics['response_time_ms'], {
        'username': session.get('username', ''),
        'message_count': message_count
    })
    
    messages = session_data.get('messages', []) if session_data else []
    logger.info(f"✅ GET処理完了 - HTML返却: {len(messages)} messages")
    return render_template('index.html', messages=messages, version=VERSION, username=session.get('username', 'Unknown'))

def generate_personalized_advice(user_attrs: Dict, medicines: List[Dict], symptoms: List[str], client, influenza_risk: bool = False, influenza_reason: str = "") -> str:
    """
    ユーザー属性に基づいた個別アドバイスをChatGPTで生成（インフルエンザリスク対応含む）
    
    Args:
        user_attrs: ユーザー属性情報
        medicines: 推奨医薬品リスト
        symptoms: 症状リスト
        client: OpenAIクライアント
        influenza_risk: インフルエンザリスクの有無
        influenza_reason: インフルエンザリスクの理由
    
    Returns:
        個別アドバイステキスト
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
    
    # 推奨医薬品の名前リストとリスク警告を収集
    medicine_names = [m.get('product_name', '') or m.get('name', '') for m in medicines[:3]]
    risk_warnings = []
    for m in medicines[:3]:
        if m.get('risk_warning'):
            risk_warnings.append(f"{m.get('product_name', '') or m.get('name', '')}: {m.get('risk_warning')}")
    
    # インフルエンザリスク情報を追加
    influenza_info = ""
    if influenza_risk:
        influenza_info = f"\n\n【重要】インフルエンザの可能性: {influenza_reason}\nインフルエンザの可能性がある場合は、アスピリンを含む医薬品の使用は避け、早めに医療機関を受診することをお勧めします。"
    
    # リスク成分警告情報を追加
    risk_warning_info = ""
    if risk_warnings:
        risk_warning_info = f"\n\n【リスク成分について】\n{chr(10).join(risk_warnings)}\nこれらの成分が含まれる医薬品については、使用前に必ず添付文書を確認し、不安な点があれば薬剤師または登録販売者にご相談ください。"
    
    prompt = f"""
あなたは登録販売者です。以下のユーザー情報と推奨医薬品を基に、このユーザーに合わせた個別のアドバイスを100-150字程度で生成してください。

【ユーザー情報】
{attr_summary}

【症状】
{', '.join(symptoms) if symptoms else '症状情報なし'}

【推奨医薬品】
{', '.join(medicine_names) if medicine_names else '推奨医薬品なし'}{influenza_info}{risk_warning_info}

【生成するアドバイス】
- ユーザーの年齢、性別、妊娠状態などを考慮
- 推奨医薬品がこのユーザーに適している理由
- 特に注意すべきポイント
- インフルエンザリスクがある場合はその注意喚起を含める
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

def check_missing_attributes(user_attributes):
    """不足している属性情報をチェックし、追加質問を生成"""
    missing_questions = []
    missing_priority = 'optional'
    
    # 必須情報のチェック
    if not user_attributes.get('age'):
        missing_questions.append('年齢を教えてください。（医薬品の適切な選択に必要です）')
        missing_priority = 'critical'
    
    if not user_attributes.get('gender'):
        missing_questions.append('性別を教えてください。（男性/女性）')
        missing_priority = 'critical'
    
    # 重要情報のチェック
    if user_attributes.get('gender') == 'female' and user_attributes.get('pregnant') is None:
        missing_questions.append('現在、妊娠中または授乳中ですか？（はい/いいえ）')
        if missing_priority == 'optional':
            missing_priority = 'important'
    
    if not user_attributes.get('symptom_duration_days'):
        missing_questions.append('症状はいつ頃から続いていますか？（例：昨日から、3日前から）')
        if missing_priority == 'optional':
            missing_priority = 'important'
    
    # 症状期間が7日を超える場合の医療機関受診案内
    symptom_duration = user_attributes.get('symptom_duration_days')
    if symptom_duration and symptom_duration > 7:
        missing_questions.append('⚠️ 症状が7日を超えている場合は、市販薬での対応が困難な可能性があります。医療機関（病院・クリニック）での受診をお勧めします。')
        missing_priority = 'critical'
    
    # 任意情報のチェック
    if not user_attributes.get('allergies'):
        missing_questions.append('アレルギーはありますか？（薬物アレルギー、食物アレルギーなど）')
    
    if not user_attributes.get('current_medications'):
        missing_questions.append('現在服用中の薬はありますか？')
    
    if not user_attributes.get('medical_history'):
        missing_questions.append('持病や既往歴はありますか？')
    
    return missing_questions, missing_priority

def is_operation_command(user_message: str) -> bool:
    """
    操作指示を検出（誤検出を防ぐための厳密な検出ロジック）
    
    セキュリティ対策:
    - 操作指示キーワードが文脈的に操作指示として使われているかを確認
    - 命令形（「更新して」「更新してください」など）を含む場合のみ検出
    - 症状記述（例: 「症状が更新されました」）は誤検出しない
    """
    import re
    
    # 操作指示のパターン（命令形を含む）
    operation_patterns = [
        r'情報を(足しました|追加しました).*更新',
        r'更新して(ください|くれ)',
        r'再読み込み(してください|してくれ)',
        r'リロード(してください|してくれ)',
        r'reload',
        r'refresh',
        r'更新(してください|してくれ|しろ|せよ)',
        r'情報を更新',
        r'ページを更新',
        r'画面を更新'
    ]
    
    # 症状記述として使われる可能性のあるパターン（除外）
    symptom_patterns = [
        r'症状が更新',
        r'状態が更新',
        r'体調が更新',
        r'痛みが更新'
    ]
    
    # 症状記述パターンにマッチする場合は除外
    for pattern in symptom_patterns:
        if re.search(pattern, user_message):
            return False
    
    # 操作指示パターンにマッチする場合は検出
    for pattern in operation_patterns:
        if re.search(pattern, user_message, re.IGNORECASE):
            return True
    
    return False

def is_symptom_input(message):
    """メッセージが症状入力かどうかを判定"""
    if not message:
        return False

    text = message.strip()
    lower_text = text.lower()

    # 症状を示すキーワード（優先判定）
    symptom_keywords = [
        '痛い', '痛み', '熱', '発熱', '咳', '鼻水', '頭痛', '腹痛', '吐き気', '嘔吐', '下痢', '便秘',
        '痒い', 'かゆい', '腫れ', '炎症', '発疹', '湿疹', 'めまい', 'だるい', '倦怠感', '疲れ', '不調', '症状',
        '喉', 'のど', '胃', '腸', '目', '耳', '鼻', '皮膚', '関節', '筋肉', '肩こり', '腰痛', '風邪', 'インフルエンザ',
        '寒気', '寒気がする', '寒気がします', '寒気があります', '寒気があり', '寒気が',
        '痺れ', 'しびれ', 'むくみ', '倦怠', '倦怠感', 'だるさ'
    ]

    # 質問を示すキーワード
    question_keywords = [
        'ですか', 'でしょうか', 'ですか？', 'でしょうか？', 'どう', '何', 'なぜ', 'いつ',
        '副作用', '飲み方', '注意', '効果', '効き目', '時間', '回数', '量', '併用',
        'ドーピング', '禁止', '違反', '大丈夫', '安全', '危険', '問題', '影響',
        '一緒に', '同時に', '飲んで', '使って', '服用', '投与', '飲み合わせ',
        'スポーツ', '競技', '運動', 'トレーニング', '試合', '大会', '検査', '陽性',
        '成分', '効能', '作用', 'メカニズム', '仕組み',
        '飲む', '使う', '摂取', '飲むタイミング', '飲む時間',
        '食前', '食後', '食間', '空腹時', '満腹時', '就寝前', '起床時',
        '他の薬', '併用', '同時', '一緒', '組み合わせ',
        '注意点', '気をつける', '避ける', '控える', '中止', '停止',
        '当たる', '当たります', '対象', '対象外', '含まれる', '含まれない',
        '使える', '使えない', '可能', '不可能', '適切', '不適切',
        '効く', '効かない', '効果的', '効果的でない',
        '副作用が出る', '副作用がある', '副作用がない',
        '安全性', '危険性', 'リスク',
        '教えて', '教えてください', '知りたい', '聞きたい'
    ]

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

    has_symptom_keyword = any(keyword in text for keyword in symptom_keywords)
    has_question_keyword = any(keyword in text for keyword in question_keywords)
    has_attribute_keyword = any(keyword in text for keyword in attribute_keywords)
    ends_with_question_mark = text.endswith('？') or text.endswith('?') or lower_text.endswith('?')

    # 【修正】属性キーワードと症状キーワードの数を比較
    # 追加質問への回答（属性情報が多く含まれる）を正しく判定するため
    attribute_count = sum(1 for keyword in attribute_keywords if keyword in text)
    symptom_count = sum(1 for keyword in symptom_keywords if keyword in text)
    
    # 属性キーワードが3つ以上含まれており、症状キーワードより多い場合は属性応答として優先
    # 例: "19歳です。女性です。妊娠中です。授乳していません。アレルギーはなしです。現在ビタミン剤を服用しています。症状は昨日から続いています。"
    if attribute_count >= 3 and attribute_count > symptom_count:
        return False
    
    # 質問キーワードまたは疑問符が含まれる場合は質問として扱う
    if has_question_keyword or ends_with_question_mark:
        return False
    
    # 症状キーワードが含まれている場合は症状入力と判定
    if has_symptom_keyword:
        return True

    # 明確な症状キーワードがなく、属性情報のみの場合は症状入力とみなさない
    if has_attribute_keyword:
        return False

    # デフォルトは症状入力として扱う（自由入力で症状を説明するケースを許容）
    return True

@app.route('/clear', methods=['POST'])
def clear_chat():
    """チャット履歴をクリア"""
    session['messages'] = []
    session.modified = True
    sid = session.get('_id')
    if sid:
        session_data = get_session_from_db(sid)
        if session_data:
            session_data['messages'] = []
            save_session_to_db(sid, session_data)
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

@app.route('/api/sessions', methods=['GET', 'POST'])
def api_sessions():
    """セッション情報を返す（GET）またはユーザー属性を保存（POST）"""
    try:
        sid = session.get('_id', 'unknown')
        
        # POSTリクエストの場合：ユーザー属性を保存
        if request.method == 'POST':
            data = request.get_json()
            user_attributes = data.get('user_attributes', {})
            
            if not sid or sid == 'unknown':
                sid = str(int(time.time() * 1000000))
                session['_id'] = sid
                session['username'] = f'ユーザー{get_next_user_number()}'
            
            # セッションとDBの両方にuser_attributesを保存
            session['user_attributes'] = user_attributes
            session.modified = True
            
            session_data = get_session_from_db(sid)
            if not session_data:
                session_data = {
                    'session_id': sid,
                    'username': session.get('username', f'ユーザー{get_next_user_number()}'),
                    'messages': [],
                    'session_active': True,
                    'last_activity': datetime.now(),
                    'client_ip': request.remote_addr,
                    'user_agent': request.headers.get('User-Agent', ''),
                    'user_attributes': user_attributes
                }
            else:
                session_data['user_attributes'] = user_attributes
                session_data['last_activity'] = datetime.now()
            
            save_session_to_db(sid, session_data)
            logger.info(f"💾 ユーザー属性を保存: {sid}")
            return jsonify({'status': 'ok', 'message': 'ユーザー情報を保存しました'})
        
        # GETリクエストの場合：セッション情報を返す
        all_sessions = get_all_sessions_from_db()
        logger.info(f"🔍 /api/sessions called - Session ID: {sid}")
        logger.info(f"🔍 ALL_SESSIONS keys: {list(all_sessions.keys())}")
        
        # セッションIDがない場合は新規作成
        if not sid or sid == 'unknown':
            sid = str(int(time.time() * 1000000))
            session['_id'] = sid
            session['username'] = f'ユーザー{get_next_user_number()}'
            logger.info(f"🆕 新しいセッションIDを作成: {sid}")
        
        # DBに存在しない場合は復旧
        session_data = get_session_from_db(sid)
        if not session_data:
            logger.warning(f"⚠️ /api/sessions - セッションIDがDBに存在しません (sid={sid})。セッションから復旧を試みます。")
            session_data = {
                'session_id': sid,
                'username': session.get('username', f'ユーザー{get_next_user_number()}'),
                'messages': session.get('messages', []),
                'session_active': True,
                'last_activity': datetime.now(),
                'client_ip': request.remote_addr,
                'user_agent': request.headers.get('User-Agent', ''),
                'user_attributes': session.get('user_attributes', {})
            }
            save_session_to_db(sid, session_data)
            logger.info(f"🆕 新規セッション作成: {sid}")
        else:
            # 既存セッションの場合はlast_activityのみ更新
            session_data['last_activity'] = datetime.now()
            save_session_to_db(sid, session_data)
            logger.info(f"🔄 既存セッション更新: {sid} ({len(session_data.get('messages', []))} messages)")
        
        # DBから取得（セッションCookieの肥大化を防ぐ）
        messages = session_data.get('messages', [])
        logger.info(f"📦 /api/sessions - DBから取得: {len(messages)} messages (sid={sid})")
        
        # セッションCookie肥大化を防ぐため、messagesをDBのみに保存
        # Flaskセッションからはmessagesを削除
        if 'messages' in session:
            del session['messages']
            session.modified = True
            logger.info(f"📝 Session cookie size reduced - messages only in DB")
        
        # user_attributesを取得（セッションまたはDBから）
        user_attributes = session.get('user_attributes', {})
        if not user_attributes:
            user_attributes = session_data.get('user_attributes', {})
        
        session_data = {
            'session_id': sid,
            'messages_count': len(messages),
            'last_activity': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'session_active': len(messages) > 0,
            'messages': messages,
            'user_attributes': user_attributes  # user_attributesを追加
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
    
    if request.method == 'GET':
        queue = get_manual_reply_queue()
        return jsonify(queue)
    
    elif request.method == 'POST':
        data = request.get_json()
        session_id = data.get('session_id')
        reply_message = data.get('reply_message')
        
        logger.info(f"Manual reply request received: session_id={session_id}, message={reply_message[:50] if reply_message else None}...")
        all_sessions = get_all_sessions_from_db()
        if os.getenv('DEBUG_MODE', 'false').lower() == 'true':
            logger.debug(f"Current session keys: {list(all_sessions.keys())}")
        
        if not session_id or not reply_message:
            return jsonify({'error': 'session_id and reply_message are required'}), 400
        
        # キューから該当するメッセージを削除
        queue = get_manual_reply_queue()
        for i, pending in enumerate(queue):
            if pending['session_id'] == session_id:
                queue.pop(i)
                set_manual_reply_queue(queue)
                logger.info(f"Removed pending message from queue for session {session_id}")
                break
        
        # 指定されたセッションIDのユーザーセッションに返信メッセージを追加
        target_session = get_session_from_db(session_id)
        if target_session:
            if os.getenv('DEBUG_MODE', 'false').lower() == 'true':
                logger.debug(f"Found target session: {target_session.get('session_id', 'unknown')}")
            
            # 返信メッセージを追加
            manual_reply_message = {
                'type': 'bot',
                'content': reply_message,
                'diagnosis': None,
                'manual_reply': True  # 手動返信のフラグ
            }
            
            if 'messages' not in target_session:
                target_session['messages'] = []
            target_session['messages'].append(manual_reply_message)
            target_session['last_activity'] = datetime.now()  # 最終アクティビティを更新
            
            # DBを更新
            save_session_to_db(session_id, target_session)
            
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
            logger.info(f"📝 DB updated: {len(target_session['messages'])} messages")
            logger.info(f"📝 Target session info: {target_session}")
            logger.info(f"📝 Manual reply message added: {manual_reply_message}")
            
            # メインサイトでの反映確認用ログ
            logger.info(f"=== Manual Reply Summary ===")
            logger.info(f"Session ID: {session_id}")
            logger.info(f"Total messages in DB: {len(target_session['messages'])}")
            logger.info(f"Manual reply messages: {len([msg for msg in target_session['messages'] if msg.get('manual_reply')])}")
            logger.info(f"Latest message: {target_session['messages'][-1] if target_session['messages'] else 'None'}")
            logger.info(f"===========================")
            
            return jsonify({
                'message': '手動返信を送信しました',
                'remaining_queue': len(get_manual_reply_queue()),
                'target_session_id': session_id,
                'messages_count': len(target_session['messages']),
                'session_updated': True
            })
        else:
            all_sessions = get_all_sessions_from_db()
            logger.error(f"❌ Session {session_id} not found in DB")
            logger.error(f"❌ Available sessions: {list(all_sessions.keys())}")
            return jsonify({'error': f'Session {session_id} not found'}), 404
    
    return jsonify({'error': 'Method not allowed'}), 405

@app.route('/api/all_sessions')
def api_all_sessions():
    result = []
    all_sessions = get_all_sessions_from_db()
    for sid, info in all_sessions.items():
        result.append({
            'session_id': sid,
            'username': info.get('username', ''),
            'messages': info.get('messages', []),
            'messages_count': len(info.get('messages', []))
        })
    
    # デバッグ用ログ
    logger.info(f"📊 All sessions API called: {len(result)} sessions")
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
        
        all_sessions = get_all_sessions_from_db()
        for sid, info in all_sessions.items():
            last_activity = info.get('last_activity', 0)
            # last_activityがdatetimeオブジェクトの場合はtimestampに変換
            if isinstance(last_activity, datetime):
                last_activity = last_activity.timestamp()
            elif isinstance(last_activity, str):
                try:
                    last_activity = datetime.fromisoformat(last_activity.replace('Z', '+00:00')).timestamp()
                except:
                    last_activity = 0
            
            if current_time - (last_activity or 0) < SESSION_TIMEOUT:
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
            'total_sessions': len(all_sessions),
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
        all_sessions = get_all_sessions_from_db()
        queue = get_manual_reply_queue()
        debug_info = {
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'total_sessions': len(all_sessions),
            'sessions_with_manual_replies': [],
            'manual_reply_queue': queue
        }
        
        for sid, info in all_sessions.items():
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
    # 現在のセッション情報をクリア（ユーザーが明示的に新しいセッションを開始した場合のみ）
    session.clear()

    # 新しいセッションIDとユーザー名を割り当て
    sid = str(int(time.time() * 1000)) + str(id(session))
    session['_id'] = sid
    user_number = get_next_user_number()
    session['username'] = f'ユーザー{user_number}'
    session['messages'] = []
    session.modified = True

    # DBに新規登録
    client_ip = request.remote_addr
    user_agent = request.headers.get('User-Agent', '')
    session_data = {
        'session_id': sid,
        'username': session['username'],
        'messages': [],
        'last_activity': datetime.now(),
        'client_ip': client_ip,
        'user_agent': user_agent,
        'user_attributes': session.get('user_attributes', {}),
        'session_active': True
    }
    save_session_to_db(sid, session_data)

    return jsonify({'message': '新しいセッションを開始しました', 'username': session['username']}), 200

@app.route('/api/request_admin', methods=['POST'])
def request_admin():
    """管理者対応要請を受け付ける（個別チャット単位）"""
    sid = session.get('_id')
    username = session.get('username', 'unknown')
    if sid:
        # セッションに要請フラグとAI自動応答OFFフラグを追加（個別チャット単位）
        session_data = get_session_from_db(sid) or {}

        # 既存セッションが存在しない場合は基本情報を補完
        if not session_data:
            session_data = {
                'session_id': sid,
                'username': username,
                'messages': session.get('messages', []).copy(),
                'last_activity': datetime.now(),
                'client_ip': request.remote_addr,
                'user_agent': request.headers.get('User-Agent', ''),
                'user_attributes': session.get('user_attributes', {}),
                'session_active': True
            }

        session_data['admin_request'] = True
        session_data['ai_auto_reply'] = False  # このチャットのみAI自動応答OFF

        session['admin_request'] = True
        session['ai_auto_reply'] = False  # このチャットのみAI自動応答OFF

        # システムメッセージを追加
        system_message = {
            'type': 'bot',
            'content': '薬剤師対応を要請しました。しばらくお待ちください。',
            'admin_request': True,
            'style_class': 'admin-request'
        }
        if 'messages' not in session:
            session['messages'] = []
        session['messages'].append(system_message)

        # DBにも保存（ページ更新後も表示されるように）
        messages_for_db = session_data.get('messages') or []
        messages_for_db.append(system_message)
        session_data['messages'] = messages_for_db
        session_data['last_activity'] = datetime.now()
        save_session_to_db(sid, session_data)

        session.modified = True
        
        # MANUAL_REPLY_QUEUEに同じセッションIDのadmin_requestがなければ追加
        queue = get_manual_reply_queue()
        already_exists = any(item.get('session_id') == sid and item.get('admin_request') for item in queue)
        if not already_exists:
            queue.append({
                'session_id': sid,
                'username': username,
                'user_message': '【薬剤師要請】' + username,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'status': 'admin_requested',
                'admin_request': True
            })
            set_manual_reply_queue(queue)
        
        logger.info(f"💊 薬剤師要請: {username} (Session: {sid}) - このチャットのみAI自動応答OFF")
        return jsonify({'status': 'ok', 'message': '薬剤師対応を要請しました'})
    return jsonify({'status': 'error', 'message': 'No session'}), 400

@app.route('/api/admin_mode', methods=['POST'])
def api_admin_mode():
    set_admin_mode(True)
    set_ai_auto_reply(False)
    return jsonify({'admin_mode': get_admin_mode(), 'ai_auto_reply': get_ai_auto_reply(), 'message': '管理者対応モードに切り替えました'})

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
    all_sessions = get_all_sessions_from_db()
    current_time = time.time()
    active_sessions = 0
    for s in all_sessions.values():
        last_activity = s.get('last_activity', 0)
        if isinstance(last_activity, datetime):
            last_activity = last_activity.timestamp()
        elif isinstance(last_activity, str):
            try:
                last_activity = datetime.fromisoformat(last_activity.replace('Z', '+00:00')).timestamp()
            except:
                last_activity = 0
        if current_time - (last_activity or 0) < SESSION_TIMEOUT:
            active_sessions += 1
    
    return jsonify({
        'status': 'ok',
        'csv_load_status': csv_load_status,
        'total_sessions': len(all_sessions),
        'active_sessions': active_sessions,
        'manual_reply_queue': len(get_manual_reply_queue()),
        'ai_auto_reply': get_ai_auto_reply(),
        'admin_mode': get_admin_mode(),
        'performance_stats': performance_stats
    })

@app.route('/admin/access_stats', methods=['GET'])
def admin_access_stats():
    """アクセス統計を取得"""
    from analytics import get_access_statistics
    stats = get_access_statistics()
    return jsonify(stats)

@app.route('/admin/performance_stats', methods=['GET'])
def admin_performance_stats():
    """パフォーマンス統計を取得"""
    from performance_monitor import get_performance_statistics
    stats = get_performance_statistics()
    return jsonify(stats)

@app.route('/admin/browser_distribution', methods=['GET'])
def admin_browser_distribution():
    """ブラウザ分布を取得"""
    from analytics import get_browser_distribution
    distribution = get_browser_distribution()
    return jsonify(distribution)

@app.route('/admin/os_distribution', methods=['GET'])
def admin_os_distribution():
    """OS分布を取得"""
    from analytics import get_os_distribution
    distribution = get_os_distribution()
    return jsonify(distribution)

@app.route('/admin/device_distribution', methods=['GET'])
def admin_device_distribution():
    """デバイス分布を取得"""
    from analytics import get_device_distribution
    distribution = get_device_distribution()
    return jsonify(distribution)

@app.route('/admin/realtime_monitoring', methods=['GET'])
def admin_realtime_monitoring():
    """リアルタイム監視データを取得"""
    from performance_monitor import get_global_monitor
    monitor = get_global_monitor()
    metrics = monitor.get_metrics()
    
    all_sessions = get_all_sessions_from_db()
    return jsonify({
        'memory_usage_percent': metrics.get('memory_usage_percent', 0),
        'cpu_usage_percent': metrics.get('cpu_usage_percent', 0),
        'response_time_ms': metrics.get('response_time_ms', 0),
        'active_sessions': len(all_sessions),
        'api_calls': metrics.get('api_calls', 0),
        'cache_hit_rate': metrics.get('cache_hit_rate', 0)
    })

@app.route('/admin/export_monitoring_data', methods=['GET'])
def admin_export_monitoring_data():
    """監視データをエクスポート"""
    from analytics import get_access_statistics
    from performance_monitor import get_performance_statistics
    import json
    
    data = {
        'access_stats': get_access_statistics(),
        'performance_stats': get_performance_statistics(),
        'export_time': datetime.now().isoformat()
    }
    
    return jsonify(data)

@app.route('/clear_logs', methods=['POST'])
def clear_logs():
    """ログとセッション履歴をクリア"""
    global network_logs
    
    # ネットワークログをクリア
    network_logs.clear()
    
    # すべてのセッションをクリア（管理者が明示的にクリアした場合のみ）
    # 注意: これによりすべてのチャット履歴が削除されます
    db = get_database()
    if db and (db.connection or db.connection_pool):
        # DBからすべてのセッションを削除
        all_sessions = get_all_sessions_from_db()
        for sid in all_sessions.keys():
            db.delete_session(sid)
        logger.info("🗑️ All sessions cleared from database")
    else:
        # フォールバック: メモリから削除
        ALL_SESSIONS.clear()
        logger.warning("⚠️ DB unavailable, cleared memory sessions only")
    
    # 手動返信待ちキューをクリア
    set_manual_reply_queue([])
    
    # ログファイルもクリア
    log_file = 'log/recommendation_log.jsonl'
    if os.path.exists(log_file):
        try:
            with open(log_file, 'w', encoding='utf-8') as f:
                pass  # ファイルを空にする
            logger.info("📝 ログファイルをクリアしました")
        except Exception as e:
            logger.error(f"❌ ログファイルのクリアに失敗: {e}")
    
    logger.info("🗑️ ログ、セッション履歴、手動返信待ちキューをすべてクリアしました")
    
    return jsonify({'status': 'ok', 'message': 'ログ、セッション履歴、手動返信待ちキューをクリアしました'})

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
        start_time = time.time()
        
        # OpenAI APIキーを確認
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            logger.error("❌ OPENAI_API_KEY が環境変数に設定されていません")
            add_network_log(
                'POST',
                '管理画面 - 医薬品相談テスト',
                {'message': user_message},
                None,
                time.time() - start_time,
                'failed',
                'OpenAI APIキーが設定されていません'
            )
            return jsonify({
                'status': 'error',
                'message': 'OpenAI APIキーが設定されていません',
                'error': '環境変数 OPENAI_API_KEY を設定してください'
            }), 500
        
        # OpenAIクライアントを初期化
        from openai import OpenAI
        test_client = OpenAI(api_key=api_key)
        logger.info(f"✅ OpenAIクライアント初期化成功（医薬品相談テスト用）")
        
        # 症状抽出を実行
        from medicine_logic import select_symptoms_via_gpt
        symptoms_result = select_symptoms_via_gpt(user_message, None, test_client)
        
        # 医薬品推奨を実行
        if symptoms_result and symptoms_result.get('status') == 'success':
            symptoms = symptoms_result.get('symptoms', [])
            
            # ルールベース推奨を試行
            from medicine_logic import analyze_symptoms_and_medicine_type
            medicine_type_result = analyze_symptoms_and_medicine_type(user_message, test_client)
            
            if medicine_type_result and medicine_type_result.get('medicine_type'):
                medicine_type = medicine_type_result['medicine_type']
                
                # ルールベース推奨
                from medicine_logic import rule_based_medicine_recommendation
                recommendation = rule_based_medicine_recommendation(
                    user_text=user_message,
                    user_info={},
                    client=test_client
                )
                
                # NaN値を処理してJSON互換にする
                import json
                import math
                
                def clean_nan(obj):
                    """NaN/Infinityを処理"""
                    if isinstance(obj, dict):
                        return {k: clean_nan(v) for k, v in obj.items()}
                    elif isinstance(obj, list):
                        return [clean_nan(item) for item in obj]
                    elif isinstance(obj, float):
                        if math.isnan(obj) or math.isinf(obj):
                            return None
                        return obj
                    return obj
                
                clean_recommendation = clean_nan(recommendation)
                
                # パフォーマンス統計を更新
                response_time = time.time() - start_time
                add_network_log(
                    'POST',
                    '管理画面 - 医薬品相談テスト',
                    {'message': user_message, 'type': 'rule_based'},
                    clean_recommendation,
                    response_time,
                    'success'
                )
                
                logger.info(f"✅ 医薬品相談テスト成功（ルールベース）: {response_time:.2f}秒")
                
                return jsonify({
                    'status': 'ok',
                    'message': '医薬品推奨を実行しました',
                    'symptoms': symptoms,
                    'medicine_type': medicine_type,
                    'recommendation': clean_recommendation
                })
            else:
                # AI推奨
                from medicine_logic import comprehensive_medicine_recommendation
                recommendation = comprehensive_medicine_recommendation(
                    user_text=user_message,
                    client=test_client
                )
                
                # NaN値を処理してJSON互換にする
                import json
                import math
                
                def clean_nan(obj):
                    """NaN/Infinityを処理"""
                    if isinstance(obj, dict):
                        return {k: clean_nan(v) for k, v in obj.items()}
                    elif isinstance(obj, list):
                        return [clean_nan(item) for item in obj]
                    elif isinstance(obj, float):
                        if math.isnan(obj) or math.isinf(obj):
                            return None
                        return obj
                    return obj
                
                clean_recommendation = clean_nan(recommendation)
                
                # パフォーマンス統計を更新
                response_time = time.time() - start_time
                add_network_log(
                    'POST',
                    '管理画面 - 医薬品相談テスト',
                    {'message': user_message, 'type': 'ai_based'},
                    clean_recommendation,
                    response_time,
                    'success'
                )
                
                logger.info(f"✅ 医薬品相談テスト成功（AI）: {response_time:.2f}秒")
                
                return jsonify({
                    'status': 'ok',
                    'message': '医薬品推奨を実行しました（AI）',
                    'symptoms': symptoms,
                    'recommendation': clean_recommendation
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
        
        # エラー時もパフォーマンス統計を更新
        response_time = time.time() - start_time if 'start_time' in locals() else 0
        add_network_log(
            'POST',
            '管理画面 - 医薬品相談テスト',
            {'message': user_message},
            None,
            response_time,
            'failed',
            str(e)
        )
        
        return jsonify({
            'status': 'error',
            'message': 'エラーが発生しました',
            'error': str(e)
        }), 500

@app.route('/api/admin/sessions', methods=['GET'])
def get_all_sessions():
    """全セッション情報を取得"""
    cleanup_old_sessions(force=True)  # 管理画面では強制実行
    
    all_sessions = get_all_sessions_from_db()
    sessions_data = []
    for sid, info in all_sessions.items():
        # infoがNoneまたはMockオブジェクトの場合はスキップ
        if info is None or hasattr(info, '_mock_name'):
            continue
            
        last_activity = info.get('last_activity', 0) if isinstance(info, dict) else 0
        if isinstance(last_activity, datetime):
            last_activity = last_activity.timestamp()
        elif isinstance(last_activity, str):
            try:
                last_activity = datetime.fromisoformat(last_activity.replace('Z', '+00:00')).timestamp()
            except:
                last_activity = 0
        elif not isinstance(last_activity, (int, float)):
            last_activity = 0
        
        # セッションデータをシリアライズ可能な形式に変換
        session_dict = {
            'session_id': str(sid),
            'username': str(info.get('username', 'Unknown')) if isinstance(info, dict) else 'Unknown',
            'messages': list(info.get('messages', [])) if isinstance(info, dict) and isinstance(info.get('messages'), list) else [],
            'last_activity': float(last_activity),
            'session_active': bool(info.get('session_active', True)) if isinstance(info, dict) else True,
            'client_ip': str(info.get('client_ip', '')) if isinstance(info, dict) else '',
            'user_agent': str(info.get('user_agent', '')) if isinstance(info, dict) else '',
            'user_attributes': dict(info.get('user_attributes', {})) if isinstance(info, dict) and isinstance(info.get('user_attributes'), dict) else {}
        }
        sessions_data.append(session_dict)
    
    # グローバル状態を取得（Mockオブジェクトの場合はboolに変換）
    admin_mode = get_admin_mode()
    ai_auto_reply = get_ai_auto_reply()
    
    # Mockオブジェクトの場合はデフォルト値を使用
    if hasattr(admin_mode, '_mock_name'):
        admin_mode = False
    if hasattr(ai_auto_reply, '_mock_name'):
        ai_auto_reply = True
    
    return jsonify({
        'sessions': sessions_data,
        'admin_mode': bool(admin_mode),
        'ai_auto_reply': bool(ai_auto_reply)
    })

@app.route('/api/admin/sessions/<session_id>', methods=['DELETE'])
def delete_session(session_id):
    """セッションを削除"""
    try:
        db = get_database()
        if db and (db.connection or db.connection_pool):
            success = db.delete_session(session_id)
            if success:
                return jsonify({'status': 'success', 'message': 'セッションを削除しました'})
            else:
                return jsonify({'status': 'error', 'message': 'セッションが見つかりませんでした'}), 404
        else:
            return jsonify({'status': 'error', 'message': 'データベース接続エラー'}), 500
    except Exception as e:
        logger.error(f"❌ セッション削除エラー: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/admin/sessions/delete_all', methods=['DELETE'])
def delete_all_sessions():
    """全セッションを削除"""
    try:
        db = get_database()
        if db and (db.connection or db.connection_pool):
            deleted_count = db.delete_all_sessions()
            return jsonify({'status': 'success', 'message': f'{deleted_count}件のセッションを削除しました', 'deleted_count': deleted_count})
        else:
            return jsonify({'status': 'error', 'message': 'データベース接続エラー'}), 500
    except Exception as e:
        logger.error(f"❌ 全セッション削除エラー: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/admin/sessions/<session_id>', methods=['PUT'])
def update_session(session_id):
    """セッション情報を更新"""
    try:
        data = request.json
        session_data = get_session_from_db(session_id)
        if not session_data:
            return jsonify({'status': 'error', 'message': 'セッションが見つかりませんでした'}), 404
        
        # 更新可能なフィールド
        if 'username' in data:
            session_data['username'] = data['username']
        if 'session_active' in data:
            session_data['session_active'] = data['session_active']
        if 'user_attributes' in data:
            session_data['user_attributes'] = data['user_attributes']
        
        session_data['last_activity'] = datetime.now()
        
        success = save_session_to_db(session_id, session_data)
        if success:
            return jsonify({'status': 'success', 'message': 'セッション情報を更新しました'})
        else:
            return jsonify({'status': 'error', 'message': 'セッション更新に失敗しました'}), 500
    except Exception as e:
        logger.error(f"❌ セッション更新エラー: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/admin/send_message', methods=['POST'])
def admin_send_message():
    """管理者からのメッセージ送信"""
    data = request.json
    session_id = data.get('session_id')
    message = data.get('message')
    
    if not session_id or not message:
        return jsonify({'status': 'error', 'message': 'session_idとmessageが必要です'}), 400
    
    session_data = get_session_from_db(session_id)
    if not session_data:
        return jsonify({'status': 'error', 'message': 'セッションが見つかりません'}), 404
    
    # 管理者メッセージを追加
    ai_response = {
        'role': 'ai',
        'content': message,
        'timestamp': datetime.now().isoformat(),
        'from_admin': True
    }
    
    if 'messages' not in session_data:
        session_data['messages'] = []
    session_data['messages'].append(ai_response)
    session_data['last_activity'] = datetime.now()
    save_session_to_db(session_id, session_data)
    
    return jsonify({'status': 'success', 'message': 'メッセージを送信しました'})

@app.route('/api/main_sessions', methods=['GET'])
def api_main_sessions():
    """全セッション情報を取得（admin_chat.html用）"""
    cleanup_old_sessions(force=True)  # 管理画面では強制実行
    
    all_sessions = get_all_sessions_from_db()
    sessions_list = []
    for sid, info in all_sessions.items():
        detailed_diag = ADMIN_SESSIONS.get(sid, {}).get('detailed_diagnosis')
        # 互換対応: detailed_diagnosis に session_id が無ければ付与（フロントの一致判定用）
        if isinstance(detailed_diag, dict) and 'session_id' not in detailed_diag:
            try:
                detailed_diag = dict(detailed_diag)
                detailed_diag['session_id'] = sid
            except Exception:
                pass
        sessions_list.append({
            'session_id': sid,
            'username': info.get('username', 'Unknown'),
            'messages': info.get('messages', []),
            'last_activity': info.get('last_activity', 0),
            'message_count': len(info.get('messages', [])),
            'user_info': info.get('user_attributes', {}),
            'attributes': info.get('user_attributes', {}),
            # 管理者向けに詳細な診断情報（スコア内訳を含む）も返す
            'detailed_diagnosis': detailed_diag
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

    return jsonify({'sessions': sessions_list})

@app.route('/api/main_manual_reply_queue', methods=['GET', 'POST'])
def api_main_manual_reply_queue():
    """手動返信キューの管理"""
    
    if request.method == 'GET':
        queue = get_manual_reply_queue()
        return jsonify(queue)
    
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
        
        queue = get_manual_reply_queue()
        
        if action == 'add':
            session_id = data.get('session_id')
            if session_id:
                session_data = get_session_from_db(session_id)
                if session_data:
                    # キューに追加（既存のキュー形式に合わせる）
                    queue_item = {
                        'session_id': session_id,
                        'user_message': '',
                        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'status': 'pending'
                    }
                    if queue_item not in queue:
                        queue.append(queue_item)
                        set_manual_reply_queue(queue)
                return jsonify({'status': 'success', 'queue': get_manual_reply_queue()})
        
        elif action == 'remove':
            session_id = data.get('session_id')
            if session_id:
                queue = [q for q in queue if q.get('session_id') != session_id]
                set_manual_reply_queue(queue)
            return jsonify({'status': 'success', 'queue': get_manual_reply_queue()})
        
        elif action == 'reply':
            # reply_messageとmessageの両方をサポート
            message = data.get('reply_message') or data.get('message')
            
            if session_id and message:
                session_data = get_session_from_db(session_id)
                if session_data:
                    # 管理者メッセージを追加（manual_replyフラグを使用）
                    manual_reply = {
                        'type': 'bot',
                        'content': message,
                        'timestamp': datetime.now().isoformat(),
                        'manual_reply': True
                    }
                    
                    if 'messages' not in session_data:
                        session_data['messages'] = []
                    session_data['messages'].append(manual_reply)
                    session_data['last_activity'] = datetime.now()
                    save_session_to_db(session_id, session_data)
                    
                    logger.info(f"💬 Manual reply sent to session {session_id}: {message[:50]}...")
                    
                    # キューから削除
                    queue = [q for q in queue if q.get('session_id') != session_id]
                    set_manual_reply_queue(queue)
                    
                    return jsonify({'status': 'success', 'message': 'メッセージを送信しました'})
        
        return jsonify({'status': 'error', 'message': '無効なアクションです'}), 400

@app.route('/api/main_ai_control', methods=['GET', 'POST'])
def api_main_ai_control():
    """AI自動応答の制御"""
    
    if request.method == 'GET':
        return jsonify({
            'ai_auto_reply': get_ai_auto_reply(),
            'admin_mode': get_admin_mode(),
            'manual_reply_message': get_manual_reply_message()
        })
    
    elif request.method == 'POST':
        data = request.json
        action = data.get('action')
        mode = data.get('mode')  # 'auto'/'manual' または 'on'/'off' に対応
        
        # 'on'/'off'を'auto'/'manual'に変換（後方互換性のため）
        if mode == 'on':
            mode = 'auto'
        elif mode == 'off':
            mode = 'manual'
        
        # modeパラメータがある場合はそれを使用（後方互換性のためactionも対応）
        if mode == 'auto' or action == 'enable':
            set_ai_auto_reply(True)
            set_admin_mode(False)
            message = 'AI自動応答を有効化しました'
        elif mode == 'manual' or action == 'disable':
            set_ai_auto_reply(False)
            set_admin_mode(True)
            message = 'AI自動応答を無効化しました'
        else:
            return jsonify({'error': '無効なパラメータです'}), 400
        
        return jsonify({
            'ai_auto_reply': get_ai_auto_reply(),
            'admin_mode': get_admin_mode(),
            'message': message,
            'manual_reply_message': get_manual_reply_message()
        })

@app.route('/api/manual_reply_message', methods=['GET', 'POST'])
def api_manual_reply_message():
    """手動返信時の自動メッセージの取得・保存"""
    
    if request.method == 'GET':
        return jsonify({
            'message': get_manual_reply_message()
        })
    
    elif request.method == 'POST':
        data = request.json
        message = data.get('message', '').strip()
        
        if not message:
            return jsonify({'error': 'メッセージが空です'}), 400
        
        # メッセージを保存
        set_manual_reply_message(message)
        logger.info(f"💾 手動返信メッセージを更新 (長さ: {len(message)}): {message[:50]}...")
        
        # 保存した値を確実に取得（globals()から直接取得、なければ保存したmessageを使用）
        saved_message = globals().get('MANUAL_REPLY_MESSAGE', message)
        logger.info(f"💾 保存したメッセージを取得 (長さ: {len(saved_message)}): {saved_message[:50]}...")
        
        return jsonify({
            'message': 'メッセージを保存しました',
            'manual_reply_message': saved_message
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
        
        # DBにも保存
        if sid:
            session_data = get_session_from_db(sid)
            if session_data:
                session_data['user_attributes'] = session['user_attributes'].copy()
                session_data['last_activity'] = datetime.now()
                save_session_to_db(sid, session_data)
                logger.info(f"✅ User attributes saved to session {sid}")
        
        return jsonify({'status': 'success', 'message': 'ユーザー属性を保存しました'})

# フィードバック関連API
@app.route('/api/submit_feedback', methods=['POST'])
def submit_feedback():
    """フィードバックをデータベースに保存"""
    try:
        data = request.json
        logger.info(f"📝 Feedback submission: {data}")
        
        # データベース接続確認
        db = get_database()
        if not (db and (db.connection or db.connection_pool)):
            return jsonify({'error': 'Database not available'}), 500
        
        # 必須フィールドの検証
        required_fields = ['report_type', 'user_message', 'ai_response']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # レート制限チェック（同一セッションから60秒に1回まで）
        session_id = session.get('_id')
        if session_id:
            # 簡易的なレート制限（実際の実装ではRedis等を使用）
            current_time = time.time()
            last_feedback_time = session.get('last_feedback_time', 0)
            if current_time - last_feedback_time < 60:
                return jsonify({'error': 'Rate limit exceeded. Please wait 60 seconds.'}), 429
            session['last_feedback_time'] = current_time
        
        # フィードバックテキストの文字数制限
        feedback_text = data.get('feedback_text', '')
        if len(feedback_text) > 1000:
            return jsonify({'error': 'Feedback text too long (max 1000 characters)'}), 400
        
        # データベースに保存
        feedback_id = db.insert_feedback(
            report_type=data['report_type'],
            session_id=session_id,
            username=session.get('username', 'Unknown'),
            user_message=data['user_message'],
            ai_response=data['ai_response'],
            security_score=data.get('security_score'),
            feedback_text=feedback_text,
            is_google_form=data.get('is_google_form', False)
        )
        
        if feedback_id:
            logger.info(f"✅ Feedback saved with ID: {feedback_id}")
            return jsonify({'status': 'success', 'feedback_id': feedback_id})
        else:
            return jsonify({'error': 'Failed to save feedback'}), 500
            
    except Exception as e:
        logger.error(f"❌ Feedback submission error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/get_feedback_reports', methods=['GET'])
def get_feedback_reports():
    """フィードバック報告一覧を取得（管理画面用）"""
    try:
        db = get_database()
        if not (db and (db.connection or db.connection_pool)):
            return jsonify({'error': 'Database not available'}), 500
        
        # クエリパラメータ
        limit = request.args.get('limit', 100, type=int)
        unresolved_only = request.args.get('unresolved_only', 'false').lower() == 'true'
        
        reports = db.get_feedback_reports(limit=limit, unresolved_only=unresolved_only)
        
        logger.info(f"📊 Retrieved {len(reports)} feedback reports")
        return jsonify({'reports': reports})
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"❌ Get feedback reports error: {str(e)}")
        logger.error(f"❌ Traceback: {error_trace}")
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

@app.route('/api/resolve_feedback/<int:feedback_id>', methods=['POST'])
def resolve_feedback(feedback_id):
    """フィードバックを解決済みにマーク"""
    try:
        db = get_database()
        if not (db and (db.connection or db.connection_pool)):
            return jsonify({'error': 'Database not available'}), 500
        
        success = db.resolve_feedback(feedback_id)
        
        if success:
            logger.info(f"✅ Feedback {feedback_id} marked as resolved")
            return jsonify({'status': 'success'})
        else:
            return jsonify({'error': 'Failed to resolve feedback'}), 500
            
    except Exception as e:
        logger.error(f"❌ Resolve feedback error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/delete_feedback/<int:feedback_id>', methods=['POST'])
def delete_feedback(feedback_id):
    """フィードバックを削除"""
    try:
        db = get_database()
        if not (db and (db.connection or db.connection_pool)):
            return jsonify({'error': 'Database not available'}), 500

        success = db.delete_feedback(feedback_id)

        if success:
            logger.info(f"🗑️ Feedback {feedback_id} deleted")
            return jsonify({'status': 'success'})
        else:
            return jsonify({'error': 'Failed to delete feedback'}), 500

    except Exception as e:
        logger.error(f"❌ Delete feedback error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/translate', methods=['POST'])
def translate_text():
    """テキスト翻訳API"""
    try:
        data = request.get_json()
        text = data.get('text', '')
        target_language = data.get('target_language', 'ja')
        
        if not text:
            return jsonify({'error': 'No text provided'}), 400
        
        # ChatGPTを使用して翻訳
        translation_prompt = f"""
以下の医薬品関連情報を{target_language}に翻訳してください。医療専門用語は正確に翻訳し、医薬品名は適切に翻訳してください。

翻訳対象テキスト:
{text}

翻訳:
"""
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a medical translator specializing in medicine recommendations. Translate accurately while maintaining medical terminology."},
                {"role": "user", "content": translation_prompt}
            ],
            temperature=0.1,
            max_tokens=2000
        )
        
        translated_text = response.choices[0].message.content.strip()
        
        return jsonify({
            'translated_text': translated_text,
            'original_text': text,
            'target_language': target_language
        })
        
    except Exception as e:
        logger.error(f"翻訳エラー: {e}")
        return jsonify({'error': 'Translation failed'}), 500

@app.route('/api/set_language', methods=['POST'])
def set_language():
    """UI言語を設定"""
    try:
        data = request.get_json()
        language = data.get('language', 'ja')
        
        if language not in ['ja', 'en', 'ko', 'zh']:
            return jsonify({'error': 'Invalid language code'}), 400
        
        # セッションにUI言語を保存
        session['ui_language'] = language
        session.modified = True
        
        logger.info(f"🌍 UI言語を設定: {language}")
        
        return jsonify({
            'status': 'success',
            'language': language,
            'message': f'Language set to {language}'
        })
        
    except Exception as e:
        logger.error(f"言語設定エラー: {e}")
        return jsonify({'error': 'Failed to set language'}), 500

def find_free_port(start_port=5000, max_attempts=100):
    """利用可能なポートを見つける"""
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('', port))
                return port
        except OSError:
            continue
    raise RuntimeError(f"利用可能なポートが見つかりませんでした ({start_port}-{start_port + max_attempts - 1})")

def is_port_in_use(port):
    """ポートが使用中かどうかをチェック"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('', port))
            return False
        except OSError:
            return True

if __name__ == '__main__':
    logger.info("🚀 Starting Medicine Recommendation System...")
    
    # 最小限のログ出力で起動時間を短縮
    requested_port = int(os.getenv('PORT', 5000))
    debug_mode = os.getenv('FLASK_ENV') != 'production'
    
    # ポートが使用中の場合は、利用可能なポートを探す
    if is_port_in_use(requested_port):
        logger.warning(f"⚠️ Port {requested_port} is already in use. Finding alternative port...")
        port = find_free_port(requested_port + 1)
        logger.info(f"✅ Found available port: {port}")
    else:
        port = requested_port
    
    logger.info(f"🌐 Starting Flask server on port {port} (debug={debug_mode})...")
    app.run(debug=debug_mode, port=port, host='0.0.0.0')