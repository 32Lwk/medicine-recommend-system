"""
PostgreSQL接続管理とテーブル初期化
"""
import os
import psycopg2
from psycopg2.extras import RealDictCursor
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        self.connection = None
        self.database_url = os.getenv('DATABASE_URL')
        
    def connect(self):
        """データベースに接続"""
        try:
            if not self.database_url:
                logger.warning("DATABASE_URL not found. Using fallback mode.")
                return False
                
            self.connection = psycopg2.connect(self.database_url)
            logger.info("✅ PostgreSQL connection established")
            return True
            
        except Exception as e:
            logger.error(f"❌ Database connection failed: {str(e)}")
            return False
    
    def initialize_tables(self):
        """テーブルを初期化"""
        if not self.connection:
            logger.error("❌ No database connection")
            return False
            
        try:
            cursor = self.connection.cursor()
            
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
            self.connection.commit()
            
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
            
            self.connection.commit()
            cursor.close()
            
            logger.info("✅ Database tables initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Table initialization failed: {str(e)}")
            return False
    
    def insert_feedback(self, report_type, session_id, username, user_message, 
                       ai_response, security_score=None, feedback_text=None, 
                       is_google_form=False):
        """フィードバックをデータベースに保存"""
        if not self.connection:
            logger.error("❌ No database connection")
            return False
            
        try:
            cursor = self.connection.cursor()
            
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
            self.connection.commit()
            cursor.close()
            
            logger.info(f"✅ Feedback saved with ID: {feedback_id}")
            return feedback_id
            
        except Exception as e:
            logger.error(f"❌ Failed to save feedback: {str(e)}")
            return False
    
    def get_feedback_reports(self, limit=100, unresolved_only=False):
        """フィードバック報告一覧を取得"""
        if not self.connection:
            logger.error("❌ No database connection")
            return []
            
        try:
            cursor = self.connection.cursor(cursor_factory=RealDictCursor)
            
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
            return []
    
    def resolve_feedback(self, feedback_id):
        """フィードバックを解決済みにマーク"""
        if not self.connection:
            logger.error("❌ No database connection")
            return False
            
        try:
            cursor = self.connection.cursor()
            
            update_sql = """
            UPDATE feedback_reports 
            SET resolved = TRUE 
            WHERE id = %s;
            """
            
            cursor.execute(update_sql, (feedback_id,))
            self.connection.commit()
            cursor.close()
            
            logger.info(f"✅ Feedback {feedback_id} marked as resolved")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to resolve feedback: {str(e)}")
            return False
    
    def close(self):
        """データベース接続を閉じる"""
        if self.connection:
            self.connection.close()
            logger.info("✅ Database connection closed")

# グローバルインスタンス
db_manager = DatabaseManager()

def init_database():
    """データベースを初期化（アプリ起動時に呼び出し）"""
    if db_manager.connect():
        return db_manager.initialize_tables()
    return False

def get_database():
    """データベースマネージャーを取得"""
    return db_manager
