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

## 推奨本番セット（例）

7分発表・10枚構成。各スライドで1案を選び PowerPoint / Keynote に取り込む。

1. `slide01-title-A` — タイトル（参考レイアウトに最も近い）
2. `slide02-problem-A` — 課題
3. `slide03-solution-D` — ソリューション（3カラム）
4. `slide04-demo-A` — デモ
5. `slide05-scoring-B` — ルール + LLM
6. `slide06-pipeline-A` — パイプライン
7. `slide07-multiagent-A` — エージェント図
8. `slide08-safety-A` — 5層防御
9. `slide09-techstack-B` — クラウド構成
10. `slide10-summary-C` — クロージング（参考レイアウト踏襲）

## 注意（生成AI画像）

- 日本語テキストは誤字・崩れがあり得る → 本番前に目視確認、PowerPoint で差し替え推奨
- QRコードは実URLで再生成すること
- 技術図スライドも**同一パレット**で統一（暗色テーマに戻さない）

## 正本ドキュメント

- `docs/ARCHITECTURE_MULTI_AGENT.md`
- `docs/SECURITY_IMPLEMENTATION.md`
- `docs/FASTAPI_ARCHITECTURE.md`
- `docs/アプリ概要.md`
