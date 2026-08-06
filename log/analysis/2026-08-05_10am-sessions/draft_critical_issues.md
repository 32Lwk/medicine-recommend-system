# 2026-08-05 10:00+ JST クリティカルセッション深掘り

| 項目 | 値 |
|------|-----|
| 分析対象期間 | 2026-08-05 10:13〜10:16 JST（UTC 01:13〜01:16） |
| ログ export | `downloaded-aws-logs-20260805-20260805-20260805-020929`（正本）、`020844`（部分 export・比較用） |
| Neon DB | `gentle-frog-62003272`（medicine-recommend 本番） |
| 対象セッション | 2 件（intent_mismatch 1 件 + no_candidates 連鎖 1 件） |

---

## エグゼクティブサマリー

| session_id | ユーザー入力 | 判定 | intent alignment |
|------------|-------------|------|------------------|
| `1785892363748640562488` | 頭がクラクラする | **critical** — 症状入力なのに concierge 挨拶のみ | **poor** |
| `1785892380409230461341` | 肌がかゆい → 属性フォロー | **warning** — ルーティングは Physical だが NLU/スコアリング失敗で no_candidates 連発 | **fair** |

両セッションとも最終的に運営者の手動返信（「回答ができず、申し訳ございません」）が Neon に追記されており、**ユーザー体験としては薬推奨に至らなかった**。

---

## セッション 1: `1785892363748640562488`

### 概要

| 項目 | 値 |
|------|-----|
| チャネル | web |
| ターン数 | 1（CloudWatch） / Neon 3 メッセージ（bot 手動返信含む） |
| 時刻（JST） | ユーザー 10:15:09 → bot 10:15:15 |
| heuristic grade | `needs_improvement`（`symptom_ignored` ×1, critical） |

### 会話フロー

```
[10:15:09 JST] user: 頭がクラクラする
[10:15:15 JST] bot: concierge_greeting（sage_status）
  「こんにちは！頭がクラクラするとのこと、お辛いですね。当窓口では…具体的な症状について教えていただければ…」
[10:43:40 JST] bot: manual_reply（運営者）
  「回答ができず、申し訳ございません。改善させていただきます。」
```

### ルーティング（shadow vs execution）

| レイヤ | primary | sub_route | handler | intent | mismatch |
|--------|---------|-----------|---------|--------|----------|
| **shadow**（01:15:15.896561） | Physical | rule_based_recommend | — | triage: Physical / **dizziness** (conf 0.97, llm) | false |
| **execution**（01:15:15.896720） | — | rule_based_recommend（dispatch 側） | **concierge_agent** | **greeting** | **true** |

- `concierge_intent_source`: `execution_sync`（`sync_concierge_execution_metadata` 経由）
- counseling_detail: `concierge_intent: "greeting"`, `llm_used: true`

**解釈**: Shadow ルーターは正しく Physical / めまい系症状と判定したが、実実行は orchestrator / rule_based に到達せず、concierge の greeting パスで終了した。**execution mismatch = true** はユーザー報告どおり。

### パイプライン・タイミング

| 指標 | 値 |
|------|-----|
| pipeline total | **13,386 ms** |
| E2E（推定） | ~6 s（10:15:09 → 10:15:15 JST） |
| LLM 呼び出し | 3 回 / 3,942 ms / ¥0.137 |
| 主要フェーズ | triage → medicine_qa_route → **concierge_resolve_intent → concierge_agent.greeting** |
| **未到達** | `before_orchestrator`, `rule_based_start` なし |

`store_gate_cache_hit: True` — ゲートキャッシュが関与した可能性あり。

### Neon 確認（`sessions.messages`）

```json
[
  {"type":"user","content":"頭がクラクラする","timestamp":"2026-08-05T10:15:09+09:00"},
  {"type":"bot","content":"sage_status","concierge":true,"greeting":true,
   "diagnosis":{"kind":"concierge_greeting","feedback_context":{"concierge_intent":"greeting"}}},
  {"type":"bot","content":"回答ができず…","manual_reply":true,"timestamp":"2026-08-05T10:43:40+09:00"}
]
```

- `user_attributes`: age=21, gender=男性, other_info=「頭がクラクラする」— 属性は部分的に抽出されているが推奨には未使用
- CloudWatch の `intent_mismatches.routing` は空 `{}`（020929 export では dialogue_route 行が intent_router.rows に未集約）

### 根本原因（推定）

1. **Shadow と execution の分岐**: `dialogue_route_shadow` は Physical/rule_based を指示するが、パイプラインは medicine_qa 通過後に concierge greeting へフォールスルー。
2. **症状無視**: greeting 応答は症状に言及するが、**市販薬推奨・追加質問・escalation のいずれにも進まない**（`symptom_ignored`）。
3. **concierge_execution_sync**: 実行結果として greeting が確定し、metadata 同期ログに `mismatch: true` が記録。

### ユーザー影響

- めまい症状で相談したユーザーに**挨拶テンプレのみ**返却。
- 28 分後に運営手動謝罪 — **自助で薬を選べず、待ち時間も発生**。
- サービス目的（OTC 推奨）からの逸脱が最大級。

### intent alignment verdict: **poor**

| 観点 | 評価 |
|------|------|
| triage（shadow） | ✅ Physical / dizziness |
| execution | ❌ concierge / greeting |
| 推奨到達 | ❌ |
| DB 整合 | ✅ Neon と counseling_detail 一致 |

### エラー・シグナル

| type | severity | 備考 |
|------|----------|------|
| `symptom_ignored` | critical | intent_mismatches / intent_review_queue に登録 |
| `execution_mismatch` | — | raw log `dialogue_route_execution.mismatch=true` |
| HTTP / infra | なし | — |

---

## セッション 2: `1785892380409230461341`

### 概要

| 項目 | 値 |
|------|-----|
| チャネル | web |
| ターン数 | 2（020929） / 020844 では途中 2 ターン（内容相違あり） |
| 期間（JST） | 10:13:24 〜 10:15:30（ターン間 ~98 s） |
| heuristic grade | `good`（**過小評価** — no_candidates ×2 は heuristic 未検出） |

### 会話フロー（020929 正本）

```
[10:13:24 JST] user: 肌がかゆい
[10:13:52 JST] bot: sage_reco — error.no_candidates
  + additional_questions（年齢・性別・期間・アレルギー・服薬・持病）
[10:15:30 JST] user: 25歳です。男性です。アレルギーはありません。…症状は1週間前から続いています。
[10:15:30 JST] bot: sage_reco — error.no_candidates（再発）
[10:45:00 JST] bot: manual_reply（運営者）— Neon のみ
```

### 020844 vs 020929 の相違（重要）

| export | ターン 2 ユーザー入力 | 備考 |
|--------|----------------------|------|
| **020844**（部分） | **熱っぽい** | 同一 trace_id、response 未記録（chat_flow のみ） |
| **020929**（完全） | **属性一括回答**（25歳・男性…） | counseling_detail 2 件目と一致 |

020844 はログ取得時点でセッションが未完了だった。**Neon に「熱っぽい」は存在せず**、正しいユーザー行動は属性フォローアップと判断する。

### ルーティング

#### ターン 1「肌がかゆい」

| レイヤ | 値 |
|--------|-----|
| shadow | Physical / rule_based_recommend / **itching** (guard, conf 0.94) — mismatch **false** |
| dispatch | physical_agent, handled **true** |
| execution | physical_agent, layer2 — mismatch **false** |
| chat_flow triage（020844） | Physical / **feverish** (conf 0.96) ← shadow の itching と不一致 |

ルーティング自体は Physical に統一されるが、**トリアージ subcategory がログ間で揺れ**（itching vs feverish）。

#### ターン 2「25歳です。男性です。…」

| レイヤ | 値 |
|--------|-----|
| shadow | Physical / rule_based — mismatch **true** (`gate_improvement`), triage **Other / general_other** |
| dispatch / execution | physical_agent, layer2 — mismatch **false** |

属性回答を general_other と見なす shadow mismatch は「改善候補」分類だが、**症状コンテキストの継続がトリアージに伝播していない**可能性。

### diagnosis エラー詳細

**ターン 1**

```json
{
  "error": {"type": "no_candidates", "severity": "warn"},
  "symptoms": [],
  "missing_priority": "critical",
  "recommended_medicines": [],
  "additional_questions": ["年齢を…", "性別を…", "症状はいつ頃から…", …]
}
```

**ターン 2** — 属性充足後も同一:

```json
{
  "error": {"type": "no_candidates", "severity": "warn"},
  "symptoms": [],
  "missing_priority": "optional",
  "recommended_medicines": []
}
```

→ **NLU が「かゆみ」を symptoms に載せられず**、rule_based スコアリングで候補 0 件。属性フォローでも症状再抽出・マージが機能していない。

### パイプライン・タイミング

| ターン | pipeline total | E2E | LLM | 主要ボトルネック |
|--------|----------------|-----|-----|------------------|
| 1 | **35,238 ms** | 17,801 ms | 4 回 / ¥0.136 | nlu_batch ~3.3 s, rule_based ~2.4 s |
| 2 | **33,313 ms** | — | 4 回 / ¥0.236 | 同上（stage2 triage 追加） |

- trace_id（ターン 1）: `3ce73b04-a302-4dc9-8c25-70825281840d`
- ターン 2 は dispatch ログ上 user_input に typo「**あれるぎ**」（アレルギー）— ログ整形時の文字化けまたは入力正規化の問題の可能性

### Neon 確認

**messages（3 件のみ — ターン 2 ユーザー入力なし）**

```json
[
  {"type":"user","content":"肌がかゆい"},
  {"type":"bot","content":"sage_reco","diagnosis":{"error":{"type":"no_candidates"},...}},
  {"type":"bot","content":"回答ができず…","manual_reply":true}
]
```

**user_attributes（ターン 2 後も未更新）**

```json
{"age": null, "gender": null, "allergies": [], "symptom_duration_days": null, ...}
```

→ CloudWatch counseling_detail にはターン 2 が存在するが、**Neon messages / user_attributes への永続化が欠落**。DB とログの不整合。

### 根本原因（推定）

1. **NLU 症状抽出失敗**: 「肌がかゆい」から `symptoms: []` — かゆみ系キーワードが rule_based パイプラインに渡っていない。
2. **no_candidates 連鎖**: ターン 1 で属性質問を出すが、ターン 2 の属性テキストから症状が復元されず再び no_candidates。
3. **ヒューリスティック盲点**: `heuristic grade=good` — routing は正しくても **recommendation 品質は未評価**。
4. **永続化ギャップ**: フォローアップターンが Neon に保存されず、後続リクエストでも user_attributes が空のまま。

### ユーザー影響

- 初回から「医薬品が見つかりませんでした」— **不安・不信**。
- 6 項目の属性入力（~98 s 待機）後も同エラー — **二重の手間**。
- 32 分後の手動謝罪 — 自助完結不可。
- かゆみ（皮膚症状）向け OTC（抗ヒスタミン・外用など）が本来提示可能なケース。

### intent alignment verdict: **fair**

| 観点 | 評価 |
|------|------|
| routing（shadow/dispatch） | ✅ Physical / rule_based |
| execution handler | ✅ physical_agent |
| triage 一貫性 | ⚠️ itching vs feverish / turn2 Other |
| 推奨到達 | ❌ no_candidates ×2 |
| DB 整合 | ❌ ターン 2 未永続、attributes 空 |
| heuristic | ⚠️ good は misleading |

### エラー・シグナル

| type | severity | 備考 |
|------|----------|------|
| `no_candidates` | warn（UI） | ターン 1・2 両方 |
| `symptoms: []` | — | 根因シグナル |
| intent_mismatches | — | 本セッションは未登録（セッション 1 のみ） |
| shadow mismatch T2 | gate_improvement | 属性回答の triage 分類 |

---

## 横断比較

| 観点 | セッション 1（めまい） | セッション 2（かゆみ） |
|------|------------------------|------------------------|
| 主因 | execution が concierge greeting に逸脱 | NLU 症状空 → スコアリング 0 件 |
| routing 正しさ | shadow ✅ / execution ❌ | shadow ✅ / execution ✅ |
| mismatch 種別 | **execution regression** | なし（shadow gate_improvement のみ T2） |
| 推奨 | 未到達 | 未到達 |
| pipeline 遅延 | ~13 s | ~35 s ×2 |
| Neon 手動返信 | 10:43 JST | 10:45 JST |
| intent alignment | **poor** | **fair** |

---

## 推奨アクション（優先度順）

### P0 — セッション 1

1. **Physical shadow 確定後に concierge greeting へ落ちる経路を特定** — `PIPELINE_PERF` で orchestrator 未到達の分岐条件を再現テスト。
2. **初回ターン症状入力では greeting を抑止** — `symptom_ignored` 自動検知と execution mismatch アラート連携。

### P0 — セッション 2

1. **「肌がかゆい」NLU 回帰テスト** — symptoms に「かゆみ」が載るか CSV / golden case 追加。
2. **属性フォローアップ時の症状コンテキストマージ** — user_attributes 更新 + 前ターン症状の nlu_result 引き継ぎ。
3. **Neon 永続化監査** — counseling_detail 2 ターン目が messages に無い原因（save_session_to_db タイミング）調査。

### P1 — 観測

1. `intent_router.rows` が 020929 で空 — export パイプラインで dialogue_route ログの集約漏れ修正。
2. heuristic に `no_candidates` / `symptoms_empty` を critical 相当で加点。

---

## 参照ファイル

| 種別 | パス |
|------|------|
| セッション transcript | `log/analysis/downloaded-aws-logs-20260805-20260805-20260805-020929/sessions/1785892363748640562488.md` |
| セッション transcript | `log/analysis/downloaded-aws-logs-20260805-20260805-20260805-020929/sessions/1785892380409230461341.md` |
| 部分 export 比較 | `log/analysis/downloaded-aws-logs-20260805-20260805-20260805-020844/sessions/1785892380409230461341.md` |
| intent_mismatches | `log/analysis/.../020929/sections/user_sessions.json` |
| raw routing | `log/raw/downloaded-aws-logs-20260805-20260805-20260805-020942.json` |
| Neon | `gentle-frog-62003272`.sessions（本分析時点クエリ） |

---

*Draft generated: 2026-08-05 — AWS log deep-dive + Neon cross-check*
