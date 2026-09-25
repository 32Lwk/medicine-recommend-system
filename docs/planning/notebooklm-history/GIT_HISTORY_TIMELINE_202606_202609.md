# Git 変更履歴タイムライン（2026-06 〜 2026-09）

- 生成日: 2026-09-22
- 範囲: `main`（`origin/main` よりローカル ahead 2 コミットあり）
- 月別コミット数（概算）: 2026-06 ≈94 / 2026-07 ≈130 / 2026-08 ≈36 / 2026-09 ≈3（〜09-21）

## 時代区分（監修用）

### 2026-06 — 基盤・セキュリティ・リモート再編

- GitHub 正本復帰・履歴分割・シークレット redaction（GCP ログ含む）
- 代表: `2f59caa` restore GitHub primary / `895ec11` security redact / `b48a337` GCP log sanitize

### 2026-07 — Chat Pipeline v2・Medicine QA・RAG・AWS 初期

- v2 パイプライン既定 ON、SSE/レイテンシ改善、Medicine QA・比較 Q&A
- Local RAG / Bedrock Managed KB / PMDA 取込・OTC 画像 R2
- Concierge 技術 FAQ（Amazon Q 風）・AWS staging / CodePipeline
- 代表: `c5c467d` default v2 ON / `77b823b` unified pipeline / `88d14b0` dual KB RAG / `74b7fde` AWS staging / `d24f4f7` 返信遅延 v3

### 2026-08 — AWS 本番寄り運用・クロスクラウド・Physical NLU

- AWS アカウント移行 `620992446973`、コスト削減（WAF 撤去・cold-start・Wake Worker）
- 比較 Q&A / Physical NLU / GPT E2E・レイテンシゲート
- GCP 非表示方針撤廃・contact channel / operator card
- 代表: `6a40759` AWS account migrate / `5881bdb` wake-on-access / `0f4e7fa` idle stop URL / `a33a34c` Physical NLU / `40c8a1f` AWS log sync（Claude 調査の基準コミット）

### 2026-09 — Jev IntentRouter 導入プログラム

| 日付 | コミット | 内容 |
| --- | --- | --- |
| 2026-09-20 | `7c5c662` | Jev 導入分析・eval harness |
| 2026-09-21 | `b536620` | Phase 1 local shadow（default OFF） |
| 2026-09-21 | `b706613` | Phase1C live eval PDCA / Focus next-flow |

#### 作業ツリー上の続き（未コミット含む・2026-09-22）

- Supervisor Round0〜Round4 並列エージェント（A–G）文書群
- Gate A-accuracy: **Not Passed**（live `20260922_012129`）
- Gate B+ / primary / staging / production: **Hard No-Go**
- 正本: `docs/planning/codex-parallel-jev-20260921/JEV_FINAL_SUPERVISOR_REPORT_20260922.md`

## Claude 調査（2026-09-14 @ `40c8a1f`）との接続

同時期の外部成果物（本パック）が示した継続課題:

1. スコアリング底上げで副作用・相互作用が最終順位に届かない
2. 年齢欄パース誤抽出（小児安全）
3. NSAID 重複警告のキー不一致
4. 推奨 p95 ≈24s → VH 導入前の性能前提
5. 改善ロードマップ Phase0 に「構造に触れない安全修正」を前倒し

これらは 7〜8 月の機能拡張（QA・RAG・AWS）の裏で残った品質負債として、Jev 導入とは別軸で監修対象。

## 直近コミット（抜粋）

詳細は `_git_log_raw.txt` を参照。上位の流れ:

```
b706613 2026-09-21 feat(jev): Phase1C live eval PDCA / Focus
b536620 2026-09-21 feat(routing): Jev Phase 1 local shadow OFF
7c5c662 2026-09-20 docs: Jev introduction analysis + eval harness
40c8a1f 2026-08-29 chore: AWS log exports / contest capacity
…（中略: AWS wake/cost, Physical NLU, SSE, RAG, Medicine QA）…
c5c467d 2026-07-22 feat: default v2 pipeline ON
74b7fde 2026-07-23 feat: AWS/Cloudflare staging rollout
```
