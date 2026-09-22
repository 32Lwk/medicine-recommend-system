# Gate A-accuracy 判定（live 20260922_012129）

- 実行: `scripts/eval_jev_intent_router_10.py --backends current,jev:minimal --repeat 10 --order seed_random --seed 42`
- 証跡: `log/analysis/jev_intent_router_eval_10_20260922_012129.json` / `.md`
- commit SHA（実行時 dirty worktree あり）: `b7066137e8afd1358ee1d4abb647f716963e5ae7`
- fixture: `tests/fixtures/jev_intent_router_eval_10.yaml`
- scoring: `score_joint_decision` / production stack / fallback=0 / api_err=0 / eval_err=0

## 正本数値

| 指標 | current | jev:minimal |
| --- | ---: | ---: |
| accuracy_gate_pct | 100.0 (100/100) | 100.0 (100/100) |
| exempt_n | 0 | 0 |
| warm mean ms | 1576.93 | 241.28 |
| warm P95 ms | 3646.66 | 311.85 |
| warm mean Δ | **1335.65** | (≥900 → 点推定 Pass) |
| warm P95 Δ | **3334.81** | (≥2500 → 点推定 Pass) |
| scenario-cluster CI (mean Δ) | **[826.7, 1943.02]** | 下限 &lt;900 → **保守基準 Fail** |
| cost | OpenAI saved proxy 0.854 / Jev est 0.908 | 純減なし（推定） |

raw disagreement 20（Emergency sub 命名揺らぎ + SessionOps delete alias）。joint gate は双方 100%。

## 判定

```text
Gate A-accuracy: Not Passed
未達項目:
  - scenario-cluster 95% CI 下限 (826.7ms) が avg短縮ゲート 900ms を下回る（保守）
  - コスト純減は未達（推定同士で Jev 側がわずかに高い）
  - pilot 10 は製品安全の証明に使えない（Smoke のみ）
根拠:
  - 点推定の joint / avg / P95 は達成。方法論（seed_random・repeat10・cluster CI・gate accuracy）は充足。
  - 禁止語「条件付きPassed」を使わず、CI保守未達を残すため Not Passed。
次の改善:
  - warm 専用の追加 repeat または cold 除外後の CI 再計算設計を固定
  - OpenAI 実測コスト突合
  - Gate B は依然 Hard No-Go（人間医療承認・expanded FN）
```

Gate B / primary / staging / prod: **Hard No-Go**（変更なし）

## 証拠ラベル

| 項目 | ラベル |
| --- | --- |
| joint accuracy / latency warm / scenario-cluster CI / fallback 件数 | **実測**（`log/analysis/jev_intent_router_eval_10_20260922_012129.*`） |
| OpenAI saved（JPY） | **measured_proxy**（実測プロキシ。請求突合は未検証） |
| Jev cost / net saved | **estimated** |
| Gate B 医療 FN=0 / expanded 人間承認 / Focus 本番効果 | **未検証** |
| `log/jev_intent_router_shadow.jsonl` 本番相当サンプリング | **未検証**（ローカルにファイル未生成） |

