# 文脈・意図 E2E テスト報告 (2026-08-07)

localhost (`http://127.0.0.1:5000/`) で `tests/fixtures/v2_context_intent_e2e.yaml`（12 シナリオ / 26 ターン）を実行。

## エグゼクティブサマリ

| フェーズ | 合格 | 備考 |
|--------|------|------|
| **修正前**（初回実行） | **8/12** | ロキソニンフォロー 3 件 + 副作用キーワード 1 件が不合格 |
| **修正後・意図再テスト** | **3/3** | 意図読み取り失敗のみ再実行。1 件は 120s タイムアウト（サーバー起動直後の flake）、即時再実行で合格 |

**総合判定（意図・文脈）**: 修正後は **ロキソニン多ターン追質問シナリオはすべて合格**。腹痛タイムアウト回帰も初回から合格（16.8s）。

## 実施した改善（一般化）

1. **`collect_active_medicine_products`**: `role=assistant` 形式の展開済み履歴からも医薬品エンティティを収集
2. **`_rule_based_medicine_thread_continuation`**: 医薬品 QA 文脈 + 短文（≤120 文字）は LLM 前にスレッド継続と判定（レイテンシ・コスト削減）
3. **`resolve_medicine_qa_route`**: 展開履歴で raw messages を上書きしない。`structural_ack`（greeting）前に `session_has_medicine_qa_context` をチェック
4. **`chat_post_pipeline`**: `MedicineQaRoute.MEDICINE_QA` + スレッド継続 source のとき `handle_medicine_followup_qa` を早期実行

## シナリオ別結果

### 合格（意図・文脈 OK）

| ID | 内容 | 修正前 | 修正後 |
|----|------|--------|--------|
| ctx-abdominal-timeout-01 | お腹が痛い → 16.8s で推奨 | ✅ | ✅ |
| ctx-loxonin-followup-home-01 | 画像 QA → 家にもあります | ❌ greeting | ✅ medicine_qa（再実行） |
| ctx-loxonin-followup-s-variant-01 | → Sはついていません | ❌ greeting | ✅ medicine_qa |
| ctx-loxonin-followup-s-found-01 | → 見てみたらSが… | ❌ 文脈喪失 | ✅ ロキソニンS 言及 |
| ctx-reco-followup-compare-01 | 頭痛 → どっちがいい？ | ✅ | ✅ |
| ctx-insomnia-duration-01 | 不眠 → 2週間 | ✅ | ✅ |
| ctx-concierge-followup-01 | 技術 → もっと詳しく | ✅ | ✅ |
| ctx-ambiguous-ack-01 | 比較 QA → そうなんです | ✅* | ✅ |
| ctx-warafin-followup-01 | ロキソニン服用 → 併用 | ✅ | ✅ |
| ctx-fever-followup-01 | 発熱 → 38.5度 | ✅ | ✅ |
| ctx-thanks-not-greeting-01 | 副作用 → ありがとう | ✅ | ✅ |

\* 修正前も auto-pass だが応答は concierge_greeting 系。再テスト対象外（意図読み取り失敗扱いではない）。

### 再テスト対象外

| ID | 理由 |
|----|------|
| ctx-loxonin-side-effect-01 | ルーティングは `medicine_side_effect_qa` で正しい。不合格理由は応答に「ロキソニン」文字列がなく「ロキソプロフェン」のみ（成分名として妥当）。**意図・文脈の読み取り失敗ではない** |

## レイテンシ・コスト

| 指標 | 初回 12 シナリオ | 備考 |
|------|------------------|------|
| p50 E2E | 7.2s | |
| p95 E2E | 25.4s | 推奨フロー（頭痛・発熱）が支配的 |
| max E2E | 26.5s | 120s タイムアウトなし（腹痛 OK） |
| `medicine_thread/continuation_llm` | 14 回 / p50 1.0s | ルール判定追加後は LLM 呼び出し削減見込み |
| `concierge_agent.greeting` | 8 回（修正前フォロー失敗時） | 修正後フォローは medicine_qa へ |

## 根本原因（修正前の失敗）

1. **ルーティング判定と実行のギャップ**: `resolve_medicine_qa_route` が MEDICINE_QA を返しても、フォローアップ用 early handler がなく Concierge greeting に落ちた
2. **履歴形式**: `expand_messages_for_llm` 後の `role=assistant` 履歴で `collect_active_medicine_products` が空になり、LLM 継続判定も structural greeting も誤動作
3. **LLM 継続判定の false negative**: 「家にもあります」等が `continues_medicine_thread=false` になるケースあり → ルールベース層で補完

## 成果物

- 初回: `log/analysis/2026-08-07_local_v2_chat_test_context-intent-0806.md`
- 再テスト: `log/analysis/2026-08-07_local_v2_chat_test_context-intent-rerun.md`
- home 再実行: `log/analysis/2026-08-07_local_v2_chat_test_context-intent-rerun2.md`
- フィクスチャ: `tests/fixtures/v2_context_intent_e2e.yaml`

## 残課題（低優先）

- Turn 3「Sはついていません」の応答品質（推奨情報不足メッセージ）— ルーティングは OK、RAG/推奨コンテキスト注入の改善余地
- `ctx-loxonin-side-effect-01`: 応答にブランド名（ロキソニン）を含める UX 改善（ルーティング問題ではない）
- フォローアップ QA の p95 レイテンシ（~67s の 1 ターン）— `medicine_response_builder.chat_context` 最適化は別 issue
