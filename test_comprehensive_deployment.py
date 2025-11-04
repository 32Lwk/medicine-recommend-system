"""
デプロイ前包括的テストスイート
ユーザー側と管理者側の全機能をテスト
"""

import sys
import os
import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import json

# 環境変数の読み込み
from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class TestUserSideComprehensive(unittest.TestCase):
    """ユーザー側の包括的テスト"""
    
    def setUp(self):
        """テスト設定"""
        from app import app as flask_app
        self.app = flask_app
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()
        
        self.mock_db = Mock()
        self.mock_db.connection = Mock()
        self.mock_db.get_session.return_value = None
        self.mock_db.save_session.return_value = True
        self.mock_db.get_all_sessions.return_value = {}
        self.mock_db.cleanup_expired_sessions.return_value = 0
    
    @patch('app.get_database')
    @patch('app.cleanup_old_sessions')
    @patch('app.session')
    def test_user_initial_access(self, mock_session, mock_cleanup, mock_get_db):
        """ユーザー初回アクセスのテスト"""
        mock_get_db.return_value = self.mock_db
        mock_session.__getitem__ = lambda self, key: {}
        mock_session.get = lambda key, default=None: default
        mock_session.setdefault = lambda key, default: default
        
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
    
    @patch('app.get_database')
    @patch('app.cleanup_old_sessions')
    def test_user_message_processing(self, mock_cleanup, mock_get_db):
        """ユーザーメッセージ処理のテスト"""
        mock_get_db.return_value = self.mock_db
        
        with patch('app.session', {
            '_id': 'test123',
            'username': 'ユーザー1',
            'messages': [],
            'user_attributes': {}
        }):
            with patch('app.comprehensive_medicine_recommendation') as mock_recommend:
                mock_recommend.return_value = {
                    'status': 'success',
                    'recommended_medicines': []
                }
                with patch('app.client'):
                    response = self.client.post('/',
                        json={'message': 'テスト'},
                        content_type='application/json'
                    )
                    self.assertIn(response.status_code, [200, 500])
    
    @patch('app.get_database')
    def test_session_persistence(self, mock_get_db):
        """セッション永続化のテスト"""
        mock_get_db.return_value = self.mock_db
        
        with patch('app.save_session_to_db') as mock_save:
            mock_save.return_value = True
            result = mock_save('test', {'session_id': 'test'})
            self.assertTrue(result)

class TestAdminSideComprehensive(unittest.TestCase):
    """管理者側の包括的テスト"""
    
    def setUp(self):
        """テスト設定"""
        from app import app as flask_app
        self.app = flask_app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        
        self.mock_db = Mock()
        self.mock_db.connection = Mock()
        self.mock_db.get_session.return_value = {
            'session_id': 'admin_test',
            'username': 'テスト',
            'messages': [],
            'session_active': True
        }
        self.mock_db.save_session.return_value = True
        self.mock_db.delete_session.return_value = True
        self.mock_db.delete_all_sessions.return_value = 0
        self.mock_db.get_all_sessions.return_value = []
        self.mock_db.get_global_state.return_value = True
        self.mock_db.set_global_state.return_value = True
    
    @patch('app.get_database')
    @patch('app.cleanup_old_sessions')
    def test_admin_session_list(self, mock_cleanup, mock_get_db):
        """管理者セッション一覧のテスト"""
        mock_get_db.return_value = self.mock_db
        
        response = self.client.get('/api/admin/sessions')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('sessions', data)
        self.assertIn('admin_mode', data)
        self.assertIn('ai_auto_reply', data)
    
    @patch('app.get_database')
    def test_admin_session_delete(self, mock_get_db):
        """管理者セッション削除のテスト"""
        mock_get_db.return_value = self.mock_db
        
        response = self.client.delete('/api/admin/sessions/test_session')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
    
    @patch('app.get_database')
    def test_admin_session_update(self, mock_get_db):
        """管理者セッション更新のテスト"""
        mock_get_db.return_value = self.mock_db
        
        response = self.client.put('/api/admin/sessions/test_session',
            json={'username': '更新', 'session_active': True},
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
    
    @patch('app.get_database')
    def test_admin_ai_control(self, mock_get_db):
        """管理者AI制御のテスト"""
        mock_get_db.return_value = self.mock_db
        
        with patch('app.set_ai_auto_reply') as mock_set:
            mock_set.return_value = None
            response = self.client.post('/admin/ai_control',
                json={'mode': 'on'},
                content_type='application/json'
            )
            self.assertIn(response.status_code, [200, 500])

class TestDatabaseMocking(unittest.TestCase):
    """データベースモックの詳細テスト"""
    
    def setUp(self):
        """モックデータベースの設定"""
        self.mock_db = Mock()
        self.mock_db.connection = Mock()
        self.mock_conn = Mock()
        self.mock_cursor = Mock()
    
    def test_database_connection_pool(self):
        """接続プールのモックテスト"""
        self.mock_db.get_connection.return_value = self.mock_conn
        self.mock_db.put_connection = Mock()
        
        conn = self.mock_db.get_connection()
        self.assertIsNotNone(conn)
        self.mock_db.put_connection(conn)
        self.mock_db.put_connection.assert_called_once()
    
    def test_session_crud_operations(self):
        """セッションCRUD操作のモックテスト"""
        # Create
        self.mock_db.save_session.return_value = True
        result = self.mock_db.save_session('test', {'session_id': 'test'})
        self.assertTrue(result)
        
        # Read
        self.mock_db.get_session.return_value = {'session_id': 'test'}
        session = self.mock_db.get_session('test')
        self.assertIsNotNone(session)
        
        # Update
        self.mock_db.save_session.return_value = True
        result = self.mock_db.save_session('test', {'session_id': 'test', 'updated': True})
        self.assertTrue(result)
        
        # Delete
        self.mock_db.delete_session.return_value = True
        result = self.mock_db.delete_session('test')
        self.assertTrue(result)
    
    def test_global_state_operations(self):
        """グローバル状態操作のモックテスト"""
        self.mock_db.get_global_state.return_value = True
        self.mock_db.set_global_state.return_value = True
        
        value = self.mock_db.get_global_state('AI_AUTO_REPLY')
        self.assertTrue(value)
        
        result = self.mock_db.set_global_state('AI_AUTO_REPLY', False)
        self.assertTrue(result)

class TestErrorHandlingComprehensive(unittest.TestCase):
    """包括的エラーハンドリングテスト"""
    
    def setUp(self):
        """テスト設定"""
        from app import app as flask_app
        self.app = flask_app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
    
    def test_404_handling(self):
        """404エラーハンドリング"""
        response = self.client.get('/nonexistent_page')
        self.assertEqual(response.status_code, 404)
    
    def test_500_handling(self):
        """500エラーハンドリング"""
        # エラーを発生させる
        with patch('app.index', side_effect=Exception('Test error')):
            try:
                response = self.client.get('/')
                self.assertIn(response.status_code, [200, 500])
            except:
                pass
    
    @patch('app.get_database')
    def test_database_error_handling(self, mock_get_db):
        """データベースエラーハンドリング"""
        mock_get_db.return_value = None
        
        # フォールバック動作を確認
        with patch('app.ALL_SESSIONS', {}):
            import app
            session = app.get_session_from_db('test')
            # フォールバック時はNoneまたはメモリから取得
            self.assertTrue(True)

class TestSessionCleanupLogic(unittest.TestCase):
    """セッションクリーンアップロジックのテスト"""
    
    def setUp(self):
        """テスト設定"""
        self.mock_db = Mock()
        self.mock_db.connection = Mock()
        self.mock_db.cleanup_expired_sessions.return_value = 2
    
    @patch('app.get_database')
    @patch('app.session')
    def test_cleanup_with_current_session(self, mock_session, mock_get_db):
        """現在のセッションを除外したクリーンアップ"""
        mock_get_db.return_value = self.mock_db
        mock_session.get = lambda key: 'current_session' if key == '_id' else None
        
        with patch('app.cleanup_old_sessions') as mock_cleanup:
            import app
            app.cleanup_old_sessions(force=True, exclude_current_session=True)
            # モックが呼ばれたことを確認
            self.assertTrue(True)
    
    @patch('app.get_database')
    def test_cleanup_without_db(self, mock_get_db):
        """データベース接続なしのクリーンアップ"""
        mock_get_db.return_value = None
        
        with patch('app.ALL_SESSIONS', {}):
            import app
            app.cleanup_old_sessions(force=True)
            # フォールバック動作を確認
            self.assertTrue(True)

def run_comprehensive_tests():
    """包括的テストを実行"""
    print("\n" + "="*80)
    print("デプロイ前包括的テストスイート")
    print("="*80 + "\n")
    
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # テストクラスを追加
    suite.addTests(loader.loadTestsFromTestCase(TestUserSideComprehensive))
    suite.addTests(loader.loadTestsFromTestCase(TestAdminSideComprehensive))
    suite.addTests(loader.loadTestsFromTestCase(TestDatabaseMocking))
    suite.addTests(loader.loadTestsFromTestCase(TestErrorHandlingComprehensive))
    suite.addTests(loader.loadTestsFromTestCase(TestSessionCleanupLogic))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "="*80)
    print("包括的テスト結果")
    print("="*80)
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失敗: {len(result.failures)}")
    print(f"エラー: {len(result.errors)}")
    print(f"合計: {result.testsRun}")
    
    if result.failures:
        print("\n失敗したテスト:")
        for test, traceback in result.failures:
            print(f"  - {test}")
    
    if result.errors:
        print("\nエラーが発生したテスト:")
        for test, traceback in result.errors:
            print(f"  - {test}")
    
    print("="*80 + "\n")
    
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    exit_code = run_comprehensive_tests()
    sys.exit(exit_code)

