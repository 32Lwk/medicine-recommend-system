"""
PostgreSQL接続管理とテーブル初期化
"""
import os
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    from psycopg2 import pool
except Exception as e:
    # psycopg2が利用できない環境ではDB機能を無効化（アプリは継続動作）
    psycopg2 = None
    RealDictCursor = None
    pool = None
    import logging as _logging
    _logging.getLogger(__name__).warning(f"psycopg2 not available: {e}. Database features disabled.")
import logging
import json
import math
from datetime import datetime

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        self.connection = None
        self.connection_pool = None
        self.database_url = os.getenv('DATABASE_URL')
        self.min_connections = 2
        self.max_connections = 10
        
    def connect(self):
        """データベースに接続または接続プールを作成"""
        try:
            if psycopg2 is None or pool is None:
                logger.warning("psycopg2 not installed. Skipping database connection.")
                return False
            if not self.database_url:
                logger.warning("DATABASE_URL not found. Using fallback mode.")
                return False
            
            # 接続プールを作成
            try:
                self.connection_pool = pool.ThreadedConnectionPool(
                    self.min_connections,
                    self.max_connections,
                    self.database_url,
                    connect_timeout=10,
                    application_name="medicine-recommend-system"
                )
                logger.info(f"✅ PostgreSQL connection pool created (min: {self.min_connections}, max: {self.max_connections})")
                # 初期接続をテスト
                test_conn = self.get_connection()
                if test_conn:
                    self.put_connection(test_conn)
                    return True
                return False
            except Exception as pool_error:
                logger.warning(f"⚠️ Connection pool creation failed, using single connection: {str(pool_error)}")
                # フォールバック: 単一接続
                self.connection = psycopg2.connect(
                    self.database_url,
                    connect_timeout=10,
                    application_name="medicine-recommend-system"
                )
                logger.info("✅ PostgreSQL connection established (fallback mode)")
                return True
            
        except Exception as e:
            logger.error(f"❌ Database connection failed: {str(e)}")
            return False
    
    def get_connection(self):
        """接続プールから接続を取得、または単一接続を返す"""
        if self.connection_pool:
            try:
                conn = self.connection_pool.getconn()
                # 接続の有効性をチェック
                if conn:
                    try:
                        cursor = conn.cursor()
                        cursor.execute("SELECT 1")
                        cursor.close()
                    except Exception as e:
                        logger.warning(f"⚠️ Connection validation failed: {str(e)}, reconnecting...")
                        try:
                            conn.close()
                        except:
                            pass
                        # 再接続を試行
                        self.connect()
                        conn = self.connection_pool.getconn()
                return conn
            except Exception as e:
                logger.error(f"❌ Failed to get connection from pool: {str(e)}")
                # 再接続を試行
                try:
                    self.connect()
                    return self.connection_pool.getconn()
                except:
                    return None
        elif self.connection:
            return self.connection
        else:
            logger.error("❌ No database connection available")
            return None
    
    def put_connection(self, conn):
        """接続をプールに返す"""
        if self.connection_pool and conn:
            try:
                self.connection_pool.putconn(conn)
            except Exception as e:
                logger.error(f"❌ Failed to return connection to pool: {str(e)}")
    
    def initialize_tables(self):
        """テーブルを初期化"""
        conn = self.get_connection()
        if not conn:
            logger.error("❌ No database connection")
            return False
            
        try:
            cursor = conn.cursor()
            
            # feedback_reportsテーブルを作成
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS feedback_reports (
                id SERIAL PRIMARY KEY,
                report_type VARCHAR(50) NOT NULL,
                session_id VARCHAR(255),
                username VARCHAR(255),
                user_message TEXT,
                ai_response TEXT,
                security_score FLOAT,
                feedback_text TEXT,
                is_google_form BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved BOOLEAN DEFAULT FALSE
            );
            """
            
            cursor.execute(create_table_sql)
            
            # sessionsテーブルを作成（マルチインスタンス対応）
            create_sessions_table_sql = """
            CREATE TABLE IF NOT EXISTS sessions (
                session_id VARCHAR(255) PRIMARY KEY,
                username VARCHAR(255),
                messages JSONB,
                user_attributes JSONB,
                last_activity TIMESTAMP NOT NULL,
                client_ip VARCHAR(255),
                user_agent TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                session_active BOOLEAN DEFAULT TRUE
            );
            """
            
            
            cursor.execute(create_sessions_table_sql)
            
            # 既存のテーブルにsession_activeカラムがない場合は追加
            try:
                # PostgreSQLでは直接ALTER TABLEを試行し、エラーが発生した場合は無視
                alter_sql = """
                DO $$ 
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name='sessions' AND column_name='session_active'
                    ) THEN
                        ALTER TABLE sessions ADD COLUMN session_active BOOLEAN DEFAULT TRUE;
                    END IF;
                END $$;
                """
                cursor.execute(alter_sql)
            except Exception as e:
                # カラムが既に存在する場合はエラーを無視
                logger.debug(f"session_active column may already exist: {e}")
            
            # global_stateテーブルを作成（グローバル変数の共有）
            create_global_state_table_sql = """
            CREATE TABLE IF NOT EXISTS global_state (
                key VARCHAR(255) PRIMARY KEY,
                value JSONB NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
            cursor.execute(create_global_state_table_sql)
            
            conn.commit()
            
            # インデックスを作成（パフォーマンス向上）
            index_sql = """
            CREATE INDEX IF NOT EXISTS idx_feedback_reports_created_at 
            ON feedback_reports(created_at DESC);
            """
            cursor.execute(index_sql)
            
            index_sql2 = """
            CREATE INDEX IF NOT EXISTS idx_feedback_reports_resolved 
            ON feedback_reports(resolved);
            """
            cursor.execute(index_sql2)
            
            # sessionsテーブルのインデックス
            index_sessions_sql = """
            CREATE INDEX IF NOT EXISTS idx_sessions_last_activity 
            ON sessions(last_activity);
            """
            cursor.execute(index_sessions_sql)
            
            # global_stateテーブルのインデックス
            index_global_state_sql = """
            CREATE INDEX IF NOT EXISTS idx_global_state_updated_at 
            ON global_state(updated_at);
            """
            cursor.execute(index_global_state_sql)
            
            conn.commit()
            cursor.close()
            self.put_connection(conn)
            
            logger.info("✅ Database tables initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Table initialization failed: {str(e)}")
            if conn:
                conn.rollback()
                self.put_connection(conn)
            return False
    
    def insert_feedback(self, report_type, session_id, username, user_message, 
                       ai_response, security_score=None, feedback_text=None, 
                       is_google_form=False):
        """フィードバックをデータベースに保存"""
        conn = self.get_connection()
        if not conn:
            logger.error("❌ No database connection")
            return False
            
        try:
            cursor = conn.cursor()
            
            insert_sql = """
            INSERT INTO feedback_reports 
            (report_type, session_id, username, user_message, ai_response, 
             security_score, feedback_text, is_google_form)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id;
            """
            
            cursor.execute(insert_sql, (
                report_type, session_id, username, user_message, ai_response,
                security_score, feedback_text, is_google_form
            ))
            
            feedback_id = cursor.fetchone()[0]
            conn.commit()
            cursor.close()
            self.put_connection(conn)
            
            logger.info(f"✅ Feedback saved with ID: {feedback_id}")
            return feedback_id
            
        except Exception as e:
            logger.error(f"❌ Failed to save feedback: {str(e)}")
            if conn:
                conn.rollback()
                self.put_connection(conn)
            return False
    
    def get_feedback_reports(self, limit=100, unresolved_only=False):
        """フィードバック報告一覧を取得"""
        conn = self.get_connection()
        if not conn:
            logger.error("❌ No database connection")
            return []
            
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            where_clause = "WHERE resolved = FALSE" if unresolved_only else ""
            limit_clause = f"LIMIT {limit}"
            
            select_sql = f"""
            SELECT * FROM feedback_reports 
            {where_clause}
            ORDER BY created_at DESC 
            {limit_clause};
            """
            
            cursor.execute(select_sql)
            results = cursor.fetchall()
            cursor.close()
            self.put_connection(conn)
            
            # RealDictCursorの結果を辞書のリストに変換
            reports = []
            for row in results:
                report = dict(row)
                # datetimeオブジェクトを文字列に変換
                if report['created_at']:
                    report['created_at'] = report['created_at'].isoformat()
                reports.append(report)
            
            logger.info(f"✅ Retrieved {len(reports)} feedback reports")
            return reports
            
        except Exception as e:
            logger.error(f"❌ Failed to get feedback reports: {str(e)}")
            if conn:
                self.put_connection(conn)
            return []
    
    def resolve_feedback(self, feedback_id):
        """フィードバックを解決済みにマーク"""
        conn = self.get_connection()
        if not conn:
            logger.error("❌ No database connection")
            return False
            
        try:
            cursor = conn.cursor()
            
            update_sql = """
            UPDATE feedback_reports 
            SET resolved = TRUE 
            WHERE id = %s;
            """
            
            cursor.execute(update_sql, (feedback_id,))
            conn.commit()
            cursor.close()
            self.put_connection(conn)
            
            logger.info(f"✅ Feedback {feedback_id} marked as resolved")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to resolve feedback: {str(e)}")
            if conn:
                conn.rollback()
                self.put_connection(conn)
            return False

    def delete_feedback(self, feedback_id):
        """フィードバックを削除"""
        conn = self.get_connection()
        if not conn:
            logger.error("❌ No database connection")
            return False

        try:
            cursor = conn.cursor()

            delete_sql = """
            DELETE FROM feedback_reports
            WHERE id = %s;
            """

            cursor.execute(delete_sql, (feedback_id,))
            conn.commit()
            cursor.close()
            self.put_connection(conn)

            logger.info(f"🗑️ Feedback {feedback_id} deleted")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to delete feedback: {str(e)}")
            if conn:
                conn.rollback()
                self.put_connection(conn)
            return False
    
    def _convert_nan_to_null(self, obj):
        """NaN値をnullに変換する再帰関数（JSONシリアライズ対応）"""
        if isinstance(obj, dict):
            return {k: self._convert_nan_to_null(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_nan_to_null(item) for item in obj]
        elif isinstance(obj, float) and math.isnan(obj):
            return None
        else:
            return obj
    
    def save_session(self, session_id, data):
        """セッションをデータベースに保存"""
        conn = self.get_connection()
        if not conn:
            logger.error("❌ No database connection")
            return False
        
        try:
            cursor = conn.cursor()
            
            # NaN値をnullに変換してからJSONBに変換
            messages_data = self._convert_nan_to_null(data.get('messages', []))
            user_attributes_data = self._convert_nan_to_null(data.get('user_attributes', {}))
            
            messages_json = json.dumps(messages_data, ensure_ascii=False)
            user_attributes_json = json.dumps(user_attributes_data, ensure_ascii=False)
            
            insert_sql = """
            INSERT INTO sessions 
            (session_id, username, messages, user_attributes, last_activity, client_ip, user_agent, created_at, session_active)
            VALUES (%s, %s, %s::jsonb, %s::jsonb, %s, %s, %s, %s, %s)
            ON CONFLICT (session_id) 
            DO UPDATE SET
                username = EXCLUDED.username,
                messages = EXCLUDED.messages,
                user_attributes = EXCLUDED.user_attributes,
                last_activity = EXCLUDED.last_activity,
                client_ip = EXCLUDED.client_ip,
                user_agent = EXCLUDED.user_agent,
                session_active = COALESCE(EXCLUDED.session_active, sessions.session_active);
            """
            
            cursor.execute(insert_sql, (
                session_id,
                data.get('username'),
                messages_json,
                user_attributes_json,
                data.get('last_activity', datetime.now()),
                data.get('client_ip'),
                data.get('user_agent'),
                data.get('created_at', datetime.now()),
                data.get('session_active', True)  # デフォルトはTrue（アクティブ）
            ))
            
            conn.commit()
            cursor.close()
            self.put_connection(conn)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to save session: {str(e)}")
            if conn:
                conn.rollback()
                self.put_connection(conn)
            return False
    
    def get_session(self, session_id):
        """セッションをデータベースから取得"""
        conn = self.get_connection()
        if not conn:
            logger.error("❌ No database connection")
            return None
        
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            select_sql = """
            SELECT * FROM sessions WHERE session_id = %s;
            """
            
            cursor.execute(select_sql, (session_id,))
            result = cursor.fetchone()
            cursor.close()
            self.put_connection(conn)
            
            if result:
                session_data = dict(result)
                # JSONBフィールドをPythonオブジェクトに変換
                if session_data.get('messages'):
                    if isinstance(session_data['messages'], str):
                        session_data['messages'] = json.loads(session_data['messages'])
                else:
                    session_data['messages'] = []
                
                if session_data.get('user_attributes'):
                    if isinstance(session_data['user_attributes'], str):
                        session_data['user_attributes'] = json.loads(session_data['user_attributes'])
                else:
                    session_data['user_attributes'] = {}
                
                return session_data
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to get session: {str(e)}")
            if conn:
                self.put_connection(conn)
            return None
    
    def delete_session(self, session_id):
        """セッションをデータベースから削除"""
        conn = self.get_connection()
        if not conn:
            logger.error("❌ No database connection")
            return False
        
        try:
            cursor = conn.cursor()
            
            delete_sql = """
            DELETE FROM sessions WHERE session_id = %s;
            """
            
            cursor.execute(delete_sql, (session_id,))
            conn.commit()
            cursor.close()
            self.put_connection(conn)
            
            logger.info(f"✅ Session {session_id} deleted")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to delete session: {str(e)}")
            if conn:
                conn.rollback()
                self.put_connection(conn)
            return False
    
    def cleanup_expired_sessions(self, timeout_seconds, exclude_session_ids=None, chat_end_timeout_seconds=None):
        """期限切れセッションを削除
        
        Args:
            timeout_seconds: 通常のタイムアウト（秒）
            exclude_session_ids: 削除から除外するセッションIDのリスト（アクティブなセッション）
            chat_end_timeout_seconds: チャット終了後の削除タイムアウト（秒）。Noneの場合は通常のタイムアウトを使用
        """
        conn = self.get_connection()
        if not conn:
            logger.error("❌ No database connection")
            return 0
        
        try:
            cursor = conn.cursor()
            
            # 除外するセッションIDのリスト
            exclude_list = exclude_session_ids or []
            exclude_condition = ""
            if exclude_list:
                placeholders = ','.join(['%s'] * len(exclude_list))
                exclude_condition = f"AND session_id NOT IN ({placeholders})"
            
            # チャット終了後のタイムアウト（デフォルトは通常のタイムアウト）
            chat_end_timeout = chat_end_timeout_seconds or timeout_seconds
            
            # セッションがアクティブでない場合（session_active = false）は、chat_end_timeoutを使用
            # セッションがアクティブな場合（session_active = true または NULL）は、通常のtimeoutを使用
            if exclude_list:
                # 除外セッションがある場合のSQL
                placeholders = ','.join(['%s'] * len(exclude_list))
                delete_sql = f"""
                DELETE FROM sessions 
                WHERE (
                    (session_active = false AND last_activity < NOW() - INTERVAL '{chat_end_timeout} seconds')
                    OR
                    (COALESCE(session_active, true) = true AND last_activity < NOW() - INTERVAL '{timeout_seconds} seconds')
                )
                AND session_id NOT IN ({placeholders});
                """
                # パラメータ化クエリで実行（SQLインジェクション対策）
                cursor.execute(delete_sql, tuple(exclude_list))
            else:
                # 除外セッションがない場合のSQL
                delete_sql = f"""
                DELETE FROM sessions 
                WHERE (
                    (session_active = false AND last_activity < NOW() - INTERVAL '{chat_end_timeout} seconds')
                    OR
                    (COALESCE(session_active, true) = true AND last_activity < NOW() - INTERVAL '{timeout_seconds} seconds')
                );
                """
                cursor.execute(delete_sql)
            deleted_count = cursor.rowcount
            conn.commit()
            cursor.close()
            self.put_connection(conn)
            
            if deleted_count > 0:
                logger.info(f"✅ Cleaned up {deleted_count} expired sessions")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"❌ Failed to cleanup expired sessions: {str(e)}")
            if conn:
                conn.rollback()
                self.put_connection(conn)
            return 0
    
    def delete_session(self, session_id):
        """セッションを削除"""
        conn = self.get_connection()
        if not conn:
            logger.error("❌ No database connection")
            return False
        
        try:
            cursor = conn.cursor()
            delete_sql = "DELETE FROM sessions WHERE session_id = %s;"
            cursor.execute(delete_sql, (session_id,))
            deleted_count = cursor.rowcount
            conn.commit()
            cursor.close()
            self.put_connection(conn)
            
            if deleted_count > 0:
                logger.info(f"✅ Session {session_id} deleted")
                return True
            return False
            
        except Exception as e:
            logger.error(f"❌ Failed to delete session: {str(e)}")
            if conn:
                conn.rollback()
                self.put_connection(conn)
            return False
    
    def delete_all_sessions(self):
        """全セッションを削除"""
        conn = self.get_connection()
        if not conn:
            logger.error("❌ No database connection")
            return 0
        
        try:
            cursor = conn.cursor()
            delete_sql = "DELETE FROM sessions;"
            cursor.execute(delete_sql)
            deleted_count = cursor.rowcount
            conn.commit()
            cursor.close()
            self.put_connection(conn)
            
            if deleted_count > 0:
                logger.info(f"✅ Deleted {deleted_count} sessions")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"❌ Failed to delete all sessions: {str(e)}")
            if conn:
                conn.rollback()
                self.put_connection(conn)
            return 0
    
    def get_all_sessions(self):
        """全てのセッションを取得（管理用）"""
        conn = self.get_connection()
        if not conn:
            logger.error("❌ No database connection")
            return []
        
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            select_sql = """
            SELECT * FROM sessions ORDER BY last_activity DESC;
            """
            
            cursor.execute(select_sql)
            results = cursor.fetchall()
            cursor.close()
            self.put_connection(conn)
            
            sessions = []
            for row in results:
                session_data = dict(row)
                # JSONBフィールドをPythonオブジェクトに変換
                if session_data.get('messages'):
                    if isinstance(session_data['messages'], str):
                        session_data['messages'] = json.loads(session_data['messages'])
                else:
                    session_data['messages'] = []
                
                if session_data.get('user_attributes'):
                    if isinstance(session_data['user_attributes'], str):
                        session_data['user_attributes'] = json.loads(session_data['user_attributes'])
                else:
                    session_data['user_attributes'] = {}
                
                sessions.append(session_data)
            
            return sessions
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ Failed to get all sessions: {error_msg}")
            import traceback
            logger.debug(f"Traceback: {traceback.format_exc()}")
            
            # SSLエラーの場合は接続を閉じて再接続を試行
            if "SSL" in error_msg or "decryption" in error_msg or "bad record mac" in error_msg:
                logger.warning("⚠️ SSL error detected, attempting to reconnect...")
                if conn:
                    try:
                        conn.close()
                    except:
                        pass
                # 再接続を試行
                try:
                    self.connect()
                    conn = self.get_connection()
                    if conn:
                        logger.info("✅ Database reconnected successfully")
                except Exception as reconnect_error:
                    logger.error(f"❌ Reconnection failed: {str(reconnect_error)}")
            
            if conn:
                try:
                    self.put_connection(conn)
                except:
                    pass
            return []
    
    def get_global_state(self, key, default_value=None):
        """グローバル状態を取得"""
        conn = self.get_connection()
        if not conn:
            logger.error("❌ No database connection")
            return default_value
        
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            select_sql = """
            SELECT value FROM global_state WHERE key = %s;
            """
            
            cursor.execute(select_sql, (key,))
            result = cursor.fetchone()
            cursor.close()
            self.put_connection(conn)
            
            if result:
                value = result['value']
                # JSONBフィールドをPythonオブジェクトに変換
                if isinstance(value, str):
                    try:
                        return json.loads(value)
                    except json.JSONDecodeError:
                        return value
                return value
            
            # デフォルト値を設定
            if default_value is not None:
                self.set_global_state(key, default_value)
                return default_value
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to get global state: {str(e)}")
            if conn:
                self.put_connection(conn)
            return default_value
    
    def set_global_state(self, key, value):
        """グローバル状態を設定"""
        conn = self.get_connection()
        if not conn:
            logger.error("❌ No database connection")
            return False
        
        try:
            cursor = conn.cursor()
            
            # NaN値をnullに変換してからJSONBに変換
            value_data = self._convert_nan_to_null(value)
            value_json = json.dumps(value_data, ensure_ascii=False)
            
            insert_sql = """
            INSERT INTO global_state (key, value, updated_at)
            VALUES (%s, %s::jsonb, CURRENT_TIMESTAMP)
            ON CONFLICT (key) 
            DO UPDATE SET
                value = EXCLUDED.value,
                updated_at = CURRENT_TIMESTAMP;
            """
            
            cursor.execute(insert_sql, (key, value_json))
            conn.commit()
            cursor.close()
            self.put_connection(conn)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to set global state: {str(e)}")
            if conn:
                conn.rollback()
                self.put_connection(conn)
            return False
    
    def close(self):
        """データベース接続を閉じる"""
        if self.connection_pool:
            try:
                self.connection_pool.closeall()
                logger.info("✅ Database connection pool closed")
            except Exception as e:
                logger.error(f"❌ Error closing connection pool: {str(e)}")
        elif self.connection:
            self.connection.close()
            logger.info("✅ Database connection closed")

# グローバルインスタンス
db_manager = DatabaseManager()

def init_database():
    """データベースを初期化（アプリ起動時に呼び出し）"""
    try:
        if db_manager.connect():
            return db_manager.initialize_tables()
        return False
    except Exception as e:
        logger.warning(f"⚠️ Database initialization error: {str(e)} - continuing without database")
        return False

def get_database():
    """データベースマネージャーを取得"""
    return db_manager
