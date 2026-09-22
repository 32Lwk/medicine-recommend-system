# Agent E: Round 4 再反証（Round3 是正後）

> ## ERRATUM（2026-09-22 Agent G）
>
> 本書の「live 未実行」前提は **失効**。live `012129` 実行後も Gate A-accuracy = **Not Passed** / Gate B = **Hard No-Go**（`JEV_GATE_A_ACCURACY_VERDICT_20260922.md`）。「条件付き Yes（証拠採取）」は live **開始許可**の話であり、禁止語「条件付きPassed」とは別物。ゲート語を上げない。


- Role: Independent Adversarial Reviewer
- Date: 2026-09-22
- Scope: Round3 是正（A/B/D）の再検証のみ。コード改修なし。
- Method: ソース監査 + **実行再現**（`.venv\Scripts\python.exe`）+ 関連 pytest `112 passed`
- 自己採点: **禁止**
- 先行報告: `JEV_ADVERSARIAL_AGENT_E_20260922.md`（Round1）

**ゲート語前提（不変）:** Gate A-accuracy = **Not Passed** / Gate B = **Hard No-Go**（Supervisor 固定。live 実行後も合格に書き換えない）。

---

## 1. E-C1 / E-C2 実行再現（必実施）

### 手順

`scripts/eval_jev_intent_router_10._evaluate_prediction` と `jev_decisions.score_joint_decision` に同一 expect/actual を投入し、`joint_ok` / `primary_ok` / `sub_ok` / `safety_ok` / `forbidden_hit` の一致を確認。

### 結果

| ケース | Round1 | Round4 A≡B | joint | 判定 |
| --- | --- | --- | --- | --- |
| `alias_sub`（chest_pain_* → emergency_dispatch） | A=False / B=True | **一致** | True | E-C1 解消 |
| `forbidden_in_accept` | A=True / B=False | **一致** | False | E-C1 解消 |
| `safety_risk_flags`（meta.risk_flags のみ） | A=True / B=False | **一致** | False | **E-C2 解消** |
| `emergency_fp`（Concierge gold → Emergency） | A=False / B=True | **一致** | True | E-C1 解消（B契約に一本化） |
| `safety_action_ok`（明示 safety_action） | — | **一致** | True | 正の対照 |
| `transport_ok=False` | — | **一致** | False | 一本化確認 |

**結論:** Round1 の **E-C1 / E-C2 は Closed**。A は thin adapter で `score_joint_decision` のみを呼ぶ。`risk_flags` 単独では safety を満たさない。

関連 unit: `tests/scripts/test_eval_jev_intent_router_10.py` の `test_score_joint_matches_agent_b_*` 群が同趣旨を固定。

---

## 2. Round3 是正チェックリスト

| Round3 対象 | 状態 | 証拠 |
| --- | --- | --- |
| A: `score_joint_decision` 一本化 | **Closed** | `_evaluate_prediction` docstring + 実行 A≡B |
| A: risk_flags ≠ safety | **Closed** | `safety_risk_flags` joint=False |
| A: cold `insufficient_n` | **Closed** | `COLD_STATS_MIN_N=5`；n&lt;5 で stats=null |
| A: order 用語 | **Closed（用語）** | `case_paired_sequential` / `interleaved` deprecated alias；default=`seed_random` |
| A: 二系統 accuracy | **Closed** | `accuracy_scored_pct` + `accuracy_attempted_pct` |
| A: raw disagreement | **Closed** | alias-only 差分が disagreement に残る（実行で `alias_only_sub_diff=True`） |
| B: 本番未配線明記 | **Closed（文書）** | モジュール / `score_joint_decision` / `effective_high_risk` WARNING |
| B: Emergency FP sub 自動拡大廃止 | **Closed（旧抜け道）** | `accept_sub_routes` に `medical_examination`/`none` を勝手に足さない |
| B: 観測フィールド | **部分 Closed** | B は `sub_accuracy_exempt` / `emergency_fp_sub_kind` / `alternate_primary_used` を返す。**A adapter が転送しない** → §3 |
| D: `jev_cost_usd` field_semantics | **Closed** | `"estimated (alias of jev_cost_usd_estimate)"` + deprecation フラグ |

---

## 3. Round3 で新たに入った抜け道・過大宣伝

### E4-H1.（新規 High）`sub_accuracy_exempt` が joint を無条件 sub-pass にする

| 項目 | 内容 |
| --- | --- |
| 対象Agent | **B**（契約）/ **A**（観測未転送） |
| ファイル | `jev_decisions.score_joint_decision`（`alternate_primary_used==Emergency` なら `sub_ok=True`）；`eval._evaluate_prediction`（exempt フィールド非転送） |
| 再現条件 | Concierge + `emergency_fp_tolerated` / `accept_alternate_primaries:[Emergency]` で actual=`Emergency` / `sub_route=rule_based_recommend`（ゴミ sub）→ **joint True**, `sub_accuracy_exempt=True`, `emergency_fp_sub_kind=other`。`medical_examination` も joint True（kind タグのみ） |
| なぜ危険か | 旧 E-H4（accept 集合の水増し）は潰したが、代替として **sub 採点そのものを免除**している。joint% に混ぜると精度水増し。A が観測フィールドをレポートに出さないため、live 集計で exempt 行を除外できない |
| 推奨修正 | **A:** `sub_accuracy_exempt` / `emergency_fp_sub_kind` / `alternate_primary_used` を結果行とサマリ必須化。Gate 向け accuracy は `exempt=False` 行のみ、または primary-only 別指標。**B/F:** exempt 行を joint 分母から外す契約を Gate B 文書に固定 |
| ゲートへの影響 | live 開始後も **joint% を無条件に Gate 証拠にできない** |

### E4-H2.（残存 High）latency CI トップレベルが request-level 優先

| 項目 | 内容 |
| --- | --- |
| 対象Agent | **A** |
| ファイル | `_build_latency_ci_block`（コメント: top-level mirror request-level） |
| 再現条件 | paired 十分 → `ci["method"] == "numpy_bootstrap_request_level"`（実行確認済）。scenario_cluster は併記されるがトップは楽観側 |
| なぜ危険か | Round1 E-M1 未解消。要約/JSON の浅い読みで狭い CI を「有意」と誤読 |
| 推奨修正 | Gate 用キーを `scenario_cluster` のみにせよ。トップの `method/ci95_*` を cluster に切り替え、request-level は `deprecated_optimistic` 明示 |
| ゲートへの影響 | 速度条項の誤 Pass 誘発 |

### E4-M1.（新規 Medium）`seed_random` はケース順をシャッフルしない

| 項目 | 内容 |
| --- | --- |
| 対象Agent | **A** |
| ファイル | `_build_eval_schedule` order=`seed_random` |
| 再現条件 | scenarios s0..s2 → current 実行順は常に s0,s1,s2（実行確認）。シャッフルは **ケース内 backend 順のみ** |
| なぜ危険か | 名前が「全面ランダム」に聞こえる。ケース間の時間相関・暖機勾配は残る。docstring は正直だが CLI 名は過大 |
| 推奨修正 | レポート必須注記を強化、または `seed_random_backends_within_case` に改名。真の job シャッフルが必要なら別モード |
| ゲートへの影響 | 方法論完璧を主張するな；許容範囲なら文書固定で live 可 |

### E4-M2.（残存）overall latency に cold 1点が混入

| 項目 | 内容 |
| --- | --- |
| 対象Agent | **A** |
| ファイル | `_summarize`：`latency`（overall）は min_n 無し；cold のみ insufficient |
| 再現条件 | cold=1 + warm=N → overall P95 に cold が混ざる |
| 推奨修正 | Gate 用は warm-only（または cold 除外）を明示キーに |
| ゲートへの影響 | P95 主張は warm / Gate キーに限定せよ |

---

## 4. Round1 指摘のステータス一覧

### Critical

| ID | 状態 | メモ |
| --- | --- | --- |
| E-C1 採点ドリフト | **Closed** | A≡B 実行再現 |
| E-C2 risk_flags safety 抜け道 | **Closed** | joint=False 再現 |

**Round4 新規 Critical: なし**（E4-H1 は High。ただし Gate 証拠としては Critical 級の扱いを要求）

### High

| ID | 状態 | メモ |
| --- | --- | --- |
| E-H1 cold n=1 統計 | **Closed** | insufficient_n；P95 出さない |
| E-H2 擬似 interleaved 誤称 | **Closed（用語）** / 手法は case_paired として残存 | default は seed_random（backend 内シャッフル） |
| E-H3 survivor accuracy | **Closed（可視化）** | attempted 系追加。Gate はどちらを正とするか未固定 → live 条件で固定必須 |
| E-H4 alias / FP 水増し | **部分 Closed** | accept 自動拡大は廃止。**exempt に置換（E4-H1）** |
| E-H5 effective_high_risk 未配線 | **Open** | 文書警告のみ。本番接続なし（Round3 範囲外・妥当） |
| E-H6 shadow 同期コスト | **Open** | Agent C / Supervisor。Round3 対象外 |
| E-H7 mock≠live Runtime | **Open** | C 範囲。live 開始で一部検証可能 |
| E-H8 jev_cost_usd 誤読 | **Closed** | field_semantics + deprecated |
| E-H9 pilot joint に safety 無し | **Open** | fixture 非改変方針のため残存。safety キー比率の明示は live レポート条件 |
| E4-H1 sub_accuracy_exempt | **Open（新規）** | §3 |
| E4-H2 CI top=request-level | **Open（残存強化）** | §3 |

### Medium

| ID | 状態 | メモ |
| --- | --- | --- |
| E-M1 request-level 楽観 CI | **Open** → E4-H2 に昇格扱い推奨 | トップ優先が残存 |
| E-M2 exc_info 残存 | **Open** | Round3 非対象 |
| E-M3 inline fallback | **Open** | fallback_count&gt;0 なら証跡 invalid（条件に残す） |
| E-M4 measured_proxy / saved 語感 | **Open** | ラベルは改善済みだが語感リスク残 |
| E-M5 medical_examination enum | **Open** | F/B 持ち越し |
| E-M6 atexit wait=False | **Open** | C |
| E-M7 intake「受理」誤読 | **Open** | G/Supervisor 文書 |
| E4-M1 seed_random 範囲 | **Open（新規）** | §3 |
| E4-M2 overall に cold 混入 | **Open** | §3 |

### Low（Round1）

| ID | 状態 |
| --- | --- |
| E-L1 delete 両載 | Open（fixture 非改変） |
| E-L2 自己評価欄 | 対象外確認のみ |
| E-L3 PRIMARY getter | Open（実行非参照は維持） |

---

## 5. live を開始してよいか

### 判定: **条件付き Yes（証拠採取のみ）**

**無条件 Yes ではない。** Gate A-accuracy を live 一発で Passed にする許可ではない。

### 開始してよい条件（すべて必須）

1. **採点:** 引き続き `score_joint_decision` 一本化を維持（現状 OK）。
2. **order:** `--order seed_random`（default）を使い、レポートに「within-case backend shuffle only」を残す。`interleaved` / case_paired を Gate 速度証拠に使うな。
3. **accuracy:** `accuracy_scored_pct` と `accuracy_attempted_pct` を併記。Gate 判定前に **どちらを正本にするか** Supervisor が文書固定。
4. **exempt:** live レポート前に A が `sub_accuracy_exempt` / `emergency_fp_sub_kind` / `alternate_primary_used` を JSON 行へ出すこと。出せないなら joint% を Gate 提出物に含めるな（接続・latency のみ可）。
5. **latency CI:** Gate 速度判断は **`latency_ci.scenario_cluster` のみ**。トップレベル request-level を読つな。
6. **cold:** `insufficient_n` の cold 統計を引用するな。P95 は warm または overall（cold 混入注記付き）を明示。
7. **fallback / 輸送:** `fallback_count>0` または production stack 以外は **証跡 invalid**。
8. **コスト:** `jev_cost_usd` を実測と呼ぶな。`jev_cost_usd_estimate` + semantics のみ。
9. **repeat:** ownership どおり **repeat≥10**。旧 033321（repeat=3・旧順序）は引き続き参考値のみ。
10. **ゲート語:** 結果が出るまで **Not Passed / Hard No-Go**。禁止語（条件付き Passed 等）禁止。

### まだ live を始めるな、となる条件

- exempt 観測なしのまま joint% を Gate 提出する計画のとき
- request-level CI だけで速度合格を主張する計画のとき
- fixture ラベル改変や sample 恣意除外で閾値を満たす計画のとき

---

## 6. Round4 総合

| 問い | 答え |
| --- | --- |
| Round3 は Critical（E-C1/C2）を閉じたか | **Yes（実行再現）** |
| Round3 で新規 Critical が入ったか | **No** |
| Round3 で新規 High が入ったか | **Yes（E4-H1 exempt 観測欠落）** |
| Round1 を Passed に上げるか | **No**（live 未・High 残） |
| live 開始 | **条件付き Yes**（§5） |
| Gate A-accuracy | **Not Passed 維持** |
| Gate B | **Hard No-Go 維持** |

### 差戻し一文（必要なら）

| 優先 | 担当 | 一文 |
| --- | --- | --- |
| P0（live Gate 提出前） | A | exempt / fp_kind / alternate_primary_used を結果行へ転送し、Gate 用 accuracy から exempt を分離せよ |
| P0（live Gate 提出前） | A | CI トップを scenario_cluster に切り替えよ |
| P1 | B/F | sub_accuracy_exempt 行の joint 分母扱いを Gate B 文書で固定 |
| P2 | C/Supervisor | E-H5/H6 は live 後も Open — PRIMARY / dev shadow 前に残件 |

---

*Agent E Round4 — 2026-09-22. 改修なし / commit・push なし / fixture 非改変 / live API 非実行。*
