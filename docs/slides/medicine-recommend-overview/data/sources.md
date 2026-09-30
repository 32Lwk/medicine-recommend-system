# 出典

docs/slides/medicine-recommend-overview/data/sources.json から build-sources.mjs で作る（手で直さない）。 リンクの確認 2026-09-30。

## 一次調査

| № | 調査 | だれ・何人 | いつ | 方法 | 記録 | 使うページ |
|---|---|---|---|---|---|---|
| P1 | 収録データ（市販薬・飲み合わせ・副作用・効能・辞書・画像） | このリポジトリ | 2026-09 | data/ の CSV・JSON を calc.py で集計 | data/otc_medicine_data.csv ほか | summary, problem, data, a-db, a-inter, a-dict, a-import |
| P2 | 推薦のオフライン点検（600件） | 開発者 | 2026-09-30 | 規則だけで実行（AIなし）。scripts/eval_reco_offline_safety.py | log/analysis/2026-09-30_reco_offline_eval.md・.json・_before_fix.* | summary, eval, eval2, risk, a-gate, a-tie, a-inter, a-dict, a-eval-method, a-eval-metrics, a-eval-all, a-eval-emer, a-eval-limits |
| P3 | 開発の履歴 | このリポジトリ | 2025-10〜2026-09 | git log・ファイル数の集計 | git の履歴（calc.py の dev_stats） | summary, track, a-agents, a-hist |
| P4 | Jev による意図の判定の試験 | 開発者 | 2026-09-21〜24 | 10 の場面 × 3 回の比較と、安全の関門の判定 | docs/planning/codex-parallel-jev-20260921/ | jev, a-jev-what, a-jev-lat, a-jev-gate |
| P5 | AWS 検証環境の費用計画と実績 | 開発者 | 2026-08-07 更新 | 見積もりと請求の実績 | docs/ops/AWS_COST_PLAN.md | arch-aws, a-aws, a-env, a-cost |
| P6 | 画面の撮影 | 開発者 | 2026-09-30 | ローカル環境をブラウザで操作して撮影 | docs/slides/medicine-recommend-overview/screens/ | cover, screens1, screens2, risk, a-llm, a-scr-safety, a-scr-a11y |
| P7 | コードと利用規約 | このリポジトリ | 2026-09 | 重み・部品・規約の原文 | src/security/enhanced_safety_checker.py・src/agents・src/content/about_modal_html.json | pipeline, scoring, safety, a-flow, a-pipe, a-agents, a-weights, a-exclude, a-privacy, a-license |

## 外部の資料

### 01 課題と解決

| № | 発行者「資料名」 | 日付 | URL | 使うページ |
|---|---|---|---|---|
| 1 | e-Gov 法令検索「医薬品、医療機器等の品質、有効性及び安全性の確保等に関する法律 第36条の10」 | 2026 | https://laws.e-gov.go.jp/law/335AC0000000145 | problem, a-law |
| 2 | 厚生労働省「薬事工業生産動態統計調査 令和6年 年報（一般用医薬品の生産金額）」 | 2025 | https://www.mhlw.go.jp/toukei/list/105-1.html | market |
| 3 | 総務省統計局「人口推計（2024年10月1日現在）」 | 2025-04 | https://www.stat.go.jp/data/jinsui/2024np/index.html | market |
| 4 | 日本政府観光局（JNTO）「訪日外客統計（2024年）」 | 2025-01 | https://statistics.jnto.go.jp/ | market |

### 02 しくみ

| № | 発行者「資料名」 | 日付 | URL | 使うページ |
|---|---|---|---|---|
| 5 | 医薬品医療機器総合機構（PMDA）「一般用医薬品・要指導医薬品 情報検索」 | 2026 | https://www.pmda.go.jp/PmdaSearch/otcSearch/ | data, a-import |

### 04 これから

| № | 発行者「資料名」 | 日付 | URL | 使うページ |
|---|---|---|---|---|
| 6 | PolyForm Project「PolyForm Noncommercial License 1.0.0」 | 2019 | https://polyformproject.org/licenses/noncommercial/1.0.0/ | business, a-license |

## 前提の一覧

| ID | 数字 | 置いた値 | 状態 | 置き方・理由 | 計算の場所 | 使うページ |
|---|---|---|---|---|---|---|
| A1 | いまの運用費 | 約3,000円/月 | 仮置き | 開発者の申告（2026-09-30）。本番・検証・AIの合計で、内訳は未集計 | calc.py の COST_MONTHLY_YEN | business, a-cost |
| A2 | 検証環境の月額 | 止めておくと $6〜7、ずっと動かすと $31〜32 | 推計 | AWS の費用計画の見積もり（一次調査 P5）。実績は 2026-08-01〜07 の $1.28 | calc.py の AWS | arch-aws, a-aws, a-cost |
| A3 | 困りごと・使われる場面 | 夜・読みにくさ・言葉の壁 | 仮置き | 開発者の店頭での経験から置いた仮説。利用者での実証はこれから | 本文 | problem, market |
| A4 | 似たサービスの整理 | 5つの相手 | 推計 | 2026年9月時点の内部の整理（docs/planning/ux-pdca-20260922/02_MARKET_AND_COMPETITIVE.md） | 本文 | a-comp, a-pos |
