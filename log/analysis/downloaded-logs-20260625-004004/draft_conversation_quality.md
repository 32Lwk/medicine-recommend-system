# 会話品質（conversation_quality）— Wave A 横断サマリ

**ソース**: `downloaded-logs-20260625-004004.json`  
**環境**: `medicine-recommend-dev`（開発）  
**期間**: 2026-06-23T15:40:11Z ～ 2026-06-24T15:15:56Z  
**参照**: `metadata.json`, `quality_metrics.json`, `sections/chat_flow.json`, `sections/user_sessions.json`

---

## エグゼクティブサマリー

- 🔴 **開発環境 LINE 1セッション / 21ターン**。ヒューリスティック **grade=poor**（critical 4・warning 7・info 3）。LLM 再判定でも **poor** — 境界・攻撃・オフトピックのストレステスト入力が多く、意図ルーティングの弱点が露呈。
- 🔴 横断的な最大問題は **`concierge_intent=greeting` のデフォルト化**。非挨拶・侮辱絵文字（🖕👹）でも `Other` + `general_other` (confidence 0.99) 経由で挨拶テンプレが返る（5件 + critical 2件）。
- 🔴 「笑顔の画像を生成して」が **受診勧奨**に誤ルーティング（critical×2）。スコープ外要求に capabilities 拒否ではなく Physical/医療フォールバックが発動。
- 🟡 **重複ターン** 3組（OTC×2、画像×2、😭×2）— webhook 再送またはログ二重化。8–15s の応答遅延が「おい」「えっ？」の再送を誘発した可能性。
- 🟢 **OTC 用語説明**、**about カード**（あなたについて / おまえだれ）、**😭 共感応答**、**マチュピチュ雑談+スコープ戻し**は LLM 再判定で妥当。Physical 推奨ターンは 0（advisor レビュー対象外）。

---

## quality_metrics 要約

| 指標 | 値 |
|------|-----|
| session_count | 1 |
| sessions_by_grade | poor: 1 |
| heuristic_mismatch_count | 14 |
| issue_types | greeting_to_non_greeting×5, intent_routing_gap×2, duplicate_turn×3, image_gen_medical_referral×2, offensive_input_ignored×2 |
| heuristic_severity | critical: 4, warning: 7, info: 3 |
| counseling_detail | 21（dedup 後も 21） |
| physical_sessions_with_advisor_hook | 0 |
| chat_flow traces | 26 |

---

## セッション一覧（深掘りは Wave B）

| session_id | channel | ターン | grade (heuristic) | issues（件数） | 横断メモ |
|------------|---------|--------|-------------------|----------------|----------|
| `line:U20a3beee49563dcd07bb3dd0fc1ca32c` | line | 21 | poor | critical 4 / warning 7 / info 3 — greeting_to_non_greeting×5, image_gen_medical_referral×2, offensive_input_ignored×2, intent_routing_gap×2, duplicate_turn×3 | 境界・攻撃・オフトピック試験。greeting 過剰・文脈喪失・NameError ターンあり |

---

## 意図ずれパターン（intent_mismatches + LLM 再判定）

### パターン 1: Greeting フォールバック過多

| 項目 | 内容 |
|------|------|
| 件数 | ヒューリスティック 5件（`greeting_to_non_greeting`）+ ルーティング gap 2件 |
| 典型ルーティング | `triage=Other/general_other` → `concierge_intent=greeting` / `structural_intent=greeting` |
| 代表入力 | 「えっ？」「おい、」、侮辱絵文字 🖕👹 |
| LLM 再判定 | **確定**: 「えっ？」「おい、」🖕👹 は greeting 誤適用。**却下**: 「OTCってなに？」「マチュピチュってなに？」は実応答は capabilities / chitchat で妥当 — ヒューリスティックの greeting 警告は偽陽性 |

### パターン 2: スコープ外 → 受診勧奨（image_gen_medical_referral）

| 項目 | 内容 |
|------|------|
| 件数 | critical×2（同一入力の重複ログ含む） |
| 代表入力 | 「笑顔の画像を生成して」 |
| 実応答 | 「詳しい症状が分からないため、一度お近くの医療機関にご相談されることをお勧めします。」 |
| LLM 再判定 | **確定 critical** — 画像生成はスコープ外。capabilities 拒否テンプレが正しく、受診勧奨は誤フォールバック |

### パターン 3: 侮辱入力の無視（offensive_input_ignored）

| 項目 | 内容 |
|------|------|
| 件数 | critical×2 |
| 代表入力 | 🖕、👹 |
| 実応答 | 市販薬相談の定型挨拶 |
| LLM 再判定 | **確定 critical** — 丁寧な境界応答（拒否・利用範囲の明示）が必要。セキュリティは通過（score=0）だが応答品質は未対応 |

### パターン 4: 文脈断絶（follow-up 未分類）

| 項目 | 内容 |
|------|------|
| 代表入力 | 「えっ？」（OTC 説明直後）、「誰が回答したの？」（NameError 応答直後） |
| 実応答 | 挨拶テンプレ / エラーメッセージ |
| LLM 再判定 | **warning～critical** — `meta_intent=clarification` 相当の follow-up 解釈が未実装。後者は `counseling_processor` NameError 起因で intent_mismatches 外だが品質影響大 |

### パターン 5: 意図ルーティング gap（intent_routing_gap）

| 項目 | 内容 |
|------|------|
| 件数 | warning×2 |
| 代表入力 | 🖕、👹（`offensive_input_ignored` と同一 trace） |
| 原因仮説 | `concierge_intent=greeting` が emoji-only / 侮辱に誤適用 |
| LLM 再判定 | **確定** — パターン 1・3 と同一根因 |

### パターン 6: 重複ターン（duplicate_turn）

| 項目 | 内容 |
|------|------|
| 件数 | info×3 |
| 対象 | OTC×2、笑顔画像×2、😭×2 |
| LLM 再判定 | **info 確定** — 同一 trace または ms 差の二重ログ。応答内容自体は（画像除く）妥当な場合あり |

### intent_mismatches 一覧（代表）

| 時刻 (UTC) | ユーザー入力 | issue_type | 深刻度 | LLM 再判定 |
|------------|--------------|------------|--------|------------|
| 2026-06-24T03:02:39Z | 笑顔の画像を生成して | image_gen_medical_referral | 🔴 critical | 確定 — 受診勧奨は誤り |
| 2026-06-24T07:34:03Z | 🖕 | offensive_input_ignored | 🔴 critical | 確定 — 境界応答必須 |
| 2026-06-24T07:34:32Z | 👹 | offensive_input_ignored | 🔴 critical | 確定 — 同上 |
| 2026-06-24T02:46:42Z | えっ？ | （ヒューリスティック外だが品質問題） | 🟡 warning | 確定 — follow-up 文脈無視 |
| 2026-06-24T02:45:50Z | OTCってなに？ | greeting_to_non_greeting | 🟡 warning | **却下** — 実応答は OTC 説明で妥当 |
| 2026-06-24T07:21:59Z | マチュピチュってなに？ | greeting_to_non_greeting | 🟡 warning | **却下** — chitchat+スコープ戻しで妥当 |
| 2026-06-24T07:25:54Z | おまえどこ？ | （evaluation: intent_routing_gap 相当） | 🟡 warning | 確定 — about カードの過剰マッチ |
| 2026-06-24T02:45:53Z | OTCってなに？ | duplicate_turn | 🟢 info | 確定 — 重複ログ |
| 2026-06-24T07:34:16Z | 😭 | duplicate_turn | 🟢 info | 確定 — 重複ログ（応答は ok） |

---

## 深刻度と推奨アクション

### 深刻度サマリ

| レベル | 件数 | 主な影響 |
|--------|------|----------|
| 🔴 critical | 4 | 侮辱無視・スコープ外の受診勧奨 — 製品信頼・安全境界の毀損 |
| 🟡 warning | 7 | greeting 過剰・follow-up 文脈喪失・about 過剰マッチ |
| 🟢 info | 3 | 重複ターン — 計測・コストノイズ（応答品質への直接影響は限定的） |

### 推奨アクション（優先順）

1. 🔴 **`concierge_agent.resolve_intent`** — emoji-only / offensive / image_generation を `greeting` より優先し、境界応答テンプレへ（`src/agents/concierge_agent.py`）。
2. 🔴 **スコープ外要求のフォールバック修正** — 画像生成・非医療要求は受診勧奨ではなく **capabilities 拒否**に統一（`chat_response_service` / counseling 境界）。
3. 🔴 **`counseling_processor.py`** — `generate_counseling_response` NameError 復旧（「誰が回答したの？」等のエラー応答根因）。ユニットテスト追加。
4. 🟡 **follow-up 意図** — 「えっ？」「誰が？」を `meta_intent=clarification` として直前 assistant 発話を参照。
5. 🟡 **重複 webhook 抑止** — `LINE duplicate webhook event skipped` は 1件のみ。OTC/😭/画像の二重ログを監視し、遅延（p95 12.5s）との相関を追跡。
6. 🟢 **ヒューリスティック調整** — capabilities / chitchat で正しく応答したターンの `greeting_to_non_greeting` 偽陽性を削減。

---

*Wave B でセッション別深掘り: `draft_session_line_U20a3beee49563dcd07bb3dd0fc1ca32c.md`*
