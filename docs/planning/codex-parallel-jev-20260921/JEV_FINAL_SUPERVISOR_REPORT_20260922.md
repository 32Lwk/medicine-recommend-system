# Jev 導入プログラム — Supervisor 最終レポート（2026-09-22）

- 報告者: Supervisor（本セッション）
- ゲート語: Passed / Not Passed / Hard No-Go のみ
- 優先順位: 医療安全 → 精度 → 継続性 → 速度 → 監査 → コスト → 実装量

---

## 1. 実施の目的

IntentRouter 境界へ Jev を **安全に段階導入**し、医療安全を損なわずに精度・障害耐性・速度・監査・コストを証拠付きで測る。Jev 導入そのものは目的ではない。

## 2. 実施前の状態

| 項目 | 状態 |
| --- | --- |
| Phase 1 local shadow | コード済・default OFF |
| Gate A-code | Passed |
| Gate A-accuracy | Not Passed（方法論不備の旧 live / または未完） |
| Gate B+ | Hard No-Go |
| 旧 FINAL | 「条件付き Passed」という禁止語を使用（棄却対象） |

## 3. 計画

Round0 契約固定 → A–D 実装 → E/F 反証 → Round3 是正 → Round4 再反証 → live repeat≥10 → G 文書統一 → 本最終判定。

## 4. 並列エージェント構成

| Agent | ID | 役割 |
| --- | --- | --- |
| A Evaluation | [A](bb8447e9-b285-4a4a-8139-3e72c490d610) | eval 方法論 |
| B Safety/Decision | [B](3210ecd0-7386-4b55-8952-35bc074d3ae2) | joint / OR 高リスク |
| C Runtime | [C](82f05bb4-e71f-460b-8fb5-a751536231fc) | client / router 耐障害 |
| D Observability | [D](f5b9b720-5afa-41b7-a8fb-c5890b689d16) | metrics / cost 分離 |
| E Adversarial | [E](a60fa88f-ace8-4c66-aadb-d7f34b2b8125) | 独立破壊レビュー |
| F Medical | [F](cb2853ef-0e7a-4763-acc4-69d1b96dd118) | 医療安全（AI助言） |
| G Docs | [G](f7543c05-ee5b-4a76-b2b4-dec681132141) | 文書・Gate語統一 |

所有権表: `JEV_SUPERVISOR_OWNERSHIP_20260922.md`

## 5. 各担当の成果（要約）

- **A:** interleaved禁止解消 → seed_random / cluster CI / gate accuracy / `score_joint_decision` 一本化
- **B:** `effective_high_risk` OR、joint+safety、FP sub 拡大廃止、本番未配線明記
- **C:** 障害注入58、submit_failed、PRIMARY非参照維持
- **D:** schema v2、推定/実測分離、`jev_cost_usd` alias 明示
- **E:** Critical ドリフト検出→Round4でClosed。live条件付き許可
- **F:** Gate B Hard No-Go、昇格不可、境界FN既往
- **G:** 文書を Not Passed / `012129` 正本に統一

## 6. 各担当の辛口評価（Supervisor）

| Agent | 自己 | Supervisor | 一言 |
| --- | ---: | ---: | --- |
| A | — | B+→A-（R3後） | 初回ドリフトは重大。是正後は方法論合格 |
| B | B+ | B | APIは良い。本番未配線は正直 |
| C | 提出可 | B+ | mock網羅。live障害は未 |
| D | A- | B+ | schema良。actual配線待ち |
| E | （禁止） | A | Critical再現が仕事を救った |
| F | — | A- | 人間承認非代替を貫いた |
| G | — | A- | 正本経路封鎖。Progress R3残渣はSupervisor修正 |

## 7. PDCAで発見した問題

1. eval 独自採点と B 契約のドリフト（Critical）
2. risk_flags で safety 偽Pass
3. 「条件付きPassed」文書汚染
4. cold n=1 / request-level CI 楽観
5. medical_examination システム境界 FN 既往
6. `sub_accuracy_exempt` 観測漏れ（E4-H1）

## 8. 修正内容

Round3–4で上記1–2,4,6をコード是正。文書はG+SupervisorでGate語統一。live前に accuracy_gate / cluster CI top を Supervisor統合。

## 9. 精度評価（実測 `012129`）

- accuracy_gate: current **100/100**、jev **100/100**（exempt=0）
- raw disagreement 20（sub命名/alias。joint gateは双方pass）
- pilot 10 → **製品安全の証明にしない**

## 10. 速度評価（実測・warm）

| | mean | P95 |
| --- | ---: | ---: |
| current | 1577 ms | 3647 ms |
| jev | 241 ms | 312 ms |
| Δ | **1336** (≥900 Pass) | **3335** (≥2500 Pass) |
| scenario-cluster CI mean Δ | **[827, 1943]** | 下限&lt;900 → **保守 Fail** |

## 11. コスト評価

- OpenAI saved **measured_proxy** 0.854 JPY
- Jev **estimated** 0.908 JPY
- 純減 **未達**。「安い」主張禁止

## 12. 医療安全評価

- F裁定: draft上FNは観測されず ≠ 安全性証明
- medical_examination **システムFN既往** → Gate B Hard No-Go
- `gate_b_approved` 昇格 **不可**
- 人間薬剤師承認を代替しない

## 13. 障害耐性評価

- unit/mock: timeout/429/5xx/malformed等カバー（C）
- live `012129`: api_err=0、fallback=0、production stack
- shadow JSONL 実ファイル: **MISSING（未検証）** — A-codeのpath契約≠本番サンプリング済
- PRIMARY実行参照なし維持

## 14. アプリ全体への影響

- 実行routeは常にlegacy（Phase1）
- flags default OFF
- Focus本配線なし（scaffoldのみ）
- 推薦/SafetyGateはJev移行対象外維持

## 15. 残留リスク

| ID | 深刻度 | 内容 |
| --- | --- | --- |
| R1 | High | Gate B前の人間医療承認不足 |
| R2 | High | medical_examination 境界FN再発リスク |
| R3 | High | CI下限未達（速度保守） |
| R4 | Med | コスト純減未実証 |
| R5 | Med | effective_high_risk 本番未配線 |
| R6 | Med | shadow JSONL未生成 |
| R7 | Low | Emergency sub raw命名揺らぎ |

## 16. Gate判定

| Gate | 判定 |
| --- | --- |
| Phase1 local shadow コード | **Passed** |
| Gate A-code | **Passed** |
| Gate A-accuracy | **Not Passed** |
| Gate B / dev shadow | **Hard No-Go** |
| primary / staging / production | **Hard No-Go** |
| Focus本配線 | **No-Go** |

```text
Gate A-accuracy: Not Passed
未達項目:
  - scenario-cluster CI 下限 826.7ms < 900ms（保守）
  - コスト純減未達（推定）
  - pilot≠製品安全
根拠: JEV_GATE_A_ACCURACY_VERDICT_20260922.md / live 012129
次の改善: CI設計のwarm固定再測定、コスト実測突合、人間医療承認後のGate B準備のみ
```

## 17. 次の実行計画

1. CI下限を満たす追加測定設計（warm-only・母数）を文書固定して再live
2. Gate B: 人間承認チェックリスト（F）のみ。enable禁止
3. Focus本配線は IntentRouter Gate B 完了後
4. `log/jev_intent_router_shadow.jsonl` のローカル生成確認（shadow ONテスト環境）

## 18. 中止・rollback条件

高リスクFN、SafetyGate bypass、secret混入、legacy fallback失敗、証跡欠損、文書Gate語不一致、CI/P95捏造、fixtureラベル改変による合格捏造 → 即停止。rollbackは `JEV_*=false`。

## 19. 将来展望

IntentRouter が Gate B→C を証拠で越えた後に限り、Medicine QA Focus → Eligibility曖昧 → triage stage2→1 → Store補助。生成・推薦ランキング・SafetyGateはJev化しない。Jevは有限集合の高速分類器であり医療権威ではない。

---

## 重み付き総合（参考・Critical/High残でNo-Go優先）

| 軸 | 重み | 所見 |
| --- | ---: | --- |
| 医療安全 | 30 | Gate B Hard No-Go。draft FN≠証明 |
| joint accuracy | 25 | pilot gate 100%だが母数不足・CI速度未達でA-accuracy Not Passed |
| 障害耐性 | 15 | mock+live輸送OK。shadowファイル未検証 |
| latency | 15 | 点推定優秀、CI保守未達 |
| 監査・再現性 | 10 | 012129証跡あり。方法論整備済 |
| cost | 5 | 純減なし |

**Critical/High未解決あり → 次ゲート Hard No-Go（総合点に無関係）**

テスト再検証: Jev所有スイート **170 passed**（2026-09-22）
