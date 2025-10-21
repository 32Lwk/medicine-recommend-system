# Renderデプロイガイド

## 事前準備

### 1. GitHubリポジトリの準備

1. 変更をコミットしてプッシュ：

```bash
git add requirements.txt .env.example runtime.txt RENDER_DEPLOY_GUIDE.md
git commit -m "Add deployment files for Render"
git push origin main
```

⚠️ **重要**: `.env`ファイルは絶対にコミットしないでください！`.gitignore`で除外されています。

### 2. OpenAI APIキーの準備

OpenAI APIキーを取得しておいてください：
- https://platform.openai.com/api-keys

## Renderでのデプロイ手順

### ステップ1: Renderアカウントの作成

1. https://render.com にアクセス
2. 「Get Started」または「Sign Up」をクリック
3. GitHubアカウントで登録（推奨）

### ステップ2: 新しいWebサービスの作成

1. Renderダッシュボードで「New +」→「Web Service」をクリック
2. GitHubリポジトリを接続：
   - 「Connect GitHub」をクリック
   - リポジトリを選択：`medicine-recommend`
   - 「Connect」をクリック

### ステップ3: サービス設定

以下の設定を入力：

| 項目 | 値 |
|------|-----|
| **Name** | `medicine-recommend-app`（任意の名前） |
| **Region** | `Singapore`（日本に近い）または`Oregon` |
| **Branch** | `main` |
| **Root Directory** | （空白のまま） |
| **Runtime** | `Python 3` |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `gunicorn app:app` |

### ステップ4: 環境変数の設定

「Environment」セクションで「Add Environment Variable」をクリックし、以下を追加：

| Key | Value |
|-----|-------|
| `OPENAI_API_KEY` | あなたのOpenAI APIキー |
| `SECRET_KEY` | ランダムな秘密鍵（例：`python -c "import secrets; print(secrets.token_hex(32))"` で生成） |
| `FLASK_ENV` | `production` |
| `PYTHON_VERSION` | `3.9.23` |

### ステップ5: インスタンスタイプの選択

- **Free**プランで開始可能
- より高いパフォーマンスが必要な場合は有料プランを選択

### ステップ6: デプロイ

1. 「Create Web Service」をクリック
2. デプロイが自動的に開始されます（5〜10分程度）
3. ログを確認してエラーがないことを確認

### ステップ7: アプリケーションの確認

デプロイが完了したら：

1. Renderが提供するURL（例：`https://medicine-recommend-app.onrender.com`）にアクセス
2. アプリケーションが正しく動作することを確認

## トラブルシューティング

### エラー: "Module not found"

**原因**: 依存関係がインストールされていない

**解決方法**:
- `requirements.txt`に必要なパッケージが含まれているか確認
- Renderのログで `pip install` が成功しているか確認

### エラー: "Application failed to start"

**原因**: Start Commandが正しくない、またはapp.pyが見つからない

**解決方法**:
- Start Commandを確認: `gunicorn app:app`
- Rootディレクトリが正しいか確認

### エラー: "OpenAI API key not found"

**原因**: 環境変数が設定されていない

**解決方法**:
- Renderの「Environment」タブで`OPENAI_API_KEY`が設定されているか確認
- 値が正しいか確認（前後にスペースがないか）

### Freeプランの制限

- **15分間アクセスがないとスリープ状態になります**
- 再アクセス時に起動に30秒〜1分程度かかる場合があります
- 常時稼働が必要な場合は有料プランを検討してください

## 自動デプロイ

GitHubの`main`ブランチに変更をプッシュすると、Renderが自動的に再デプロイします：

```bash
git add .
git commit -m "Update application"
git push origin main
```

## カスタムドメインの設定（オプション）

1. Renderダッシュボードで「Settings」タブを開く
2. 「Custom Domain」セクションで「Add Custom Domain」をクリック
3. ドメインを入力し、指示に従ってDNS設定を行う

## コスト管理

### Freeプラン
- 月750時間まで無料
- 15分間のアイドル後にスリープ
- 512MB RAM

### Starterプラン（$7/月）
- 常時稼働
- 512MB RAM
- より高速な起動

### Standardプラン（$25/月〜）
- 2GB+ RAM
- より高いパフォーマンス

## セキュリティチェックリスト

- ✅ `.env`ファイルは`.gitignore`に含まれている
- ✅ APIキーはコードにハードコードされていない
- ✅ 環境変数でAPIキーを管理
- ✅ `SECRET_KEY`を設定
- ✅ GitHubリポジトリがプライベートの場合は問題なし（パブリックの場合は機密情報がないか再確認）

## サポート

問題が発生した場合：

1. Renderの「Logs」タブでエラーメッセージを確認
2. `Events`タブでデプロイ履歴を確認
3. Renderのドキュメント: https://render.com/docs
4. Renderサポート: https://render.com/support

---

デプロイ完了おめでとうございます！🎉

