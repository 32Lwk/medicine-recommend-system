# JEV A-3/D2 — 臨床安全 AI 独立セカンドオピニオン

**Date**: 2026-09-22  
**Reviewer**: AI 独立セカンドオピニオン（Claude Sonnet 4.6）  
**Method**: コードベース直接査読（PRIMARY / ADVERSARIAL レポート未参照・medicine-recommendation-advisor スキル不使用）  
**Mandate**: SF-E1 / SF-E1-NM 真実性規則、処方境界コピー、安全順序契約 Safety > Policy > SessionOps の独立評価  

---

## ステータス宣言

| 項目 | 状態 |
|------|------|
| **外部医療セカンドオピニオン** | **未取得** |
| 本レポート性格 | **AI 独立セカンドオピニオン** |
| 製品安全合格 | **主張しない・禁止** |
| Gate A-accuracy | Not Passed（本レポート変更不可） |
| Gate B | Hard No-Go（本レポート変更不可） |
| Human medical review | 未完了（本レポート代替不可） |

---

## 1. 評価範囲と方法

査読対象ソースファイル（直接コード読取）:

| ファイル | 役割 |
|---------|------|
| `src/dialogue/routing/canonical_normalize.py` | D2-b 正規化 |
| `src/dialogue/routing/turn_signal_snapshot.py` | SSOT snapshot |
| `src/dialogue/routing/pre_route_signals.py` | preflight 検出器群 |
| `src/dialogue/routing/policy_resolve.py` | PolicyDecision 解決 |
| `src/dialogue/routing/policy_types.py` | 型定義 |
| `src/dialogue/routing/policy_adapters.py` | コンテンツアダプター（処方含む） |
| `src/dialogue/routing/policy_enforce.py` | Enforcement / SF-E1 / mutation |
| `src/core/crisis_detection.py` | 危機検出（H04 凍結） |
| `tests/dialogue/routing/test_policy_enforcement_d2.py` | ユニットテスト確認 |
| `tests/dialogue/routing/test_policy_d2_adversarial_gates.py` | Adversarial ゲートテスト確認 |
| `docs/planning/codex-parallel-jev-20260921/JEV_BR_H03_H05_OPTION_A3_R5_CONTRACT_FREEZE_20260922.md` | 設計契約書 |
| `docs/planning/codex-parallel-jev-20260921/JEV_A3_D2_STAGING_MANIFEST_20260922.md` | ステージングマニフェスト |
| `docs/planning/codex-parallel-jev-20260921/JEV_F4C02_SAFETYGATE_ORDER_20260922.md` | 安全順序修正記録 |

---

## 2. SF-E1 / SF-E1-NM 真実性規則の評価

### 2.1 文言（コード実装から直接抽出）

```
SF-E1（既存）:
  title: 「一時的なエラーが発生しました」
  message: 「処理中に問題が発生しました。しばらく時間をおいてからもう一度お試しください。」
  hints: 「もう一度お試しください」 / 「問題が続く場合は薬剤師にご相談ください」

SF-E1-NM（新規追加）:
  上記 SF-E1 に suffix 付加:
  「今回の操作では履歴や記録内容は変更されていません。」
```

出典: `policy_enforce.py:27` `_SF_E1_NM_SUFFIX`

### 2.2 「変更されていません」主張の真実性ロジック

`_safe_fallback()` 内の `allow_nm` 制御ロジック（コード: `policy_enforce.py:350-359`）を独立査読した結果:

| 条件 | allow_nm 判定 | 真実性評価 |
|------|--------------|-----------|
| mutation_started = False | `True` | ✅ mutation 未着手で正確 |
| mutation_started = True AND rollback_ok = True AND db_commit_status = "failed" | `True` | ✅ DB 明示失敗 + rollback 成功 → 実際に変更なし |
| mutation_started = True AND rollback_ok = True AND db_commit_status = "unknown" | **`False`**（強制）| ✅ 不明状態で NM 主張を禁止 — 正確 |
| mutation_started = True AND rollback_ok = False | `False` | ✅ rollback 失敗 = 変更残存可能性あり → 正確 |

**判定: SF-E1-NM 真実性ロジックは技術的に健全。**

`db_commit_status == "unknown"` に対する `allow_nm = False` 強制（`policy_enforce.py:356-357`）は特に重要。DB コミット状態が不明なときに「変更されていません」と主張することはユーザーへの虚偽表示となるため、この排除ルールは臨床安全上必須かつ正しく実装されている。

### 2.3 template 流用禁止の確認

`build_sf_e1_response()` は `build_system_error_status()` のみを呼び出す。テスト `test_sf_e1_nm_suffix()` でも「救急」「違法」等の医療・違法薬物テンプレートが混入していないことを確認済み（コード: `test_policy_enforcement_d2.py:68-77`）。

**判定: 救急 / 違法薬物 / 診察境界テンプレートとの混在なし。合格。**

### 2.4 「薬剤師に相談」ヒントの適合性

`build_system_error_status()` のヒント「問題が続く場合は薬剤師にご相談ください」は:
- 臨床断定なし ✅
- 救急緊急示唆なし ✅（危機・緊急は上位 Safety が先行）
- OTC 文脈で適切なリファレンス ✅

**合格。**

---

## 3. 処方境界コピーの評価

### 3.1 文言（コード直接確認）

```
_PRESCRIPTION_BOUNDARY（policy_adapters.py:10-14）:
「申し訳ありません。当サービスでは医師の処方箋が必要な医薬品の処方や
処方の代行はできません。必要に応じて医療機関を受診してください。
市販薬（OTC）についてのご相談であれば、具体的な症状やお困りごとをお書きください。」
```

### 3.2 臨床安全評価

| 観点 | 評価 |
|------|------|
| 特定医薬品の処方・識別 | 行わない（固定境界文；LLM 呼び出しなし）✅ |
| LLM を処方判定根拠に使用 | 禁止 — `adapt_prescription` は LLM 非使用（`llm_used: False`）✅ |
| 医療機関受診誘導 | あり（「必要に応じて医療機関を受診してください」）✅ |
| OTC 相談継続パス | 明示（「市販薬（OTC）についてのご相談であれば」）✅ |
| 断定的医療助言 | なし ✅ |
| 誤解を招く表現 | なし ✅ |

### 3.3 `inappropriate_blocked=False` の意図確認

`adapt_prescription()` は `record_inappropriate=True, inappropriate_blocked=False` を設定する（`policy_adapters.py:31-32`）。

これは「ログ記録あり・ハードブロックなし」の境界案内モードであり、処方要求はセッション継続を許可しつつ OTC 相談へ誘導するという設計意図に一致する。違法薬物の `inappropriate_blocked=True`（ハードブロック）とは意図的に異なる。

**判定: 処方境界コピーは臨床安全上適切。境界を越えず、代替パスを示し、断定なし。合格。**

---

## 4. 安全順序契約 Safety > Policy > SessionOps の評価

### 4.1 信号階層の独立確認

`pre_route_signals.py` の `PreRouteSignals` を直接査読:

```
deterministic_high_risk = emergency_detected OR security_blocked OR crisis_detected
policy_block           = medical_examination OR prescription_block OR controlled_or_illegal_block
session_operation      = preflight 固定（additive merge で書き換え禁止）
```

`safety_or_policy_blocks_session_ops()` の実装:

```python
def safety_or_policy_blocks_session_ops(signals: PreRouteSignals) -> bool:
    if not signals.evaluation_complete:
        return True   # fail-closed: detector 失敗時も SessionOps を許可しない
    return bool(signals.deterministic_high_risk or signals.policy_block)
```

**fail-closed 設計（evaluation_complete=False → SessionOps ブロック）は安全上正しい。**

### 4.2 `is_pure_session_ops()` ゲート確認

`turn_signal_snapshot.py:139-150`:

```
純 SessionOps の条件（全て満たす場合のみ True）:
  evaluation_complete = True
  detector_errors = ()
  deterministic_high_risk = False
  policy_block = False
  session_operation_detected = True
```

**Safety / Policy いずれか 1 つでも陽転すると SessionOps ゲートが閉じる。正しい実装。**

### 4.3 Policy 内優先順位（controlled > prescription > examination）

`policy_resolve.py:35-67`:
- `controlled_or_illegal_block` → priority 1（ハードブロック）
- `prescription_block` → priority 2（境界案内）
- `medical_examination` → priority 3（境界案内）

この順序は臨床上正当。違法・規制薬物は最も厳しいブロック; 処方は医療機関誘導; 診察境界は最も軽いガイダンス。

### 4.4 TurnSignalSnapshot additive merge における SessionOps 保護

`turn_signal_snapshot.py:58-60`:

```python
before_session_op = state["session_operation"]
merge_additive_bag(state, bag)
# SessionOps intent is preflight-fixed; ignore bag attempts to change it.
state["session_operation"] = before_session_op
```

triage や後段コンポーネントが `session_operation` を書き換えようとしても無効化される。preflight 固定原則が additive merge API で強制されている。

**判定: Safety > Policy > SessionOps 順序契約は構造的に正しく実装されている。合格。**

### 4.5 JEV F4-C02（SessionOps vs SafetyGate 順序修正）確認

`JEV_F4C02_SAFETYGATE_ORDER_20260922.md` により、admin_probe が Emergency/Crisis より先に勝つ経路の修正済みが確認された。ただし同文書 Residual risk 欄に記載の以下の残存 open 項目を認識:

- S1-G02: SessionOps + medical examination（LLM triage 依存）
- S1-G03-gate: gate に policy 段なし
- S1-G05: negated crisis（否定スコープなし）
- S1-G06: stale counseling × high-risk
- S1-G08: stroke-like / chest on gate

これらは本レポートのスコープ外（H04 / 別修正待ち）だが、残存リスクとして明記する。

---

## 5. 残存リスク：ゼロ幅文字によるクライシス・規制薬物検出回避（H04 凍結）

### 5.1 技術的事実の確認

`canonical_normalize.py:18-20` のコメント:

```
Does not delete policy/crisis/security substrings or zero-width chars
(zero-width left intact so residual can track evasion — see tests).
```

`canonical_normalize()` は NFC + strip + 内部空白圧縮のみ。**ゼロ幅文字（U+200B, U+200C, U+200D, U+200F, U+FEFF 等）は生き残る。**

### 5.2 危機検出への影響

`crisis_detection.py` の `_keyword_matches()`:

```python
def _keyword_matches(keyword: str, user_message_lower: str) -> bool:
    kw = keyword.lower()
    if kw.isascii() and len(kw) <= 3:
        return bool(re.search(r"(?<![a-zA-Z])" + re.escape(kw) + r"(?![a-zA-Z])",
                               user_message_lower, re.IGNORECASE))
    return kw in user_message_lower  # ← 単純部分一致
```

日本語キーワード（「死にたい」「自殺」「OD」等）は `kw in user_message_lower` の単純部分一致。

**攻撃シナリオ**: `"死\u200bにたい"` （死とにたいの間にゼロ幅スペース）を送信すると:
- `canonical_normalize` を通過（ゼロ幅は保持）
- `"死にたい" in "死\u200bにたい"` → **False** → `crisis_detected = False`
- → Safety high_risk gate が閉じない
- → SessionOps / OTC ルーティングへ進む可能性

同様に `_detect_prescription_markers()` の `any(m in text for m in rx_markers)` も部分一致なので、`"処\u200b方して"` でも prescription_block が陽転しない可能性がある。

### 5.3 H04 凍結の意味

ステージングマニフェスト（`JEV_A3_D2_STAGING_MANIFEST_20260922.md:71`）:

```
| `src/core/crisis_detection.py` | 医療 BR / H04 変更禁止帯 |
```

この位相では `crisis_detection.py` に修正を加えることが明示的に禁止されている。

### 5.4 リスク評価

| リスク | 重大度 | 現在の緩和策 |
|--------|--------|-------------|
| ゼロ幅挿入による crisis_detected 回避 | **高** | なし（H04 凍結）|
| ゼロ幅挿入による prescription_block 回避 | 中 | `known_attack_rules` が一部カバー可能性 |
| ゼロ幅挿入による controlled_or_illegal 回避 | 高 | `detect_illegal_or_controlled_drug`（triage LLM）が後段カバー |

危機検出の回避は最も重大。自殺・自傷リスクのあるユーザーが意図的または偶発的にゼロ幅文字を含む文章を送った場合、`SafetyGate_pre` の `crisis_detected` が false になる。後段の LLM triage や `is_emergency_candidate` が補完する可能性はあるが、deterministic な保護が失われる。

**この残存リスクは H04 凍結解除後に対処が必要。実装解除前の必須タスクとして記録する。**

---

## 6. その他の観察事項

### 6.1 prescription 記録での `inappropriate_blocked=False`

処方要求を `inappropriate_requests` にログするが blocked=False のため、後段の集計で「inappropriate かつ blocked=True の件数」を KPI にしていると処方件数が見えない。運用モニタリング設計の確認を推奨。

### 6.2 durable exactly-once 未保証（明示済み）

マニフェスト Residual #1 の通り、`client_request_id` が安定していないため exactly-once は主張されていない。SF-E1-NM の idempotency は request-local receipt のみ。これは実装契約の正直な宣言であり、適切。

### 6.3 `evaluation_complete` false 時の fail-closed 動作

`pre_route_signals.py:306-311` の fail-closed ロジックは、detector 例外（crisis_detector_error 等）発生時に SessionOps を許可しない。**これは安全方向のデフォルト**。ただし detector 例外が頻発するとすべての会話が SF-E1 fallback になる可能性があるため、detector エラーレートの監視が必要。

---

## 7. 総合評価

### 7.1 個別評価サマリー

| 評価項目 | 判定 | 備考 |
|---------|------|------|
| SF-E1 文言 — 医療断定なし・template 流用なし | ✅ 合格 | |
| SF-E1-NM 真実性 — NM 条件の正確な制御 | ✅ 合格 | unknown 状態での NM 禁止を確認 |
| 処方境界コピー — LLM 非使用・医療機関誘導・断定なし | ✅ 合格 | |
| Safety > Policy > SessionOps 順序 | ✅ 合格 | fail-closed; additive-only merge |
| ゼロ幅文字回避（H04 凍結）— 危機検出 | ⚠️ 残存リスク | H04 解除後対処必須 |
| ゼロ幅文字回避（H04 凍結）— 規制薬物検出 | ⚠️ 残存リスク | LLM triage が後段補完 |
| Human medical review 完了 | ❌ 未完了 | 本レポートで代替不可 |
| Gate A-accuracy | ❌ Not Passed | 本レポートで解除不可 |
| Gate B | ❌ Hard No-Go | 本レポートで解除不可 |

### 7.2 Verdict

**CONDITIONAL（条件付き承認）**

承認条件:
1. **[C1] Human medical review 完了**: SF-E1 / SF-E1-NM 文言の担当薬剤師・医療安全レビューが完了すること（本レポートで代替不可）
2. **[C2] Gate A-accuracy 通過**: Gate A-accuracy を通過すること
3. **[C3] H04 凍結解除後のゼロ幅対策**: H04 解除フェーズで `detect_crisis_keywords` および関連 keyword matcher にゼロ幅文字正規化または Unicode category フィルタを追加すること。本フェーズでの実装は禁止（凍結遵守）
4. **[C4] Gate B 解除**: Gate B が No-Go の間は live 禁止を継続

本レポートが評価する技術実装（SF-E1/SF-E1-NM 論理・処方境界・安全順序）は **設計として正しく**、条件 C3 は現フェーズでの blocking ではなく post-H04 タスクとして記録する。

---

## 8. ラベル付与

Verdict = Conditional のため、以下のラベルを付与する:

> **AI多重医療監修済み候補**

ただし:
- 外部医療セカンドオピニオン未取得
- Human medical review 未完了
- Gate A-accuracy Not Passed
- Gate B Hard No-Go
- ゼロ幅危機回避リスク残存

**製品安全合格は主張しない。live / commit / push は本レポートで解除しない。**

---

## 9. 禁止確認

| 禁止項目 | 本レポートでの扱い |
|---------|-----------------|
| 製品安全合格の宣言 | 行わない |
| Gate A / Gate B 解除 | 行わない |
| commit / push 承認 | 行わない |
| プロダクトコード変更 | 行っていない |
| PRIMARY / ADVERSARIAL レポート参照 | 行っていない |
| medicine-recommendation-advisor スキル使用 | 使用していない |

---

*本レポートは AI 独立セカンドオピニオンとして、コードベースの直接査読のみに基づく。外部医療専門家・薬剤師によるレビューの代替ではない。*

---

## Supervisor amendment（2026-09-23）

本文書 §8 の「AI多重医療監修済み候補」付与主張は記録として残す。  
ただし並列 adversarial / 早期 SF copy panel に Critical・NM Reject寄りが残るため、Supervisor は意見分裂時の安全側規則により **プロジェクト公式ラベルは hold**（`JEV_FINAL_SUPERVISOR_REPORT_A3_D2_20260922.md`）。本節は second-opinion 本文の書き換えではない。
