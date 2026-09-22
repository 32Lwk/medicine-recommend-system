# Agent E: Independent Adversarial Review（Round 1）

> ## ERRATUM（2026-09-22 Agent G）
>
> Round1 時点の「live 未実行」は **歴史記述**。現行 live `012129` 実行後も Gate A-accuracy = **Not Passed** / Gate B = **Hard No-Go**（`JEV_GATE_A_ACCURACY_VERDICT_20260922.md`）。


- Role: Independent Adversarial Reviewer（実装非担当・破壊的レビューのみ）
- Date: 2026-09-22
- Scope: Agents A/B/C/D Round 1 成果 + Supervisor intake / ownership
- Method: コード監査 + A/B 採点ドリフトの実行再現（`.venv\Scripts\python.exe`）
- 自己採点: **禁止（本文書に自己スコアなし）**
- 改修: **なし**（修正案は各指摘の「推奨修正」のみ）

**正式ゲート語（本レビューの前提）:** Gate A-accuracy = **Not Passed** / Gate B = **Hard No-Go**（ownership 表固定）。本 Round 1 の unit green はゲート語を動かさない。

---

## 必確認 14 項目 — 即時判定

| # | 項目 | 判定 | 要約 |
| --- | --- | --- | --- |
| 1 | fixture 実装都合ラベル | **Pass（Round1差分）** | Round1 でラベル改変なし。ただし pilot は Emergency に sub 期待なし・`required_safety_action` 不在で joint が薄い（持ち越し） |
| 2 | mock だけ通って live で壊れる | **Fail** | C の障害網羅は httpx mock のみ。A live 未実行。TLS/実 API schema/接続暖機は未検証 |
| 3 | alias で誤分類を隠す | **Fail** | B/D の alias は意図的。A の disagreement 集計は alias で差分消滅。B 採点は alias で joint 水増し可能 |
| 4 | SafetyGate bypass | **条件付 Pass（Phase1）** | shadow は legacy 固定。ただし `effective_high_risk` は本番未配線。PRIMARY 将来配線時の抜け道は未閉塞 |
| 5 | API failure 本線伝播 | **Pass（例外）** | client/router fail-open。ただし schedule 前の同期 `deepcopy` / medicine resolve は本線レイテンシを侵食 |
| 6 | 非独立測定の水増し | **Fail** | request-level bootstrap 残存・repeat 相関。survivor accuracy。cold n=1 |
| 7 | 速度と精度の母集団 | **Fail** | 双方 `api_error` 除外だが backend 間で scored n がズレる。対比較は対ある行のみ |
| 8 | 推定を実測と呼ぶ | **条件付 Fail** | A は `estimated`/`measured_proxy` 分離。D の `jev_cost_usd` 互換エイリアスは semantics 外で誤読誘発 |
| 9 | eval が `score_joint_decision` 未使用 | **Fail（Critical）** | A 独自 `_evaluate_prediction`。実行再現で B と不一致 |
| 10 | interleaved が実質バッチ | **条件付 Fail** | 全件バッチは廃止。だが case 内は常に current→jev の擬似 interleaved |
| 11 | cold 定義が n=1 | **Fail** | backend 初回1件のみ cold。P95/stdev 無意味 |
| 12 | Gate 抜け道・誤った成功主張 | **Fail** | risk_flags で safety 合格、forbidden 無視、Emergency sub 未採点。Supervisor は Gate 語維持（良い）が intake「受理」は甘い |
| 13 | `jev_cost_usd` 互換誤読 | **Fail** | トップレベルに残存。`field_semantics` に alias キー無し |
| 14 | PRIMARY がどこかで読まれる | **Pass（実行経路）** | `jev_client`/`jev_router` 非参照。`resolve_route` は常に legacy。flag getter とテストのみ |

---

## Critical

### E-C1. Eval が Agent B 契約を独自再実装（ドリフト確定）

| 項目 | 内容 |
| --- | --- |
| 対象Agent | **A**（主）/ **B**（契約正本・未配線） |
| ファイル | `scripts/eval_jev_intent_router_10.py`（`_evaluate_prediction` / `_evaluate_safety_action`）vs `src/services/jev_decisions.py`（`score_joint_decision`） |
| 再現条件 | 同一 expect/actual を両関数に通す（本レビューで実行） |
| 実測ドリフト | `alias_sub`: A=`False` / B=`True`；`forbidden_in_accept`: A=`True` / B=`False`；`safety_risk_flags`: A=`True` / B=`False`；`emergency_fp`: A=`False` / B=`True` |
| なぜ本番で壊れるか | Gate A-accuracy / Gate B の「joint」が eval と decisions で別物になる。live で「精度 XX%」と出ても B 契約・soft harness・将来 CI と不一致。合格/不合格が harness 選択で変わる |
| 推奨修正（担当へ） | **Agent A:** `_evaluate_prediction` を削除し `score_joint_decision` を唯一の採点入口にせよ。transport_ok / forbidden / alias / scoring flags を二重実装するな。差分テストを A の unit に追加せよ。**Agent B:** 公開 API のフィールド名を eval レポートに直結できるよう安定契約を文書化せよ |
| ゲートへの影響 | **Gate A-accuracy 証拠として Round1 eval は不合格。** 配線前の live 数値は棄却級 |

### E-C2. required_safety を risk_flags 部分集合で「合格」にする抜け道

| 項目 | 内容 |
| --- | --- |
| 対象Agent | **A** |
| ファイル | `scripts/eval_jev_intent_router_10.py` `_actual_safety_tokens` / `_evaluate_safety_action` |
| 再現条件 | `expect.required_safety_action="prescription_block"` かつ actual に `safety_action` 無し・`meta.risk_flags=["prescription_block"]` のみ → A joint **True**、B joint **False** |
| なぜ本番で壊れるか | フラグが立っただけで「安全アクション実行」と採点される。SafetyGate / block 未到達でも accuracy が上がる。fixture に safety キーが載った瞬間に **偽 Pass** |
| 推奨修正（担当へ） | **Agent A:** safety 照合を B と同じく `safety_action`（または明示の executed action）の一致に限定せよ。`risk_flags` を required_safety の充足に使うな |
| ゲートへの影響 | Gate B soft/hard の safety AND を汚染。Critical/High 未解決として **Hard No-Go 維持** |

---

## High

### E-H1. cold/warm が backend あたり n=1（統計として無意味）

| 項目 | 内容 |
| --- | --- |
| 対象Agent | **A** |
| ファイル | `scripts/eval_jev_intent_router_10.py` `_build_eval_schedule`（`seen_backend`）；unit が cold n==1 を固定化 |
| 再現条件 | interleaved + 任意 repeat≥2。各 backend の最初の1 job のみ `cold` |
| なぜ本番で壊れるか | cold P95/stdev をレポートに載せると「分離した」ように見えるが母数1。warm 偏重の overall P95 と混同され、レイテンシゲートを誤読する |
| 推奨修正（担当へ） | **Agent A:** cold を「プロセス/接続確立後の最初の K 回」または「専用 cold-only 先行パス」と定義し直し、n&lt;閾値なら統計を `null` + `insufficient_n` にせよ。n=1 の P95 を出すな |
| ゲートへの影響 | Gate A-accuracy の latency 条項を cold/warm で主張不可 |

### E-H2. 「interleaved」は case 内 current→jev 固定（擬似 interleaved）

| 項目 | 内容 |
| --- | --- |
| 対象Agent | **A** |
| ファイル | `_build_eval_schedule` order=`interleaved` |
| 再現条件 | default order。各 scenario で常に `current` の直後に `jev:*` |
| なぜ本番で壊れるか | 全件バッチよりマシだが、Jev 常に同一ケースの current 実行後。CPU/接続/キャッシュの暖機が backend 非対称。レイテンシ差 CI が方法論的に汚染されたまま |
| 推奨修正（担当へ） | **Agent A:** (1) backend 順を seed でケースごとにランダム化、(2) または true random を default にし baseline 依存だけ遅延、(3) レポートに「case-paired sequential（current-first）」と明記し interleaved と呼ぶな |
| ゲートへの影響 | 速度比較を Gate 証拠に使えない（参考値扱い強制） |

### E-H3. accuracy と latency の母集団が backend 間で不一致（survivor bias）

| 項目 | 内容 |
| --- | --- |
| 対象Agent | **A** |
| ファイル | `_scored_rows` / `_summarize` / `_pair_latencies` |
| 再現条件 | 一方 backend だけ `api_error`/`connection_error` が増える live |
| なぜ本番で壊れるか | 精度%は輸送成功行のみ。失敗が多い backend の accuracy が「成功したものだけ」で高く見える。latency summary の n も backend でズレる。対比較 CI は両成功ペアのみで別母集団 |
| 推奨修正（担当へ） | **Agent A:** レポートに `attempted` / `scored` / `paired_n` を必須表示。accuracy は (a) scored-only と (b) attempted を分母にした失敗=不正解の二系統を出せ。Gate 判定は母集団定義を固定文書化 |
| ゲートへの影響 | 単一 accuracy% での A-accuracy Pass 主張を禁止 |

### E-H4. alias / emergency_fp が誤分類を joint 成功に変換（B）＋ disagreement 隠蔽（A）

| 項目 | 内容 |
| --- | --- |
| 対象Agent | **B**, **A**, **D** |
| ファイル | `jev_decisions.normalize_sub_route_for_scoring` / `score_joint_decision`（emergency_fp 時 sub 拡大）；`eval._collect_disagreements`（alias 正規化で差分消滅）；`jev_metrics.normalize_sub_route` |
| 再現条件 | Emergency `chest_pain_*` vs `emergency_dispatch`；`scoring.emergency_fp_tolerated` + Emergency/medical_examination/none |
| なぜ本番で壊れるか | 命名差以上の臨床差を同一視すると、誤 sub が Gate 通過に見える。disagreement 一覧が空でも raw ラベルは不一致 |
| 推奨修正（担当へ） | **Agent B/F:** alias を「命名のみ」と薬剤師が文書承認するまで scoring デフォルト OFF、または raw/normalized 両方をレポート。emergency_fp の sub 自動拡大をやめ、alternate primary のみに限定。**Agent A:** disagreement は raw 必須・normalized は別欄 |
| ゲートへの影響 | Gate B accuracy 水増しリスク。Hard No-Go 維持根拠 |

### E-H5. `effective_high_risk` / joint helper が本番経路に未配線（契約の紙だけ）

| 項目 | 内容 |
| --- | --- |
| 対象Agent | **B**（実装）/ **Supervisor**（router 所有） |
| ファイル | `jev_decisions.py`（定義のみ）；`src/` 他に参照ゼロ |
| 再現条件 | `rg effective_high_risk` → decisions とテスト以外なし |
| なぜ本番で壊れるか | 「OR で Jev 陰性解除禁止」を満たしたように読めるが、SafetyGate / PRIMARY 実行経路は別。PRIMARY 有効化時に helper 未接続だと **真の bypass** |
| 推奨修正（担当へ） | **Supervisor:** PRIMARY 配線前に `effective_high_risk` を gate/router の必須経路に接続。未接続のまま「fail-safe 完了」と書くな。**Agent B:** モジュール docstring に「本番未配線」を赤字で残せ |
| ゲートへの影響 | Gate B / primary canary 前の必須未完 |

### E-H6. shadow ON 時の同期コストが本線を侵食（fail-open ≠ 無料）

| 項目 | 内容 |
| --- | --- |
| 対象Agent | **C**（主）/ **Supervisor**（`router._maybe_schedule_jev_shadow`） |
| ファイル | `jev_router.build_jev_router_state`（`_medicine_names` 等）、`schedule_jev_shadow`（`deepcopy`）、`router.py` 呼び出し |
| 再現条件 | `JEV_ENABLED`+shadow ON。毎リクエストで state 構築+deepcopy+（条件により）薬品解決 |
| なぜ本番で壊れるか | API 例外は本線に出ないが、同期処理で P95 が悪化。dev shadow 有効化で「本線非干渉」がレイテンシ意味で破綻 |
| 推奨修正（担当へ） | **Agent C / Supervisor:** state 構築を executor 内へ移す、または予算付き・計測付き。deepcopy 二重（worker 内でも再実行）をやめよ。本線前後に shadow schedule ms をメトリクス化 |
| ゲートへの影響 | Gate B / dev shadow 前に「本線レイテンシ中立」未証明 |

### E-H7. Runtime「完了」は mock 緑のみ — live 壊れ余地

| 項目 | 内容 |
| --- | --- |
| 対象Agent | **C** |
| ファイル | `tests/services/test_jev_client.py`（全面 mock）、Agent C 報告「58 passed」 |
| 再現条件 | unit のみ。実 TypeSafe・DNS・TLS・429 実レート未実施 |
| なぜ本番で壊れるか | mock の例外分類と実 httpx/HTTP2/プロキシ配下の挙動は別。schema 変化・部分 JSON・usage 欠落の本番組合せは未踏 |
| 推奨修正（担当へ） | **Agent C:** staging 向け契約テスト（または recorded cassette）を必須化。Round1 を「mock reliability」と改名し Runtime Complete と呼ぶな |
| ゲートへの影響 | A-code の「本番耐性」過大解釈を禁止 |

### E-H8. `jev_cost_usd` 互換エイリアスが semantics 外

| 項目 | 内容 |
| --- | --- |
| 対象Agent | **D** |
| ファイル | `src/services/jev_metrics.py` record payload；`build_cost_payload.field_semantics` |
| 再現条件 | `field_semantics` に `jev_cost_usd` キーなし。トップレベル `jev_cost_usd == jev_cost_usd_estimate` |
| なぜ本番で壊れるか | ダッシュボード/手集計が短いキーを実測 USD と誤読し、70% 削減判定を汚染 |
| 推奨修正（担当へ） | **Agent D:** (1) `field_semantics["jev_cost_usd"]="estimated_compat_alias"` を必須、(2) 可能なら alias を非デフォルト/段階削除、(3) 集計サンプルに「`jev_cost_usd` を actual 扱いしたら Fail」テスト |
| ゲートへの影響 | Gate B cost 条項の証拠資格なし（現状 OpenAI actual 未配線と合わせて） |

### E-H9. pilot joint が safety を採点不能（キー不在）なのに「joint」と呼ぶ

| 項目 | 内容 |
| --- | --- |
| 対象Agent | **A**, **B**, fixture 所有 **F** |
| ファイル | `tests/fixtures/jev_intent_router_eval_10.yaml`；A/B の「未定義=採点外」 |
| 再現条件 | pilot 全件に `required_safety_action` なし。Emergency は sub 期待もなし |
| なぜ本番で壊れるか | primary(+sub) だけの「joint」を Gate 用語と混同すると、safety 未検証のまま精度合格に見える |
| 推奨修正（担当へ） | **Agent A:** レポート見出しを `joint_primary_sub` / `joint_with_safety` に分離。safety unscored 比率を必須表示。**F:** safety fixture 無しの数値を A-accuracy に使うな |
| ゲートへの影響 | Gate A-accuracy / B の joint 定義不一致 |

---

## Medium

### E-M1. request-level bootstrap 残存による楽観 CI

| 項目 | 内容 |
| --- | --- |
| 対象Agent | **A** |
| ファイル | `_bootstrap_latency_diff_ci` + `_bootstrap_scenario_cluster_latency_diff_ci` |
| 再現条件 | repeat≥2。request-level が同一 scenario 内相関を無視 |
| なぜ本番で壊れるか | 狭い CI を「有意」と誤読。cluster 併記は改善だが、要約が request-level を主にすると水増し |
| 推奨修正 | Gate 判定は **scenario_cluster のみ**。request-level は deprecated 表示 |
| ゲートへの影響 | 旧 033321 級の楽観再現を許す |

### E-M2. Agent C の `exc_info`「除去済」主張が過大

| 項目 | 内容 |
| --- | --- |
| 対象Agent | **C** |
| ファイル | `jev_router.py`（`_medicine_names` / `_active_symptoms` で `exc_info=True` 残存）；Supervisor 所有 `router.py` も schedule skip で `exc_info=True` |
| 再現条件 | 当該経路で例外 |
| なぜ本番で壊れるか | Bearer 直撃経路ではないが、例外チェーンに request 文脈が載る余地。報告が「除去済」だと監査が緩む |
| 推奨修正 | 残存 `exc_info` を全廃するか、秘密非含有を証明するテスト。報告を「API 経路のみ除去」に訂正 |
| ゲートへの影響 | secret 契約の証跡弱い |

### E-M3. inline httpx fallback が「評価」と「本番クライアント」を混同

| 項目 | 内容 |
| --- | --- |
| 対象Agent | **A** |
| ファイル | `_resolve_jev_stack` / `_evaluate_jev` fallback 分岐 |
| 再現条件 | production import 失敗時 |
| なぜ本番で壊れるか | fallback 経路の数値を本番 stack の証拠にすると、retry/metrics/parse 契約が別物 |
| 推奨修正 | fallback 実行時は Gate 証跡を自動 invalid。`fallback_count>0` なら Not Passed 強制 |
| ゲートへの影響 | 偽の production 契約評価 |

### E-M4. OpenAI `measured_proxy` と saved_estimate の語感汚染

| 項目 | 内容 |
| --- | --- |
| 対象Agent | **A**, **D** |
| ファイル | eval `_openai_cost_from_calls`；metrics `openai_cost_*_saved_estimate` |
| 再現条件 | コスト比較表だけ読む |
| なぜ本番で壊れるか | `measured_proxy` は請求書ではない。`saved` は対照推定。請求削減と誤読されやすい |
| 推奨修正 | レポート冒頭に「invoice なし」。`saved` を `counterfactual_estimate` に改名検討 |
| ゲートへの影響 | Gate B cost 誤判定 |

### E-M5. medical_examination ↔ Emergency enum 流用（持ち越し High 相当だが Round1 未着手）

| 項目 | 内容 |
| --- | --- |
| 対象Agent | **B** / **F** |
| ファイル | `parse_jev_answers` / `_deterministic_override`；Supervisor intake B |
| 再現条件 | medical_examination ケース |
| なぜ本番で壊れるか | primary=Emergency のまま clinically 異なる経路が同一 primary 精度に吸収 |
| 推奨修正 | F レビュー付きで primary/sub 契約を分離。エンジニア都合の同一視禁止 |
| ゲートへの影響 | Gate B 前に未解消なら Hard No-Go |

### E-M6. atexit `wait=False` による in-flight 観測欠損

| 項目 | 内容 |
| --- | --- |
| 対象Agent | **C** |
| ファイル | jev_router shutdown；Agent C「未解決」 |
| 再現条件 | Cloud Run インスタンス終了直前の shadow |
| なぜ本番で壊れるか | disagreement / 障害率が過小。可用性ログが楽観的 |
| 推奨修正 | グレースフル drain 契約 or shutdown 時 `shadow_dropped` カウンタ必須 |
| ゲートへの影響 | Gate B log completeness |

### E-M7. Supervisor intake の「Round1 受理」が Critical 未解決と矛盾しうる読み

| 項目 | 内容 |
| --- | --- |
| 対象Agent | **Supervisor / G** |
| ファイル | `JEV_SUPERVISOR_INTAKE_AGENT_*_20260922.md` |
| 再現条件 | 「受理」=方法論完了と読まれる |
| なぜ本番で壊れるか | A の B 未配線を intake 自身が指摘しつつ受理。組織的に Round1 Passed と誤読されうる |
| 推奨修正 | 「受理」を「差分受領 / Gate 非変更」と定義し、**Round1 Verdict: Not Passed（統合未完）** を明記 |
| ゲートへの影響 | プロセス上のゲート抜け道 |

---

## Low

### E-L1. fixture に `delete`/`delete_confirm` 両載（実装都合の匂い・Round1 非改変）

| 項目 | 内容 |
| --- | --- |
| 対象Agent | fixture / **F**（ラベル） |
| ファイル | `jev_intent_router_eval_10.yaml` session-delete |
| 再現条件 | なし（現状） |
| なぜ本番で壊れるか | alias 無しでも通すための両載は、正規化方針を曖昧にする |
| 推奨修正 | F が単一 canonical に揃え、alias は scoring 層のみ |
| ゲートへの影響 | 低（現状は明示 accept） |

### E-L2. Agent C/D 報告の自己評価表（禁止語に近い温度）

| 項目 | 内容 |
| --- | --- |
| 対象Agent | **C**, **D** |
| ファイル | 各 Agent 報告の自己評価セクション |
| 再現条件 | 文書読解 |
| なぜ本番で壊れるか | 「提出可能」「A-」が Gate 語と並ぶと誤読。ownership は自己採点禁止意図と整合しにくい |
| 推奨修正 | 自己評価欄削除。事実（pytest 数・未配線）のみ |
| ゲートへの影響 | 文書汚染（実行は不変） |

### E-L3. PRIMARY flag getter の存在自体が誤配線誘発

| 項目 | 内容 |
| --- | --- |
| 対象Agent | **C** |
| ファイル | `config/llm_flags.py` `is_jev_intent_router_primary_enabled` |
| 再現条件 | 将来の PR が getter を router に接続 |
| なぜ本番で壊れるか | 実行非参照でも「ON にすれば効く」と誤解。現状テストは防波堤 |
| 推奨修正 | Phase1 中は getter を `NotImplemented` / 常に False + 警告、または import 時 assert |
| ゲートへの影響 | primary Hard No-Go の防衛力強化 |

---

## 必確認ごとの証拠メモ（短）

1. **fixture:** Round1 diff でラベル変更なし（Agent 報告・ownership 一致）。pilot の薄さは別問題（E-H9）。
2. **mock/live:** C=httpx mock；A live 未実行（自己申告どおり）。
3. **alias:** B/D 二重表+同期テストはドリフト検知になるが、採点側で誤分類を隠す能力そのものは残存。A disagreement は意図的に alias 無視。
4. **SafetyGate:** Phase1 `resolve_route` 常に legacy。bypass は「将来 PRIMARY + OR 未配線」が本命（E-H5）。
5. **API 伝播:** worker/schedule は例外を握りつぶす。同期コストは別（E-H6）。
6. **非独立:** request-level CI・repeat・cold n=1。
7. **母集団:** `_scored_rows` 共通フィルタでも backend 間 n 不一致；pair は交差のみ。
8. **推定≠実測:** A は概ね分離。D alias が穴（E-H8）。
9. **ドリフト:** 実行再現で確定（E-C1/C2）。
10. **interleaved:** 全件バッチ解消。current-first 固定（E-H2）。
11. **cold n=1:** コード+unit で固定化。
12. **Gate 抜け道:** safety risk_flags、forbidden 無視、薄い joint。エージェントは Gate 語を上げていない点は評価するが、**Round1 を Passed 扱いするな**。
13. **jev_cost_usd:** 互換残存・semantics 非掲載。
14. **PRIMARY:** 実行経路非読取をソース/テストで確認。`router.py` はコメントのみ。

---

## Round 1 を Passed 扱いにしてよいか

### 判定: **No**

**理由（短縮）:**

1. **Critical が複数未解決**（E-C1 採点ドリフト、E-C2 safety 抜け道）。ownership 完了条件「Critical/High 未解決が1件あれば次ゲート Hard No-Go」に直撃。
2. live 未実行のまま方法論コードだけ緑でも **Gate A-accuracy は Not Passed のまま**であり、Round1 全体を Passed と呼ぶと禁止語「実質合格」と同型の誤読を生む。
3. cold n=1・擬似 interleaved・survivor accuracy・コスト alias により、Round2 live を走らせても **証拠資格が自動的に付かない**。

### 条件付きで「差分受領」してよい範囲（Passed ではない）

次を **すべて**満たす場合に限り、Supervisor は「Round1 成果物受領 / 統合候補」と書いてよい。**Passed と呼ぶな。**

- A が `score_joint_decision` に一本化し、E-C1/C2 の再現ケースが unit で B と一致
- cold 統計が `insufficient_n` で黙る / interleaved の current-first バイアスを文書+設計で解消
- D が `jev_cost_usd` 誤読防止を semantics/テストで閉塞
- C が「mock-only」を報告上認め、本線同期コストを計測対象化
- Gate 語は引き続き **A-accuracy: Not Passed / B: Hard No-Go**

---

## 差戻し優先度（担当への一文）

| 優先 | 担当 | 一文 |
| --- | --- | --- |
| P0 | A | `score_joint_decision` に切り替え、risk_flags safety 合格を殺せ |
| P0 | A | cold n=1 統計を出すな。current-first interleaved を方法論違反として直せ |
| P1 | B+Supervisor | `effective_high_risk` 未配線を「完了」扱いするな。PRIMARY 前に接続契約を書け |
| P1 | D | `jev_cost_usd` を semantics 付き estimated と明示するか削除せよ |
| P1 | C | mock 完了≠本番完了。schedule 同期コストを本線中立の敵と認識せよ |
| P2 | G/Supervisor | intake「受理」を Passed と読ませるな。Round1 Verdict = Not Passed（統合未完） |

---

*Agent E — Independent Adversarial Review — 2026-09-22. コード改修なし / commit・push なし / fixture 非改変。*
