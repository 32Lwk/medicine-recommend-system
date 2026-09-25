# UX 現状分析・市場調査・PDCA 改善ポートフォリオ（2026-09-22）

**目的**: チャネル UI／Web ユーザー登録／Web サイト UI・UX を軸に、現状分析と方針策定のための広く深いリサーチを行い、辛口レビューと 12 サイクル以上の PDCA を経て施策ポートフォリオを確定する。

**NotebookLM**: [Research: Medicine Recommend UX・市場・チャネル 20260922](https://notebooklm.google.com/notebook/05dd0048-3a4d-4912-bd35-66c385a9a21d)

## 文書一覧

| # | ファイル | 内容 |
|---|----------|------|
| 01 | [01_EXECUTIVE_BRIEF.md](./01_EXECUTIVE_BRIEF.md) | 上司承認用 1 枚＋結論 |
| 02 | [02_MARKET_AND_COMPETITIVE.md](./02_MARKET_AND_COMPETITIVE.md) | 市場・規制・競合 |
| 03 | [03_INTERNAL_STATUS.md](./03_INTERNAL_STATUS.md) | 社内 UX 現状・ギャップ |
| 04 | [04_SUPERVISOR_HARSH_REVIEW.md](./04_SUPERVISOR_HARSH_REVIEW.md) | 部下レポートへの辛口評価 |
| 05 | [05_ADVERSARIAL_AND_PERSONAS.md](./05_ADVERSARIAL_AND_PERSONAS.md) | 敵対シナリオ・ペルソナ |
| 06 | [06_PDCA_12_CYCLES.md](./06_PDCA_12_CYCLES.md) | PDCA 12+ サイクルログ |
| 07 | [07_UX_PORTFOLIO_90DAY.md](./07_UX_PORTFOLIO_90DAY.md) | 施策ポートフォリオ・90 日計画 |
| 08 | [08_AGENT_SYNTHESIS.md](./08_AGENT_SYNTHESIS.md) | 並列エージェント完走後の統合・Bxx対応表 |

## 並列エージェント役割（すべて success）

| 役割 | Agent | 焦点 |
|------|-------|------|
| 市場・競合アナリスト | [市場](706d883e-05ba-4f40-87a6-77a7d1149a4e) | OTC / 規制 / 競合 |
| 社内現状監査官 | [監査](a3229cb1-31ed-439d-a08b-2eccf323dea1) | フラグ・非対称・負債 |
| マルチチャネル UX | [チャネル](215699c5-9613-4113-ae3d-e761e24550dd) | Web/LINE/handoff |
| ID・登録アーキテクト | [登録](09f85bed-df11-4c06-a6fb-5907a91456bf) | 匿名 vs 会員 |
| プロダクト UI デザイナー | [UI](4095e98d-ec2d-4336-9b3d-1b7aa3a20e9e) | Sage / About / プロト |
| 敵対的 UX 評価官 | [敵対](111ea617-8ef2-4e72-96ca-be4c14a4ab5f) | 攻撃シナリオ |
| ペルソナ委員会 | [ペルソナ](7ee93807-794d-4d0d-97de-a4782116a979) | 8 ペルソナ辛口 |
| a11y・高齢 UX | [a11y](14c72169-ceca-47f8-b1fe-74e0f3b52936) | WCAG / 高齢者 |
| PDCA ファシリテーター | [PDCA](68f021ad-f802-4e1c-9a34-f2f1074b0d67) | 12+ サイクル |
| 上司辛口レビュー | [上司](64a113c2-e563-4e0a-a2f7-870beb04bb31) | 主張の殺傷 |

## No-Go（全サイクル共通）

1. SafetyGate / crisis / emergency 検出の感度下げで FP を「直す」こと
2. 会員必須化でβの専門家評価導線を塞ぐこと
3. 待ち時間をアバターで隠蔽すること（遅延増幅）
4. 薬剤師要請を「実接続」と誤認させる文言
5. プラポリ未改定のままメール等の連絡先収集
