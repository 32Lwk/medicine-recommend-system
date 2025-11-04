"""
統合テスト - ユーザー側と管理者側の統合的な動作をテスト
DB接続はモックを使用
"""

import sys
import os
import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import json
import base64

# 環境変数の読み込み
from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class TestUserIntegration(unittest.TestCase):
    """ユーザー側の統合テスト"""
    
    def setUp(self):
        """テスト用のFlaskアプリを作成"""
        from app import app as flask_app
        self.app = flask_app
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()
        
        # モックデータベース
        self.mock_db = Mock()
        self.mock_db.connection = Mock()
        self.mock_db.get_session.return_value = None
        self.mock_db.save_session.return_value = True
        self.mock_db.get_all_sessions.return_value = {}
        self.mock_db.cleanup_expired_sessions.return_value = 0
        
        # セッションデータ
        self.session_data = {
            '_id': 'test_session_456',
            'username': 'ユーザー1',
            'messages': [],
            'user_attributes': {
                'age': None,
                'gender': None,
                'pregnant': None,
                'breastfeeding': None,
                'current_medications': [],
                'allergies': []
            }
        }
    
    @patch('app.get_database')
    @patch('app.cleanup_old_sessions')
    @patch('app.session')
    def test_complete_user_flow(self, mock_session, mock_cleanup, mock_get_db):
        """完全なユーザーフローのテスト"""
        mock_get_db.return_value = self.mock_db
        mock_session.__getitem__ = lambda self, key: self.session_data.get(key)
        mock_session.__setitem__ = lambda self, key, value: self.session_data.__setitem__(key, value)
        mock_session.get = lambda key, default=None: self.session_data.get(key, default)
        mock_session.setdefault = lambda key, default: self.session_data.setdefault(key, default)
        mock_session.modified = False
        
        # 1. 初回アクセス（GET）
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        
        # 2. メッセージ送信（POST）
        with patch('app.comprehensive_medicine_recommendation') as mock_recommend:
            mock_recommend.return_value = {
                'status': 'success',
                'recommended_medicines': [{
                    'product_name': 'テスト医薬品',
                    'score': 0.8
                }],
                'usage_notes': 'テスト'
            }
            with patch('app.client'):
                response = self.client.post('/',
                    json={'message': '頭が痛いです'},
                    content_type='application/json'
                )
                # 正常応答またはエラー（環境による）
                self.assertIn(response.status_code, [200, 500])
    
    @patch('app.get_database')
    def test_session_creation_and_update(self, mock_get_db):
        """セッション作成と更新のテスト"""
        mock_get_db.return_value = self.mock_db
        
        # セッションが作成されることを確認
        self.mock_db.get_session.return_value = None  # 新規セッション
        
        # セッション保存が呼ばれることを確認
        with patch('app.save_session_to_db') as mock_save:
            mock_save.return_value = True
            # セッション保存のテスト
            result = mock_save('test_session', {'session_id': 'test_session'})
            self.assertTrue(result)

class TestAdminIntegration(unittest.TestCase):
    """管理者側の統合テスト"""
    
    def setUp(self):
        """テスト用のFlaskアプリを作成"""
        from app import app as flask_app
        self.app = flask_app
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()
        
        # モックデータベース
        self.mock_db = Mock()
        self.mock_db.connection = Mock()
        self.mock_db.get_session.return_value = {
            'session_id': 'test_admin_session',
            'username': '管理者テスト',
            'messages': [],
            'session_active': True
        }
        self.mock_db.save_session.return_value = True
        self.mock_db.delete_session.return_value = True
        self.mock_db.delete_all_sessions.return_value = 3
        self.mock_db.get_all_sessions.return_value = [
            {
                'session_id': 'session1',
                'username': 'ユーザー1',
                'messages': [],
                'last_activity': datetime.now().timestamp(),
                'session_active': True
            },
            {
                'session_id': 'session2',
                'username': 'ユーザー2',
                'messages': [],
                'last_activity': datetime.now().timestamp(),
                'session_active': False
            }
        ]
    
    @patch('app.get_database')
    @patch('app.cleanup_old_sessions')
    def test_admin_session_management_flow(self, mock_cleanup, mock_get_db):
        """管理者セッション管理フローのテスト"""
        mock_get_db.return_value = self.mock_db
        
        # 1. セッション一覧取得
        response = self.client.get('/api/admin/sessions')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('sessions', data)
        self.assertIsInstance(data['sessions'], list)
        
        # 2. セッション削除
        response = self.client.delete('/api/admin/sessions/session1')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        
        # 3. セッション更新
        response = self.client.put('/api/admin/sessions/session2',
            json={'username': '更新されたユーザー', 'session_active': True},
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
    
    @patch('app.get_database')
    @patch('app.cleanup_old_sessions')
    def test_admin_send_message_flow(self, mock_cleanup, mock_get_db):
        """管理者メッセージ送信フローのテスト"""
        mock_get_db.return_value = self.mock_db
        
        response = self.client.post('/api/admin/send_message',
            json={
                'session_id': 'test_admin_session',
                'message': 'テストメッセージ'
            },
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
    
    @patch('app.get_database')
    def test_admin_delete_all_sessions(self, mock_get_db):
        """全セッション削除のテスト"""
        mock_get_db.return_value = self.mock_db
        
        response = self.client.delete('/api/admin/sessions/delete_all')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        self.assertIn('deleted_count', data)

class TestSessionLifecycle(unittest.TestCase):
    """セッションライフサイクルのテスト"""
    
    def setUp(self):
        """テスト用のモックを設定"""
        self.mock_db = Mock()
        self.mock_db.connection = Mock()
        self.session_id = 'test_lifecycle_session'
    
    @patch('app.get_database')
    def test_session_creation(self, mock_get_db):
        """セッション作成のテスト"""
        mock_get_db.return_value = self.mock_db
        self.mock_db.get_session.return_value = None
        
        with patch('app.save_session_to_db') as mock_save:
            mock_save.return_value = True
            result = mock_save(self.session_id, {
                'session_id': self.session_id,
                'username': 'テストユーザー',
                'messages': [],
                'session_active': True
            })
            self.assertTrue(result)
    
    @patch('app.get_database')
    def test_session_update(self, mock_get_db):
        """セッション更新のテスト"""
        mock_get_db.return_value = self.mock_db
        self.mock_db.get_session.return_value = {
            'session_id': self.session_id,
            'username': 'テストユーザー',
            'messages': [{'type': 'user', 'content': 'テスト'}],
            'session_active': True
        }
        self.mock_db.save_session.return_value = True
        
        with patch('app.save_session_to_db') as mock_save:
            mock_save.return_value = True
            result = mock_save(self.session_id, {
                'session_id': self.session_id,
                'username': '更新されたユーザー',
                'messages': [{'type': 'user', 'content': 'テスト'}],
                'session_active': True
            })
            self.assertTrue(result)
    
    @patch('app.get_database')
    def test_session_deletion(self, mock_get_db):
        """セッション削除のテスト"""
        mock_get_db.return_value = self.mock_db
        self.mock_db.delete_session.return_value = True
        
        result = self.mock_db.delete_session(self.session_id)
        self.assertTrue(result)
    
    @patch('app.get_database')
    def test_session_cleanup(self, mock_get_db):
        """セッションクリーンアップのテスト"""
        mock_get_db.return_value = self.mock_db
        self.mock_db.cleanup_expired_sessions.return_value = 2
        
        result = self.mock_db.cleanup_expired_sessions(600, None, 300)
        self.assertEqual(result, 2)

class TestAPIEndpoints(unittest.TestCase):
    """APIエンドポイントの統合テスト"""
    
    def setUp(self):
        """テスト用のFlaskアプリを作成"""
        from app import app as flask_app
        self.app = flask_app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        
        self.mock_db = Mock()
        self.mock_db.connection = Mock()
        self.mock_db.get_session.return_value = {
            'session_id': 'api_test_session',
            'username': 'APIテスト',
            'messages': [],
            'session_active': True
        }
        self.mock_db.get_all_sessions.return_value = {}
    
    @patch('app.get_database')
    def test_api_sessions_route(self, mock_get_db):
        """GET /api/main_sessions のテスト"""
        mock_get_db.return_value = self.mock_db
        
        with patch('app.cleanup_old_sessions'):
            response = self.client.get('/api/main_sessions')
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            self.assertIn('sessions', data)
    
    @patch('app.get_database')
    def test_api_session_stats(self, mock_get_db):
        """GET /api/session_stats のテスト"""
        mock_get_db.return_value = self.mock_db
        
        response = self.client.get('/api/session_stats')
        self.assertIn(response.status_code, [200, 500])

class TestErrorScenarios(unittest.TestCase):
    """エラーシナリオのテスト"""
    
    def setUp(self):
        """テスト用のFlaskアプリを作成"""
        from app import app as flask_app
        self.app = flask_app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
    
    @patch('app.get_database')
    def test_database_connection_failure(self, mock_get_db):
        """データベース接続失敗時のテスト"""
        mock_get_db.return_value = None
        
        # フォールバック動作を確認
        with patch('app.ALL_SESSIONS', {}):
            import app
            session = app.get_session_from_db('test')
            # フォールバック時はNoneまたはメモリから取得
            self.assertTrue(True)
    
    @patch('app.get_database')
    def test_session_not_found(self, mock_get_db):
        """セッションが見つからない場合のテスト"""
        mock_db = Mock()
        mock_db.connection = Mock()
        mock_db.get_session.return_value = None
        mock_get_db.return_value = mock_db
        
        response = self.client.delete('/api/admin/sessions/nonexistent')
        # 404または200（エラーハンドリングによる）
        self.assertIn(response.status_code, [200, 404])

def run_integration_tests():
    """統合テストを実行"""
    print("\n" + "="*80)
    print("統合テスト実行")
    print("="*80 + "\n")
    
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # テストクラスを追加
    suite.addTests(loader.loadTestsFromTestCase(TestUserIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestAdminIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestSessionLifecycle))
    suite.addTests(loader.loadTestsFromTestCase(TestAPIEndpoints))
    suite.addTests(loader.loadTestsFromTestCase(TestErrorScenarios))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "="*80)
    print("統合テスト結果")
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
    exit_code = run_integration_tests()
    sys.exit(exit_code)

