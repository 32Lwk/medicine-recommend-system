# Supervisor 受理 — Agent E Round4 + live 開始条件固定

> ## ERRATUM（2026-09-22 Agent G）
>
> live は `012129` で実行済。Gate 語は **Not Passed / Hard No-Go** のまま。intake の「条件付き Yes」は開始許可であり合格ではない。


- Agent: [Agent E](a60fa88f-ace8-4c66-aadb-d7f34b2b8125)
- E-C1/C2: **Closed**（Supervisor 再確認済）
- live: **条件付き Yes（証拠採取のみ）** — Gate 即 Pass 禁止

## Gate 正本メトリクス（Supervisor 固定 2026-09-22）

| 用途 | 正本キー |
| --- | --- |
| joint accuracy | **`accuracy_gate_pct`**（`sub_accuracy_exempt=False` の scored のみ） |
| 参考 | `accuracy_scored_pct` / `accuracy_attempted_pct` |
| latency 短縮 CI | **`latency_ci.scenario_cluster`** のみ（request-level は deprecated） |
| latency 点推定 | **`latency_gate` / `latency_warm`**（cold 除外） |
| order | `--order seed_random`（within-case backend shuffle only） |

## E4-H1/H2 Supervisor 統合（live 前）

eval に exempt フィールド転送・`accuracy_gate_pct`・CI top=scenario_cluster・`latency_gate` を追加。unit 15 passed。

## ゲート語（live 完了まで）

Gate A-accuracy = **Not Passed** / Gate B = **Hard No-Go**
