# Jev Phase 1 — 上司辛口レビュー & PDCA 改善レポート

> ## ERRATUM（2026-09-22 Agent G）
>
> Gate A-accuracy を Gate B と同一の **Hard No-Go** に混ぜない。正は A-accuracy **Not Passed** / B **Hard No-Go**。証跡: `JEV_GATE_A_ACCURACY_VERDICT_20260922.md` / live `012129`。


- 作成日: 2026-09-21
- 役割: 実装上司（監修）＋ 医薬品監修部下（pharmacist）を含む対話的 PDCA
- 対象: Phase 0–1 local shadow 並列成果（Decisions / Client / Metrics+Router / Docs / Integration）
- テスト再検証: Jev suite **142 passed**（PDCA Round 2 後）

---

## 0. 総合（辛口）

| 判定 | 内容 |
| --- | --- |
| **初稿の実態** | 「テストが通る」ことを品質と誤認していた。医療ラベルは **不合格寄り**。観測は `-O` で消える assert、eval は契約破壊の TYPESAFE fallback 残存。 |
| **Round 1 後** | 致命傷の多くは塞いだ。ただし薬剤師と Decisions が **仮定・引用 Emergency で対立**。 |
| **Round 2 後** | 医療裁定を優先して対立解消。技術残差は「Gate B 未達」に集約。 |
| **Gate A-code** | **Passed**（実行不変・default OFF・secret 契約） |
| **Gate A-accuracy** | **Not Passed**（2026-09-22: live `012129` 実行済・CI/コスト未達。旧行は A-accuracy を Hard No-Go に誤混同） |
| **Gate B** | **Hard No-Go**（人間医療承認未・dev 未準備） |

**最初の Supervisor レポートの評点（A-/A）は甘すぎた。** 本レポートの初稿換算は **C〜B-**。PDCA 後でも **B+（コード）/ C（医療ラベル運用）**。

---

## 1. エージェント別・辛口採点カード

### 1.1 Decisions（[agent](9e2bd673-4d50-4caa-b829-7060d9dd2c23)）

| 時点 | 点 | 一言 |
| --- | ---: | --- |
| 初稿納品 | **D+** | unit は綺麗。fixture が臨床事故の種。Noul 優先を eval と逆にした独断。 |
| 自己批判 Round1 | **C+ → B-** | Emergency 優先復帰・危険ラベル是正は評価。だが仮定・引用を Emergency 主にしたのは **別種の統計汚染**。 |
| Round2（薬剤師受容後） | **B** | 医療裁定に従い、schema smoke のみ。実行 primary に手を出さない自制は合格。 |

**初稿で許されないミス**

1. hypothetical / quoted を Concierge **単独**正解 → 胸痛キーワード弱体化＝**間接 Emergency FN**
2. Noul 競合 Security 優先 → 臨床エスカレーションを隠す
3. 処方箋に `rule_based_recommend` 許容 → OTC 推薦パスを金ラベル化
4. `valid=False` で risk_flags 消去 → 監査不能

**改善された点:** Emergency→Security 優先、invalid 時 flags 保持、prescription forbidden helper、fixture soft schema。

**残債:** medical_examination が Emergency enum 流用、prescription/controlled に Jev 軸なし、Gate B harness 未実装。

---

### 1.2 Client + Flags（[agent](682eda79-2779-42cc-982d-04a381b0a3eb)）

| 時点 | 点 | 一言 |
| --- | ---: | --- |
| 初稿 | **B-** | 本番 client の JEV_API_KEY のみは良い。timeout 一括・eval 契約破壊を見逃した。 |
| Round1 | **B** | connect/read 分離、eval TYPESAFE 削除、caplog。まだ「運用で壊れない」手前。 |
| Round2 | **B+** | 閾値 0–1 外→既定、eval `recent_turns`+alias。 |

**辛口コメント:** 「client は綺麗」は過大評価だった。**eval が本番契約を壊す**状態で A を付けるのは監査放棄。Round1 で破壊的修正したのは正しい。

**残債:** eval が自前 httpx のまま（本番 client 二重実装）、caller の `logger.exception` による Bearer 漏洩は境界外。

---

### 1.3 Metrics + Router（[agent](b999c07c-e455-4213-a6eb-3e0c24fc4578)）

| 時点 | 点 | 一言 |
| --- | ---: | --- |
| 初稿 | **C+** | 機能は動くが **assert 契約検査**は本番論外。観測フィールド不足。 |
| Round1 | **A-** | ForbiddenJevStateError、disagreement_class、alias mismatch 検知。ここは一番伸びた。 |
| Round2 | **A-** | focus は「読むだけ」配線。pipeline が書かないため実効は薄いが、契約どおり。 |

**辛口コメント:** 初稿で assert を許した時点で Gate B 意識が足りない。自己批判で直したのは評価。focus 未注入を「peer 待ち」で放置したのは半分正しいが、Round2 で読取配線までやったのは妥当。

**残債:** meta 内未知キーは緩い、async executed join レース、focus の session 永続が無いため観測 enrichment はほぼ常に空。

---

### 1.4 Docs（[agent](ca9f7ccb-f2ee-454f-9e12-3654e727ef08)）

| 時点 | 点 | 一言 |
| --- | ---: | --- |
| Phase0 初稿 | **B** | 凍結表は有用。だが「書いたら終わり」。 |
| Round1 辛口監査 | **B+** | Supervisor 追記と本体の矛盾を捕まえたのは正しい。Test Plan の「dev shadow まで」誤記是正は必須だった。 |

**辛口コメント:** **追記パッチは監査合格にならない。** 本体 § が「未配線」のまま残るドキュメントは嘘と同じ。

**残債:** Synthesis / Progress の古い未解決質問リスト、cost「達成」誤読リスク。

---

### 1.5 統合配線（上司直轄）

| 項目 | 点 | コメント |
| --- | ---: | --- |
| resolve_route 常に legacy | **A** | PRIMARY 未参照は構造的に正しい |
| pipeline 二重起動抑止 | **A-** | Jev ON 時のみ。OFF 時の v2 shadow 継続は意図どおり |
| corr id lifecycle | **B+** | Round0 追記で clear。完璧ではないが Gate A は足りる |
| deterministic_signals | **B+** | legacy/triage 由来。SafetyGate 生信号そのものではない |

---

### 1.6 医薬品監修部下（[pharmacist](58b7b605-d4ce-4a5b-8fd7-48de8e485a4b)）

| 観点 | 点 | コメント |
| --- | ---: | --- |
| 厳しさ | **A** | 初稿 fixture を臨床事故相当として切った |
| 裁定の質 | **A-** | Concierge 主 + Emergency 代替 = 統計汚染と間接 FN の両回避 |
| 成果物 | **A-** | `JEV_SAFETY_FIXTURE_PHARMACIST_REVIEW_20260921.md` + YAML 更新 |

**上司裁定:** エンジニア（Decisions）の「Emergency 主期待」案は **棄却**。薬剤師案を正とする。

根拠:
1. Emergency 主正解 → live 救急統計汚染、FN=0 監視が腐る
2. Concierge のみ hard → キーワード検出弱体化＝**間接 FN**
3. よって `accept_alternate_primaries: [Emergency]` + `emergency_fp_tolerated` が唯一の採点契約

**未達:** `pharmacist_reviewed_draft` ≠ Gate B 人間承認。**まだ本番ラベルではない。**

---

## 2. PDCA ログ

### Round 0（初回実装）
- Plan → 並列実装 → 甘い Supervisor Go
- **Check 失敗:** 医療ラベル・観測・eval 契約を深掘り不足

### Round 1（辛口自己批判 + 薬剤師投入）
| Agent | Do | Check |
| --- | --- | --- |
| Decisions | Noul/fixture/invalid flags 修正 | 仮定・引用で再びエンジニア独断 → 薬剤師と衝突 |
| Client | timeout 分離、eval JEV only | 閾値 clamp 未 |
| Metrics | assert 廃止、disagreement_class | focus 未 |
| Docs | ドリフト是正、Gate 二層化 | Synthesis stale 残 |
| Pharmacist | YAML 全面 Revise | 人間 Gate B 未 |

### Round 2（対立解消 + 残差潰し）
| Agent | Do | Check |
| --- | --- | --- |
| Decisions | 薬剤師判定受容、schema smoke | 62 tests green |
| Client | unit-interval clamp、eval recent_turns | 45 tests green |
| Metrics/Router | focus 読取配線 | 実効薄いが契約充足 |
| Pharmacist | エンジニア案棄却を文書化 | 裁定確定 |

**Act（現状の運用ルール）**

1. expanded fixture は **CI accuracy hard-fail 禁止**
2. Emergency/Security/medical_examination/prescription/controlled は **Jev 単独確定禁止**
3. live 再評価は `recent_turns`(+alias) 契約で実施
4. Gate B は人間医療承認 + secret/観測/rollback まで揃ってから

---

## 3. 初稿 vs 現状 — 何が嘘だったか

| 初稿の甘い言い方 | 実態 |
| --- | --- |
| 「fixture 器として Go」 | 危険ラベル入り。**器すら危ない** |
| 「Client A」 | eval が TYPESAFE fallback で Phase1 契約破壊 |
| 「Metrics A-」 | assert が `-O` で消える |
| 「Gate A 条件付き Go」 | A-code と A-accuracy を混ぜていた |
| 「追記で R1–R3 解消」 | 本体セクションが未更新のまま残存していた |

---

## 4. まだやってはいけないこと（再確認）

- `JEV_*=true` の dev 有効化
- expanded を CI hard-fail
- PRIMARY canary
- SessionOps の Jev primary
- `with_baseline_triage` 復活
- 薬剤師 draft を「承認済み」と読むこと

---

## 5. 次の PDCA（Round 3 候補）

1. **P:** Gate B 採点ハーネス仕様（`accept_alternate_primaries` / `emergency_fn_exempt` / joint）を Test Plan に freeze
2. **D:** 人間医療レビューで `gate_b_approved` へ昇格可能なシナリオだけ選別
3. **C:** live `jev:minimal` repeat≥3（接続失敗は accuracy 分母から除外）
4. **A:** 合格シナリオだけ soft CI。全体 hard-fail はまだ禁止
5. eval を `jev_client.evaluate_system_one` に寄せて二重実装を解消
6. pipeline が focus を session に残すかどうかは **別変更・別承認**（Jev のためだけにやらない）

---

## 6. 参照

- 薬剤師レビュー: `JEV_SAFETY_FIXTURE_PHARMACIST_REVIEW_20260921.md`
- 契約凍結: `JEV_PHASE0_CONTRACT_FREEZE_20260921.md`
- 旧 Supervisor（甘い）: `JEV_PHASE1_LOCAL_SHADOW_SUPERVISOR_REPORT_20260921.md` — **本レポートが上位**

---

*Supervisor harsh PDCA — 2026-09-21*
