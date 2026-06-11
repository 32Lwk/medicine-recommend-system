# チャット欄パーティクル色ポリシー

## 背景

- チャット欄（`.chat-messages`）の**背景色は変更しない**（既定: `rgba(192, 192, 192, 1)`）。
- 医薬品相談 UI として、落下パーティクルは**黒・極暗色で沈まない**ようにする。

## ルール

1. **`#000` / `rgb(0,0,0)` は使用しない**（`particleColor` およびスプライトの主色）。
2. **粒子色（16 進 `#rrggbb`）の相対輝度（WCAG）を 0.55 未満にしない**（`PARTICLE_PROFILES` の選色・pytest で担保。クライアントは同等の下限に近い `sanitizeParticleColor` でフォールバック）。
3. **背景とのコントラスト比**は明色同士のため必ずしも高くならない。数値表と手順は `PARTICLE_CONTRAST_VERIFICATION.md`。
4. **絵文字粒子**は `particleColor` を CSS `color` で明示し、ブラウザ既定の黒に依存しない。あわせて `.snowflake-inner` に軽い `text-shadow` を当てる。

## 実装

- プロファイルは `src/core/season_manager.py` の `PARTICLE_PROFILES` / `get_particle_profile` で定義。
- クライアントは `static/js/main.js` の `createSeasonalParticles` で `prefers-reduced-motion: reduce` のとき粒子を生成しない。

## AI 生成スプライト

- 透明 PNG。暗い輪郭・黒ベタを避け、**淡色・中間色**を基調にする。
- 生成プロンプト・モデル・ライセンス注意は **`PARTICLE_AI_SPRITES.md`** に追記する。

## 関連ドキュメント

- `PARTICLE_CONTRAST_VERIFICATION.md` … 固定背景 #c0c0c0 との検証表・手順
- `PARTICLE_DECORATION_OK_NG.md` … 行事別の文化的配慮
- `STATIC_SEASON_ASSETS.md` … ディレクトリ規約
