# 会話品質 — 横断サマリ（Wave A: conversation_quality）

**環境:** `medicine-recommend-dev`（GCP Cloud Run）  
**期間:** 2026-07-26 06:08 UTC ～ 2026-07-28 04:49 UTC  
**データソース:** `downloaded-logs-20260726-20260728-20260728-044951.json`（36,910 エントリ）

---

## エグゼクティブサマリ（最大5項目）

- 🟢 **9セッション中8が `good`、1が `acceptable_with_issues`** — `counseling_detail` 14件・trace-only 0。返信本文は概ね復元済み（Wave B で LLM 再評価推奨）。
- 🟡 **ヒューリスティック intent mismatch は1件のみ** — `1785057159607653291042` の「やあこんちは」で `greeting_to_non_greeting`（input_labels=`general` vs concierge=`greeting`）。実入力は挨拶だがラベル分類の不一致が警告を誘発。
- 🔴 **極端な遅延ターンが複数** — 最大 **351.8s**（画像リクエスト）、**160.5s**（医薬品比較）、**77.8s**（Physical 推奨）。LLM 合計は数秒～25s 程度で、**safety_gate 以降の待ち・rule_based スコアリング・クライアント側待ち**がボトルネック。
- 🟡 **triage と shadow route の不一致（gate_improvement）** — 「ロキソニンとイブの画像見せて」3回中、triage が `Other/general_other` のとき shadow は `Physical/medicine_qa` を提案。4回目（別セッション）で `Ask/medication_identification` に修正され mismatch 解消。
- 🟡 **開発・QA トラフィック主体** — dev トークン `mrcdev…` のシステムエラー2セッション、インフラ/architecture 質問（AWS/GCP、GitHub/GitLab）、画像生成・暴言ブロックなど。本番ユーザー相当の長期相談は `喉が痛いです。` 1件のみ。

---

## セッション一覧

| session_id（末尾6桁） | channel | turns | grade | 主な論点（issues） |
|----------------------|---------|------:|-------|-------------------|
| `…3291042` | web | 7 | **acceptable_with_issues** | greeting mismatch×1；暴言「しね」ブロック；画像リクエスト3回（triage 不一致・351s 遅延）；blocked 入力1件 |
| `…5935322` | web | 1 | good | AWS/GCP → `architecture` concierge；~16.6s |
| `…2837424` | web | 2 | good | 挨拶→architecture 質問；2ターン目応答空（別 sid に routing） |
| `…934393` | web | 2 | good | dev トークン → システムエラー（~1.6s） |
| `…759270` | web | 2 | good | dev トークン → システムエラー（~1.2s） |
| `…689258` | web | 2 | good | 画像リクエスト；trace **351.8s**（safety_gate 後 ~342s 空白） |
| `…822001` | web | 2 | good | 画像リクエスト；triage=`Ask/medication_identification`（正）；~12.3s |
| `…131055` | web | 1 | good | Physical `sore_throat`；rule_based 推奨 **~77.8s**；推奨イベント23件 |
| `…553845` | web | 6 | good | 医薬品比較→GitHub/GitLab→フォロー「どっち」；160s/45s/30s 遅延；最終ターンは文脈解釈良好 |

**集計:** セッション 9 / ターン 25 / trace-only 0 / chat_flow trace 14 / counseling_detail 14 / heuristic_mismatch 1

**grade 分布:** `good` 8 / `acceptable_with_issues` 1

---

## 意図不一致（intent mismatches）

### ヒューリスティック（conversation 品質）

| session | 入力 | issue_type | severity | 概要 |
|---------|------|------------|----------|------|
| `1785057159607653291042` | やあこんにちは | `greeting_to_non_greeting` | warning | input_labels=`general` なのに concierge=`greeting` で挨拶テンプレ返却。実入力は挨拶のため **false positive 疑い**（Wave B でラベラー確認） |

### dialogue_route shadow（gate_improvement）

「ロキソニンとイブの画像見せて」で triage=`Other/general_other` のとき、shadow が `Physical/medicine_qa`（confidence 0.94）を提案 — **実行 route との差分**（3 trace）。  
別セッション `1785058927087582422001` では triage=`Ask/medication_identification` となり shadow mismatch なし。

### 文脈フォローアップ（品質上の論点・heuristic 外）

| session | 入力 | 期待 | 観測 |
|---------|------|------|------|
| `1785205185643537553845` | このサービスはどっちなの？ | GitHub/GitLab 文脈 | 最終応答は医薬品 vs 非医薬品の切り分けで妥当。中間ターンは medicine_qa 経路（`select_symptoms` 呼び出し）— Wave B で応答品質確認 |

---

## 遅延ターン（slow turn patterns）

`slow_traces_ge_8s`: **9 / 14 trace**（≥8s 閾値）

### パターン別

| パターン | 代表入力 | total_ms | 主因（breakdown） | LLM |
|----------|----------|---------:|-------------------|-----|
| **A. safety_gate 支配** | やあこんにちは | 22,448 | safety_gate ~12.3s + triage ~6.6s | 7 calls / ~8.2s |
| **B. safety_gate + concierge** | AWS/GCP, GitHub/GitLab | 16,563 / 44,693 | safety_gate ~7.7–25.9s；concierge_build ~2.3–9.8s | 2–6 calls |
| **C. triage 2段 + QA** | ロキソニン画像（通常） | 12,324–15,062 | triage stage1+2 ~3–4.5s；safety_gate ~5.2s | 1–3 calls |
| **D. safety_gate 後の長時間空白** | ロキソニン画像（retry） | **351,778** | safety_gate_done @9.1s → 2nd perf @351s。**LLM 2 calls のみ** — タイムアウト/再送/ストリーム待ち疑い | 2 calls / ~2.9s |
| **E. safety_gate 後の answer 遅延** | ロキソニン vs イブ | **160,502** | safety_gate @15.6s → answer_stream LLM @142s 後。**中間 ~145s 未計測** | 4 calls / ~6.8s |
| **F. rule_based Physical** | 喉が痛いです。 | **77,819** | safety_gate ~20s；nlu_batch ~3.9s；rb_scoring ~12.8s；rb_explain_batch ~15.3s | 12 calls / ~25.5s |
| **G. medicine_qa + missing_info** | このサービスはどっち | 29,846 | rb_missing_info ~13.7s；focus_llm 多数 | 8 calls / ~9.1s |

### 早期終了（対照）

| 入力 | total_ms | 備考 |
|------|---------:|------|
| しね | 2,055 | triage=null、LLM 0 — 暴言ブロック |
| mrcdev… | 1,184–1,596 | dev トークン、LLM 0 — 即エラー |

### 横断所見

- **LLM レイテンシ合計は通常 3–25s** に収まるが、**pipeline total が 30s～352s** になるケースは LLM 以外（safety_gate、rule_based スコアリング、ストリーム/クライアント待ち、再試行）が支配的。
- 挨拶1ターンで **focus_llm が3回** 走るなど、非 Physical 入力でも medicine_qa 副次呼び出しが latency/cost を押し上げている。
- HTTP **429×18**（metadata/quality_metrics）— レート制限が遅延・再試行の一因の可能性（D/E パターン）。

---

## セッション横断の共通パターン

### 1. データ品質（前回期間との改善）

| 指標 | 値 |
|------|-----|
| `trace_only_session_count` | 0 / 9 |
| `counseling_detail_count` | 14 |
| `response_missing`（主要ターン） | 少数（conversation_history の render 名 `sage_qa`/`sage_status` はプレビュー表記） |

`counseling_detail` から返信本文が取得でき、Wave A 横断評価が可能。

### 2. 意図カテゴリ分布（14 chat_flow trace）

| triage category | 件数 | 備考 |
|-----------------|-----:|------|
| Other/general_other | 9 | 挨拶・architecture・画像（誤分類含む） |
| Ask/* | 3 | medication_difference, medication_identification |
| Physical/sore_throat | 1 | 本番相当の症状申告 |
| triage=null | 2 | 暴言・dev トークン |

concierge 経路: `greeting`(2), `architecture`(2)。残りは medicine_qa / rule_based / security 短絡。

### 3. Physical 推奨

- `physical_sessions_with_advisor_hook`: 1（`1785075195430764131055`）
- `physical_recommendation_log_events`: 23
- rule_based パイプライン（missing_info → scoring → explain_batch → carousel）が **~73s** まで伸びる典型例

### 4. セキュリティ・暴言

- 「しね」→ 2s でブロック、適切な拒否メッセージ
- blocked 入力（admin_only）も別途記録

### 5. 開発トラフィック

- `mrcdev00000000000001` ×2セッション — `system_error` sage_status
- architecture 質問（AWS/GCP, GitHub/GitLab）は concierge `meta_architecture` で応答

---

## 重要度別所見

| 重要度 | 所見 |
|--------|------|
| 🔴 critical | 351s / 160s 級の pipeline 遅延 — safety_gate 以降の未計測区間が UX を著しく損なう。原因切り分け（429 再試行・ストリーム・DB）要 |
| 🟡 warning | 画像リクエストの triage 不一致（Other vs Ask/medication_identification）— 3回失敗後に正分類 |
| 🟡 warning | 挨拶ターンで focus_llm 3–4回 — 不要な medicine_qa 副次呼び出し |
| 🟡 warning | HTTP 429×18 — dev 環境レート制限 |
| 🟢 info | 8/9 セッション good；暴言・dev トークン処理は妥当 |
| 🟢 info | フォロー「このサービスはどっち」— 最終応答で GitHub/GitLab を非対象と明示（文脈理解良好） |

---

## 推奨アクション

1. 🔴 **351s / 160s 遅延の調査** — `pipeline_perf` breakdown に safety_gate_done 以降のフェーズを追加。429 ログと突合。
2. 🟡 **画像リクエスト triage** — `product_image` / `medication_identification` への early routing 強化（gate_improvement shadow 3件）。
3. 🟡 **挨拶 fast path** — greeting 確定時の focus_llm スキップで ~22s → 短縮余地。
4. 🟡 **input_labels ラベラー** — 「やあこんにちは」を `greeting` に — false positive mismatch 解消。
5. 🟢 **Wave B** — 9セッション個別 LLM 再評価。特に Physical 1件は `medicine-recommendation-advisor` 必須。

---

## 参照

- `quality_metrics.json`: session 9, good 8 / acceptable_with_issues 1, heuristic_mismatch 1, counseling_detail 14
- `metadata.json`: primary_service=`medicine-recommend-dev`, 36,910 entries, ERROR 1, WARNING 24
- `sections/chat_flow.json`: trace 14, slow_traces_ge_8s 9
- `sections/user_sessions.json`: intent_mismatches 1, physical_recommendation_log_events 23

**Wave B 委譲:** セッション別ターン表・返信内容評価・推奨品質レビューは `draft_session_*.md` で実施。
