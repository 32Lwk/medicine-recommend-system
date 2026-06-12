"""
PostgreSQL接続管理とテーブル初期化
"""
import os
from typing import Optional
from urllib.parse import quote_plus
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
    _logging.getLogger(__name__).info(
        "psycopg2 が無いため PostgreSQL は使いません（任意依存）。`pip install psycopg2-binary` で有効化できます。詳細: %s",
        e,
    )
import logging
import json
import math
from datetime import datetime

logger = logging.getLogger(__name__)


def resolve_database_url() -> Optional[str]:
    """DATABASE_URL または POSTGRES_* / PG* から接続文字列を解決する。"""
    url = (os.getenv('DATABASE_URL') or '').strip()
    if url:
        return url
    user = (os.getenv('POSTGRES_USER') or os.getenv('PGUSER') or '').strip()
    password = os.getenv('POSTGRES_PASSWORD') or os.getenv('PGPASSWORD') or ''
    host = (os.getenv('POSTGRES_HOST') or os.getenv('PGHOST') or '').strip()
    port = (os.getenv('POSTGRES_PORT') or os.getenv('PGPORT') or '5432').strip()
    dbname = (os.getenv('POSTGRES_DB') or os.getenv('PGDATABASE') or '').strip()
    if not (host and user and dbname):
        return None
    password_part = f":{quote_plus(password)}" if password else ''
    sslmode = os.getenv('DATABASE_SSLMODE', 'require')
    return (
        f"postgresql://{quote_plus(user)}{password_part}@"
        f"{host}:{port}/{quote_plus(dbname)}?sslmode={sslmode}"
    )


class DatabaseManager:
    def __init__(self):
        self.connection = None
        self.connection_pool = None
        self.database_url = resolve_database_url()
        # init_database / connect が False のときの理由（起動ログ用）
        self.startup_skip_reason: Optional[str] = None
        # 環境変数から接続プール設定を取得（デフォルト値は小規模環境向け）
        self.min_connections = int(os.getenv('DB_MIN_CONNECTIONS', 2))
        self.max_connections = int(os.getenv('DB_MAX_CONNECTIONS', 10))
        self.reconnect_retries = 3
        self.reconnect_backoff = 1  # 秒
        self._reconnecting = False  # 再帰防止フラグ

    def _mark_db_unavailable(self, reason: str = "connect_failed") -> None:
        """以降の get_connection を即失敗させ、再接続ループで数十秒ブロックしない。"""
        self.startup_skip_reason = reason
        if self.connection_pool:
            try:
                self.connection_pool.closeall()
            except Exception:
                pass
            self.connection_pool = None
        if self.connection:
            try:
                self.connection.close()
            except Exception:
                pass
            self.connection = None
        try:
            from src.services import session_manager as sm

            sm._db_persist_enabled = False
        except Exception:
            pass

    def is_available(self) -> bool:
        """接続プールまたは単一接続が有効か。"""
        if self.startup_skip_reason in ("connect_failed", "no_url", "no_driver"):
            return False
        return bool(self.connection_pool or self.connection)

    def is_intentionally_disabled(self) -> bool:
        """DATABASE_URL 未設定など、起動時に DB を使わない想定か。"""
        reason = self.startup_skip_reason
        if reason in ("no_url", "no_driver"):
            return True
        if not self.database_url and not self.is_available():
            return True
        return False
        
    def connect(self):
        """データベースに接続または接続プールを作成"""
        self.startup_skip_reason = None
        try:
            if psycopg2 is None or pool is None:
                self.startup_skip_reason = "no_driver"
                return False
            if not self.database_url:
                self.startup_skip_reason = "no_url"
                return False
            
            # 接続プールを作成
            try:
                # SSLモードを環境変数から取得（デフォルトはrequire）
                sslmode = os.getenv('DATABASE_SSLMODE', 'require')
                
                # 接続パラメータを構築
                connect_kwargs = {
                    'connect_timeout': 5,  # 10秒から5秒に短縮（早期エラー検出）
                    'application_name': "medicine-recommend-system"
                }
                
                # DATABASE_URLにsslmodeが含まれていない場合のみ追加
                if 'sslmode=' not in self.database_url.lower():
                    # DATABASE_URLにsslmodeパラメータを追加
                    separator = '&' if '?' in self.database_url else '?'
                    self.database_url = f"{self.database_url}{separator}sslmode={sslmode}"
                
                self.connection_pool = pool.ThreadedConnectionPool(
                    self.min_connections,
                    self.max_connections,
                    self.database_url,
                    **connect_kwargs
                )
                logger.info(f"✅ PostgreSQL connection pool created (min: {self.min_connections}, max: {self.max_connections})")
                # 初期接続をテスト（再帰を防ぐため直接接続プールから取得）
                try:
                    test_conn = self.connection_pool.getconn()
                    if test_conn:
                        cursor = test_conn.cursor()
                        cursor.execute("SELECT 1")
                        cursor.close()
                        self.connection_pool.putconn(test_conn)
                        return True
                except Exception as test_error:
                    logger.warning(f"⚠️ Initial connection test failed: {str(test_error)}")
                    try:
                        if test_conn:
                            self.connection_pool.putconn(test_conn)
                    except:
                        pass
                self._mark_db_unavailable("connect_failed")
                return False
            except Exception as pool_error:
                logger.warning(f"⚠️ Connection pool creation failed, using single connection: {str(pool_error)}")
                # フォールバック: 単一接続
                sslmode = os.getenv('DATABASE_SSLMODE', 'require')
                connect_kwargs = {
                    'connect_timeout': 5,  # 10秒から5秒に短縮
                    'application_name': "medicine-recommend-system"
                }
                # DATABASE_URLにsslmodeが含まれていない場合のみ追加
                db_url = self.database_url
                if 'sslmode=' not in db_url.lower():
                    separator = '&' if '?' in db_url else '?'
                    db_url = f"{db_url}{separator}sslmode={sslmode}"
                
                self.connection = psycopg2.connect(
                    db_url,
                    **connect_kwargs
                )
                logger.info("✅ PostgreSQL connection established (fallback mode)")
                return True
            
        except Exception as e:
            self.startup_skip_reason = "connect_failed"
            logger.error(f"❌ Database connection failed: {str(e)}")
            return False
    
    def _is_ssl_error(self, error_msg: str) -> bool:
        """SSLエラーかどうかを判定"""
        ssl_keywords = ["SSL", "ssl", "decryption", "bad record mac", "ssl connection", "certificate"]
        return any(keyword in error_msg for keyword in ssl_keywords)
    
    def _reconnect_with_retry(self):
        """リトライ付き再接続（再帰防止付き）"""
        # 既に再接続中の場合は再帰を防ぐ
        if self._reconnecting:
            logger.warning("⚠️ Reconnection already in progress, skipping recursive call")
            return False
        
        self._reconnecting = True
        try:
            for attempt in range(self.reconnect_retries):
                try:
                    # バックオフ: 試行回数に応じて待機時間を増やす
                    if attempt > 0:
                        import time
                        wait_time = self.reconnect_backoff * (2 ** (attempt - 1))
                        logger.info(f"⏳ Reconnection attempt {attempt + 1}/{self.reconnect_retries}, waiting {wait_time}s...")
                        time.sleep(wait_time)
                    
                    # 接続プールを閉じて再初期化
                    if self.connection_pool:
                        try:
                            self.connection_pool.closeall()
                        except:
                            pass
                        self.connection_pool = None
                    
                    # 単一接続も閉じる
                    if self.connection:
                        try:
                            self.connection.close()
                        except:
                            pass
                        self.connection = None
                    
                    # 再接続を試行（再帰フラグを一時的に解除してconnect()を呼ぶ）
                    self._reconnecting = False
                    try:
                        if self.connect():
                            logger.info(f"✅ Reconnection successful (attempt {attempt + 1})")
                            return True
                    finally:
                        self._reconnecting = True
                except Exception as e:
                    logger.warning(f"⚠️ Reconnection attempt {attempt + 1} failed: {str(e)}")
            
            logger.error(f"❌ All reconnection attempts failed")
            self._mark_db_unavailable("connect_failed")
            return False
        finally:
            self._reconnecting = False
    
    def get_connection(self):
        """接続プールから接続を取得、または単一接続を返す"""
        if self.startup_skip_reason in ("connect_failed", "no_url", "no_driver"):
            return None
        if not self.is_available():
            if not self.is_intentionally_disabled():
                logger.error("❌ No database connection available")
            return None
        if self.connection_pool:
            try:
                conn = self.connection_pool.getconn()
                # 接続の有効性をチェック
                if conn:
                    # 接続が閉じている場合は再接続
                    if conn.closed:
                        logger.warning("⚠️ Connection is closed, reconnecting...")
                        try:
                            conn.close()
                        except:
                            pass
                        if self._reconnect_with_retry():
                            try:
                                if self.connection_pool:
                                    conn = self.connection_pool.getconn()
                                else:
                                    return None
                            except Exception as get_error:
                                logger.error(f"❌ Failed to get connection after reconnect: {str(get_error)}")
                                return None
                        else:
                            return None
                    else:
                        # 接続が開いている場合、簡単なクエリで有効性を確認
                        try:
                            cursor = conn.cursor()
                            cursor.execute("SELECT 1")
                            cursor.close()
                            # SELECT 1が成功すれば接続は有効
                        except Exception as e:
                            # クエリ実行に失敗した場合のみ再接続
                            error_msg = str(e)
                            logger.warning(f"⚠️ Connection validation failed: {error_msg}, reconnecting...")
                            try:
                                conn.close()
                            except:
                                pass
                            if self._reconnect_with_retry():
                                try:
                                    if self.connection_pool:
                                        conn = self.connection_pool.getconn()
                                    else:
                                        return None
                                except Exception as get_error:
                                    logger.error(f"❌ Failed to get connection after reconnect: {str(get_error)}")
                                    return None
                            else:
                                return None
                return conn
            except Exception as e:
                error_msg = str(e)
                logger.error(f"❌ Failed to get connection from pool: {error_msg}")
                
                # 再接続を試行（再帰防止フラグにより安全）
                if self._reconnect_with_retry():
                    try:
                        if self.connection_pool:
                            return self.connection_pool.getconn()
                        elif self.connection:
                            return self.connection
                        else:
                            return None
                    except Exception as get_error:
                        logger.error(f"❌ Failed to get connection after reconnect: {str(get_error)}")
                        return None
                return None
        elif self.connection:
            # 単一接続の場合も検証
            try:
                if self.connection.closed:
                    logger.warning("⚠️ Single connection is closed, reconnecting...")
                    if self._reconnect_with_retry():
                        return self.connection
                    return None
                
                cursor = self.connection.cursor()
                cursor.execute("SELECT 1")
                cursor.close()
                return self.connection
            except Exception as e:
                error_msg = str(e)
                logger.warning(f"⚠️ Single connection validation failed: {error_msg}")
                # 再接続を試行（再帰防止フラグにより安全）
                if self._reconnect_with_retry():
                    return self.connection
                return None
        if not self.is_intentionally_disabled():
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

            try:
                alter_negative_reason_sql = """
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name='feedback_reports' AND column_name='negative_reason'
                    ) THEN
                        ALTER TABLE feedback_reports ADD COLUMN negative_reason VARCHAR(64);
                    END IF;
                END $$;
                """
                cursor.execute(alter_negative_reason_sql)
            except Exception as e:
                logger.debug(f"negative_reason column may already exist: {e}")

            try:
                alter_processing_sql = """
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name='sessions' AND column_name='processing_status'
                    ) THEN
                        ALTER TABLE sessions ADD COLUMN processing_status JSONB;
                    END IF;
                END $$;
                """
                cursor.execute(alter_processing_sql)
            except Exception as e:
                logger.debug(f"processing_status column may already exist: {e}")
            
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
            try:
                from src.services.admin_settings_service import ensure_llm_tables
                ensure_llm_tables()
            except Exception as llm_tbl_err:
                logger.warning("LLM auxiliary tables init skipped: %s", llm_tbl_err)
            return True
            
        except Exception as e:
            logger.error(f"❌ Table initialization failed: {str(e)}")
            if conn:
                conn.rollback()
                self.put_connection(conn)
            return False
    
    def insert_feedback(self, report_type, session_id, username, user_message, 
                       ai_response, security_score=None, feedback_text=None, 
                       is_google_form=False, negative_reason=None):
        """フィードバックをデータベースに保存"""
        conn = self.get_connection()
        if not conn:
            return False
            
        try:
            cursor = conn.cursor()
            
            insert_sql = """
            INSERT INTO feedback_reports 
            (report_type, session_id, username, user_message, ai_response, 
             security_score, feedback_text, is_google_form, negative_reason)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id;
            """
            
            cursor.execute(insert_sql, (
                report_type, session_id, username, user_message, ai_response,
                security_score, feedback_text, is_google_form, negative_reason
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
            return []
        
        if RealDictCursor is None:
            logger.error("❌ RealDictCursor not available")
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
                try:
                    # RealDictCursorの結果は既に辞書形式
                    report = dict(row) if not isinstance(row, dict) else row
                    # datetimeオブジェクトを文字列に変換
                    if 'created_at' in report and report['created_at']:
                        if hasattr(report['created_at'], 'isoformat'):
                            report['created_at'] = report['created_at'].isoformat()
                        elif isinstance(report['created_at'], str):
                            # 既に文字列の場合はそのまま
                            pass
                    reports.append(report)
                except Exception as row_error:
                    logger.error(f"❌ Error processing feedback report row: {str(row_error)}")
                    import traceback
                    logger.error(f"❌ Row error traceback: {traceback.format_exc()}")
                    continue
            
            logger.info(f"✅ Retrieved {len(reports)} feedback reports")
            return reports
            
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            logger.error(f"❌ Failed to get feedback reports: {str(e)}")
            logger.error(f"❌ Traceback: {error_trace}")
            if conn:
                self.put_connection(conn)
            return []
    
    def resolve_feedback(self, feedback_id):
        """フィードバックを解決済みにマーク"""
        conn = self.get_connection()
        if not conn:
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

    def update_processing_status_only(self, session_id, status_dict):
        """processing_status カラムのみ更新（messages は触らない）"""
        conn = self.get_connection()
        if not conn:
            return False
        try:
            cursor = conn.cursor()
            status_json = json.dumps(status_dict, ensure_ascii=False) if status_dict is not None else None
            update_sql = """
            UPDATE sessions
            SET processing_status = %s::jsonb, last_activity = %s
            WHERE session_id = %s;
            """
            cursor.execute(
                update_sql,
                (status_json, datetime.now(), session_id),
            )
            conn.commit()
            cursor.close()
            self.put_connection(conn)
            return True
        except Exception as e:
            logger.error(f"❌ Failed to update processing_status: {str(e)}")
            if conn:
                conn.rollback()
                self.put_connection(conn)
            return False

    def get_processing_status_only(self, session_id):
        """processing_status カラムのみ取得"""
        conn = self.get_connection()
        if not conn:
            return None
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute(
                "SELECT processing_status FROM sessions WHERE session_id = %s;",
                (session_id,),
            )
            result = cursor.fetchone()
            cursor.close()
            self.put_connection(conn)
            if not result:
                return None
            raw = result.get("processing_status")
            if raw is None:
                return None
            if isinstance(raw, str):
                return json.loads(raw)
            return dict(raw)
        except Exception as e:
            logger.error(f"❌ Failed to get processing_status: {str(e)}")
            if conn:
                self.put_connection(conn)
            return None
    
    def get_session(self, session_id):
        """セッションをデータベースから取得"""
        conn = self.get_connection()
        if not conn:
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
    
    def _empty_messages_sql(self) -> str:
        """messages が空の行を判定する SQL 断片。"""
        return (
            "(messages IS NULL OR messages = '[]'::jsonb "
            "OR (jsonb_typeof(messages) = 'array' AND jsonb_array_length(messages) = 0))"
        )

    def purge_all_empty_sessions(self, exclude_session_ids=None):
        """メッセージ0件のセッションを一括削除（起動時・管理用）。"""
        conn = self.get_connection()
        if not conn:
            return 0
        exclude_list = list(exclude_session_ids or [])
        try:
            cursor = conn.cursor()
            empty_cond = self._empty_messages_sql()
            if exclude_list:
                placeholders = ','.join(['%s'] * len(exclude_list))
                delete_sql = f"""
                DELETE FROM sessions
                WHERE {empty_cond}
                AND session_id NOT IN ({placeholders});
                """
                cursor.execute(delete_sql, tuple(exclude_list))
            else:
                delete_sql = f"DELETE FROM sessions WHERE {empty_cond};"
                cursor.execute(delete_sql)
            deleted_count = cursor.rowcount
            conn.commit()
            cursor.close()
            self.put_connection(conn)
            if deleted_count > 0:
                logger.info("Purged %s empty sessions", deleted_count)
            return deleted_count
        except Exception as e:
            logger.error("Failed to purge empty sessions: %s", e)
            if conn:
                conn.rollback()
                self.put_connection(conn)
            return 0

    def cleanup_expired_sessions(
        self,
        timeout_seconds,
        exclude_session_ids=None,
        chat_end_timeout_seconds=None,
        empty_session_timeout_seconds=None,
        skip_empty_sessions=False,
    ):
        """期限切れセッションを削除
        
        Args:
            timeout_seconds: 通常のタイムアウト（秒）
            exclude_session_ids: 削除から除外するセッションIDのリスト（アクティブなセッション）
            chat_end_timeout_seconds: チャット終了後の削除タイムアウト（秒）。Noneの場合は通常のタイムアウトを使用
            empty_session_timeout_seconds: メッセージ0件セッションの削除タイムアウト（秒）
            skip_empty_sessions: True のときメッセージ0件セッションは削除しない（管理画面の一覧表示用）
        """
        conn = self.get_connection()
        if not conn:
            return 0
        
        try:
            cursor = conn.cursor()
            
            exclude_list = exclude_session_ids or []
            chat_end_timeout = int(chat_end_timeout_seconds or timeout_seconds)
            empty_timeout = int(empty_session_timeout_seconds or timeout_seconds)
            empty_cond = self._empty_messages_sql()

            expire_clause = f"""
                (
                    (session_active = false AND last_activity < NOW() - INTERVAL '{chat_end_timeout} seconds')
                    OR
                    (COALESCE(session_active, true) = true AND last_activity < NOW() - INTERVAL '{int(timeout_seconds)} seconds')
                )
            """
            if not skip_empty_sessions:
                expire_clause += f"""
                OR
                ({empty_cond} AND last_activity < NOW() - INTERVAL '{empty_timeout} seconds')
                """

            if exclude_list:
                placeholders = ','.join(['%s'] * len(exclude_list))
                delete_sql = f"""
                DELETE FROM sessions
                WHERE ({expire_clause})
                AND session_id NOT IN ({placeholders});
                """
                cursor.execute(delete_sql, tuple(exclude_list))
            else:
                delete_sql = f"DELETE FROM sessions WHERE ({expire_clause});"
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
            if self._is_ssl_error(error_msg):
                logger.warning("⚠️ SSL error detected, attempting to reconnect...")
                if conn:
                    try:
                        conn.close()
                    except:
                        pass
                # 再接続を試行（リトライ付き）
                if self._reconnect_with_retry():
                    conn = self.get_connection()
                    if conn:
                        logger.info("✅ Database reconnected successfully")
            
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

def _log_database_startup_outcome(success: bool) -> None:
    """init_database から一度だけ呼び出し、起動時の DB 状態を分かりやすくログする。"""
    if success:
        logger.info("✅ Database initialized successfully.")
        return
    reason = getattr(db_manager, "startup_skip_reason", None) or "unknown"
    if reason == "no_url":
        logger.info(
            "データベース未設定（DATABASE_URL なし）: フィードバック・DB セッション共有は無効。"
            " チャット・CSV ベースの推奨は利用可能です。"
        )
        return
    if reason == "no_driver":
        logger.info(
            "PostgreSQL ドライバ（psycopg2）未インストール: DB 機能は無効。"
            " `pip install psycopg2-binary` で有効化できます。チャット等は利用可能です。"
        )
        return
    if reason == "connect_failed":
        logger.warning(
            "データベース接続に失敗しました: フィードバック等は無効です。"
            " DATABASE_URL・ネットワーク・SSL 設定を確認してください。"
        )
        return
    if reason == "init_failed":
        logger.warning(
            "データベースには接続できましたがテーブル初期化に失敗しました。"
            " 権限・スキーマを確認してください。"
        )
        return
    logger.warning(
        "⚠️ Database initialization failed. Feedback features will be disabled. (reason=%s)",
        reason,
    )


def init_database():
    """データベースを初期化（アプリ起動時に呼び出し）"""
    try:
        if db_manager.connect():
            if db_manager.initialize_tables():
                _log_database_startup_outcome(True)
                return True
            db_manager.startup_skip_reason = "init_failed"
            _log_database_startup_outcome(False)
            return False
        _log_database_startup_outcome(False)
        return False
    except Exception as e:
        db_manager.startup_skip_reason = "error"
        logger.warning(f"⚠️ Database initialization error: {str(e)} - continuing without database")
        return False

def get_database():
    """データベースマネージャーを取得"""
    return db_manager
