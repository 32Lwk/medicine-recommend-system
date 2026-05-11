# チャット型医薬品相談ツール

症状を入力すると適切な市販薬を提案し、飲み合わせ・注意点のアドバイスを提供するAIシステムです。ルールベースとAIのハイブリッド推奨を採用しています。

## β版について

研究開発中の試験運用版です。公開対象は企業・行政・薬剤師・登録販売者など専門関係者に限定し、一般公開はしていません。詳細は [アプリ概要](docs/アプリ概要.md) を参照してください。

## クイックスタート

**本番・推奨（FastAPI / ASGI）**

```bash
pip install -r requirements.txt
# 環境変数: OPENAI_API_KEY, SECRET_KEY 必須。DATABASE_URL, DEEPL_API_KEY 推奨
./start.sh
# または: gunicorn -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:${PORT:-5000}
# http://localhost:5000 でアクセス（PORT 未設定時）
```

**ローカル開発（Windows 含む・uvicorn）**

```bash
python app.py
# 既定で FastAPI（main:app）。http://localhost:5000（PORT 未設定時）
```

詳細は [docs/FASTAPI_ARCHITECTURE.md](docs/FASTAPI_ARCHITECTURE.md) を参照してください。

管理者画面は `http://localhost:5000/admin`、詳細なセットアップ・環境変数・API一覧は [docs/会社向け概要書類.md](docs/会社向け概要書類.md) や [docs/アプリ概要.md](docs/アプリ概要.md) を参照してください。

## ドキュメント・リンク

- [アプリ概要](docs/アプリ概要.md)
- [開発・更新履歴](docs/CHANGELOG.md)
- [プライバシーポリシー](docs/プライバシーポリシー.md) / [免責事項・利用規約](docs/免責事項・利用規約.md)
- [運営者情報・連絡先](docs/運営者情報.md)  
  不具合報告: https://forms.gle/UB8kZHd4VHenmRUN6  
  リポジトリ: https://github.com/32Lwk

## 免責事項

本システムは情報提供を目的としており、医療アドバイスではありません。医薬品の使用や症状が重い・長引く場合は、薬剤師・登録販売者または医療機関に相談してください。
