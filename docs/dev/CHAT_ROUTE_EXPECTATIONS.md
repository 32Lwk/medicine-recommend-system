# チャットルート期待挙動（Chat Route Expectations）

HTTP ルート表は [`ROUTE_SPEC.md`](ROUTE_SPEC.md)。本書は **1 ユーザー発話 → bot 応答** のルーティング期待値と決定権を定義する。  
Golden test 正解源: 本書 + [`tests/fixtures/expected_v2_diff.yaml`](../../tests/fixtures/expected_v2_diff.yaml) + [`tests/fixtures/route_spec_scenarios.yaml`](../../tests/fixtures/route_spec_scenarios.yaml)。

---

## 決定権マトリクス（現行 → v2 目標）

| 決定 | 現行（問題） | v2 目標（Wave） | 備考 |
|------|-------------|----------------|------|
| category route | triage + meta_triage + orchestrator + legacy | **IntentRouter 単一**（1b） | 1a は旧 100% |
| session delete/summary/status | SessionAgent + fast-path + meta `session_ops` | **SessionOpsHandler 単一**（1a） | delete 強制上書き廃止 |
| pending_memory_delete | 全入力吸収 | Physical/Emergency で **auto-cancel**（Pre-P0） | |
| 履歴窓 | 各所 3/5/8/10/20… | **ContextProvider**（1a） | override 表は CHAT_PIPELINE_V2.md |
| bot 無応答 | end_guard → redirect 補完 | **fail-loud** + 観測（Pre-P0） | |
| OTC 推奨 | rule_based + optional GPT fallback | **rule_based 維持** | |
| 店舗案内 | triage + concierge | fever 時 **絶対禁止**（Pre-P0） | |
| 配信形式 | Web SSE / LINE Push 各所分岐 | **ResponseEnvelope**（1a） | |

---

## 期待 route 表（代表）

| user_input 例 | primary_route | sub_route / agent | must_not |
|---------------|---------------|-------------------|----------|
| `頭痛い` | Physical | rule_based_recommend | store, session_delete_confirm |
| `39度の熱があります` | Physical | fever_flow | **store**, greeting_only |
| `胸が痛い` | Emergency | emergency_dispatch | store |
| `履歴消して` | SessionOps | delete → QR confirm | — |
| pending 中 `頭痛い` | Physical | auto_cancel_pending | delete_confirm_only |
| `ステータスを教えて` | SessionOps | status_card | greeting |
| `履歴を要約して` | SessionOps | summarize | greeting |
| `こんにちは` | Concierge | greeting | medicine_card |
| `技術スタックは？` | Concierge | architecture | medicine_card |
| `技術面を詳しく`（前 architecture） | Concierge | architecture_followup | **greeting** |
| `プリンシプルオブプログラミングとは？` | Concierge | redirect | medicine_card |
| `しね` / `殺すぞ` | Security | aggressive_input | ignore |
| `PI耐性を測っています` | Security | known_attack | normal_chat |
| `近くの薬局`（非発熱） | Store | store_locator | — |
| `39度の熱` 後 `近くの薬局` | Physical | fever_flow | store（発熱中） |

---

## 旧フィールド → dialogue_state 移行 owner

| レガシー field | dialogue_state キー | owner PR | 備考 |
|----------------|---------------------|----------|------|
| `pending_memory_delete` | `pending.session_delete` | Pre-P0 | Physical 優先で cancel |
| `concierge_state` | `concierge` | CCR → 1a dual-write | topic, last_intent |
| `counseling_mode` | `counseling.active` | Wave 2 | 1a では mirror のみ |
| `handoff_*` | `handoff` | Wave 2 | line↔web |
| `episode_id` | `dialogue.episode_id` | 既存維持 | 変更なし |

読取優先: `dialogue_state` > `concierge_state` > レガシー（[`CHAT_PIPELINE_V2.md`](CHAT_PIPELINE_V2.md)）。

---

## correction 再実行（agent 別）

| 直前 route | correction 例 | 再実行 |
|------------|---------------|--------|
| Physical | 「違う、熱がある」 | triage 再実行 → fever_flow |
| SessionOps | 「やっぱり消さない」 | pending clear |
| Concierge architecture | 「もっと詳しく」 | 同一 topic、greeting 禁止 |
| Store | 「やめて」 | redirect or physical |

**契約**: 1 POST 1 回。同一リクエスト内の連鎖 dispatch 禁止。

---

## シナリオ索引

全 30+ 件: [`tests/fixtures/route_spec_scenarios.yaml`](../../tests/fixtures/route_spec_scenarios.yaml)

| グループ | 件数 | ID  prefix |
|---------|------|------------|
| LINE | 6 | `line-` |
| Web | 6 | `web-` |
| handoff | 5 | `handoff-` |
| emergency | 5 | `emergency-` |
| session_ops + correction | 8 | `session-` / `corr-` |

---

## expected_v2_diff との関係

[`expected_v2_diff.yaml`](../../tests/fixtures/expected_v2_diff.yaml) は **意図的 breaking change** のみ列挙。  
旧 pipeline と一致しないが **正しい** 挙動は本書と scenarios が正とする。

---

## ROUTE_SPEC 追記

HTTP レイヤのチャット POST（`POST /`, `POST /line/webhook` 内部）の期待 status は従来どおり **200**（LINE webhook は署名 OK 即 200）。  
ルート期待は **応答 body / Flex / session.messages** で検証する（contract tests 参照）。
