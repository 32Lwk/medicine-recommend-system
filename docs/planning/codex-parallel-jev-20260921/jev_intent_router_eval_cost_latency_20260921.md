# Jev IntentRouter 定量評価・コスト／レイテンシ試算

作成日: 2026-09-21  
担当: Agent B（定量評価とコスト試算）  
対象: `jev:minimal` のみ（本番配線は対象外）

## 1. 結論

- 基準レポート `log/analysis/jev_intent_router_eval_10_20260921_013619.{json,md}` では、current と `jev:minimal` はともに **30/30（100.0%）**。
- `jev:minimal` は current 比で **avg 919.50ms短縮、P50 580.08ms短縮、P95 2,622.76ms短縮**。
- latency Go 条件「avg 900ms以上、またはP95 2,500ms以上の短縮」は、**avg・P95の両方で達成（Go）**。
- Jev usage は平均 **input 1,358.5 tokens / output 367.7 tokens**。公式単価では **$0.000057057/call**（inputのみ課金）。参考換算を 1 USD = 157 JPY と置くと **約0.00896円/call**。
- IntentRouter の OpenAI cost を70%削減できた場合、OpenAI側は平均 **0.02814円/call削減**。Jev代を差し引いた純削減は **約0.01918円/call（元のOpenAI費比47.7%）**。したがって「OpenAI cost 70%削減」と「総支払額70%削減」は別指標として管理する必要がある。
- ただし今回の再計測は外部API接続拒否（`WinError 10061`）で完走できなかった。新規の不完全ログは採用せず、`013619` を最新の有効実測とする。
- `jev:with_baseline_triage` は確定方針どおり**非採用**。参考として既存 `013452` は9/10で、medicine comparisonを1件失敗している。今回このmodeは実行していない。

## 2. 根拠と評価条件

### 2.1 採用データ

| 用途 | 根拠 |
| --- | --- |
| 精度・latency・usage | `log/analysis/jev_intent_router_eval_10_20260921_013619.json` |
| 人間可読サマリ | `log/analysis/jev_intent_router_eval_10_20260921_013619.md` |
| 非採用modeの確認のみ | `log/analysis/jev_intent_router_eval_10_20260921_013452.{json,md}` |
| OpenAI分類コスト | `log/analysis/downloaded-logs-20260704-20260726-20260726-052450/sections/llm_cost.json` |
| 閾値・単価・確定方針 | `docs/planning/JEV_IMPLEMENTATION_TEST_PLAN_2026-09-21.md` §3, §8 |

`013619` は10シナリオを各3回実行した30件/backendで、`use_cache=false`、Jev modelは `jev-latest`。

### 2.2 今回の再計測

実行コマンド:

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONIOENCODING='utf-8'
python scripts/eval_jev_intent_router_10.py --jev-state-mode minimal --repeat 3
```

`.env` に `JEV_API_KEY` が存在することだけを確認し、値は表示していない。実行環境から外部APIへの接続が拒否され、current側で `openai.APIConnectionError` / `WinError 10061` が反復したため中断した。Jevを含む比較全体を完走できず、timestamp付きjson+mdは生成されていない。接続不能な実行を結果に混ぜるとaccuracy・latencyを歪めるため、新規結果は不採用とした。

## 3. 既存 `013619` の再解釈

### 3.1 backend別

| Backend | Accuracy | Passed | Avg ms | P50 ms | P95 ms | Min ms | Max ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| current | 100.0% | 30/30 | 1,456.28 | 1,112.62 | 3,216.91 | 15.30 | 3,830.97 |
| `jev:minimal` | 100.0% | 30/30 | 536.78 | 532.54 | 594.15 | 493.61 | 637.77 |

| 指標 | 短縮量 | 短縮率 | Speedup |
| --- | ---: | ---: | ---: |
| Avg | 919.50ms | 63.1% | 2.71x |
| P50 | 580.08ms | 52.1% | 2.09x |
| P95 | 2,622.76ms | 81.5% | 5.41x |

解釈: Jevの分布は493.61–637.77msと狭い。一方、currentはシナリオ依存のばらつきが大きく、P95短縮効果がavgより顕著。ただし10ケース×3回の小標本なので、本番トラフィックのtail latencyを保証する値ではない。

### 3.2 シナリオ別平均短縮

| シナリオ | Current ms | Jev ms | 短縮 ms | 短縮率 | 判定 |
| --- | ---: | ---: | ---: | ---: | --- |
| prompt injection | 3,368.01 | 536.54 | 2,831.46 | 84.1% | 大幅改善 |
| store locator | 2,272.64 | 553.82 | 1,718.82 | 75.6% | 大幅改善 |
| emergency breathing | 1,543.72 | 536.55 | 1,007.17 | 65.2% | 改善 |
| counseling insomnia/anxiety | 1,391.64 | 562.45 | 829.19 | 59.6% | 改善 |
| physical headache | 1,370.22 | 556.06 | 814.16 | 59.4% | 改善 |
| medicine side effect | 1,104.88 | 535.55 | 569.34 | 51.5% | 改善 |
| fever flow | 1,093.05 | 527.26 | 565.79 | 51.8% | 改善 |
| medicine comparison | 1,043.07 | 529.59 | 513.48 | 49.2% | 改善 |
| concierge architecture | 885.44 | 521.45 | 363.99 | 41.1% | 改善 |
| session delete | 490.13 | 508.57 | **-18.44** | **-3.8%** | 悪化 |

9/10シナリオで短縮。SessionOpsはcurrent fast-pathの方が18.44ms速く、確定方針どおり最初のprimary対象から外す根拠になる。

### 3.3 Jev usage

| 指標 | Input tokens | Output tokens |
| --- | ---: | ---: |
| 平均 | 1,358.5 | 367.7 |
| 最小 | 1,349 | 365 |
| 最大 | 1,373 | 371 |

課金対象はinputのみ。30 call合計inputは40,755 tokens、公式単価では **$0.00171171**。outputは無料。

## 4. コスト試算

### 4.1 Jev callコスト

計算式:

```text
1,358.5 tokens / 1,000,000 × $0.042 = $0.000057057/call
```

| 呼出数 | Jev input cost (USD) | 参考JPY（157円/USD） |
| ---: | ---: | ---: |
| 1 | $0.000057057 | 0.00896円 |
| 1,000 | $0.057057 | 8.96円 |
| 100,000 | $5.7057 | 895.79円 |
| 1,000,000 | $57.057 | 8,957.95円 |

JPY値は比較用の仮定であり、請求時の為替・手数料は未反映。`pipeline_perf` にはまずUSD原価を保存し、JPY換算レートも併記するのが安全。

### 4.2 既存OpenAI分類コスト

コストログの `recent_calls` をpath別に再集計した。

| Path | Calls | Avg cost JPY | Avg prompt tokens | Avg completion tokens | Total cost JPY |
| --- | ---: | ---: | ---: | ---: | ---: |
| `llm_triage.stage1` | 17 | 0.1022 | 3,310.4 | 95.1 | 1.7367 |
| `llm_triage.stage2` | 12 | 0.1147 | 3,729.2 | 93.3 | 1.3763 |
| `dialogue.intent_router_llm` | 9 | 0.0402 | 1,265.2 | 75.7 | 0.3620 |
| 分類系合計 | 38 | 0.0914（加重平均） | — | — | 3.4750 |

本担当のprimary対象はIntentRouterであり、stage1/2の削減は将来のtriage fan-out評価まで実現済み削減に含めない。

### 4.3 IntentRouter置換時の削減見込み

`dialogue.intent_router_llm` の現状平均0.0402円/callを基準にする。置換率をOpenAI call削減率と同一と仮定する。

| Jev primary成功率（OpenAI削減率） | OpenAI saved JPY/対象turn | Jev cost JPY/対象turn | 純削減 JPY/対象turn | 純削減率（現行OpenAI比） | ≥70% OpenAI目標 |
| ---: | ---: | ---: | ---: | ---: | --- |
| 50% | 0.02010 | 0.00896 | 0.01114 | 27.7% | 未達 |
| 70% | 0.02814 | 0.00896 | 0.01918 | 47.7% | **達成境界** |
| 80% | 0.03216 | 0.00896 | 0.02320 | 57.7% | 達成 |
| 100% | 0.04020 | 0.00896 | 0.03124 | 77.7% | 達成 |

注意: 表は「Jevを対象turnで1回呼び、失敗・低confidence時はOpenAIへfallbackする」前提。Jev shadowを常時併走する期間はOpenAI削減が発生せず、総額は約0.00896円/対象turn増える。70%目標の判定式は次のとおり。

```text
openai_reduction_rate
  = 1 - post_primary_dialogue.intent_router_llm_cost
        / pre_primary_dialogue.intent_router_llm_cost

合格: openai_reduction_rate >= 0.70
```

## 5. Go / No-Go判定

| 条件 | 最新実測 | 判定 |
| --- | ---: | --- |
| 10ケース精度 | current 30/30、Jev 30/30 | 合格 |
| avg短縮 ≥900ms | 919.50ms | **合格（+19.50ms）** |
| P95短縮 ≥2,500ms | 2,622.76ms | **合格（+122.76ms）** |
| latency総合（OR条件） | 両方合格 | **Go** |
| Emergency/Security/medical_examination FN=0 | 既存10ケース内のEmergency/Securityは合格。medical_examination専用fixtureなし | 条件付き／未完 |
| 拡張fixture 100% | emergency/security拡張集合は未計測 | 未判定 |
| OpenAI cost ≥70%削減 | primary運用ログなし | 未判定 |

したがって、**10ケースのaccuracyとlatencyに限ればGo**。一方、primary canary全体としては高リスク拡張fixture、disagreement、fallback率、実運用OpenAI cost削減が未計測なので、現時点の総合判定は **Phase 0継続／primary化はNo-Go**。

## 6. `pipeline_perf` 追加フィールド案

1リクエスト／1 decision単位で、次を構造化して記録する。

| フィールド | 型・例 | 意味 |
| --- | --- | --- |
| `jev_usage` | `{input_tokens: 1358, output_tokens: 368, cost_usd: 0.00005704, model: "jev-latest"}` | Jev実usageと原価。未呼出時は`null` |
| `latency_ms` | `{jev: 536.8, legacy: null, decision_total: 538.1}` | Jev、fallback legacy、decision全体を分離 |
| `fallback_reason` | `null`, `timeout`, `http_429`, `http_5xx`, `http_4xx`, `low_confidence`, `schema_error`, `high_risk_disagreement` | fallback分類。自由文ではなくenum |
| `legacy_saved_calls` | `{dialogue_intent_router_llm: 1, llm_triage_stage1: 0, llm_triage_stage2: 0, total: 1}` | 実際に省略できたlegacy call数 |
| `openai_cost_saved_estimate_jpy` | `0.0402` | 同path・同期間の対照平均を基にした推定削減。Jev代は差し引かない |
| `disagreement` | `{evaluated: true, any: false, primary: false, sub_route: false, safety: false, legacy_route: "Physical", jev_route: "Physical"}` | shadow/監査時の差分。未比較は`evaluated:false` |

合わせて以下も推奨する。

- `jev_attempted`, `jev_accepted`, `legacy_fallback_called`: call funnelを再構成するためのboolean。
- `jev_confidence`, `confidence_threshold`: low confidence率と閾値変更の影響確認。
- `cost_basis`: `{source_log, path, avg_cost_jpy, calculated_at}`。推定値の根拠を追跡可能にする。
- `usd_jpy_rate`: JPY換算した場合のレート。原価USDを上書きしない。
- `risk_flags`: `emergency`, `security`, `medical_examination`。高リスクdisagreementを抽出する。

## 7. 計測ギャップ

- 今回のrepeat=3再計測はネットワーク接続拒否で未完。`013619` の再現性を別時刻・別ネットワークで確認できていない。
- 10ケース×3回は母数が小さく、本番P95/P99、429、5xx、timeout、cold startを評価できない。
- `jev-latest` はversion pinされておらず、将来の再計測でモデル差が混入し得る。
- accuracyは期待route一致であり、confidence calibration、low-confidence fallback率を測っていない。
- medical_examinationを含む高リスク拡張fixtureがなく、FN=0を十分に立証できない。
- currentとJevを同一時刻・交互順で測る設計ではないため、ネットワーク時間帯差を排除できない。
- OpenAIコスト根拠は2026-07の38 classifier callsで標本が小さい。現行モデル・prompt・単価変更後の値か再確認が必要。
- `legacy_saved_calls` とOpenAI削減額はまだ本番相当のshadow/primaryログで実測されていない。
- `disagreement` はJev/legacy/executed routeの三者を同一request_idで結合した実測がない。

## 8. Phase 0 計測整備タスク

### P0-1: 再現可能な評価出力

- **主張:** 接続失敗と判定失敗を分離しないとaccuracyが壊れる。
- **根拠:** 今回は外部API接続拒否が発生し、完走前に中断した。
- **検証方法:** backendごとに`attempted/succeeded/api_error/eval_failed`を集計し、APIエラーをaccuracy分母から分離したレポートを生成する。
- **合格条件:** 接続失敗時にもjson+mdが生成され、有効sample数と失敗理由が明示される。
- **失敗時の次手:** backend単独実行（`--skip-current`等）と疎通1件のpreflightを先に行う。

### P0-2: latency統計の強化

- **主張:** 30件ではtail評価が不安定。
- **根拠:** latency閾値の余裕はavg 19.50ms、P95 122.76msと大きくない。
- **検証方法:** minimalのみ、各ケース最低10回、実行順をcurrent/Jevで交互またはランダム化し、P50/P95/P99とbootstrap CIを出す。
- **合格条件:** 95% CIの保守側でもavg 900msまたはP95 2,500ms短縮を満たす。
- **失敗時の次手:** route別primary対象を絞り、SessionOpsを明示的に除外する。

### P0-3: usage・コストの実測連携

- **主張:** 70%目標はOpenAI callの実削減で判定すべき。
- **根拠:** Jev代込みの純削減率とOpenAI削減率は一致しない。
- **検証方法:** `jev_usage`, `legacy_saved_calls`, path別OpenAI actual cost、Jev cost USDを同一requestに記録する。
- **合格条件:** 直近150件と累積の両方でOpenAI IntentRouter cost削減率を算出でき、70%以上。
- **失敗時の次手:** fallback理由上位を改善し、primary対象route／confidence閾値を再調整する。

### P0-4: disagreement・安全性

- **主張:** 100%の10ケースだけでは医療安全を保証できない。
- **根拠:** medical_examination専用fixtureと本番分布のdisagreementが未計測。
- **検証方法:** Emergency/Security/medical_examinationの拡張fixtureとshadowログを追加し、primary/sub/safety別に差分集計する。
- **合格条件:** 高リスクFN=0、高リスクdisagreement全件レビュー、Jev単独確定なし。
- **失敗時の次手:** 高リスクrouteは常時legacy/deterministic gate優先とし、Jevを補助判定に限定する。

### P0-5: model/version・環境固定

- **主張:** `jev-latest` のままでは時系列比較が崩れる。
- **根拠:** alias更新が評価差に混入し得る。
- **検証方法:** model version、fixture hash、git SHA、timeout、retry、実行host、timestampをレポートへ保存する。
- **合格条件:** 同条件の再実行を機械的に識別できる。
- **失敗時の次手:** shadow中はaliasと解決versionを併記し、primary前にversion pinする。

## 9. 他エージェントへの依頼メモ

- 実装担当: 本番配線ではなくPhase 0の計測schema案として、`pipeline_perf` に第6節のフィールドを入れられるイベント境界と既存schema互換性を確認してほしい。
- 安全性担当: Emergency/Security/medical_examinationの追加fixtureを作り、FN=0と二重ゲートを検証してほしい。特にmedical_examinationは現10ケースに専用例がない。
- 評価基盤担当: minimal専用の疎通preflight、backend別エラー集計、交互実行、10 repeat以上、CI算出を評価スクリプト拡張案にしてほしい。`with_baseline_triage` は実行対象に含めない。
- 運用／コスト担当: current期間とprimary期間の `dialogue.intent_router_llm` actual costを同じ集計窓で比較し、為替レートを分離した総支払額も併記してほしい。
- 統合担当: 10ケースではlatency Goだが、primary化の総合判定はPhase 0未完のNo-Goとして計画へ反映してほしい。SessionOpsはprimary対象外を維持する。

