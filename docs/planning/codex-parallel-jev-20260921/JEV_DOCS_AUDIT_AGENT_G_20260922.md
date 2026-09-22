# JEV Documentation Audit — Agent G（2026-09-22）

- 役割: Documentation Auditor（辛口）
- 範囲: `docs/planning/codex-parallel-jev-20260921/` + `docs/planning/JEV_IMPLEMENTATION_TEST_PLAN_2026-09-21.md`
- 禁止遵守: production code 変更なし / fixture ラベル変更なし / git commit なし / Gate を Passed に書き換えなし

## 0. Supervisor 固定判定（本監査で変更せず）

| 項目 | 判定 |
| --- | --- |
| Phase1 local shadow / Gate A-code | **Passed** |
| Gate A-accuracy | **Not Passed**（根拠: `JEV_GATE_A_ACCURACY_VERDICT_20260922.md`） |
| Gate B / primary / staging / prod | **Hard No-Go** |
| Focus 本配線 | **No-Go** |

禁止語: 条件付きPassed / ほぼPassed / 実質合格  
許可語: Passed / Not Passed / Hard No-Go のみ

**現行証跡リンク**

- 判定: [`JEV_GATE_A_ACCURACY_VERDICT_20260922.md`](./JEV_GATE_A_ACCURACY_VERDICT_20260922.md)
- live: `log/analysis/jev_intent_router_eval_10_20260922_012129.json` / `.md`
- 所有権: [`JEV_SUPERVISOR_OWNERSHIP_20260922.md`](./JEV_SUPERVISOR_OWNERSHIP_20260922.md)

---

## 1. 監査結論（辛口）

**文書ドリフトは実在した。** Round0 が指摘した「条件付き Passed」は FINAL 本文 §3.4 では既に置換されていたが、§3.2 が旧 `033321` を「正本ラン」として残し、Test Plan / Phase0 / Progress / Next Flow / Local Shadow / Harsh PDCA が「live 未完」と現行 live 実行を矛盾させていた。

本 Agent G 作業後、読者が誤って A-accuracy を合格と読む最短経路は塞いだ。**Gate 語はすべて Not Passed / Hard No-Go 側に統一。媚びた言い回しで合格に寄せていない。**

残リスク: 並列エージェント成果物（20260921 系 Synthesis / Execution Plan / cost_latency）は歴史スナップショットとして `013619` を「最新有効実測」と書く。冒頭 ERRATUM は付けていない箇所がある（意図的に履歴保全）。**現行ゲートの正本は常に verdict + `012129`。**

---

## 2. パス照合（実測）

| パス | 結果 | 備考 |
| --- | --- | --- |
| `log/analysis/jev_intent_router_eval_10_20260922_012129.{json,md}` | **OK** | Gate 証跡正本 |
| `docs/.../JEV_GATE_A_ACCURACY_VERDICT_20260922.md` | **OK** | 判定正本 |
| `log/analysis/jev_intent_router_eval_10_20260921_033321.*` | **OK** | 参考のみ（不適格） |
| `log/analysis/jev_intent_router_eval_10_20260921_032512.*` | **OK** | 参考 |
| `log/analysis/jev_intent_router_eval_10_20260921_013619.*` | **OK** | smoke |
| `tests/fixtures/jev_intent_router_eval_10.yaml` | **OK** | fixture ラベルは未変更 |
| `tests/fixtures/jev_intent_router_safety_expanded.yaml` | **OK** | draft |
| `scripts/eval_jev_intent_router_10.py` | **OK** | |
| `scripts/eval_jev_medicine_qa_focus_shadow.py` | **OK** | Focus scaffold |
| `src/services/jev_{client,decisions,metrics}.py` / `jev_router.py` | **OK** | コード存在のみ確認 |
| `log/analysis/.../sections/llm_cost.json`（Test Plan §3 参照） | **OK** | |
| `log/jev_intent_router_shadow.jsonl` | **MISSING** | 契約上の想定パス。ローカル未生成 → **未検証** |
| Phase0 相対リンク `../../JEV_IMPLEMENTATION_TEST_PLAN_2026-09-21.md` | **OK** | 解決先存在 |

**パス監査の辛口所見:** 文書が「shadow JSONL がある前提」で語る箇所があるが、ワークツリーにファイルが無い。これは Gate A-code の「path 契約」と「実ファイル存在」の混同。A-code Passed を「本番サンプリング済」と誤読するな。

---

## 3. 証拠ラベル規約（以後必須）

| ラベル | 意味 | 本プログラムでの例 |
| --- | --- | --- |
| **実測** | live / ログから直接得た値 | `012129` joint accuracy、warm latency、scenario-cluster CI、fallback=0 |
| **measured_proxy** | 実測だが請求突合ではない | OpenAI saved JPY in `012129` |
| **estimated** | 単価×usage 等の推定 | Jev cost、net saved |
| **未検証** | 未実行・未承認・ファイル無し | Gate B 医療承認、expanded FN=0、Focus 本番効果、shadow JSONL 実体 |

verdict 末尾に同表を追記済み。点推定 Pass ≠ Gate Passed。

---

## 4. 発見した矛盾と是正

### 4.1 Critical（ゲート誤読）

| ID | 文書 | 問題 | 是正 |
| --- | --- | --- | --- |
| G-C1 | `JEV_FINAL_SUPERVISOR_REPORT_20260921.md` | 旧「条件付き Passed」+ §3.2 が `033321` を正本扱い + 結びが「準備は整っている」 | ERRATUM 拡張、§3.2 を `012129` 正本化、§3.4/§10/§11 同期。判定は **Not Passed** |
| G-C2 | `JEV_PHASE1_HARSH_PDCA_...` | A-accuracy を Gate B と一緒に **Hard No-Go** 表記 | 二行に分離。A-accuracy = **Not Passed** |
| G-C3 | Test Plan / Phase0 / Progress / Next Flow | 「A-accuracy 未完」「live 未」が現行 live と矛盾 | **Not Passed（実行済）** に統一。verdict / `012129` リンク |

### 4.2 High（正本ドリフト）

| ID | 文書 | 問題 | 是正 |
| --- | --- | --- | --- |
| G-H1 | FINAL §10 | 「最新 paired live = 033321」 | `012129` + verdict を最新、`033321` は参考 |
| G-H2 | `JEV_LIVE_EVAL_NOTES_...032512` | 単独読了で現行判定に見える | ERRATUM: 履歴。正本は `012129` |
| G-H3 | Agent E Round4 / intakes / A_R3 | 「live 未実行」前提が失効後も残存 | ERRATUM。ゲート語は上げない。「条件付き Yes」= 開始許可 ≠ 条件付きPassed |
| G-H4 | Local Shadow Supervisor | 「未完 / Not Passed」「live 未実施」チェックリスト | 見出し・表・A11/R9/§7.1 を **Not Passed + 012129** に同期 |

### 4.3 Medium（歴史文書の意図的未改稿）

| ID | 文書 | 扱い |
| --- | --- | --- |
| G-M1 | `JEV_PARALLEL_SYNTHESIS` / `jev_intent_router_eval_cost_latency` / `JEV_HYPOTHESIS_*` / Execution Plan | `013619` を最新実測と記載。**スナップショット保全**。現行ゲートの正本ではないと本監査で宣言 |
| G-M2 | `JEV_SAFETY_FIXTURE_PHARMACIST_REVIEW` の「Approve（条件付き）」 | 薬剤師レビュー文脈。Gate 語「条件付きPassed」とは別。Gate B は Hard No-Go のまま |
| G-M3 | ownership 内の Passed テンプレ行 | 判定例示（if/then）。現行状態の主張ではない |

### 4.4 禁止語スキャン結果

本文中の「条件付き Passed / 実質合格」残存は **棄却・禁止・ERRATUM・対比例** のみ。合格主張としての使用は **0 件**（是正後）。

---

## 5. 是正したファイル一覧

| ファイル | 変更種別 |
| --- | --- |
| `JEV_FINAL_SUPERVISOR_REPORT_20260921.md` | ERRATUM 拡張 + §3.2/3.4/10/11 本文 |
| `JEV_IMPLEMENTATION_TEST_PLAN_2026-09-21.md` | ERRATUM + Phase1/§9.8 |
| `JEV_PHASE0_CONTRACT_FREEZE_20260921.md` | 状態表 + ERRATUM |
| `JEV_NEXT_FLOW_PHASE1C-FOCUS_20260921.md` | 前提・§0・§1.1 |
| `JEV_PROGRESS_AND_NEXT_PLAN_20260921.md` | ヘッダ判定 + §2 + 現在地 |
| `JEV_LIVE_EVAL_NOTES_20260921_032512.md` | ERRATUM |
| `JEV_SUPERVISOR_ROUND0_AUDIT_20260922.md` | Agent G フォロー追記 |
| `JEV_SUPERVISOR_OWNERSHIP_20260922.md` | 証跡ポインタ |
| `JEV_PHASE1_HARSH_PDCA_SUPERVISOR_REPORT_20260921.md` | ERRATUM + ゲート表分離 |
| `JEV_PHASE1_LOCAL_SHADOW_SUPERVISOR_REPORT_20260921.md` | ERRATUM + 判定表同期 |
| `JEV_ADVERSARIAL_AGENT_E_20260922.md` | ERRATUM |
| `JEV_ADVERSARIAL_AGENT_E_ROUND4_20260922.md` | ERRATUM + 前提行 |
| `JEV_SUPERVISOR_INTAKE_AGENT_E_R4_20260922.md` | ERRATUM |
| `JEV_SUPERVISOR_INTAKE_AGENT_A_R3_20260922.md` | ERRATUM |
| `JEV_GATE_A_ACCURACY_VERDICT_20260922.md` | 証拠ラベル節追記 |
| **本ファイル** | 監査報告 |

---

## 6. live `012129` サマリ（ラベル付き・判定は Not Passed）

| 指標 | 値 | ラベル |
| --- | --- | --- |
| accuracy_gate | 100/100 both backends | 実測 |
| warm mean Δ | 1335.65 ms | 実測（点推定 ≥900） |
| warm P95 Δ | 3334.81 ms | 実測（点推定 ≥2500） |
| scenario-cluster 95% CI | [826.7, 1943.02] | 実測 → **下限 <900 = 保守 Fail** |
| OpenAI saved | 0.854 JPY | measured_proxy |
| Jev cost / net | 0.908 / -0.054 JPY | estimated |
| fallback / api_err / eval_err | 0 | 実測 |
| **Gate A-accuracy** | **Not Passed** | 判定語 |

旧 `033321` / `032512` / `013619` は **Gate 証拠不適格または smoke**。

---

## 7. 残課題（Agent G 外 / 文書だけでは閉じない）

1. scenario-cluster CI 下限を満たす追加設計（warm 専用 repeat 等）— **Runtime/Eval**
2. OpenAI cost の請求突合（measured_proxy → 実測）— **Observability**
3. expanded fixture 人間医療承認 — **Medical**（未検証のまま Gate B Hard No-Go）
4. `log/jev_intent_router_shadow.jsonl` 実体生成と禁止フィールド監査 — **未検証**
5. 20260921 並列スナップショットへの一括「最新は 012129」横断 ERRATUM — 任意（本監査は正本経路を優先封鎖）

---

## 8. Agent G 自己チェック

| チェック | 結果 |
| --- | --- |
| Gate A-accuracy を Passed に書いていない | **OK** |
| 条件付きPassed で合格主張していない | **OK** |
| `012129` + verdict へリンクした | **OK** |
| 実測/推定/未検証を明示した | **OK** |
| production code / fixture / commit に触れていない | **OK** |
| パス照合を実施した | **OK**（shadow JSONL = MISSING を報告） |

---

*Agent G Documentation Auditor — 2026-09-22*
