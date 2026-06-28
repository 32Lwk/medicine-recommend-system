# セッション深掘り分析（Wave B）

**session_id**: `line:U20a3beee49563dcd07bb3dd0fc1ca32c`  
**分析元**: `log/analysis/downloaded-logs-20260626-20260627-20260627-162735/sections/user_sessions.json`  
**transcript**: `sessions/line_U20a3beee49563dcd07bb3dd0fc1ca32c.md`  
**生成日**: 2026-06-28  
**環境**: medicine-recommend-dev（GCP Cloud Run ログ export）

---

## 1. セッションメタデータ

| 項目 | 値 |
|------|-----|
| チャネル | line |
| 時間範囲 | `2026-06-26 16:01:10` ～ `2026-06-27 07:51:20`（ログ UTC 相当） |
| ターン数 | 35 |
| ヒューリスティック総合評価 | **good**（参考のみ） |
| **LLM 総合評価** | **poor** |
| ターンソース内訳 | chat_flow=35（**trace-only**） |
| response_missing | **35 / 35 ターン**（100%） |
| セッション特性 | 開発者・QA 的プロービング。挨拶・攻撃的入力・履歴/セッション操作・メタ質問（アーキテクチャ）・Physical/Emergency 症状の混在 |

### physical_recommendation_summary / medicine_recommendation_review

| 項目 | 値 |
|------|-----|
| physical_turn_count | 5（ねむい / 頭痛い / 39度の熱 / 胸痛みではなくない？ / 胸が痛い） |
| recommendation_event_count | **0**（全 Physical ターンで推奨イベント未記録） |
| has_medicine_list | 全ターン false |
| advisor 照合 | 推奨品リストがログに存在しないため **CSV/PMDA 照合は N/A**。ルーティング・欠損情報収集・Emergency 短絡のみ評価 |

**medicine-recommendation-advisor 所見（ルーティング・安全面）**

| ターン | 入力 | トリアージ | 所見 |
|--------|------|-----------|------|
| 4 | ねむい | Physical/drowsiness 0.98 | PhysicalOrchestrator + NLU batch 実行。推奨未到達は追加質問フェーズの可能性あり。**返信未記録のため UX 未検証** |
| 11 | 頭痛い | **なし**（triage_ms=null） | 🔴 Physical 症状なのにトリアージ未実行（1.5s 短絡）。推奨フロー完全スキップの疑い |
| 13 | 39度の熱 | Physical/fever 0.99 | PhysicalOrchestrator + `missing_info_service`。39°C は高熱 — **受診・緊急度案内**が応答に含まれるか要確認。推奨イベント 0 |
| 25 | 胸痛みではなくない？ | Other/general_other | 🔴 `physical_symptom` ラベル付きなのに `redirect`。前ターン「心の病」文脈で誤ルートの可能性 |
| 27 | 胸が痛い | Emergency/keyword_match 0.95 | triage 3.4ms・LLM 0 回 — **Emergency キーワード短絡は妥当**。OTC 推奨不要。119/受診案内の有無は返信未記録 |

---

## 2. エグゼクティブサマリ

- **trace-only セッション**: `counseling_detail` 0 件のため全ターン返信本文が欠落。ルーティング・E2E・LLM path のみ評価可能。
- **ヒューリスティック good ≠ 品質 good**: issue_count=0 だが、Physical 症状スキップ（T11）、session_admin 未ハンドオフ（T9/T21/T28）、メタ質問の counseling 誤ルート（T29）など **LLM 再判定で複数 critical**。
- **Physical フロー**: 5 症状ターンすべて `recommendation_event_count=0`。T4/T13 は PhysicalOrchestrator 到達、T11 はトリアージ未到達、T27 は Emergency 短絡。
- **攻撃的入力**: T5「しね」はセキュリティ短絡（LLM 0、1.5s）— 妥当と推定。
- **メタ/アーキテクチャ**: T30–32 は `concierge_agent.meta_architecture` で妥当。T35「トリアージエージェントのスペック」は `redirect` — **architecture 期待**。
- **推奨アクション**: (1) dev で counseling_detail 全文ログ有効化、(2) Physical 短絡経路（T11）調査、(3) session_admin 意図の handoff 統一、(4) meta_follow_up → architecture 優先。

---

## 3. 全会話テーブル（全35ターン・LLM 再判定付き）

| # | ユーザー送信 | ボット返信時刻 | ユーザー入力 | ボット返信 | E2E (ms) | Pipeline (ms) | 前ターン間隔 | handoff / route | LLM判定 | 意図ずれ |
|---|-------------|----------------|--------------|------------|----------|---------------|-------------|-----------------|---------|----------|
| 1 | 16:00:57 | 16:01:10 | はーわーく | **ログ未記録** | 13,323 | 13,323 | — | OtherHandler / greeting | 🟡 ok* | なし |
| 2 | 18:59:47 | 18:59:59 | こに | **ログ未記録** | 12,628 | 12,628 | 10.7h | OtherHandler / greeting | 🟡 ok* | なし |
| 3 | 19:00:01 | 19:00:11 | ははは | **ログ未記録** | 9,699 | 9,699 | 12s | OtherHandler / greeting | 🟡 ok* | なし |
| 4 | 19:00:14 | 19:00:23 | ねむい | **ログ未記録** | 8,938 | 8,938 | 12s | PhysicalOrchestrator / Physical·drowsiness | 🟡 warning | 軽微 — Physical 到達も推奨イベント 0 |
| 5 | 19:00:32 | 19:00:34 | しね | **ログ未記録** | 1,496 | 1,496 | 11s | （セキュリティ短絡） | ✅ good* | なし（攻撃的入力ブロック推定） |
| 6 | 19:00:51 | 19:01:01 | おーい | **ログ未記録** | 10,186 | 10,186 | 27s | OtherHandler / greeting | 🟡 ok* | なし |
| 7 | 19:01:03 | 19:01:07 | 履歴要約して | **ログ未記録** | 3,583 | 3,583 | 6s | session_agent.summarize | ✅ good* | なし |
| 8 | 19:01:20 | 19:01:28 | わた | **ログ未記録** | 8,698 | 8,698 | 22s | OtherHandler / greeting | 🟡 ok* | なし |
| 9 | 19:01:33 | 19:01:40 | 履歴って消せるの？ | **ログ未記録** | 7,436 | 7,436 | 12s | session_admin triage / handoff=null | 🔴 critical | **あり** — 削除要求がオーケストレーター未到達 |
| 10 | 19:01:57 | 19:01:59 | 何が記録されてる | **ログ未記録** | 2,167 | 2,167 | 19s | handoff=null, triage=null | 🟡 warning | 軽微 — プライバシー FAQ 短絡の可能性、ルート不明 |
| 11 | 19:02:09 | 19:02:10 | 頭痛い | **ログ未記録** | 1,514 | 1,514 | 11s | triage=null, physical_symptom ラベルのみ | 🔴 critical | **あり** — Physical 症状がトリアージ未実行 |
| 12 | 19:02:17 | 19:02:19 | いいえ | **ログ未記録** | 1,940 | 1,940 | 9s | handoff=null | 🟡 ok* | なし（T11 フォローアップと推定、未検証） |
| 13 | 19:03:20 | 19:03:35 | 39度の熱 | **ログ未記録** | 14,652 | 14,652 | 76s | PhysicalOrchestrator / fever + missing_info | 🟡 warning | 軽微 — 高熱で missing_info は許容範囲も受診案内要確認 |
| 14 | 02:42:40 | 02:42:52 | 添付した写真を超高解像度… | **ログ未記録** | 11,864 | 11,864 | 7.7h | OtherHandler / redirect | ✅ good* | なし（スコープ外） |
| 15 | 04:01:32 | 04:01:40 | やあ | **ログ未記録** | 7,412 | 7,412 | 1.3h | OtherHandler / greeting | 🟡 ok* | なし |
| 16 | 04:01:47 | 04:01:55 | はろー | **ログ未記録** | 8,139 | 8,139 | 15s | OtherHandler / greeting | 🟡 ok* | なし |
| 17 | 04:03:14 | 04:03:25 | 君の名は？ | **ログ未記録** | 10,875 | 10,875 | 90s | OtherHandler / app_about | ✅ good* | なし |
| 18 | 04:03:38 | 04:03:49 | /admin | **ログ未記録** | 10,702 | 10,702 | 24s | session_admin + counseling 生成 | 🟡 warning | 軽微 — 管理コマンドの応答仕様要確認 |
| 19 | 04:04:05 | 04:04:20 | 和訳して | **ログ未記録** | 14,688 | 14,688 | 31s | counseling チェーン（5 LLM） | 🟡 warning | 軽微 — スコープ外は redirect 期待 |
| 20 | 04:04:34 | 04:04:37 | 要約して | **ログ未記録** | 3,520 | 3,520 | 18s | session_agent.summarize | ✅ good* | なし |
| 21 | 04:04:49 | 04:04:51 | 履歴削除でき？？ | **ログ未記録** | 1,551 | 1,551 | 14s | handoff=null, triage=null | 🔴 critical | **あり** — T9 と同種の削除要求が短絡 |
| 22 | 04:35:19 | 04:35:27 | こんにちは | **ログ未記録** | 7,170 | 7,170 | 31m | OtherHandler / greeting | 🟡 ok* | なし |
| 23 | 04:44:42 | 04:44:48 | 本日中に物理学実験のレポート… | **ログ未記録** | 6,233 | 6,233 | 9m | OtherHandler / redirect | ✅ good* | なし（スコープ外） |
| 24 | 04:45:43 | 04:45:51 | 心の病です | **ログ未記録** | 7,990 | 7,990 | 63s | CounselingManager / Emotional | ✅ good* | なし |
| 25 | 04:46:37 | 04:46:45 | 胸痛みではなくない？ | **ログ未記録** | 7,791 | 7,791 | 54s | OtherHandler / redirect | 🔴 critical | **あり** — 胸痛文脈の physical_symptom が redirect |
| 26 | 04:47:18 | 04:47:30 | は？ | **ログ未記録** | 12,175 | 12,175 | 45s | counseling 継続（5 LLM） | 🟡 warning | 軽微 — T25 誤応答への反応と推定 |
| 27 | 04:47:33 | 04:47:36 | 胸が痛い | **ログ未記録** | 2,976 | 2,976 | 5s | Emergency/keyword_match 短絡 | ✅ good* | なし（Emergency 短絡妥当、返信未検証） |
| 28 | 04:54:30 | 04:54:40 | 履歴を教えて | **ログ未記録** | 10,572 | 10,572 | 7m | session_admin triage → counseling | 🟡 warning | **あり** — session_admin なのに counseling 生成 |
| 29 | 04:54:51 | 04:55:03 | 技術面を詳しくおしえて | **ログ未記録** | 12,534 | 12,534 | 23s | counseling チェーン（handoff=null） | 🔴 critical | **あり** — meta_follow_up が architecture 未到達 |
| 30 | 04:55:17 | 04:55:22 | 技術スタックは？ | **ログ未記録** | 5,148 | 5,148 | 19s | OtherHandler / architecture | ✅ good* | なし |
| 31 | 04:55:33 | 04:55:38 | マルチエージェントなの？ | **ログ未記録** | 4,422 | 4,422 | 16s | OtherHandler / architecture | ✅ good* | なし |
| 32 | 04:55:51 | 04:56:00 | 役割分担は？ | **ログ未記録** | 9,365 | 9,365 | 23s | architecture + meta_triage | ✅ good* | なし |
| 33 | 07:48:54 | 07:49:06 | やああ | **ログ未記録** | 11,453 | 11,453 | 2.9h | OtherHandler / greeting | 🟡 ok* | なし |
| 34 | 07:49:23 | 07:49:30 | ブンブンハローYouTube | **ログ未記録** | 7,074 | 7,074 | 25s | OtherHandler / redirect | ✅ good* | なし |
| 35 | 07:51:14 | 07:51:20 | トリアージエージェントのスペック教えて | **ログ未記録** | 6,190 | 6,190 | 110s | OtherHandler / redirect | 🟡 warning | **あり** — architecture/meta 期待 |

\* `ok*` / `good*`: ルーティング・レイテンシは妥当と推定するが、**返信本文がログ未記録のためユーザー体験は未検証**。

**判定集計（LLM）**: critical 5 / warning 10 / good・ok* 20

---

## 4. 重要ターン詳細（timing / LLM / 原因）

### T4 — ねむい（Physical）

| フェーズ | ms |
|---------|-----|
| トリアージ | 2,640 |
| オーケストレーター | 4,615 |
| NLU batch | ~3,710 |

| path | model | latency |
|------|-------|---------|
| llm_triage.stage1 | gpt-5.4-mini | 2,044 ms |

- **handoff**: PhysicalOrchestrator（Physical/drowsiness 0.98）
- **所見**: NLU batch 実行後 `orch_route_end` で終了。推奨イベント未記録 — 追加質問フェーズか、ログギャップ。

### T5 — しね（攻撃的）

| フェーズ | ms |
|---------|-----|
| （breakdown なし — セキュリティ前後のみ） | ~808 delivery |

- **LLM**: 0 回
- **所見**: `before_security` 後すぐ `delivery_mode` — 攻撃的入力ブロックの典型パターン。✅ 妥当。

### T9 / T21 — 履歴削除系

| ターン | triage | handoff | E2E |
|--------|--------|---------|-----|
| T9 履歴って消せるの？ | Other/session_admin 0.98 | **null** | 7,436 ms |
| T21 履歴削除でき？？ | **null** | **null** | 1,551 ms |

- **原因推定**: session_admin 意図は stage2 まで到達するがオーケストレーター handoff なし。T21 は triage 自体スキップ。
- **推奨**: `session_admin` → 専用 SessionHandler（削除不可説明・保持期間・admin 導線）への明示 handoff。

### T11 — 頭痛い 🔴

| フェーズ | ms |
|---------|-----|
| セキュリティ | 5.8 |
| トリアージ | **null** |
| delivery | 896 |

- **input_labels**: `physical_symptom`
- **LLM**: 0 回
- **原因推定**: Physical 症状の早期短絡経路（キャッシュ/ルール/前ターン状態）が誤作動し、PhysicalOrchestrator 未到達。
- **リスク**: OTC 相談の核心機能がスキップ — **最優先調査**。

### T13 — 39度の熱

| フェーズ | ms |
|---------|-----|
| トリアージ | 3,622 |
| オーケストレーター | 8,974 |

| path | model | latency |
|------|-------|---------|
| llm_triage.stage1 | gpt-5.4-mini | 3,033 ms |
| missing_info_service | gpt-5.4-mini | 2,837 ms |

- **handoff**: PhysicalOrchestrator（Physical/fever 0.99）
- **所見**: missing_info は情報収集として妥当。39°C は **受診・緊急度の明示**が必須（advisor 観点）。推奨品ログなし。

### T25–T27 — 胸痛コンテキスト

| # | 入力 | triage | route | 判定 |
|---|------|--------|-------|------|
| 25 | 胸痛みではなくない？ | Other/general_other | redirect | 🔴 誤ルート |
| 26 | は？ | Other/general_other | counseling | 継続処理 |
| 27 | 胸が痛い | **Emergency**/keyword_match | 3.4ms 短絡 | ✅ Emergency 妥当 |

- T24「心の病」→ T25 でユーザーが胸痛を否定するメタ質問。redirect は counseling 継続と解釈された可能性があるが、`physical_symptom` ラベルと矛盾。
- T27 は keyword_match Emergency 短絡 — **119/受診案内テンプレ**が返っている想定（未検証）。

### T29 — 技術面を詳しく 🔴

| path | 件数 |
|------|------|
| llm_triage.stage1/2 | 2 |
| counseling_topic_shift / processor / generator | 3 |

- **input_labels**: `meta_follow_up`
- **handoff**: null（T28 counseling 継続）
- **原因**: 直前 T28「履歴を教えて」が counseling に入ったため、T29 も counseling チェーンに拘束。T30 以降で architecture に復帰。
- **推奨**: meta_follow_up + 技術キーワードで counseling から architecture へ強制切替。

### T30–32 — アーキテクチャ質問 ✅

| # | concierge | LLM path |
|---|-----------|----------|
| 30 | architecture | concierge_agent.meta_architecture |
| 31 | architecture | concierge_agent.meta_architecture |
| 32 | architecture + meta | stage1/2 + meta_triage + meta_architecture |

- triage_ms 1.6–3.5s → キャッシュヒット含む高速 path。ルーティング良好。

### T35 — トリアージエージェントのスペック

| path | model |
|------|-------|
| llm_triage.stage1/2 | gpt-5.4-mini |
| concierge | **redirect**（build 0.1ms） |

- **所見**: 「トリアージエージェント」は製品メタ情報 — `architecture` または `app_about` が自然。redirect はスコープ外扱いで許容範囲だが、dev テスト意図なら architecture 期待。

---

## 5. パフォーマンス概要

| 指標 | 値 |
|------|-----|
| E2E 中央値（概算） | ~8,000 ms |
| E2E 最大 | 14,652 ms（T13 39度の熱） |
| E2E 最小 | 1,496 ms（T5 しね — ブロック） |
| トリアージ dominant | T1–3, T6, T16–17 等で 3–6.8s |
| LLM コスト（セッション概算） | 多数の triage+concierge 呼び出し — dev プロービングによる高頻度 LLM |

**遅延所見**: 初回ターン（T1）POST→セキュリティ 1,051ms — コールドスタート寄与。挨拶系で triage 2段 × concierge が 10–13s — dev 許容だが本番 UX 改善余地あり。

---

## 6. 問題一覧と推奨アクション

| 重要度 | 問題 | 根拠 | 推奨アクション |
|--------|------|------|----------------|
| 🔴 critical | 全ターン response_missing | counseling_detail 0 件 | dev 全経路で `finalize_pipeline_response` 非同期 counseling_detail 出力を確認。エクスポート filter も点検 |
| 🔴 critical | T11 頭痛い — Physical トリアージスキップ | triage_ms=null, LLM 0, 1.5s | `physical_symptom` 短絡経路を grep（`chat_recommendation_flow` / emoji_route）。再現テスト追加 |
| 🔴 critical | T9/T21 履歴削除 — handoff なし | session_admin triage → null | session_admin → SessionAdminHandler の handoff ルール明示化 |
| 🔴 critical | T29 技術質問 → counseling | meta_follow_up + counseling 5 LLM | counseling 継続中の meta/architecture キーワードで強制 switch |
| 🔴 critical | T25 胸痛否定 → redirect | physical_symptom + redirect | 胸痛キーワード + 否定形の triage ルール見直し |
| 🟡 warning | Physical 5 ターン推奨イベント 0 | physical_recommendation_summary | missing_info 後の recommend ログが出ているか Cloud Logging で trace 追跡 |
| 🟡 warning | T13 39°C 高熱 | fever 0.99 + missing_info | 高熱閾値での受診案内テンプレート必須化（advisor 方針） |
| 🟡 warning | T35 triage spec → redirect | redirect 0.1ms | architecture ルートにマッピング追加検討 |
| 🟢 info | T5 攻撃的入力ブロック | 1.5s, LLM 0 | 現状維持 |
| 🟢 info | T7/T20 履歴要約 | session_agent.summarize | 現状維持 |
| 🟢 info | T27 Emergency 短絡 | keyword_match 3.4ms | 返信内容のみ counseling_detail で検証 |

---

## 7. セッション総合評価（LLM）

| 項目 | 評価 |
|------|------|
| **総合グレード** | **poor** |
| 強み | 攻撃的入力ブロック（T5）、履歴要約 fast path（T7/T20）、Emergency キーワード短絡（T27）、architecture 連続質問（T30–32）のルーティング |
| 弱み | 100% response_missing で品質未検証、Physical スキップ（T11）、session_admin 未処理（T9/T21）、counseling 誤拘束（T29）、胸痛文脈 misroute（T25）、推奨イベント全程 0 |
| ユーザー像 | 内部テスト/開発者 — 本番ユーザー体験評価には counseling_detail 復旧が前提 |

**結論**: ヒューリスティック `good` は **ログ可視性ギャップ**（返信未記録 + issue 検出ルール未カバー）により過大評価。ルーティング観点では dev プロービングに対し部分的成功だが、Physical/session_admin/counseling 境界の不具合が複数あり、**本番投入前に要修正**。
