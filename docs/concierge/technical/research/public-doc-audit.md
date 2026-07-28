# docs/public/ 監査 — Meta KB 対象 7 件（R0）

> 監査日: 2026-07-28。横断 retrieve / `generate_doc_answer_text` の根拠確認。

| ファイル | 行数目安 | intent | doc_type | 直接 intent 回答 | RAG pool | 備考 |
|----------|-----------|--------|----------|-----------------|----------|------|
| `アプリ概要.md` | ~150 | doc_app_overview | overview | ○ | ○ | 作成意図 SSOT 補完: 11-app-mission |
| `プライバシーポリシー.md` | ~200 | doc_privacy | legal_privacy | ○（全文参照） | ○（横断のみ） | 条項 paraphrase 禁止 |
| `免責事項・利用規約.md` | ~180 | doc_terms | legal_terms | ○（全文参照） | ○ | 薬機法 meta → doc_terms |
| `医薬品相談先.md` | ~80 | doc_consultation | consultation | ○ | ○ | PMDA/#7119 必須 |
| `運営者情報.md` | ~60 | doc_operator | operator | ○ | ○ | 個人特定情報は開示ポリシー準拠 |
| `会社向け概要書類.md` | ~120 | — | enterprise | △（RAG+深掘り） | ○ | enterprise_overview |
| `企業向け簡略版概要資料.md` | ~80 | — | enterprise | △ | ○ | 同上 |

## cross-doc 質問 taxonomy（横断 retrieve）

| パターン | 例 | 主 intent | 参照 doc |
|----------|-----|-----------|----------|
| データ×プライバシー | 「チャット保存とプライバシー」 | architecture | 04-data-security + プライバシー |
| β×利用規約 | 「β版 試験運用 条件」 | doc_terms | 免責 + アプリ概要 |
| 作成意図×技術 | 「なぜ作った？ルールベースは？」 | doc_app_overview | 11 + アプリ概要 |
| 相談×免責 | 「診断と相談窓口」 | doc_consultation | 医薬品相談先 + 免責 |
| 企業×概要 | 「導入事例 会社向け」 | architecture | enterprise + アプリ概要 |

## ギャップ

- enterprise doc に専用 intent なし → architecture / capabilities で RAG 補助
- 運営者個人情報: doc_operator プロンプトでマスク済み

## eval カバレッジ

- retrieve: `concierge_kb_legal_meta.yaml`（10問）
- intent: `concierge_intent_routing.yaml`（法務 8 + 境界 5）
- quality: `concierge_technical_quality.yaml`（法務/概要 15問）
