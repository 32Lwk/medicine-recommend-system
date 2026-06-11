# 技育祭プレゼン — スライド画像仕様

技術面中心のプレゼン用スライド。**各スライド5案（A〜E）**、計50枚。  
生成: Cursor `GenerateImage`（**参考スライド1と同じやさしい医療パンフレット調**）。

## デザイン方針（`スライド1.PNG` 準拠）

| 項目 | 内容 |
|------|------|
| 比率 | 16:9（プレゼン投影想定） |
| 背景 | クリーム／和紙風の紙テクスチャ |
| 配色 | **セージグリーン・オリーブ・医療グリーン** + クリーム（`#e8ece4` 系） |
| レイアウト | 3カラム（左：セージパネル／中央：タブレット or 図／右：縦書き見出し） |
| タイポ | 見出し＝明朝（縦書き可）、本文＝ゴシック |
| 装飾 | 葉っぱの水彩イラスト、 pill＋吹き出しアイコン、細線アイコン |
| タブレットUI | 明るいグリーンのヘッダー、白／緑のチャットバブル |

### 避けるもの（旧版で乖離していた要素）

- ダークネイビー・ネオン・シアン／紫のサイバー風
- ガラスモーフィズム・DNA helix・六角グリッド
- テックカンファレンス風のグロー／Bloom

### 正本参考

- `チャット型医薬品推奨ツール_画像/スライド1.PNG`
- パレット指針: `.cursor/skills/medicine-about-redesign/SKILL.md`

## スライド一覧

| # | ファイル接頭辞 | テーマ | 案 |
|---|----------------|--------|-----|
| 01 | `slide01-title-` | タイトル・一言概要 | A〜E |
| 02 | `slide02-problem-` | 課題・背景 | A〜E |
| 03 | `slide03-solution-` | 解決策（ハイブリッド） | A〜E |
| 04 | `slide04-demo-` | デモ・UX | A〜E |
| 05 | `slide05-scoring-` | ハイブリッドスコアリング | A〜E |
| 06 | `slide06-pipeline-` | 処理パイプライン・SSE | A〜E |
| 07 | `slide07-multiagent-` | マルチエージェント | A〜E |
| 08 | `slide08-safety-` | 安全性・緊急対応 | A〜E |
| 09 | `slide09-techstack-` | 技術スタック・運用 | A〜E |
| 10 | `slide10-summary-` | まとめ・展望 | A〜E |

## 発表用本番セット（確定）

**`docs/archive/gikushosai/presentation_deck/`** に 01〜10 の PNG を配置済み。  
`スライド1.PNG` のデザイン（クリーム和紙・セージ・3カラム・明朝縦書き）に統一。

| # | ファイル | 内容 |
|---|---------|------|
| 1 | `01-title.png` | タイトル |
| 2 | `02-problem.png` | 課題 |
| 3 | `03-solution.png` | ハイブリッド解決策 |
| 4 | `04-demo.png` | デモ |
| 5 | `05-scoring.png` | スコアリング |
| 6 | `06-pipeline.png` | SSE・リアルタイム応答 |
| 7 | `07-multiagent.png` | マルチエージェント分岐 |
| 8 | `08-safety.png` | 緊急対応表 |
| 9 | `09-techstack.png` | フロント/バック構成 |
| 10 | `10-summary.png` | まとめ |

代替案は `docs/archive/gikushosai/presentation_images/`（55枚）を参照。

## 注意（生成AI画像）

- 日本語テキストは誤字・崩れがあり得る → 本番前に目視確認、PowerPoint で差し替え推奨
- QRコードは実URLで再生成すること
- 技術図スライドも**同一パレット**で統一（暗色テーマに戻さない）

## 正本ドキュメント

- `docs/dev/ARCHITECTURE_MULTI_AGENT.md`
- `docs/security/SECURITY_IMPLEMENTATION.md`
- `docs/dev/FASTAPI_ARCHITECTURE.md`
- `docs/public/アプリ概要.md`
