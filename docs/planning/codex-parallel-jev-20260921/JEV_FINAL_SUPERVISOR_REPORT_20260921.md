# Jev 導入プログラム — 上司最終レポート

- 作成日: 2026-09-21
- 報告者: 実装上司（監修）／並列エージェント＋医薬品監修部下を統括
- 評価軸の優先順位: **①回答精度（joint） ②速度（latency） ③コスト**
- 読者: プロダクトオーナー（辛口評価を前提）

> ## ERRATUM（2026-09-22 Supervisor / Agent G）
>
> 本レポート旧 §3.4 の「Gate A-accuracy: **条件付き Passed**」は **無効**（禁止語）。
> ゲート語は `Passed` / `Not Passed` / `Hard No-Go` のみ許可。
>
> **正式判定（変更不可）:**
> - Phase1 local shadow / Gate A-code = **Passed**
> - Gate A-accuracy = **Not Passed**
> - Gate B / primary / staging / prod = **Hard No-Go**
> - Focus 本配線 = **No-Go**
>
> **Gate A-accuracy の現行証跡（正本）:** live `20260922_012129`
> （`log/analysis/jev_intent_router_eval_10_20260922_012129.{json,md}`）
> 判定文書: `JEV_GATE_A_ACCURACY_VERDICT_20260922.md`
> （scenario-cluster CI 下限 &lt;900ms・コスト純減未達・pilot 母数 → **Not Passed**）。
>
> 旧「正本」`033321` / `032512` / `013619` は **参考値のみ**（repeat=3 または方法論違反。Gate 証拠に使わない）。
> 所有権: `JEV_SUPERVISOR_OWNERSHIP_20260922.md`。監査: `JEV_DOCS_AUDIT_AGENT_G_20260922.md`。
> §3.2 の数値表は履歴。個別指標の Pass/Fail 表記はゲート語ではない。

---

## 1. 実施の目的

本プログラムの目的は、TypeSafe System One（Jev）を **Chat Pipeline v2 の IntentRouter 境界に安全に導入**し、次を同時に達成することである。

1. **精度**: primary + 必須 sub-route の joint で現行と同等以上（高リスク FN=0）
2. **速度**: IntentRouter／分類レイヤの待ち時間を大幅短縮（avg ≥900ms **または** P95 ≥2500ms 短縮）
3. **コスト**: OpenAI IntentRouter 削減と Jev 込み総分類費を **分離して**可視化し、誤った「安い」判断を防ぐ
4. **安全**: Emergency / Security / medical_examination / 処方・規制薬 block を **Jev 単独で確定しない**
5. **運用**: default OFF の local shadow →（条件充足後）dev shadow → primary canary。本番は別承認

**やらないこと（目的の外側）**: 推薦ランキングの Jev 化、SessionOps primary、`with_baseline_triage`、Gate 未達での dev 有効化。

---

## 2. 実施前の目的・計画（ベースライン）

| 項目 | 実施前の計画値 / 前提 |
| --- | --- |
| Pilot 根拠 | `013619`: current / `jev:minimal` とも **30/30**、avg 短縮 **919ms**、P95 短縮 **2623ms** |
| Adapter | `jev:minimal` のみ（`with_baseline_triage` 棄却） |
| Phase 1 | local shadow のみ。実行 route は常に legacy。PRIMARY 構造的無視 |
| Secret | `JEV_API_KEY` のみ（`TYPESAFE_API_KEY` fallback 禁止） |
| 次ターゲット順 | Focus → Eligibility → triage stage2 → stage1 → Store |
| Gate | A local → live 再評価 → B dev shadow → C canary。staging/prod は別承認 |

正本ドキュメント: `JEV_PARALLEL_SYNTHESIS_20260921.md`、実行計画 `JEV_EXECUTION_PLAN_PHASE0-2_20260921.md`。

---

## 3. 現状（実装・ゲート・数値）

### 3.1 実装ステータス

| 領域 | 状態 |
| --- | --- |
| Phase 0 契約凍結 | 完了（`JEV_PHASE0_CONTRACT_FREEZE` / Gate B scoring contract） |
| Phase 1 local shadow | **コード完了・default OFF** |
| 本番 client / decisions / metrics / router 差し込み | 完了 |
| 医薬品監修 draft fixture | 完了（`pharmacist_reviewed_draft`。人間 Gate B 未承認） |
| Focus 次ターゲット | **スキャフォールドのみ**（本番未配線） |
| dev shadow 有効化 | **未実施（Hard No-Go）** |
| primary / staging / prod | **未実施（Hard No-Go）** |

主要コード: `jev_client.py`, `jev_decisions.py`, `jev_metrics.py`, `jev_router.py`, `router.py`, `dispatcher.py`, `chat_post_pipeline.py`（二重 shadow 抑止）。

### 3.2 最新 live 評価（精度・速度・コスト）

**Gate 証跡の正本ラン（実測）:** `log/analysis/jev_intent_router_eval_10_20260922_012129`
（repeat=10 / `seed_random` / production scoring）。判定: `JEV_GATE_A_ACCURACY_VERDICT_20260922.md` → **Not Passed**。

| Backend | Acc（実測） | warm mean | warm P95 |
| --- | ---: | ---: | ---: |
| current | 100/100 (100%) | 1576.93 ms | 3646.66 ms |
| `jev:minimal` | 100/100 (100%) | 241.28 ms | 311.85 ms |

| 指標 | 値 | ラベル | ゲート語への寄与 |
| --- | --- | --- | --- |
| warm mean Δ | **1335.65 ms** | 実測 | 点推定は ≥900 だが **ゲート合格ではない** |
| warm P95 Δ | **3334.81 ms** | 実測 | 点推定は ≥2500 |
| scenario-cluster 95% CI（mean Δ） | **[826.7, 1943.02]** | 実測 | 下限 <900 → **保守 Fail → A-accuracy Not Passed** |
| OpenAI saved | 0.854 JPY | **measured_proxy** | 純減主張不可 |
| Jev cost | 0.908 JPY | **estimated** | 同上 |
| Net | **-0.054 JPY** | 推定同士 | 「安い」とは言えない |
| fallback / api_err / eval_err | 0 | 実測 | 分母汚染なし |

**履歴ラン（参考・Gate 証拠不適格）**

| ラン | 位置づけ | 備考 |
| --- | --- | --- |
| `033321` | 参考 | repeat=3・旧実行順。旧レポートが誤って「正本」扱いにしていた |
| `032512` | 参考 | Client 都度生成・latency 不合格記録 |
| `013619` | smoke のみ | pilot 30/30。Gate クローズに使わない |

### 3.3 Soft safety live（拡張 fixture）

- 初回: soft_pass **14/17**（fail 3）— medical_examination 境界 FN 等
- PDCA: soft harness に deterministic `medical_examination` 配線 → 当該シナリオ soft_pass 化
- 残: Store+症状、conflicting follow-up 等は **観測継続**（CI hard-fail 禁止）

### 3.4 ゲート総括

| Gate | 判定 | 根拠 |
| --- | --- | --- |
| **A-code**（local 実装） | **Passed** | default OFF、常に legacy、secret 契約、unit green |
| **A-accuracy**（live） | **Not Passed** | 正本 live `012129` + `JEV_GATE_A_ACCURACY_VERDICT_20260922.md`。CI 下限未達・コスト純減未達・pilot 母数。旧「条件付き Passed」棄却 |
| **B**（dev shadow） | **Hard No-Go** | 人間医療承認・150 decisions・運用準備未 |
| **C+ / primary / prod** | **Hard No-Go** | 計画どおり |

---

## 4. 課題（構造的）

1. **比較の非対称**: current は triage+IntentRouter、Jev は System One 1 call。速度比較は「分類スタック置換」としては妥当だが、「IntentRouter 単体置換」のコスト議論とは混同できない。
2. **pilot 10 は母数不足**: Gate B の安全性を単独保証しない（Synthesis 確定方針）。
3. **高リスク軸の enum 流用**: medical_examination が Emergency に載る。臨床境界と 119 級救急が統計で混ざる。
4. **focus の session 永続がない**: shadow enrichment はほぼ空。Focus 導入前に別決定が必要。
5. **コストの「純削減」未実証**: IntentRouter 推定節約 ≈ Jev 代。70% OpenAI 削減は **primary 運用後の実測**が必要。
6. **ドキュメント追記負債**: 一度「直した」と書いて本体が古い問題が再発しやすい（監査ルール化が必要）。

---

## 5. 問題（具体・優先度）

| ID | 深刻度 | 問題 | 状態 |
| --- | --- | --- | --- |
| P1 | Critical（済） | fixture 危険ラベル（仮定 Concierge 固定等） | 薬剤師 draft で是正 |
| P2 | High（済） | eval `TYPESAFE` fallback / state キー不一致 | 契約寄せ済 |
| P3 | High（済） | assert 禁止検査・latency 都度 Client | 本番耐性化・再利用 |
| P4 | High | P95 短縮が閾値未達・CI 下限未達 | **残**（追加サンプル / cold-warm 分離） |
| P5 | High | medical_examination を Jev 単独で Physical に落とす | soft harness は修正。**本番は既存 gate OR 必須** |
| P6 | Med | Store+症状で Store 勝ち | soft fail 観測中 |
| P7 | Med | conflicting meta で Counseling miss | adapter/state 方針未決 |
| P8 | Med | コスト net 微マイナス（推定同士） | 計測定義の再校正が必要 |
| P9 | Low | Emergency sub naming 揺らぎ | alias 正規化で大半解消 |

---

## 6. 改善策（実施済み PDCA 要約）

### Round 群（連続実施）

1. **契約・コード**: Phase 0 freeze、shadow 差し込み、PRIMARY 無視、二重起動抑止
2. **辛口レビュー**: 初稿 A 評定を撤回。薬剤師投入
3. **医療裁定**: hypothetical/quoted = Concierge 主 + Emergency 代替
4. **観測強化**: disagreement_class、forbidden state 本番検査、focus 読取
5. **eval 本番寄せ**: `evaluate_system_one` + `parse_jev_answers`、コスト分離、bootstrap CI
6. **latency**: httpx Client 再利用 → Jev avg **690→274ms**
7. **safety soft**: deterministic medical_examination 配線
8. **次フロー**: Gate B scoring contract、Phase1C–Focus 計画、Focus pilot scaffold

### 改善策（未実施・推奨順）

1. repeat≥10 の cold/warm 分離 live（P95/CI を確定）
2. 人間による `gate_b_approved` 昇格レビュー
3. OpenAI cost を `dialogue.intent_router_llm` 実ログと突合（推定の校正）
4. Store+症状・conflicting の adapter ルール（shadow 比較用、実行不変）
5. Focus shadow の本配線は **IntentRouter Gate B 後**
6. dev 準備（secret/log/rollback）のみ先行。**enable は別承認**

---

## 7. 実装後の評価（多角的）

### 7.1 精度（最重要）

| 視点 | 評価 |
| --- | --- |
| Pilot joint | **優秀**（30/30 × current/Jev、api_err=0） |
| 高リスク soft | **注意**（medical_examination は deterministic 必須と実証） |
| 別名ノイズ | **改善済**（delete / chest_pain_* alias） |
| 一般化 | **不足**（10 シナリオは smoke） |

**辛口**: 「100%」はパイロット合格であり、**製品安全の合格ではない**。

### 7.2 速度（最重要）

| 視点 | 評価 |
| --- | --- |
| Avg 短縮（点推定） | **合格**（約 1057ms ≥900） |
| P95 短縮 | **不合格寄り**（約 2363ms <2500） |
| CI 保守側 | **不合格寄り**（下限 797ms） |
| 実装改善効果 | **大**（Client 再利用が決定打） |
| ユーザー体感 | IntentRouter 待ちが主ボトルネックなら体感改善は大きい。生成系 P95 は別問題 |

**辛口**: 速度は「avg OR」でギリギリ合格ライン。**P95 を売り文句にしてはいけない**。

### 7.3 コスト

| 視点 | 評価 |
| --- | --- |
| 計測分離 | **達成**（OpenAI saved vs Jev total） |
| 純削減（推定） | **未達**（微マイナス） |
| 70% OpenAI 削減目標 | **未測定**（primary 後） |
| 解釈 | 速度価値と安全価値が主便益。コスト単独ではまだ勝てない可能性 |

**辛口**: 「安いから Jev」は現時点で根拠薄弱。**速い・同等精度・安全二重化**が導入理由。

### 7.4 安全・医療

| 視点 | 評価 |
| --- | --- |
| 実行経路 | Phase 1 は Jev が決定を変えない → **安全側** |
| ラベル品質 | 薬剤師 draft まで到達。**人間承認前** |
| 境界ケース | medical_examination / Store+症状 / conflicting が残課題 |

### 7.5 エンジニアリング・組織

| 視点 | 評価 |
| --- | --- |
| 並列 PDCA | 有効（自己批判→薬剤師裁定→再測定） |
| 初稿監査 | 甘さあり。辛口 Round で回収 |
| 再現性 | レポート・JSONL・eval スクリプトが揃い始めた |

### 7.6 総合スコア（上司）

| 領域 | 点 |
| --- | ---: |
| 精度（pilot） | **A-** |
| 速度 | **B+**（avg Pass / P95・CI 留保） |
| コスト | **C+** |
| 安全設計（Phase1） | **A-** |
| 医療ラベル運用 | **B-** |
| 次フロー準備 | **B+** |
| **総合** | **B+**（dev 有効化はまだ不可） |

---

## 8. 今後の計画（改善点・他プロセス横断可）

### 8.1 直近（1–2 週間）

1. **Phase 1C クローズ作業**: repeat≥10、cold/warm、P95/CI 再判定 → `JEV_LIVE_EVAL` 追記
2. **Gate B 人間レビュー会**: scoring contract に沿ってシナリオ昇格
3. **コスト校正**: Cloud Logging / `pipeline_perf` の IntentRouter 実費と突合
4. soft safety 残 fail（Store+症状、conflicting）の adapter 方針決定

### 8.2 中期（Gate B → C）

1. Phase 1D: dev secret / log / rollback 準備のみ
2. 明示承認後に dev shadow（150 eligible、disagreement≤0.5%、FN=0）
3. Gate C 後に低リスク primary canary（confidence≥0.85、SessionOps 除外）

### 8.3 次の Jev 最適配置（Focus）

- 正本: `JEV_NEXT_FLOW_PHASE1C-FOCUS_20260921.md`
- scaffold: `scripts/eval_jev_medicine_qa_focus_shadow.py` + pilot YAML
- **Eligibility と統合しない**（Synthesis 確定）
- 成功条件: physical pivot FN=0、focus macro-F1 非劣性

### 8.4 アプリ全体・他プロセス横断

| 領域 | 提案 |
| --- | --- |
| 推薦コア | 引き続き rule-based が権威。Jev は分類境界のみ |
| SafetyGate / diagnosis_guard | Jev と OR。Jev 陰性で解除禁止を回帰テスト化 |
| 観測 | `pipeline_perf` に Jev cost / saved calls を正式フィールド化 |
| ドキュメント CI | 「追記と本体の矛盾」を検出する lint（見出し差分チェック） |
| 評価文化 | live 数値なき「完了」報告を禁止（今回の辛口 PDCA を標準化） |

### 8.5 Explicit No-Go（再掲）

- draft fixture の CI hard-fail
- Gate B 前の `JEV_*=true`
- PRIMARY / staging / production の自動進行
- SessionOps Jev primary
- triage stage1+2 の早期 1-call 統合
- `baseline_triage_hint` 復活

---

## 9. 本プロジェクトの今後への展望と展開

Jev は「LLM を全部置き換える銀の弾丸」ではない。本リポジトリにおける最適解は次の段階導入である。

1. **IntentRouter shadow →（条件付）primary** で分類待ちを削る  
2. **Focus shadow** で Medicine QA の観点選択を軽量化（Eligibility は分離）  
3. その後に曖昧 Eligibility・triage stage2 と段階評価  
4. 推薦・説明・Safety の本線は既存アーキテクチャを維持  

成功時の姿: ユーザー体感は「振り分けが速い」、医療安全は「既存 gate が最終決定」、コストは「OpenAI 分類の一部が消えるが Jev 代を差し引いて純減を実測で示す」。

失敗時の逃げ道はすでにコードにある: **`JEV_ENABLED=false` / shadow OFF / PRIMARY 未実装**。Phase 1 の最大の価値は、この逃げ道を保ったまま計測基盤を本番品質に近づけることだった。

---

## 10. 添付・参照（必読）

| 文書 | 内容 |
| --- | --- |
| `JEV_PHASE1_HARSH_PDCA_SUPERVISOR_REPORT_20260921.md` | 辛口 PDCA 詳細 |
| `JEV_SAFETY_FIXTURE_PHARMACIST_REVIEW_20260921.md` | 薬剤師レビュー |
| `JEV_GATE_B_SCORING_CONTRACT_20260921.md` | Gate B 採点契約 |
| `JEV_NEXT_FLOW_PHASE1C-FOCUS_20260921.md` | 次フロー正本 |
| `JEV_LIVE_EVAL_NOTES_20260921_032512.md` | latency 不合格ランの記録 |
| `JEV_SOFT_SAFETY_LIVE_FINDINGS_20260921.md` | soft fail 分析 |
| `JEV_GATE_A_ACCURACY_VERDICT_20260922.md` | Gate A-accuracy **Not Passed** 正本 |
| `log/analysis/jev_intent_router_eval_10_20260922_012129.*` | **現行 Gate 証跡 live（実測）** |
| `log/analysis/jev_intent_router_eval_10_20260921_033321.*` | 参考（旧・不適格） |
| `JEV_DOCS_AUDIT_AGENT_G_20260922.md` | 文書監査 |

---

## 11. オーナーへの一文

**Gate A-accuracy は Not Passed（live `012129`）。Gate B / primary / staging / prod は Hard No-Go。Focus 本配線は No-Go。** 点推定の latency 改善や pilot 100% を合格と読まない。コスト純減は未実証。dev 有効化の議論に進むな。

辛口総合: 方法論付き live は取れたが **ゲートは未達**。次は CI 保守基準・コスト実測・医療承認であり、「準備が整った」は Gate 語ではない。

---

*Final supervisor report — 2026-09-21*
