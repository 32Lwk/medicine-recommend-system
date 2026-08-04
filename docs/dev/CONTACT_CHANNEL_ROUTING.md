# 連絡先・案内カード文脈ルーティング

**最終更新: 2026-08-05**

本サービスの「運営者」「連絡先」「案内カード」「LINE 公式アカウント」を、店舗案内・医薬品 Q&A・支払い案内と誤ルートしないための一般設計。

---

## 問題（2026-08-05 修正前）

| 症状 | 原因 |
|------|------|
| 「運用者はだれ？」で intro のみ表示、連絡先カードが無い | `sage_diagnosis.sections` が空のまま「直後の案内カード」と文言だけ表示 |
| 「案内カード見せて」→ 支払い方法 / 商品画像 | 「案内」→ 店舗、「カード」→ 支払いキーワード、「見せて」→ 商品画像の個別誤判定 |
| フォローアップ（「メールは？」等）が store / medicine_qa に流れる | DB 未接続時 `get_medicine_qa_session_context` が例外、履歴未参照、`resolve_prior_meta_intent` が session.messages を見ない |
| LINE 案内の `kind` が `concierge_capabilities` | execution sync が intent `capabilities` で diagnosis kind を上書き |

---

## 中核モジュール

| ファイル | 役割 |
|---------|------|
| `src/services/contact_channel_intent.py` | 連絡チャネル分類（`line_account` / `operator_contact` / `operator_identity` / `line_technical`）、文脈付きフォローアップ、`is_service_contact_ui_request` |
| `src/services/status_diagnosis_builder.py` | `build_concierge_operator_status` — 同一カード内にメール・フォーム sections |
| `src/services/medicine_qa_eligibility.py` | contact channel を medicine_qa より優先 |
| `src/services/routing_context.py` | `evaluate_store_gate` — contact channel 検出時は store を抑止 |
| `src/services/store_inquiry_handler.py` | `案内カード` 除外、`detect_payment_inquiry` からサービス連絡先 UI を除外 |
| `src/dialogue/routing/gate.py` | 決定論 gate 冒頭で contact channel → Concierge |
| `static/js/ui/status_renderer.js` | `concierge_operator` / `concierge_doc_operator` は常に card レイアウト |

---

## 分類ルール（概要）

1. **初回** — `運用者` / `開発者` / `不具合報告` / `メール` / `案内カード` → `operator_contact` → `doc_operator`
2. **フォローアップ** — 直前が operator 文脈なら短い発話（「見せて」「メールは？」「フォームどこ？」「もう一度」）→ `operator_contact`
3. **LINE** — `LINE教えて` 等 → `line_account`（payload は LINE カード、`kind=concierge_line_account`）
4. **除外** — 店舗の「案内カード」表現は `_probe_store_inquiry_keywords` で除外。支払い subtype の `カード` は `is_service_contact_ui_request` で除外

---

## UI 表示

- intro 文は `normalize_operator_intro_for_inline_card` で「直後の案内カード」→「下記」に置換
- 連絡先 HTML は `build_operator_contact_sections_html()` を sections に同梱（Web / status カード共通）
- LINE アカウントは `build_line_account_status` の sections に QR / line.me リンク

---

## テスト

| 種別 | パス |
|------|------|
| ユニット | `tests/concierge/test_contact_channel_intent.py`, `test_contact_context_routing.py` |
| フィクスチャ | `tests/fixtures/concierge_contact_channel.yaml`, `concierge_contact_context_e2e.yaml` |
| ローカル E2E | `python scripts/concierge_contact_context_e2e.py`（`:5000`） |
| AWS E2E | `V2_TEST_BASE_URL=https://aws.medicine.yutok.dev/ python scripts/concierge_contact_context_e2e.py` |

---

## 関連

- [`CHAT_ROUTE_EXPECTATIONS.md`](CHAT_ROUTE_EXPECTATIONS.md) — 代表ルート表
- [`docs/concierge/technical/00-disclosure-policy.md`](../concierge/technical/00-disclosure-policy.md) — PII 非開示・窓口案内
- [`docs/planning/CONCIERGE_CONTEXT_ROUTING_PLAN_2026-06-27.md`](../planning/CONCIERGE_CONTEXT_ROUTING_PLAN_2026-06-27.md)
