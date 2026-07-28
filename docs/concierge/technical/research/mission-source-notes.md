# 作成意図リサーチ — 公開 SSOT 執筆用メモ（R0）

> **公開可否**: 本ファイルは開発者向け。ユーザー回答の正本は `11-app-mission-and-status.md` と `docs/public/アプリ概要.md`。

## 一次ソース（公開向け）

| ソース | 抽出内容 | 公開 |
|--------|----------|------|
| `docs/public/アプリ概要.md` | 開発背景・利用目的・β現状・将来像 | OK |
| `docs/public/免責事項・利用規約.md` | 試験運用・非診断 | OK |
| `docs/concierge/technical/11-app-mission-and-status.md` | 作成意図 SSOT 要約 | OK |

## 二次ソース（mitou / 大会向け — 公開可能部分のみ）

| ソース | 公開可能な要点 | SSOT 反映 |
|--------|---------------|-----------|
| `docs/archive/mitou/docs/project_summary_800.md` | セルフメディケーション社会課題・ルール+LLM ハイブリッド | 11-app-mission |
| `docs/archive/mitou/docs/phase1_answers.md` | 開発動機（現場経験） | アプリ概要と整合済 |
| `docs/archive/mitou/docs/proposal_draft.md` | 潜在空間ベクトル・ハイブリッドスコア（将来研究） | 将来像のみ（未実装は明記） |

## 公開不可 / 回答に使わない

- 未踏申請の内部評価コメント（採択戦略）
- 個人連絡先の過度な詳細（運営者情報 SSOT・doc_operator プロンプトで制御）
- 内部 env 名・未公開 infra 詳細

## ギャップ（今後ヒアリング候補）

- ロードマップの具体的時期（公開 doc に無い場合は「検討中」）
- 企業連携の具体名（NDA 対象）
