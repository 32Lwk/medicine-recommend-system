# 季節パーティクル用スプライト

- **置き場所**: `static/img/particles/<イベントまたは汎用名>/` に **PNG（32bit 透明推奨）** を置く。
- **参照**: `src/core/season_manager.py` の `PARTICLE_PROFILES[*]['sprites']` に `path`（例: `img/particles/valentine/heart-glow.png`）と任意の `weight` を記載する。
- **命名**: ASCII の小文字＋ハイフン（`heart-glow.png`）を推奨（URL・ログの可読性のため）。
- **生成**: 本番では画像 API を呼ばない。開発時に **Cursor の画像生成**などで PNG を作り、本ディレクトリへコミットする（プロンプトは `docs/ui/PARTICLE_AI_SPRITES.md`）。
