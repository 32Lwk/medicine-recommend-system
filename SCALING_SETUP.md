# Render Manual Scaling設定ガイド

## 概要
このアプリケーションを2-3台のインスタンスで同時接続15台程度に対応させるための設定手順です。

## 前提条件
- Renderアカウントでサービスがデプロイ済みであること
- PostgreSQLデータベースが設定済みであること（DATABASE_URL環境変数が設定されていること）

## 手動設定手順

### 1. Renderダッシュボードにアクセス
1. https://dashboard.render.com にログイン
2. 対象のサービス（medicine-recommend-system）を選択

### 2. Manual Scaling設定
1. 左側のメニューから「Settings」を選択
2. 「Manual Scaling」セクションを探す
3. 「Instance Count」を **2** または **3** に変更
4. 「Save Changes」をクリック

### 3. 環境変数の確認
以下の環境変数が設定されていることを確認してください：
- `DATABASE_URL`: PostgreSQLデータベースの接続URL（必須）
- `OPENAI_API_KEY`: OpenAI APIキー（既存の設定）
- その他の必要な環境変数

### 4. デプロイの確認
- インスタンス数変更後、各インスタンスが正常に起動することを確認
- ログで以下のメッセージが表示されることを確認：
  - `✅ PostgreSQL connection pool created`
  - `✅ Database tables initialized successfully`

## 期待される効果

### スケーリング前（1台）
- 同時接続数: 約4-5台
- 502エラーが発生する可能性あり

### スケーリング後（2-3台）
- 同時接続数: 約15台以上
- セッションデータはPostgreSQLで共有されるため、どのインスタンスに接続しても同じセッション情報が利用可能
- グローバル状態（AI_AUTO_REPLY、ADMIN_MODE等）もPostgreSQLで共有される

## 注意事項

1. **データベース接続**: すべてのインスタンスが同じPostgreSQLデータベースに接続する必要があります
2. **セッション共有**: セッションデータはPostgreSQLに保存されるため、複数インスタンス間で共有されます
3. **コスト**: インスタンス数を増やすと、Renderの利用料金が増加します
4. **パフォーマンス**: 接続プール（最小2、最大10）により、データベース接続の効率が向上します

## トラブルシューティング

### インスタンスが起動しない場合
- ログを確認してエラーメッセージを確認
- DATABASE_URLが正しく設定されているか確認
- PostgreSQLデータベースが利用可能か確認

### セッションが共有されない場合
- すべてのインスタンスが同じDATABASE_URLを使用しているか確認
- データベースの接続ログを確認
- `sessions`テーブルと`global_state`テーブルが作成されているか確認

### パフォーマンスが低下する場合
- データベース接続プールの設定を調整（database.pyの`min_connections`と`max_connections`）
- PostgreSQLデータベースのリソースを確認
- 不要なセッションをクリーンアップ

## テスト方法

### 同時接続テスト
以下のようなスクリプトで同時接続をテストできます：

```python
import requests
import threading
import time

def test_connection(url):
    try:
        response = requests.post(url, json={'message': 'テストメッセージ'}, timeout=30)
        print(f"Status: {response.status_code}, Response: {response.text[:100]}")
    except Exception as e:
        print(f"Error: {e}")

url = "https://your-app.onrender.com/"
threads = []

# 15台の同時接続をシミュレート
for i in range(15):
    thread = threading.Thread(target=test_connection, args=(url,))
    threads.append(thread)
    thread.start()
    time.sleep(0.5)  # 少し間隔を空ける

for thread in threads:
    thread.join()
```

すべての接続が正常に処理されることを確認してください。

