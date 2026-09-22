# Jev Gate 責務分離マトリクス（2026-09-22）

- 正本: 本ファイル + `JEV_PHASE0_CONTRACT_FREEZE_20260921.md` + ユーザー最終指示
- 判定語: **Passed / Not Passed / Hard No-Go** のみ
- 禁止: 条件付きPassed / ほぼPassed / 製品安全合格 / 臨床的に安全 / 本番導入可能

---

## Gate A-code（コード安全）— 現状 **再審査必要**

| 検証項目 | 合否条件 | 証拠ラベル |
| --- | --- | --- |
| default OFF | フラグ既定 false | unit確認済み（再審査中） |
| legacy return | shadow で実行 route 不変 | unit/integration確認済み（再審査中） |
| fail-open | Jev 失敗で本番継続 | unit確認済み（再審査中） |
| PRIMARY 非参照 | Phase1 で PRIMARY 無視 | unit確認済み（再審査中） |
| queue 上限 | bounded executor | unit確認済み（再審査中） |
| secret 非出力 | ログに key/Authorization 無し | unit確認済み（再審査中） |
| 責務境界 | SafetyGate/SessionOps が Jev 専用モジュールに非依存 | 再審査中 |

開始固定（2026-09-22 境界修復）: Gate A-code は **再審査必要**。本サイクルで Passed へ上げることを目的としない。

---

## Gate A-accuracy（IntentRouter pilot）— 現状 **Not Passed**

| 検証項目 | 合否条件 | Gate A 合否に使うか |
| --- | --- | --- |
| accuracy_gate_pct | 100% | **Yes** |
| primary/sub joint | 100% | **Yes** |
| API error | 0 | **Yes** |
| eval error | 0 | **Yes** |
| fallback | 0 | **Yes** |
| forbidden payload | 0 | **Yes** |
| shadow main-path mutation | 0 | **Yes** |
| warm mean Δ | ≥900ms | **Yes**（選定済契約） |
| warm scenario-cluster CI lower | ≥900ms | **Yes**（選定済契約） |
| warm P95 Δ / P95 CI | （未選定） | **No** — mean 契約を事後切替禁止 |
| コスト（OpenAI saved / Jev / fallback後 / 総分類費） | 報告必須 | **No**（ユーザー確定） |
| 再現性（seed/fixture SHA/コマンド） | 必須メタ | 証跡必須 |
| shadow JSONL schema | ローカル隔離で適合 | 証跡必須 |

### 許可される合格表現

```text
固定pilot fixtureと固定評価契約において、
IntentRouterの精度・速度・障害耐性基準を満たした
```

### 禁止表現

製品安全に合格 / 医療安全が証明 / 本番導入可能 / 臨床的に安全

### 連続合格

同一凍結契約・同一 fixture SHA・異なる事前固定 seed（42 と 20260922）・異なる実行時刻で **2回連続**。

---

## Gate B — AI medical adversarial review — 現状 **Hard No-Go**

| 検証項目 | 備考 |
| --- | --- |
| AI医療敵対レビュー | ラベル: `ai_medical_adversarial_reviewed` |
| expanded safety fixture | FN 5軸 |
| required_safety_action | 高リスクで未定義なら contract_incomplete |
| dev shadow 準備 | 有効化は別承認 |
| rollback | 必須 |
| 人間薬剤師承認 | **今回の必須条件ではない**。`human_medical_reviewed` 捏造禁止 |

名称に「臨床承認済み」を付けない。

---

## Gate C 以降（コスト必須評価）

OpenAI saved calls / Jev費用 / fallback後OpenAI / 総分類費を必須評価。Gate A とは分離。

---

## 非ゲート（Hard No-Go 維持）

| 項目 | 判定 |
| --- | --- |
| Gate B / dev shadow 有効化 | Hard No-Go |
| primary canary | Hard No-Go |
| staging / production | Hard No-Go |
| Focus 本配線 | Hard No-Go（scaffold 維持可） |

---

## レイヤー責務（アプリ全体）

| Layer | Jev 許可 | Jev 禁止 |
| --- | --- | --- |
| Deterministic Safety | 観測のみ（OR shadow） | 解除・弱体化 |
| SessionOps | eligibility 理由の観測（`sessionops_fast_path`） | Jev API 呼出、Jev primary、分類候補扱い |
| Intent Classification | eligible な通常相談の primary/sub 分類 | Safety / SessionOps 上書き、診断・用量・禁忌判断 |
| Decision Merger | structured decision | SafetyGate 上書き |
| Recommendation | — | ランキング最終決定 |
| Response / Diagnosis Guard | — | 自然言語の権威 |

共通信号レイヤー:

```text
Low-level detectors
        ↓
pre_route_signals.py
        ├─→ SafetyGate / SessionOps probe 抑止
        ├─→ Legacy Router
        └─→ Jev Eligibility（消費のみ・検出なし）
```

禁止依存: `SafetyGate → Jev` / `SessionOps → Jev` / `危機検出 → Jev` / `pre_route_signals → jev_eligibility`

安全 OR:

```python
effective_high_risk = deterministic_high_risk or legacy_high_risk or jev_high_risk
```

Phase 1: `effective_high_risk` は shadow 観測のみ。実行 route へ反映禁止。
