# Render Python バージョン問題の修正方法

## 問題
Renderが`runtime.txt`を無視してPython 3.13.4を使用し、pandasのビルドが失敗する。

## 解決策

### 方法1: Renderダッシュボードで環境変数を設定（推奨）

1. **Renderダッシュボードにアクセス**
   - https://dashboard.render.com
   - あなたのWebサービスを選択

2. **環境変数を追加**
   - 左メニューから「Environment」タブをクリック
   - 「Add Environment Variable」をクリック
   - 以下を追加：

```
Key: PYTHON_VERSION
Value: 3.11.9
```

3. **保存して再デプロイ**
   - 「Save Changes」をクリック
   - 自動的に再デプロイが開始されます

### 方法2: Renderダッシュボードでビルドコマンドを変更

1. **Renderダッシュボードにアクセス**
   - 左メニューから「Settings」タブをクリック

2. **Build Commandを変更**
   - 現在の Build Command を以下に変更：

```bash
pip install --upgrade pip && pip install -r requirements.txt
```

3. **Start Commandを確認**
   - Start Command が以下になっているか確認：

```bash
gunicorn app:app
```

### 方法3: GitHubから再プッシュ（最新の修正を適用）

最新のコードをGitHubにプッシュしてください：

```bash
git add .python-version requirements.txt RENDER_FIX.md
git commit -m "Fix pandas compatibility with Python version specification"
git push origin main
```

## 修正内容

1. ✅ pandas を2.2.3にアップデート（より安定）
2. ✅ numpy<2.0.0 を追加（pandas互換性）
3. ✅ `.python-version` ファイルを追加

## 確認方法

デプロイログで以下を確認：
- ✅ `Using Python version 3.11.9` と表示される
- ✅ `Successfully installed pandas-2.2.3` と表示される
- ✅ ビルドが成功する

---

**最も確実な方法は、Renderダッシュボードで環境変数 `PYTHON_VERSION=3.11.9` を設定することです！**

