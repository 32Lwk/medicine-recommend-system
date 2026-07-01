# Wave A — conversation_quality クロスセッション要約

**対象ログ**: `2026-06-30-dev-9-11.md`（local-dev）  
**分析ウィンドウ**: 2026-06-30 14:15:52 〜 17:41:22（約 3.4 時間）  
**生成元**: `metadata.json`, `quality_metrics.json`, `sections/chat_flow.json`, `sections/user_sessions.json`

---

## エグゼクティブサマリー

全 219 セッションのうちエクスポート評価対象は **50 セッション**。グレードは **good 54%** と過半数が合格圏だが、**acceptable_with_issues が 38%** と課題付きセッションの比率が高い。**poor / needs_improvement は各 2 件（計 4%）**。

最大の横断的問題は、(1) **トリアージ LLM の 429（quota 枯渇）による `Other/error` 連鎖**と確認ループ、(2) **正しい triage / shadow route と実応答の乖離**（挨拶テンプレ落ち）、(3) **店舗・施設問い合わせの Store ルート未反映** の 3 系統。ヒューリスティック不一致は **27 件（critical 4 / warning 23）**。

---

## セッショングレード分布

### 全体（quality_metrics / 219 セッション）

| グレード | 件数 | 備考 |
|----------|------|------|
| （エクスポート外・未採点） | 169 | counseling 201、trace_only 18 を含む |
| poor | 2 | エクスポート 50 のみ採点 |
| needs_improvement | 2 | 同上 |
| acceptable_with_issues | 19 | 同上 |
| good | 27 | 同上 |

### エクスポート 50 セッション（`sessions_by_grade`）

| グレード | 件数 | 比率 |
|----------|------|------|
| good | 27 | 54% |
| acceptable_with_issues | 19 | 38% |
| needs_improvement | 2 | 4% |
| poor | 2 | 4% |

**所見**: 深刻欠陥（poor）は少数だが、**約 4 割が「許容だが問題あり」**。ローカル v2 チャットテスト（GPT ユーザーシミュレーション）由来の長セッションが poor に集中している。

---

## インテント不一致パターン（`intent_mismatches` 27 件）

| issue_type | 件数 | severity | 典型入力・パターン |
|------------|------|----------|-------------------|
| `greeting_to_non_greeting` | 12 | warning | 「最近眠れません」「睡眠不足です」「近くの薬局」「マツキヨは近くにありますか」「処方箋なしで買える場所」「市販薬の購入先」— **非挨拶入力に汎用挨拶テンプレ** |
| `about_question_mishandled` | 8 | warning | 「インフラ構成を教えて」「プライバシーについて」→ meta/concierge intent 不一致；「近くの薬局を教えて」「ドラッグストアはどこ？」→ **about カード／店舗案内ではなく挨拶** |
| `intent_routing_gap` | 3 | warning | triage が `Emotional/insomnia` や `Physical/fever` と高信頼なのに **挨拶応答のまま**（上記 greeting 系と重複） |
| `offensive_input_ignored` | 2 | critical | 「殺すぞ」— security 応答は返っているが、ヒューリスティックは greeting/concierge 落ちと判定 |
| `symptom_ignored` | 2 | critical | **ボット自身の直前応答がユーザー入力として再注入**された長シミュレーションの末尾ターン（頭痛相談・小児発熱相談） |

### 不一致の構造的要因

1. **triage は正しいが downstream が general ラベル** — `labels=['general']` で挨拶テンプレに落ちる（`intent_routing_gap` と併発）。
2. **shadow router は Store / Physical を選ぶが実応答が未ハンドオフ** — `intent_router` mismatch 23 件のうち **Store/store_locator が 12 件**（triage `Other/store_inquiry/facilities` 等と整合）。
3. **meta/about 質問の concierge intent 未解決** — `concierge_intent` が trace の **469/500 で null**。architecture / doc_privacy 系が about カードに到達しない。
4. **routing メタデータ欠落** — 27 件中 **7 件は routing 空**、**9 件は triage null**（主に security 短絡・trace_only 系）。

---

## trace-only セッション

| 指標 | 値 |
|------|-----|
| 全体 trace_only | **18**（quality_metrics） |
| エクスポート内 trace_only | **5**（いずれも `grade=good`） |

エクスポートされた trace-only 5 件はすべて **`turn_sources: chat_flow` のみ**（counseling_detail なし）。ヒューリスティック上は問題なしと採点されているが、実際は **応答本文がログに残っていない／未評価** の可能性が高い。

### 横断パターン（chat_flow 500 traces より）

- **`Other/error` が 117/500（23%）** — 大半が OpenAI **429 insufficient_quota** によるトリアージ失敗。
- 失敗時の典型ユーザー文言: **「もう少し詳しく教えてください」が 98 回** — `low_confidence_clarification` guard による **同一確認のループ**（clarification route 126 回 / 14 セッション）。
- trace-only 代表セッションはこのループ期間の **パイプライン perf のみ** が残るケース。

**リスク**: trace-only はグレード good でも **会話品質未検証**。全体 18 件はエクスポート外 13 件を含み、品質分布を下方に押しうる。

---

## 共通ルーティング課題

### 1. トリアージ障害 → 確認ループ（インフラ起因・会話品質に直撃）

- `chat_flow`: `Other/error` 117、`triage` カテゴリなし 127。
- `intent_router`: `resolved_by=guard` の **clarification 126 件**（最大セッション 40 ターンの clarification 連打）。
- ユーザー体験: 症状（「最近眠れなくてつらい」「鼻水が止まらない」）を述べても **同じ確認文の繰り返し**。

### 2. 挨拶フォールバック過多

- `greeting_to_non_greeting` が最多（12/27）。
- Emotional（不眠・イライラ）・Physical（発熱）・Store（薬局・ドラッグストア）いずれも **初回または途中ターンで挨拶テンプレ**。
- `intent_router` primary_route 分布: Concierge 328, Physical 255, Counseling 106 — ルートは選ばれているが **dispatch 結果が general 応答** のケースが散見。

### 3. 店舗・施設問い合わせ（Store route ギャップ）

- shadow: `Store/store_locator` + `pharmacy_location`（confidence 0.88〜0.97）で **mismatch 12 件**。
- dispatch ログでは `handler=store_inquiry, handled=true` もあるが、ヒューリスティック上は **about_question_mishandled / greeting** として不一致記録。
- **ルート決定とユーザー向け応答の間にギャップ**（Store ハンドラ実装 or 応答テンプレ未接続の疑い）。

### 4. 推奨パイプライン未到達

- `physical_sessions_with_advisor_hook`: **5**、`physical_recommendation_log_events`: **0**。
- エクスポート 50 中 **physical_turn あり & recommendation_event なし: 5 セッション**（長い頭痛・小児発熱シミュレーション）。
- advisor eligible ターンは多数あるが **構造化 recommendation_log が一切出ていない** — 推奨品質は本分析では未評価。

### 5. 長セッション・文脈維持

- poor 2 件は **62 / 34 ターン** の GPT シミュレーション。
- weakness 頻出: 「同一ユーザーが似た入力を繰り返し（最大 24 回）— 文脈維持が課題」。
- `symptom_ignored` critical は **エコー／ループ終端** のアーティファクト色が強い（要 LLM 再判定: `llm_session_review_required` はエクスポート全 50 件 true）。

---

## 重大度評価

| レベル | 内容 | 横断影響 |
|--------|------|----------|
| **P0 — 運用ブロッカー** | OpenAI 429 による triage 全滅 → clarification ループ | 複数セッションで会話不能。14:22 台の集中発生。本番でも quota 監視必須。 |
| **P1 — 機能欠陥** | Emotional/Physical/Store 入力への挨拶フォールバック | コア価値（症状相談・店舗案内）が初回で失敗。acceptable_with_issues 19 件の主因。 |
| **P1 — 機能欠険** | Store shadow と実応答の不一致 | 薬局・購入先系テストシナリオが一斉に失敗パターン。 |
| **P2 — 品質・信頼** | 長シミュレーションの文脈喪失・エコー | poor 2 件。実ユーザーでも多ターンで劣化リスク。 |
| **P2 — 観測** | trace-only 18 件は品質未計測 | メトリクスが good に偏る。ログ設計の盲点。 |
| **P3 — ヒューリスティック要再確認** | `offensive_input_ignored`（殺すぞ） | 実応答は拒否文。分類ロジックと severity の見直し。 |
| **P3** | recommendation_log 0 件 | 推奨フロー完走の証跡なし。別 Wave で追跡。 |

---

## 推奨修正（優先順）

### 即時（P0）

1. **OpenAI quota / 429 フォールバック** — triage 失敗時に同一 clarification を返さない。回数上限・指数バックオフ・「API 障害のため後ほど」明示。429 発生率をメトリクス化。
2. **clarification guard の脱出条件** — 同一フレーズ（「もう少し詳しく教えてください」）の N 回超で session_admin または人手案内へ。

### 短期（P1）

3. **非挨拶入力での greeting 抑止** — triage が Emotional / Physical / Other(store) かつ confidence ≥ 閾値なら **general ラベル挨拶に落とさない**（`intent_routing_gap` 3 件 + `greeting_to_non_greeting` 12 件の根）。
4. **Store/store_locator 応答接続** — shadow/dispatch で `store_inquiry` handled=true でもユーザーに挨拶しか返らない経路を特定し、店舗案内テンプレ（位置情報不可時の代替含む）を接続。
5. **about / meta ルート** — `architecture`, `doc_privacy` を concierge meta intent から about カードへ。店舗系は Store と分離（現状 `about_question_mishandled` に店舗文言が混入）。

### 中期（P2）

6. **多ターン文脈** — 同一ユーザー入力の連続検出、ボット発話のエコー除外、シミュレーション終端での `symptom_ignored` 誤検知防止。
7. **trace-only セッションの品質計測** — counseling_detail または assistant 応答を必ず 1 ターン以上永続化。trace_only を good 自動採点しない。
8. **recommendation_log 出力** — Physical + advisor eligible ターンで structured log を必須化（現状 0 件）。

### ヒューリスティック調整（P3）

9. **`offensive_input_ignored` 判定** — security 拒否応答が返っている場合は critical にしない、または issue_type を分離。
10. **LLM 全セッション再レビュー** — `llm_review_note` 通り、heuristic_* は参考シグナル。エクスポート 50 件はすべて `llm_session_review_required: true`。

---

## 補足メトリクス

| 項目 | 値 |
|------|-----|
| counseling_detail（raw / dedup） | 646 / 500 |
| chat_flow traces（exported） | 509（分析 JSON 内 traces 500） |
| intent_router rows / mismatch | 763 / 23 |
| heuristic_mismatch_count | 27 |
| HTTP 4xx/5xx | 0 |
| エクスポート session transcripts | 50（`manifest.json`） |

---

*本稿はセッション横断サマリーのみ。個別セッションのターン別深掘りは `sessions/*.md` および後続 Wave で実施。*
