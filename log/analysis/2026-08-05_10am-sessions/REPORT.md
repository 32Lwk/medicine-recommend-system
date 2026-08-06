# 2026-08-05 10:00 JST 以降 — セッション別詳細分析

## データソース

| ソース | 用途 |
|--------|------|
| **AWS CLI** | `AWS_PROFILE=medicine-recommend-dev` — CloudWatch `/ecs/medicine-recommend`、filter: `counseling_detail` / `PIPELINE_PERF` / `dialogue_route` |
| **Neon** | プロジェクト `gentle-frog-62003272`（medicine-recommend）— `sessions.messages` / `user_attributes` |
| **Multitask 解析** | `draft_physical_burst.md` / `draft_critical_issues.md` / `draft_concierge_meta.md` |

**分析時刻**: 2026-08-05 11:08 JST  
**対象窗口**: 2026-08-05 10:00 JST ～ 11:08 JST（UTC 01:00–02:08）

---

## エグゼクティブサマリー

1. **10:13–10:28 に Physical 症状相談が集中**（8 セッション + 問題 2 件）。頭痛系は **推奨成功**（E2E **47–58 s**）だが、**めまい・かゆみは推奨未到達**。
2. **最大の品質事故**: `1785892363748640562488`「頭がクラクラする」→ shadow は Physical だが **execution が concierge greeting**（**poor**）。Neon 上 28 分後に運営手動謝罪。
3. **NLU 失敗**: `1785892380409230461341`「肌がかゆい」→ **no_candidates ×2**（属性入力後も症状 `[]`）。Neon にターン2未永続（**fair**）。
4. **幼児鼻水 QA**（`1785892365553487814128`）は **15 歳以上製品を幼児向け質問に提示** — 内容誤り（**poor**）。
5. **10:00–11:08 の Concierge 新規 POST は未検出**。同日早朝（02:42 JST）の app_about は **255–424 s** 異常レイテンシ（別窗口・参考）。

**HTTP/infra エラー（10:00+ 窗口）**: **0 件**（5xx なし）。

---

## セッション一覧（10:00 JST 以降）

| 時刻 (JST) | session_id | 入力 | フロー | E2E | 意図整合 | grade |
|------------|------------|------|--------|-----|----------|-------|
| 10:13:24 | `1785892380409230461341` | 肌がかゆい → 属性回答 | Physical / rule_based | ~18s / ~33s | △ routing OK, NLU 失敗 | **fair** |
| 10:13:26 | `1785892370895690177498` | 頭痛がする | Physical / rule_based | **51.7s** | ◎ | **good** |
| 10:13:27 | `1785892374721038147507` | 頭痛い | Physical / rule_based | **53.1s** | ◎ | **good** |
| 10:13:40 | `1785892367772563828651` | 熱っぽい | Physical / **fever_flow** | **47.6s** | △ 解熱鎮痛のみ | **good** |
| 10:14:16 | `1785892365553487814128` | 幼児鼻水 | Physical → medicine_qa | **28.3s** | ✗ 年齢矛盾 | **poor** |
| 10:15:09 | `1785892363748640562488` | 頭がクラクラする | **Physical→concierge greeting** | **~13s** | ✗ mismatch | **poor** |
| 10:15:32 | `1785892376941414913484` | 偏頭痛 | Physical / rule_based | **53.9s** | ○ | **good** |
| 10:15:36 | `1785892416886105725292` | 脂漏性湿疹 | Physical / rule_based | **34.8s** | ✗ no_candidates | **fair** |
| 10:20:45 | `1785892798329357348510` | 喉痛+熱 | Physical / **fever_flow** | **50.3s** | ◎ 風邪薬3品 | **good** |
| 10:27:13 | `1785890421194005681438` | 頭が痛い（T2） | Physical / rule_based | **57.5s** | ◎ | **good** |

---

## 詳細（セッション別）

### 🔴 `1785892363748640562488` — めまい → greeting 誤ルート（poor）

- **意図**: めまいの OTC 相談
- **フロー**: shadow `Physical/dizziness` (0.97) → execution **`concierge_agent/greeting`**, mismatch **true**
- **応答**: 「こんにちは！…具体的な症状を教えてください」— **推奨・追加質問なし**
- **時間**: pipeline **13.4 s** / E2E ~6 s
- **エラー**: `symptom_ignored` (critical)。Neon **10:43** 手動「回答ができず…」

### 🟡 `1785892380409230461341` — かゆみ no_candidates（fair）

- **ターン1**「肌がかゆい」: Physical/rule_based → **`no_candidates`**, `symptoms: []`, 属性質問6件
- **ターン2** 属性一括回答（~98 s 後）: 再び **`no_candidates`**
- **Neon**: ターン2 **messages 未保存**, `user_attributes` 空のまま
- **時間**: ~35 s ×2

### ✅ 頭痛系（good）— `1785892374721038147507`, `1785892370895690177498`, `1785890421194005681438` T2

- 推奨: **イブ / バファリンEX / カロナールA**
- 共感・用法・受診目安あり。年齢未入力ペナルティ（-0.15）で display_score 85 前後
- E2E **51–58 s**（NLU batch ~19–26 s がボトルネック）

### ✅ `1785892798329357348510` — 喉痛+熱（good）

- fever_flow → **風邪薬3品**（スカイブブロンG / バファリンかぜEX / カゼセブンS）
- 成分重複警告あり。E2E **50.3 s**

### △ `1785892367772563828651` — 熱っぽい（good だがギャップ）

- fever_flow 入りながら **解熱鎮痛3品のみ**（#2798 の複合症状と挙動差）

### 🔴 `1785892365553487814128` — 幼児鼻水（poor）

- 「幼児が使える鼻水止め」→ **15歳以上製品** + 成分分類誤り（解熱鎮痛ラベル）

### 🟡 `1785892416886105725292` — 脂漏性湿疹（fair）

- `no_candidates` — 皮膚科受診案内のみ（dead-end）

---

## 性能・エラー横断

| 指標 | 値 |
|------|-----|
| E2E レンジ（Physical 成功系） | **47–58 s** |
| ボトルネック | `nlu_batch` 19–26 s + `rb_explain_batch` 10–13 s |
| HTTP 5xx | **0** |
| intent execution mismatch | **1**（めまい） |
| no_candidates | **3 セッション**（かゆみ×2, 湿疹×1） |
| 運営 manual_reply | **2**（10:43, 10:45 JST） |

---

## 優先アクション

| P | アクション |
|---|-----------|
| **P0** | Physical shadow 確定後の **concierge greeting フォールスルー**修正（めまい） |
| **P0** | 「肌がかゆい」NLU 回帰 + **属性フォロー時の症状マージ** + Neon 永続化監査 |
| **P0** | **幼児向け QA** に年齢適合ガード（15歳以上製品の排除） |
| **P1** | NLU batch レイテンシ削減（burst 時 50 s 超は UX リスク） |
| **P1** | skin_condition / 専門疾患 no_candidates 時の **受診エスカレーション**強化 |

---

## 付録

- Physical burst: `draft_physical_burst.md`
- Critical: `draft_critical_issues.md`
- Concierge（02:42 / 08:03 参考）: `draft_concierge_meta.md`
- AWS raw: `log/raw/downloaded-aws-logs-20260805-20260805-20260805-020929.json`
