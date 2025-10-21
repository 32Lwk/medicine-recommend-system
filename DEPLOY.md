# Renderデプロイ手順（簡易版）

## 📋 事前準備

### 1. GitHubにプッシュ

```bash
# 変更をステージング
git add requirements.txt runtime.txt gunicorn_config.py env.example DEPLOY.md RENDER_DEPLOY_GUIDE.md

# コミット
git commit -m "Renderデプロイのための設定ファイルを追加"

# プッシュ
git push origin main
```

### 2. OpenAI APIキーを準備

https://platform.openai.com/api-keys からAPIキーを取得

## 🚀 Renderでのデプロイ（5分で完了）

### Step 1: Renderにサインアップ

1. https://render.com にアクセス
2. 「Sign Up」→ GitHubアカウントで登録

### Step 2: 新規Webサービス作成

1. 「New +」→ 「Web Service」をクリック
2. GitHubリポジトリ `medicine-recommend` を選択
3. 「Connect」をクリック

### Step 3: 基本設定

| 項目 | 設定値 |
|------|--------|
| Name | `medicine-recommend-app` |
| Region | `Singapore` |
| Branch | `main` |
| Runtime | `Python 3` |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `gunicorn app:app` |
| Instance Type | `Free` |

### Step 4: 環境変数を設定

「Environment」タブで以下を追加：

```
OPENAI_API_KEY = あなたのOpenAI APIキー
SECRET_KEY = 任意のランダム文字列（32文字以上推奨）
FLASK_ENV = production
```

💡 SECRET_KEYの生成方法：
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### Step 5: デプロイ

「Create Web Service」をクリック → 5-10分待つ

### Step 6: 確認

デプロイ完了後、Renderが提供するURL（例：`https://medicine-recommend-app.onrender.com`）にアクセス

---

## ⚠️ 重要な注意事項

### セキュリティ

- ✅ **APIキーをコードに書かない**（環境変数で管理）
- ✅ **`.env`ファイルはGitにコミットしない**（`.gitignore`で除外済み）
- ✅ **公開リポジトリの場合、機密情報がないか確認**

### Freeプランの制限

- 15分間アクセスがないとスリープ状態になります
- 再アクセス時に起動に30秒〜1分程度かかります
- 月間750時間まで無料

---

## 🔧 トラブルシューティング

### デプロイが失敗する場合

1. **Renderのログを確認**
   - 「Logs」タブでエラーメッセージを確認

2. **よくあるエラー**
   - `Module not found` → `requirements.txt`を確認
   - `Application failed to start` → Start Commandを確認: `gunicorn app:app`
   - `OpenAI API key not found` → 環境変数が正しく設定されているか確認

### 動作確認

1. ルートURL `/` にアクセス → ユーザー画面が表示される
2. `/admin` にアクセス → 管理画面が表示される

---

## 🔄 更新のデプロイ

コードを変更した場合：

```bash
git add .
git commit -m "変更内容"
git push origin main
```

Renderが自動的に再デプロイします（3-5分）。

---

## 💰 コスト

- **Free**: $0/月（スリープあり）
- **Starter**: $7/月（常時稼働）
- **Standard**: $25/月〜（高性能）

---

## 📞 サポート

- Renderドキュメント: https://render.com/docs
- 詳細なガイド: `RENDER_DEPLOY_GUIDE.md` を参照

---

**デプロイ完了おめでとうございます！** 🎉

