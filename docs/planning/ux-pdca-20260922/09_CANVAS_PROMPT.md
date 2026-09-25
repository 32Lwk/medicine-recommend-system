# Canvas 作成用 AI 指示文（コピペ用）

以下のブロックを、Canvas を作れる Cursor Agent にそのまま貼り付けてください。

---

```
あなたは Cursor Canvas 作成エージェントです。
medicine-recommend の UX 調査・PDCA 成果を、チャット横で開ける視覚的ダッシュボード（.canvas.tsx）にまとめてください。

## 目的
意思決定者が 1 画面で把握できる「UX 改善方針ボード」を作る。
読む対象は経営・プロダクト・実装リード。長文レポートの再掲ではなく、構造・優先度・No-Go・90日計画を視覚化する。

## 必須スキル
1. `C:\Users\yutok\.cursor\skills-cursor\canvas\SKILL.md` を読む
2. `C:\Users\yutok\.cursor\skills-cursor\canvas\sdk\index.d.ts` で import 可能な API を確認する
3. データはすべてインライン埋め込み（fetch / ネットワーク禁止）
4. import は `cursor/canvas` のみ。相対 import・npm・Node 禁止
5. default export の React コンポーネント 1 つ
6. 色は `useHostTheme()` のトークンのみ（ハードコード hex 禁止）
7. 禁止: gradient / box-shadow / emoji 装飾 / 虹色だらけ / 全部同じ Card の壁

## 出力パス（厳守）
`C:\Users\yutok\.cursor\projects\d-Programing-medicine-recommend\canvases\ux-pdca-20260922.canvas.tsx`

既存の他 canvas は触らない。このファイルを新規作成（または同名なら上書き更新）。

## 正本データ（読んでインライン化する）
リポジトリ: `d:\Programing\medicine-recommend`

必ず読む:
- `docs/planning/ux-pdca-20260922/00_INDEX.md`
- `docs/planning/ux-pdca-20260922/01_EXECUTIVE_BRIEF.md`
- `docs/planning/ux-pdca-20260922/02_MARKET_AND_COMPETITIVE.md`
- `docs/planning/ux-pdca-20260922/03_INTERNAL_STATUS.md`
- `docs/planning/ux-pdca-20260922/04_SUPERVISOR_HARSH_REVIEW.md`
- `docs/planning/ux-pdca-20260922/05_ADVERSARIAL_AND_PERSONAS.md`
- `docs/planning/ux-pdca-20260922/06_PDCA_12_CYCLES.md`
- `docs/planning/ux-pdca-20260922/07_UX_PORTFOLIO_90DAY.md`
- `docs/planning/ux-pdca-20260922/08_AGENT_SYNTHESIS.md`

NotebookLM URL（キャプションに出典として記載可）:
https://notebooklm.google.com/notebook/05dd0048-3a4d-4912-bd35-66c385a9a21d

空セクション・「TODO」「No data」は出さない。データがあるセクションだけ描画する。

## 画面構成（この順番・この情報量）

### Hero（最上部・最大の視線）
- H1: 「UX PDCA 方針ボード — medicine-recommend」
- 副題: 2026-09-22 / チャネル・Web登録・サイトUI
- Callout（tone: danger または warning）で一文判決:
  「見た目刷新・必須会員・VHは却下。安全対称・待ち実測・軽量継続ID・選択移植が Must。」
- Stat 4つ横並び（Row/Grid）:
  1. Physical p95 ≈24s → 目標 <15s
  2. UX十二種: 本番未設定=OFF
  3. PDCA: 14 cycles（Kill/Pivot/Keep の件数を Pill または Stat で）
  4. Must 施策数（07 の Must 件数）

### Section A — スコープ地図
- 3カラム Grid: チャネル / Web登録 / サイトUI
- 各カラムに現状1行 + 方針1行（Pill で Keep/Pivot/Kill 感）
- 小さな Text で「意図的非対称は可。危険な非対称（Web pending medical cancel 欠落）は不可」

### Section B — 市場・規制（コンパクト）
- Table または Stat+Text:
  - OTC 生産 R6: 9,331億円 (+6.0%)
  - 広義市場/定義差の注意（インテージ前年割れ等は脚注）
  - 2026-05 薬機法: 要指導オンライン（薬剤師ビデオ）／指定濫用防止
  - 競合: 有人薬局アプリ vs AI相談 vs 汎用LLM → 自社は「診断しない中間層」
- Callout: 「市場が大きい≠今すぐ会員・VH。βのKPIは安全実証と専門家評価」

### Section C — 致命ギャップ Top（視覚優先）
- Table（列: # / ギャップ / 種別 / 90日位置）
- 最低8行、最大12行。03 と 08 の Top / B01–B05 を優先
- TableRowTone で安全系を danger/warning に

### Section D — PDCA サマリー
- 2カラム:
  - Kill した方針（必須会員、5秒約束、全フラグON、VH、全面リデザイン、進捗alone、Safety弱体化、ダッシュボード化）
  - Keep した方針（安全対称、確認ラダー、handoff永続化、待ち実測+正直表示、登録再ブランド、出口CTA、選択移植36/39/44）
- 可能なら BarChart: Kill / Pivot / Keep の件数（タイトル・軸ラベル必須）
  Caption: Source: docs/planning/ux-pdca-20260922/06_PDCA_12_CYCLES.md

### Section E — MoSCoW + 90日タイムライン
- UsageBar または segmented 表示: Must / Should / Could / Won't の件数比
- TodoList または Table で W0→W3:
  - W0 (0–2w): medical cancel / 緊急文言方針 / handoff失効UX / 薬剤師デモ明示
  - W1 (3–6w): LATENCYカナリア / 待ち3-8-15s / UX十二種カナリア / handoff Redis
  - W2 (7–10w): プロフィール再ブランド / 同意サーバ / 確認ラダー+出口CTA
  - W3 (11–13w): 36/39/44移植 / About入口 / 多言語誠実化 / a11y P0
- Pill: Must=必須, Should=推奨, Won't=90日禁止

### Section F — No-Go（赤く目立たせるが虹色にしない）
- Callout danger リスト（5項目、00_INDEX の No-Go）
- 追加1行: 「soft FP 改善を理由に SafetyGate を弱める PR は No-Go」

### Section G — 決裁が必要な3問
- Checkbox 風ではなく、番号付き Stack:
  1. Physical KPI を <15s に再合意するか / <5s を残すか
  2. LINE Login を 90日 Could のままか W2 前倒しか
  3. 本番カナリア ALLOWLIST 対象
- 下部 Text: 「承認後の第一実装 = W0-1 Web pending medical cancel 対称化」

### Footer
- 出典パス一覧（短い Text）
- NotebookLM ノート URL
- 「詳細は docs/planning/ux-pdca-20260922/」

## インタラクション（任意・推奨）
- `useCanvasState` でタブ切替: Overview | Gaps | PDCA | Roadmap
  （タブごとに上記 Section を出し分けてもよい。初期は Overview）
- フィルタ不要ならシングルページ縦スクロールでよい（無理に複雑化しない）

## デザイン指針
- Sage Terrace の世界観を模倣しすぎない（Canvas はホストテーマ準拠）
- 最初のビューポートで「判決 + 4 Stats」が読めること
- Card は重要な塊だけ。表やリストは open section も混ぜる
- チャートがある場合は title・axis・legend・caption を完備
- 日本語 UI ラベル

## 完了条件
1. 指定パスに `.canvas.tsx` が存在する
2. Canvas TypeScript check がエラーなし
3. チャット応答で、その canvas ファイルへの markdown リンク（絶対パス）を1つ提示する
4. 「チャットの横で開ける」と一文案内する
5. 中身がプレースホルダだらけでない（実データ埋め込み）

## やらないこと
- リポジトリのアプリコード改修
- Markdown レポートの全面再生成
- 新しい調査のやり直し（既存 docs を正本にする）
- 絵文字アイコン
```

---

## 使い方

1. 新しい Agent チャットを開く  
2. 上記コードフェンス内をすべて貼る  
3. 必要なら末尾に一言: 「作成後、Overview タブが最初に見えるか確認して」  

短縮版が欲しければ「Hero + Gaps + Roadmap の3セクションだけ」と追記してください。
