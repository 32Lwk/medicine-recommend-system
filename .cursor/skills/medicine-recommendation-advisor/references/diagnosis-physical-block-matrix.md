# 診断名検出後の Physical / OTC 可否マトリクス（ターゲット）

`diagnosis_blocks_otc` + `diagnosis_block_types[]` がセッションに立っている間は **rule_based / Physical を呼ばない**（ユーザーが「もう薬はいい」と言っても解除しない — 新規セッションのみ）。

## マトリクス

| 条件 \\ 診断 type | serious | chronic | mental_health | other |
|-------------------|---------|---------|---------------|-------|
| **診断名のみ**（症状なし） | 通知のみ・早期 return・OTC なし | 同左 | 同左 | 同左 |
| **診断 + 症状**（例: 癌+頭痛） | 通知 → **カウンセリング可** → **OTC 不可** | 同左 | 同左 | 同左 |
| **診断 + OTC 探索**（市販薬/何の薬） | **OTC 不可** | **OTC 不可** | **OTC 不可** | **OTC 不可** |
| **診断 + 副作用言及** | **OTC 不可**（現状 early return 維持） | 同左 | 同左 | 同左 |
| **高リスクコンテキスト**（検査中・疑い等） | **OTC 不可** | **OTC 不可** | **OTC 不可** | **OTC 不可** |
| **Triage が Physical でも** | **ブロック** | **ブロック** | **ブロック** | **ブロック** |

## カウンセリング後に Physical に流れない

現状: `should_show_counseling: true` → 後段で `run_recommendation_flow` に到達し得る。

ターゲット: 上表の type のいずれかが検出されたら **同一セッション中は Physical ハンドオフ禁止**。カウンセリング応答のみ。

## 評価時の記録

| 観測 | 分類 |
|------|------|
| ターゲットどおり OTC なし | 適切（診断ガード） |
| OTC top3 が出た | **要改善** — algorithm bug（診断ガード） |
| 診断通知すらない | **要改善** — 検出漏れ |

## コード参照

- 検出: `src/core/diagnosis_detection.py`
- ハンドラ: `src/handlers/chat/chat_diagnosis_handler.py`
- 将来: `user_attributes.diagnosis_blocks_otc`, `diagnosis_block_types`
