# Jev IntentRouter 敵対的評価（Worker E / Independent）

- Role: Independent Adversarial Evaluator（実装なし・Gate 閾値変更なし・Passed 主張禁止）
- Date: 2026-09-22（AE5 + **AE6 Eligibility v1 / Gate A v2**）
- Live 証跡: `log/analysis/jev_intent_router_eval_10_20260922_012129.json`（`use_cache=false`）— **旧契約のみ**（`scenario_cluster` cold+warm）。Gate A v2 live は未実行。
- 契約 freeze（ユーザー Option B）: `evaluation_contract_version=jev-intent-gate-a-v2` / `eligibility_contract_version=jev-intent-eligibility-v1` / Gate CI=`scenario_cluster_eligible_warm`
- 先行: `JEV_ADVERSARIAL_AGENT_E_ROUND4_20260922.md` / 本ファイル AE5 節
- 方法: コード読取監査 + 決定論ハーネス再現（ineligible→`accuracy_gate_pct` 水増し）+ 共有モジュール / `schedule_jev_shadow` / 3-track 配線照合。**fixture・閾値・本番コードは未変更（監査のみ）**

**ゲート語（本報告も不変）:** Gate A-accuracy = **Not Passed** / Gate B = **Hard No-Go**  
禁止語: 「条件付き Passed」「実質 Pass」「ほぼ合格」等の soft Pass。

---

## 0. 裁定（先に結論）

### Gate A-accuracy は引き続き Not Passed で正しいか？

**YES（Not Passed 維持が正しい）**

理由（いずれも Gate 正本契約に対する未達または未解消汚染）:

1. **実測** live `012129` の `scenario_cluster` CI 下限 **826.7ms &lt; 900ms**（旧契約正本）。
2. **実測→再計算** warm-only でも CI 下限 **≈835ms &lt; 900ms**（旧母集団でも Fail）。
3. Option B（eligible-warm）はユーザー承認済みだが、**v2 契約での live 再計測が未実施**。`012129` を Pass 根拠に転用してはならない。
4. **AE6-C1（Critical Open）:** `summaries[].accuracy_gate_pct` が ineligible 行（current ルート複製）を分母に入れ得る。tracks 集計と二重定義 — Gate 精度語を信頼できない。
5. SessionOps のシナリオ ID 黙排除は見つからず（契約どおり eligibility）。ただし **精度サマリの抜け道は残存**。

---

## 1. Supervisor 指摘の検証

| # | Supervisor 指摘 | 判定 | ラベル | 証拠 |
| --- | --- | --- | --- | --- |
| 1 | `scenario_cluster` CI が歴史的に cold+warm 混在；warm-only 再計算でも CI 下限 ≈825ms &lt; 900 | **確認** | 実測 / 実測（再計算） | JSON `latency_ci.scenario_cluster` mean=1349.24・CI=[826.7, 1943.02] は **cold+warm の scenario mean-of-means と一致**。warm-only 再計算 mean≈1332・CI_low≈835。worktree は `scenario_cluster_warm` を Gate 正本化するが **012129 成果物は旧キーのみ**（`scenario_cluster_warm` キー無し） |
| 2 | `jev-session-delete` warm mean delta ≈ −73ms | **確認** | 実測 | warm current mean 154.88 − jev 228.02 = **−73.14ms** |
| 3 | session-delete: triage≈0.14ms、runs1–9 total≈13.5ms、Jev≈200–270ms | **確認**（run0 例外あり） | 実測 | triage 全 run ≈0.13–0.29ms。runs1–9 latency ≈13.4–13.9ms。Jev 199–271ms。**run0 current のみ 1426ms**（下記 M2） |
| 4 | `use_cache=false` でも短絡 → deterministic SessionOps / triage 非対称 | **確認** | 実測 + コード | JSON `use_cache: false`。`llm_triage._session_admin_fast_path` が LLM 省略；`gate.py` `session_admin_probe` が即 SessionOps。キャッシュ不使用でも再現 |
| 5 | `jev-concierge-architecture` も triage≈0（warm 10/10）→ delta を不公正に歪めるか | **部分確認 / 影響は限定** | 実測 | triage 全 warm ≈0.10–0.18ms。ただし **route は `intent_router_llm` で ≈910–1481ms**。warm delta = **+851ms**（Jev 有利）。単独除外しても CI_low≈824 のまま Fail。session-delete 型の「current が常勝」汚染ではない |
| 6 | session-delete 単独除外で CI 下限 ≈1040 — 感度のみ、黙排除禁止 | **確認** | 実測（感度） | warm bootstrap 除外後 mean≈1489・CI_low≈**1041**。**推奨排除ではない**。Pass 主張への転用は Hostile |

---

## 2. Latency Gate 失敗の分類

| 分類 | 寄与 | 説明 |
| --- | --- | --- |
| A. 方法論バグ（cold/warm） | **寄与あり・単独原因ではない** | live 正本 CI は cold+warm 混在。warm-only に直しても CI_low≈835&lt;900 で **Fail 継続** |
| B. 不公正比較（deterministic vs API） | **寄与大（session-delete）** | current は keyword/gate 短絡（≈13ms）、Jev は毎回 API（≈200–270ms）。Δ が負になり cluster 分散と下限を押し下げ |
| C. 真の Jev 遅さ（全体） | **否定（本 pilot 範囲）** | 他 9 シナリオの warm Δ は +851〜+3489ms。Jev warm mean≈241ms。失敗主因は「Jev が全般的に遅い」ではない |
| D. SessionOps 除外による fixture overfit | **高リスク（未実行だが感度で実証）** | 除外で閾値超えに見える。**承認なき黙排除 = チート** |

**総合裁定:** Gate latency 未達は **(A) の残渣 + (B) の構造的非対称** が主因。**(C) 単独では説明できない**。**(D) で Pass を作るのは不正**。

---

## 3. 抜け道・チート経路監査

| 経路 | 状態 | ラベル | 所見 |
| --- | --- | --- | --- |
| `sub_accuracy_exempt` 精度水増し（E4-H1） | **契約 Open / 本 live は未発火** | 実測 + コード | live `exempt_n=0`。worktree は exempt 転送 + `accuracy_gate_pct` 除外済。**score_joint_decision の exempt→sub 自動パス契約は残存** |
| alias 隠蔽 | **観測は残る / joint は alias 通過** | 実測 | disagreements 20件中 alias_only 16（Emergency sub + `delete`↔`delete_confirm`）。raw は残置。joint 100% は alias 契約依存 — **隠滅ではないが採点緩和** |
| timeout padding | **未検出** | 実測 | timeout CLI は失敗分類用。sleep/pad なし。retry/fallback=0 |
| cache 不公正 | **未検出（本 run）** | 実測 | `use_cache=false`。短絡はキーワード経路 |
| request-level 楽観 CI（E4-H2） | **live 成果物は旧；worktree Closed 寄り** | 実測 + コード | JSON は request-level を deprecated 併記し top を scenario_cluster 化済だが **population=all**。worktree は `gate_canonical=scenario_cluster_warm` |
| シナリオ黙排除 | **禁止（感度のみ）** | 推定（動機） | CI を 900 超に見せる最短経路。Supervisor/本 Worker とも **Forbidden without approval** |
| SessionOps run0 の focus_llm 混入 | **測定汚染** | 実測 | run0 のみ `medicine_qa/focus_llm` measured_proxy あり・route 1426ms。decision は gate SessionOps。平均 Δ を current 側に押し上げ（Jev にやや有利）。runs1–9 の決定論短絡結論は揺るがない |

---

## 4. Critical / High / Medium 一覧

### Critical

| ID | 状態 | 要約 |
| --- | --- | --- |
| （新規なし） | — | Round4 E-C1/C2 は Closed 維持。本 live で「偽 Pass」を成立させた Critical 抜け道は未検出。**未達のまま Not Passed が正しい** |
| E-C1 / E-C2 | **Closed** | Round4 実行再現どおり |

**Critical count: 0（open） / 過去 Critical は Closed**

### High

| ID | 状態 | 要約 | ラベル |
| --- | --- | --- | --- |
| AE5-H1 | **Open** | live CI 正本が cold+warm 混在。warm-only でも CI_low&lt;900 | 実測 |
| AE5-H2 | **Open** | SessionOps deterministic vs Jev API の latency 非対称（Δ≈−73ms）が Gate CI を押し下げ | 実測 + コード |
| AE5-H3 | **Open（手続）** | SessionOps 除外感度で CI_low≈1041 — **黙排除は overfit / チート**。ユーザー承認必須 | 実測（感度） |
| E4-H1 | **Partial** | 観測・Gate accuracy 分母は worktree で緩和。**exempt 契約自体は Open** | コード / 実測(exempt=0) |
| E4-H2 | **Partial Closed（コード） / Open（証跡）** | worktree は warm 正本化。**012129 再実行前は Gate 証跡が古い** | コード / 実測 |
| E-H5 | **Open** | `effective_high_risk` 本番未配線（文書警告のみ） | 未検証（本番） |
| E-H6 | **Open** | shadow 同期コスト | 未検証 |
| E-H7 | **Open** | mock≠live Runtime | 部分実測（本 live production transport） |
| E-H9 | **Open** | pilot joint に safety カバレッジ不足（fixture 非改変） | 実測（pilot 範囲） |

**High count（Open + Partial を含む残件）: 9**  
（完全 Closed にした High は本ラウンド新規ではなし。E4-H2 はコード側のみ部分閉鎖。）

### Medium

| ID | 状態 | 要約 | ラベル |
| --- | --- | --- | --- |
| AE5-M1 | **Open（低影響）** | architecture triage≈0 だが LLM route 残存；**Gate Fail の主因ではない** | 実測 |
| AE5-M2 | **Open** | session-delete run0 に focus_llm 遅延混入 | 実測 |
| AE5-M3 | **Open** | alias による joint 緩和（delete_confirm / emergency sub） | 実測 |
| E4-M1 | **Open** | `seed_random` は backend 内シャッフルのみ | コード |
| E4-M2 | **Partial Closed** | Gate 点推定は warm-only。CI 混在は AE5-H1 | 実測 / コード |
| E-M2–M7 等 | **Open（持越し）** | Round4 一覧どおり。本報告で再実行せず | 未検証 |

---

## 5. Round4 High の worktree 後ステータス

| Round4 ID | Round4 時点 | dirty worktree 後 | 根拠 |
| --- | --- | --- | --- |
| E4-H1 exempt | Open | **Partial** | eval が `sub_accuracy_exempt` 転送・`accuracy_gate_pct` 除外。契約の exempt sub-pass は `jev_decisions` に残る |
| E4-H2 CI top | Open | **コード Closed / 証跡 Open** | `_build_latency_ci_block` が `scenario_cluster_warm` を Gate 正本化。012129 JSON は未再生成 |
| E-H4 alias/FP | 部分 Closed | **維持（exempt 置換残）** | E4-H1 へ継続 |
| E-H5/H6/H7/H9 | Open | **Open** | 本 live で閉鎖条件未充足 |
| E-C1/C2 | Closed | **Closed** | 変更なし |

ERRATUM（Agent G）どおり: Round4 の「条件付き Yes」は **live 開始許可**であり合格ではない。live 後も **Not Passed / Hard No-Go**。

---

## 6. Supervisor への推奨

### ユーザーに聞かなければ決めてはいけないこと

1. **最重要:** Gate latency 母集団に **SessionOps（および同様の決定論短絡）を残すか / 層別するか / 明示承認のうえで除外するか**。  
   - 残す = 製品置換（current 全体 vs Jev）の主張に忠実。現状のまま **Not Passed 継続が妥当**。  
   - 外す/層別 = 「LLM 経路のみの速度比較」に契約変更。**閾値 900 は触らず**、母集団定義の文書改訂 + 承認が必要。黙排除は禁止。
2. Gate A にコスト純減を含めるか（マトリクス上は現状 No）。含めるなら別ゲート語で Fail を分離せよ。
3. fixture / accept_alias / SessionOps シナリオ構成の改変許可。

### 聞かずに進めてよいこと（Pass を主張しない範囲）

- warm-only CI を正本化したスクリプトでの **再計測**（閾値変更なし）。
- triage/route 内訳のレポート必須化、SessionOps 短絡の明示ラベル。
- run0 focus_llm 混入の原因切り分け（ハーネス計測境界）。
- exempt 契約の文書固定（分母から除く既定の徹底）。
- architecture について「triage≈0 だが delta 主因ではない」注記の固定。

### やってはいけないこと

- SessionOps 除外後の CI で Pass 宣言。
- cold/warm 修正だけ、または request-level CI だけで Pass 宣言。
- Gate 閾値（900 / 2500 等）の事後緩和。
- soft Pass 言語。

---

## 7. 証拠ラベル凡例

| ラベル | 意味 |
| --- | --- |
| **実測** | `012129` JSON/MD またはそれから決定論的に再集計 |
| **コード再現** | 現行 worktree の関数を入力固定で実行し出力を確認 |
| **推定** | 動機・影響の推論（数値は感度計算でも、意図帰属は推定） |
| **未検証** | 本番配線・医療 FN・別環境未実施 |

---

## AE6 — Eligibility v1 / Gate A v2

- Scope: Option B 正式契約後の敵対監査のみ（閾値 / fixture gold / 実装変更なし）
- Shared: `src/services/jev_eligibility.py`
- Prod: `schedule_jev_shadow` が ineligible を skip
- Eval: Worker A 3-track + `scenario_cluster_eligible_warm`
- Gate A-accuracy: **Not Passed**（Passed 主張禁止）

### AE6.0 チェックリスト狩り結果（要約）

| 狩り項目 | 判定 | ID |
| --- | --- | --- |
| scenario ID hardcoding による除外 | **未検出**（eligibility モジュールに `jev-session-delete` 無し；unit で固定） | AE6-M1 Closed |
| fixture overfitting | **Open**（injection cue が pilot 文言に密着） | AE6-H3 |
| silent denominator drops | **部分**（latency tracks は明示；**accuracy summarize は黙って ineligible を混入**） | AE6-C1 |
| accuracy inflation via error exclusion | **残存**（scored から api_error 除外は従来どおり；attempted 併記あり） | AE6-M2 / E4-H3 系 |
| alias inflation | **残存**（delete↔delete_confirm / Emergency sub） | AE6-H5 / AE5-M3 |
| current vs Jev 資格ルール差 | **Open**（prod は `deterministic_signals`、eval は text のみ） | AE6-H1 |
| warm/cold mix into Gate CI | **コード上 Closed 寄り**（`require_latency_gate_eligible` + warm）。**証跡 Open**（v2 live 無し；`012129` は旧） | AE6-H6 |
| SafetyGate bypass | **PRIMARY 弱体化は未検出**。残差 S1-G02 等で SessionOps が勝つ経路は **Open** | AE6-H4 |
| production/eval eligibility drift | **Open**（信号袋・fail-open） | AE6-H1 / AE6-H2 |
| docs vs code mismatch | **Open**（契約書=eligible-only accuracy；`accuracy_note` は exempt のみ） | AE6-C1 |
| `unexpected_jev_call_count` gaming | **Open**（`eligible=True` 誤判定では増えない） | AE6-H2 |
| ineligible が current 複製で Jev 精度に化ける | **Critical Open（再現済）** | AE6-C1 |

### AE6.1 Critical

| ID | 状態 | 要約 | ラベル |
| --- | --- | --- | --- |
| **AE6-C1** | **Open** | `_evaluate_jev_ineligible_placeholder` が `actual_from=current_executed_route` で gold 採点し `pass=True` になり得る。`_build_track_aggregates` は `accuracy_gate_eligible` / `skipped_ineligible` を除外するが、**Gate 向けに見える `summaries[].accuracy_gate_pct`（`_summarize`→`_scored_rows`）は ineligible 行を分母に残す**。契約書・`tracks_note` の「accuracy = jev_eligible のみ」と不一致。SessionOps を残したまま Jev 精度 100% を装える。 | **コード再現** |

再現（決定論）: ineligible placeholder `pass=True` + eligible 1 件 → `accuracy_gate_pct=100%` / `accuracy_gate_n=2`、一方 `totals.accuracy_gate_n=1`。

**Critical open count (AE6): 1**

### AE6.2 High

| ID | 状態 | 要約 | ラベル |
| --- | --- | --- | --- |
| AE6-H1 | **Closed（Supervisor Accept；E再反証待ち）** | eval は current 後に `_deterministic_signals_from_current_result` → 本番と同じ `_deterministic_signals_from_context`。 | コード + tests |
| **AE6-H2** | **Closed（Supervisor Accept；E再反証待ち）** | (a) unexpected は false-eligible 再判定を含む。(b) eligibility 例外は fail-closed（API 非呼出）。 | コード + tests |
| **AE6-H3** | **Open** | `_detect_prompt_injection_cues` 等が pilot fixture 文言に密着。scenario-id denylist ではないが **fixture overfitting / cue 過適合** リスク。 | コード + fixture |
| **AE6-H4** | **Closed寄り（S1残差なし）** | S1-G02/G04/G05/G06/G08 Closed。PRIMARY 弱体化なし。 | コード + マトリクス |
| **AE6-H5** | **Open** | joint / alias（`delete`↔`delete_confirm`、Emergency sub）による精度緩和は Option B でも残存。eligible 分母が小さくなるほど **alias 1 件の重みが増す**。 | 実測(012129) + コード |
| **AE6-H6** | **Open（証跡）** | Gate CI 正本キーは `scenario_cluster_eligible_warm`（cold 混入防止は配線済）。**v2 live 未実行**のため Pass/Fail を新契約で主張不可。`012129` 転用は Hostile。 | コード / 未検証(live) |

**High open count (AE6): 6**

AE5 持越し（未閉鎖）: AE5-H1/H2 は Option B で **契約上は意図的に緩和**（SessionOps=Jev 対象外）。ただし **AE6-C1 未修のままの「精度 100%」主張は依然 Hostile**。E4-H1 exempt 契約・E-H5/H6/H7/H9 は Open 維持。

### AE6.3 Medium

| ID | 状態 | 要約 | ラベル |
| --- | --- | --- | --- |
| AE6-M1 | **Closed** | scenario-id denylist なし（`test_no_scenario_id_hardcoding_in_module`） | コード |
| AE6-M2 | **Open** | scored 分母から transport 失敗除外 → `accuracy_scored_pct` 楽観。`accuracy_attempted_pct` 併記で緩和済み | コード |
| AE6-M3 | **Open** | untagged `latency_class`→warm デフォルト。合成行で Gate 汚染し得る | コード |
| AE6-M4 | **Open** | `force=True`（`run_jev_shadow_sync`）はテスト用に eligibility を迂回。本番経路の既定ではないがメトリクス比較を歪め得る | コード |
| AE6-M5 | **情報** | Option B で Gate n_scenarios 10→≈9。ユーザー承認済みの母集団変更。**閾値据え置きのまま Pass しやすくなる**点は文書化し、silent cheat と区別せよ | 契約 |

### AE6.4 Live はまだ blocked か？

**YES — live_blocked = yes**

理由（いずれも単独で十分）:

1. **Gate A-accuracy = Not Passed**（v2 eligible-warm の連続 live 証跡なし；`012129` は旧契約）。
2. **AE6-C1 Critical Open** — 精度 Gate キーが契約と不一致。Critical 残存中の Pass / 本番昇格は禁止。
3. **AE6 High Open = 6**（PDCA 状態の「E Critical and High none」条件未達）。
4. **Gate B = Hard No-Go**（人間医療・expanded FN 未解消）。dev shadow / primary も Hard No-Go。

補足: 「証拠採取のための live **実行**」と「live **合格 / 本番解除**」は別語。本裁定の blocked は後者（および Pass 主張）。実行そのものは Supervisor 判断だが、**結果を Passed と書いてはならない**。

### AE6.5 Supervisor への敵対的推奨

- **今すぐ直せ（A）:** `_scored_rows` / `_summarize.accuracy_gate_pct` を `accuracy_gate_eligible=True` かつ `outcome!=skipped_ineligible` に一致させよ。`accuracy_note` を契約書と同一文言に。二重集計を禁止。
- **直せ（C/prod）:** eligibility 例外は fail-closed（skip + メトリク）に。eval にも signals を渡すか、text-only を契約に明記して drift を消すな。
- **やるな:** cue 追加で fixture だけ通す / scenario-id 除外に戻す / `unexpected_jev_call_count==0` だけで健全主張 / soft Pass。
- **ユーザー確認不要でよいこと:** AE6-C1 修正後の unit 固定、v2 契約での再 live（閾値不変）、結果が Fail なら Not Passed 維持。

---

## 8. 返却サマリ（機械可読）

```text
AE6_Critical(open): 1
AE6_High(open): 6
live_blocked: yes
Gate A-accuracy: Not Passed
Gate B: Hard No-Go
Report: docs/planning/codex-parallel-jev-20260921/JEV_ADVERSARIAL_EVALUATION_20260922.md
Why_live_blocked:
  - AE6-C1 accuracy_gate_pct includes current-copied ineligible rows
  - no Gate-A-v2 live under scenario_cluster_eligible_warm
  - High open > 0; Gate B Hard No-Go
Single most important fix:
  Align summaries[].accuracy_gate_pct with accuracy_gate_eligible (Option B track 2)
```

---

*Worker E Independent Adversarial Evaluation — 2026-09-22（AE5+AE6）。本番コード/fixture/Gate閾値は未変更。Passed 主張なし。*
