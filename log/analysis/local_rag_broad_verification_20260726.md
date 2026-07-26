# Local RAG 広域検証レポート

実施日: 2026-07-26

## 概要

固定 fixture への過適合を避け、**新規 25 件の広域表現** + **GPT 生成マルチターン 13 件**で検証。実装は略語正規化・概念展開・文脈合成など **一般ルール** で拡張（fixture 文字列の直書きなし）。

## 結果サマリ

| スイート | 件数 | Pass | Pass% |
|---------|------|------|-------|
| **広域 fixture（新規）** | 25 | 25 | **100%** |
| GPT 会話シミュレーション | 13 | 10 | **76.9%** |
| **合計（broad + GPT）** | 38 | 35 | **92.1%** |
| 既存 diverse + context（回帰） | 52 | 52 | **100%** |
| 既存 LLM stress（回帰） | 68 | 68 | **100%** |
| 単体テスト | 27+ | 27+ | **pass** |

## 広域 fixture — style 別

| style | pass/total |
|-------|------------|
| slang（スラング・若者言葉） | 7/7 |
| abbreviation（APAP/ETOH/DXM 等） | 4/4 |
| indirect（比喩・間接表現） | 4/4 |
| typo（表記ゆれ） | 2/2 |
| english_mix | 3/3 |
| dialect | 3/3 |
| polite | 2/2 |

## GPT 会話シミュレーション

- **文脈 enrichment 率**: 12/13（92%）— `会話文脈:` / `直前:` / 大会→鼻薬ヒント
- **Pass**: 10/13
- **残 NG（3）**: GPT が意図とずれた発話を生成（例: 併用確認シナリオで用法質問、ドーピングで曖昧な「あれ」）。retrieve ロジックより **生成側のブレ** が主因。プロンプト厳格化で改善余地あり。

## 実装改善（一般化）

### `local_rag_query.py`
- `_COLLOQUIAL_REWRITES`: APAP/ETOH/IBU/DXM、混ぜ/ダブル、ムカつ、腹パン、イケる 等
- 概念展開: 固まりにくい血・サラサラ系
- カテゴリ: 単剤指示語+安全確認、酒+薬 interaction 優先、変な感じ/違和感、使用方法/どのように飲む
- `context_text` 引数で会話履歴を category 推論に反映

### `local_rag_context.py`
- 履歴最終 turn と query 重複除外
- 大会/マラソン文脈 + あれ/鼻薬 → ドーピング検索語付加
- 指示語 `あの`、推奨やつ、role プレフィックス除去

### `eval_local_rag_broad.py`（新規）
- 広域 fixture + GPT テンプレート会話 eval

## 結論

- **日常表現・略語・スラング・方言・敬語・英語混じり** は広域 fixture **25/25** で retrieve + category ともに問題なし。
- **マルチターン文脈** は固定 session eval **10/10**（回帰）+ GPT 生成 **10/13** でおおむね良好。GPT 生成 3 件は advisory。
- 本番 Ask 配線（Layer 3）は前回検証どおり **5/5** 維持。

## 成果物

- `tests/fixtures/local_rag_broad_eval.yaml`
- `tests/fixtures/local_rag_gpt_context_templates.yaml`
- `scripts/eval_local_rag_broad.py`
- `log/analysis/local_rag_broad_eval.json`
- `log/analysis/local_rag_broad_gpt_eval.json`
