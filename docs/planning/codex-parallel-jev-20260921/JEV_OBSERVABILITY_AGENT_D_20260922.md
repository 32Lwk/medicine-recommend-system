# JEV Observability Agent D 報告（2026-09-22）

- Agent: **D Observability and Cost**
- Owner files: `src/services/jev_metrics.py`, `tests/services/test_jev_metrics.py`
- Schema: `jev_intent_router_shadow` **v2**
- 判定語: Gate A-accuracy は本エージェント範囲外（観測スキーマのみ）

---

## Round 0 要約（実装前監査）

### 現状

| 項目 | Round 0 時点 |
| --- | --- |
| disagreement_class | 実装済（優先順位正しい） |
| latency / retry / fallback_reason / error_class | フィールドあり |
| usage / jev_cost_usd | ありだが **推定が実測に見える命名** |
| event completeness | **なし**（必須集合・欠損フラグなし） |
| failure_reason（正規化 enum） | **なし**（fallback/error のみ） |
| OpenAI actual vs saved estimate | **なし** |
| total classification cost 分離 | **なし** |
| PII/secret 検査 | extra deny-list のみ。**payload 再帰 scrub なし**。assert は既に無いが検査が弱い |

### 仮説

1. Gate B の「log completeness 欠損なし」は、必須フィールド集合と `event_completeness` 無しでは監査不能。
2. `jev_cost_usd` を実測と誤読すると OpenAI 70% 削減判定が汚染される。
3. assert 無しでも、禁止キーが `extra` 経由や値埋め込みで JSONL に残る余地がある。

### 変更対象 / 変更しない対象

- **変更:** `jev_metrics.py` / `test_jev_metrics.py` / 本報告
- **変更しない:** decisions / client / router / eval / fixture ラベル / production routing / flags

### 成功条件

- 必須フィールド + completeness 評価
- 推定/実測のフィールド名分離
- failure_reason 正規化
- PII scrub が assert 非依存（`-O` 耐性）
- `pytest tests/services/test_jev_metrics.py -q` green

### 失敗条件

- 推定を `*_actual` に書く
- secret/PII をログ仕様に追加
- router/decisions を触る

---

## Round 1 実装

### 変更ファイル / 理由

| ファイル | 理由 |
| --- | --- |
| `src/services/jev_metrics.py` | schema v2: completeness / failure_reason / cost 分離 / jev_usage / PII scrub |
| `tests/services/test_jev_metrics.py` | 上記の回帰 + assert 非存在検査 |
| `docs/planning/.../JEV_OBSERVABILITY_AGENT_D_20260922.md` | Round0→1 証跡 |

### スキーマ要点（推定 vs 実測）

| フィールド | 種別 | 意味 |
| --- | --- | --- |
| `jev_usage.input_tokens` 等 | **actual**（API usage） | token 数。金額は入れない |
| `jev_cost_usd_estimate` | **estimated** | `$0.042/MTok × input_tokens` |
| `jev_cost_usd` | **estimated（互換エイリアス）** | 上と同じ。新規集計は estimate 側を使え |
| `cost.openai_cost_usd_actual` | **actual or null** | OpenAI 実測。未配線時 null |
| `cost.openai_cost_*_saved_estimate` | **estimated** | 対照平均に基づく削減推定 |
| `cost.legacy_saved_calls` | **actual count** | 省略できた call 数（shadow は通常 0） |
| `cost.total_classification_cost_usd_estimate` | **estimated sum** | Jev 推定 + OpenAI 実測（実測欠損時は Jev のみ） |
| `failure_reason` | enum | `none` / `timeout` / `http_*` / … / `other` |
| `event_completeness` | meta | `complete` / `missing_required` / `nullish_required` |
| `latency_ms` / `retry_count` / `fallback_reason` | 観測 | 可用性・性能 |

`cost.field_semantics` に estimated / actual を機械可読で併記。

### PII / secret

- `FORBIDDEN_LOG_KEYS` を拡張し、`scrub_forbidden_log_fields` で再帰削除/redact
- 値パターン: `sk-…` / `Bearer …` / `api_key=…` → `[REDACTED]`
- **`assert` 不使用**（`ast` テストでモジュール内 Assert 0 を保証）
- 検出時は `logger.error` + `pii_scrub` メタ。本線は fail-open（record は例外を外へ出さない）

### テスト

```text
.venv\Scripts\python.exe -m pytest tests/services/test_jev_metrics.py -q
22 passed
```

追加カバー: cost 分離、failure_reason、latency/retry、PII scrub、completeness、module assert 不在。

---

## 未解決

1. **OpenAI actual の本番配線** — kwargs は用意したが、`jev_router` / pipeline からの注入は Supervisor 所有のため未配線。shadow 中は `openai_cost_usd_actual=null` が正規。
2. **saved_estimate の対照平均** — `cost_basis` 受け口のみ。母集団集計は eval/ops 側。
3. **Gate B log sink 権限・保持期間** — D6 運用項目。コード外。
4. **legacy `usage` キー** — 互換のため残存。正本は `jev_usage`。

## 危険

- `jev_cost_usd` 互換エイリアスを「実測」と読むとコスト判定が壊れる → 文書・`field_semantics` で抑止。
- PII scrub はヒューリスティック。未知の秘密形式は取りこぼし得る → 禁止キー allowlist 運用と併用。
- completeness 失敗でも JSONL は書く（観測穴を隠さないが、本線は止めない）。

## 自己評価

| 観点 | 評価 | コメント |
| --- | --- | --- |
| 要件充足 | **A-** | 所有範囲内のスキーマ分離は完了。OpenAI actual 配線は他 owner 待ち |
| 推定/実測の明確さ | **A** | フィールド名・`field_semantics`・モジュール docstring |
| 本番耐性（assert） | **A** | scrub + error log + ast 検査 |
| Gate B 準備 | **B+** | completeness は揃ったが actual cost 未配線のため Gate B の cost 集計はまだ不足 |

**Gate 語:** 本変更は観測スキーマ改善のみ。Gate A-accuracy / Gate B 判定は変更しない（引き続き Not Passed / Hard No-Go）。

---

## Round 3 — Supervisor 差戻し対応（E-H / #13）

### 指摘
互換エイリアス `jev_cost_usd` が `field_semantics` に無く、推定であることが機械可読で固定されていなかった。

### 対応
1. `cost.field_semantics["jev_cost_usd"]` = `"estimated (alias of jev_cost_usd_estimate)"`（定数 `JEV_COST_USD_ALIAS_SEMANTICS`）
2. payload トップに `jev_cost_usd` を**維持**しつつ `jev_cost_usd_deprecated=true` + `jev_cost_usd_deprecation_note` を併記。即削除はしない。
3. モジュール docstring / `build_cost_payload` docstring で **新規集計は `jev_cost_usd_estimate` のみ推奨** を強調。
4. unit: `test_jev_cost_usd_alias_semantics_fixed` および既存 cost テストで alias キーを固定。

### pytest
```text
.venv\Scripts\python.exe -m pytest tests/services/test_jev_metrics.py -q
```

### 残留リスク
- 旧コンシューマが `jev_cost_usd` を「実測」と読む誤読は、semantics / deprecation_note で抑止するが、読まない集計スクリプトは依然あり得る。
- エイリアス削除はまだ行わない（破壊的）。将来の schema v3 で deprecate → remove を別チケット化すること。
