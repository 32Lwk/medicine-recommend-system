# 季節装飾・粒子アセットの配置規約

## 左右装飾（チャット下部）

- **ルート**: `static/img/<base_path>/`（`SEASON_CONFIG[*].base_path`）。
- **例**: `winter/valentine/choco.png` → テンプレでは `img/winter/valentine/choco.png`。
- **行事専用ディレクトリ**: 七夕・敬老・ハロウィン・七五三などは `static/img/events/<行事名>/` にまとめ、`base_path` を `events/<行事名>` とする（淡色 PNG をリポジトリにコミット。生成記録は `docs/ui/PARTICLE_AI_SPRITES.md` の「左右装飾」節。任意のプレースホルダ再生成は `scripts/gen_event_decoration_pngs.py` でも可）。
- **alt**: `IMAGE_ALT_MAPPING` にファイル名を登録する。

## 落下パーティクル用スプライト

- **ルート**: `static/img/particles/<サブフォルダ>/`。
- **プロファイル**: Python のみ（`PARTICLE_PROFILES`）。JSON は `index.html` の `#particle-profile` 経由でクライアントへ渡る。
- **詳細**: `static/img/particles/README.md`。

## チャット欄背景

- **`.chat-messages` の `background` は季節ロジックで変更しない**（`rgba(192, 192, 192, 1)` を維持）。
