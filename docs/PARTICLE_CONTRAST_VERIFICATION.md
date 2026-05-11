# 固定チャット背景に対する粒子色の検証

## 前提

- **チャット欄背景**（`.chat-messages`）は **`rgba(192, 192, 192, 1)`（#c0c0c0）固定**。季節で変えない。
- **粒子の絵文字色**は `particleColor`（CSS `color`）で指定。**`#000` / `rgb(0,0,0)` は禁止**。
- **相対輝度（WCAG の定義）**で粒子色の「暗さ」を担保する（実装・pytest では **粒子色の相対輝度 ≥ 0.55** を下限とする）。クライアントは `sanitizeParticleColor` でこれに近いクランプを行う。

## コントラスト比について

背景と粒子は**いずれも明色**のため、**コントラスト比は低め**になりやすい（装飾粒子として許容し、可読性は主にメッセージ本文側で担保）。記録用に **#c0c0c0 上でのコントラスト比**を併記する。

## 検証手順（再現）

1. `PARTICLE_PROFILES` の各 `particleColor` を取得する（`get_particle_profile` 経由でも可）。
2. 背景を **sRGB #c0c0c0** とみなし、WCAG の相対輝度 \(L\) を各 16 進色について計算する。
3. コントラスト比は \((L_{\max}+0.05)/(L_{\min}+0.05)\)（`tests/test_season_manager_particles.py` 内のヘルパーと同じ式）。

## 代表値（初版・2026-05）

| プロファイル鍵 | particleColor | 粒子側相対輝度 \(L\)（約） | 対 #c0c0c0 コントラスト比（約） |
|----------------|---------------|---------------------------|--------------------------------|
| fallback_winter | #ffffff | 1.00 | 1.82 |
| fallback_spring | #fff8e1 | 0.94 | 1.71 |
| valentine | #fce4ec | 0.82 | 1.51 |
| autumn | #ffe0b2 | 0.78 | 1.43 |
| setubun | #efebe9 | 0.84 | 1.54 |

全キーは pytest `test_particle_colors_luminance_floor` で **\(L \geq 0.55\)** を満たすことを確認する。

pytest の `EXPECTED_PARTICLE_CONTRAST_VS_CHAT_BG`（`test_particle_contrast_ratio_snapshot_vs_chat_bg`）で、各 `particleColor` と **#c0c0c0** のコントラスト比をスナップショット固定している（配色意図の変更時のみ更新）。
