# live2d-demo — Sage アバター デモの公開（Cloudflare Worker 静的配信）

公開先: https://live2d.medicine.yutok.dev （noindex・チャット本体とは無関係）

- 中身は `static/dev/avatar_demo.html` とアバターの JS / CSS / スプライト素材のコピー
- 読み上げはブラウザの Web Speech のみ（本番の `/api/tts` は呼ばない）
- `public/` は生成物（Git 管理外）

## デプロイ（手動）

```powershell
python scripts/build_live2d_site.py
cd workers/live2d-demo
npx wrangler deploy
```

初回デプロイでカスタムドメイン `live2d.medicine.yutok.dev`（ゾーン `yutok.dev`）の DNS と証明書が自動で作られる。

## 止めるとき

```powershell
cd workers/live2d-demo
npx wrangler delete
```
