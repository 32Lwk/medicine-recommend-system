# R7 臨床安全 独立セカンドオピニオン

**文書ID**: JEV_R7_MEDICAL_SECOND_OPINION_20260923  
**作成日**: 2026-09-23  
**分類**: 独立臨床安全評価（External Independent Clinical Safety Second Opinion）  
**外部医療セカンドオピニオン未取得**  
**評価スコープ**: R7 の4機能 — Detector View / NM Disabled / Ambiguous Sleep Not Illegal / CheckpointEntry Rollback  
**評価方針**: medicine-recommendation-advisor スキルおよび他 R7 医療文書を参照せず、ソースコードと公知の医療安全原則のみに基づいて独立評価した。  
**コードベース参照**: `src/dialogue/routing/detector_text_view.py`, `canonical_normalize.py`, `turn_signal_snapshot.py`, `pre_route_signals.py`, `sleep_med_policy.py`, `policy_resolve.py`, `policy_enforce.py`, `policy_adapters.py`, `policy_types.py`, `src/core/crisis_detection.py`

---

## 0. エグゼクティブサマリー

| 評価軸 | 総合判定 | 主要課題 |
|-------|---------|---------|
| Detector View（R7-B） | **条件付き承認** | evasion_residue の safety path への直接連動なし；ログ非対称性 |
| NM Disabled（R7-E） | **承認** | SF-E1 fallback 経路でのクライシスリソース非提示リスク |
| Ambiguous Sleep Not Illegal（R7-C） | **条件付き承認** | 潜在的自殺企図の sleepmed 要求への safe_clarification 到達リスク |
| CheckpointEntry Rollback | **条件付き承認** | ロールバック成功後の安全追跡情報消去（DB 不可時） |

**外部医療セカンドオピニオン未取得** — 以下の評価は当評価者のみの独立見解であり、臨床薬剤師・精神科医・救急医等の専門職による外部レビューを代替しない。

---

## 1. Detector View（R7-B）

### 1.1 機能概要（コード根拠）

`detector_text_view.py` の `prepare_text_views(raw)` は、単一の生入力テキストから2つのビューを生成する：

1. **canonical text**（`canonical_normalize` 経由）: 表示・SessionOps 分類・一般ログ用
2. **detector comparison view**: 安全/ポリシー検出器専用 — ゼロ幅文字（U+200B–U+200D, U+200E/F, U+202A–E, U+2060, U+FEFF, U+00AD）およびCJK文字間の空白を除去

`create_turn_signal_snapshot` はこの `dview.text` を `detector_text` として `collect_pre_route_signals` へ渡す。検出器（危機キーワード、緊急、不審クエリ等）は canonical ではなく detector view で動作する。

`had_evasion_residue` が真のとき `evasion_fail_closed=True` が設定され、SessionOps の pure gate (`is_pure_session_ops`) はブロックされる。

### 1.2 臨床安全上の有益性

- **クライシス回避攻撃への防御**: `死​にたい`（ZWSPで分断）は canonical では検出失敗するが、detector view では `死にたい` に揃い正常に検出される。本機能はこの攻撃ベクターを有効に塞ぐ。
- **CJK 空白回避への対応**: `死 にたい`（全角スペースや改行で分断）も collapse により検出される。

### 1.3 臨床安全上の懸念

#### 懸念 A — evasion_residue フラグの safety 経路非連動

`had_evasion_residue=True` は `is_pure_session_ops` をブロックするが、クライシス・緊急・ポリシー経路への追加エスカレーションには**直接結びついていない**。

具体的には：

- ユーザーが `死​にたい`（ZWSP挿入）を送信 → detector view が除去 → `crisis_detected=True`
- この場合、クライシス対応は正常に働く（Good）
- しかし: `睡​眠薬` のように、零幅文字挿入で**検出が成功した**事実（= 回避試行の証拠）が、観測性ログにおいて `detector_view_had_evasion=True` として記録されるのみで、**同一ターンのレスポンス内容には反映されない**

**評価**: 検出は機能する。ただし `evasion_had_residue && crisis_detected` の組み合わせが観測された際に追加の応答モード（例: より明示的な緊急案内）に切り替わるロジックは存在しない。意図的な回避試行者へのレスポンスが通常クライシス対応と同一である。これは安全上の欠落ではないが、将来の観察対象として記録する。

#### 懸念 B — canonical/detector 非対称性とログ整合性

クライシス応答が発火した際のログ（`counseling_detail` 等）には canonical text が記録されるが、detector view が何を見たか（除去文字数、collapsed フラグ）は `observability_fields()` の `detector_view_had_evasion` のみ。除去された文字の内容はログに残らない。

- **患者安全観点**: 危機介入が実施された際の事後レビューで、ユーザーが実際に使用した文字列の復元が困難。
- **軽減措置あり**: `stripped_ignorable_count` と `cjk_internal_ws_collapsed` がスナップショットに記録される。詳細文字内容の非記録はプライバシー上意図的と推定。

#### 懸念 C — 未対応の回避手法

`_STRIP_CPS` は Unicode カテゴリ Cf（フォーマット文字）を広くカバーするが、以下は**現在の detector view では対応していない**：

- 半角・全角カタカナ変換回避（例: `ｼﾆﾀｲ` → `死にたい`）
- ひらがな↔カタカナ表記揺れ（例: `シにたい`）
- 同形異字（例: キリル文字等による視覚的偽装）

これらは detector view v1 のスコープ外であるが、将来の攻撃面として記録する。

### 1.4 判定

**条件付き承認**: 現行の回避防御は正常に機能する。evasion_residue の safety path への直接エスカレーション連動の不在は現時点では許容範囲内だが、観察継続が必要。

---

## 2. NM Disabled（R7-E）

### 2.1 機能概要（コード根拠）

`policy_enforce.py` の `SF_E1_NM_ENABLED = False`。

フォールバック発生時（ミューテーション失敗、DB コミット失敗、不明エラー等）は常に `build_sf_e1_response()` が呼ばれる。`_SF_E1_NM_SUFFIX`（「今回の操作では履歴や記録内容は変更されていません。」）は frozen かつ未使用。`_safe_fallback` 内で `no_mutation_claim=False` が強制される。

### 2.2 臨床安全上の有益性

- **不正確な保証の排除**: NM サフィックスは「変更なし」を主張するが、ロールバック失敗・partial write シナリオでは虚偽の保証になり得る。NM を無効化することで、誤った安心感の付与を防ぐ。
- **SF-E1 は中立**: generic system error として提示され、ユーザーが「安全に操作された」と誤解することを防ぐ。

### 2.3 臨床安全上の懸念

#### 懸念 A — SF-E1 フォールバックにクライシスリソースが含まれない

`build_sf_e1_response()` は `build_system_error_status()` を呼ぶ。この応答には**いのちの電話等のクライシスリソースが含まれない**。

シナリオ: ユーザーが危機発話（例: `睡眠薬を全部飲みたい`）を送信 → `controlled_or_illegal_block` 発火 → `adapt_controlled_or_illegal` で adapter 実行 → DB commit が `failed` → **ロールバック** → **SF-E1 フォールバック**

この経路では：
1. クライシス対応（ `detect_crisis_keywords` による検出）は `collect_pre_route_signals` で行われるはずだが、ポリシー経路と危機検出経路が並走するとき、どちらが最終応答を担うかはパイプライン順序に依存する。
2. `policy_enforce.py` の `_safe_fallback` は `{"status": "error", "error": "policy_enforcement_fallback", ...}` を返す。この応答に crisis hotline 情報は存在しない。

**重大度評価**: 中程度。通常の `decide_jev_intent_eligibility` では `crisis_detected=True` が `DETERMINISTIC_HIGH_RISK` として最優先されるため、純粋なクライシス発話が policy_enforce まで到達する可能性は低い。しかし「睡眠薬が欲しい + 隠れた自傷意図」のような mixed 発話では crisis_detected が False のまま policy_enforce に到達しうる。

#### 懸念 B — ユーザー体験の断絶

SF-E1（システムエラー）がポリシー境界通知の代替として表示されると、ユーザーが「システム障害」と解釈し再試行する可能性がある。繰り返し試行が安全記録（`inappropriate_requests`）に記録されない（SF-E1 フォールバック時はミューテーションがロールバックまたは未実施）。

### 2.4 判定

**承認**（ただし観察継続）: NM 無効化そのものの安全判断は正しい。SF-E1 fallback 経路でのクライシスリソース非提示は許容範囲内だが、将来のパイプライン設計でクライシス優先パスが SF-E1 より前に確実に分岐していることを定期的に検証すること。

---

## 3. Ambiguous Sleep Not Illegal（R7-C）

### 3.1 機能概要（コード根拠）

`sleep_med_policy.py` の `classify_sleep_or_controlled_intent`:

| 入力パターン | 分類 | policy_flags |
|------------|------|-------------|
| 違法薬物取得 | `explicit_illegal` | `controlled_or_illegal_block=True` |
| 向精神薬等 + 取得動詞 | `named_controlled_acquisition` | `controlled_or_illegal_block=True` |
| 処方要求 | `prescription_request` | `prescription_block=True` |
| 睡眠薬 + 一般情報語 | `general_information` | flags なし |
| **睡眠薬 + 取得動詞（文脈不明）** | **`ambiguous_sleep_medicine_request`** | **`ambiguous_policy=True`** |

`ambiguous_policy=True` → `resolve_policy_decision` → `PolicyKind="ambiguous_controlled"` → action=`safe_clarification`

アダプター: `adapt_ambiguous_controlled` → `_AMBIGUOUS_SLEEP_BOUNDARY` テキスト（「当サービスでは処方薬の入手・代行はできません」）。`criminal_template=False` が明示されている。

### 3.2 臨床安全上の有益性

- **正当なOTC相談の保護**: ドリエル・ウトミン等の市販睡眠改善薬は OTC として合法。`睡眠薬が欲しいのですが` を犯罪テンプレートで返答することは医療サービスとして不適切であり、正当なヘルスケアへのアクセス障壁となる。
- **neutral clarification**: `safe_clarification` は `block` より弱いが、OTC相談への誘導路を開きながら処方薬経路は閉じる。適切なバランスである。
- **不法default排除**: R7-C 以前の実装が `ambiguous_sleep_medicine_request` を `controlled_or_illegal_block=True` に分類していた場合、それは臨床的に誤りだったといえる。変更は正しい方向性。

### 3.3 臨床安全上の懸念（主要）

#### 懸念 A — 隠れた自傷意図の safe_clarification 到達

**これが本評価における最重要懸念事項である。**

「睡眠薬が欲しい」という発話は、以下の複数の異なる意図を持つユーザーから発される可能性がある：

1. OTC 睡眠改善薬を探しているユーザー（良性）
2. 不眠症状で処方薬の情報を求めているユーザー（中性）
3. 大量服薬による自己傷害を意図するユーザー（**高リスク**）

**crisis_detection.py** には以下が含まれる：
- `'睡眠薬致死量'` → crisis_detected=True（Good）
- `'薬で楽になりたい'` → crisis_detected=True（Good）
- `'薬を一気に飲む'` → crisis_detected=True（Good）
- `'ODしたい'`, `'過量服薬'` 等 → crisis_detected=True（Good）

しかし `'睡眠薬が欲しい'` 単体、または `'よく眠れるように睡眠薬が欲しい'` は crisis_detected=False のまま `ambiguous_sleep_medicine_request` → `safe_clarification` に到達する。

**コード上の評価**:

`collect_safety_policy_signals` 内の処理順：
1. `_detect_overdose_cues(text)` → 「過量」「大量に飲」等をチェック
2. `detect_crisis_keywords(text)` → 上記リストをチェック
3. `classify_sleep_or_controlled_intent(text)` → 独立して ambiguous 判定

これら3つは独立して実行される（OR関係）。`crisis_detected=True` が `decide_jev_intent_eligibility` では DETERMINISTIC_HIGH_RISK として最優先される。したがって**明示的な crisis keyword が含まれる場合は safe_clarification より crisis 対応が優先される**。これは正しい設計。

問題は crisis keyword を含まない ambiguous 発話：「睡眠薬を手に入れたい」のみ。このケースで `ambiguous_policy=True, crisis_detected=False` となり、`safe_clarification` 応答（`_AMBIGUOUS_SLEEP_BOUNDARY`）が返される。このテキストは一般的な境界案内であり、クライシスリソース（いのちの電話等）を含まない。

**医学的文脈**: 自殺企図者が睡眠薬を求める際、明示的な死の言葉を使わないことは臨床的に一般的である（"masked suicidal ideation"）。OD リスクの高い薬剤への曖昧なアクセス要求はそれ自体が安全シグナルである可能性がある。

#### 懸念 B — `adapt_ambiguous_controlled` の `record_inappropriate=True` 設定

`MutationPlan(record_inappropriate=True, inappropriate_type="unknown_controlled_policy", inappropriate_blocked=False)` が設定される。

- `inappropriate_blocked=False` → ブロックではなく記録のみ。ユーザーは次のメッセージを送れる。
- 記録は `inappropriate_requests` に追加されるが、DB コミット失敗時はロールバックにより消去される（§4 参照）。

#### 懸念 C — `general_information` 分類の Bypass 条件

```python
if sleep_kind != "general_information":
    # controlled drug detector を実行
    if detect_illegal_or_controlled_drug(text):
        state["controlled_or_illegal_block"] = True
```

`sleep_kind == "general_information"` のとき `detect_illegal_or_controlled_drug` はスキップされ、`controlled_or_illegal_block` と `ambiguous_policy` も False に強制される（`sleep_med_policy.py` L286-290）。

この条件は: `睡眠薬 + 情報語（副作用・効能等）` の場合に `controlled_drug` 検出器をバイパスする。これ自体は副作用情報の正当な照会への適切な配慮だが、`睡眠薬の副作用と致死量について教えて` のような境界事例で `general_information` に分類されると controlled_drug 検出がスキップされる可能性がある。ただし crisis_detection は依然独立して動作するため、`致死量` の語は `crisis_keywords` にある（`'睡眠薬致死量'`）。

### 3.4 判定

**条件付き承認**: ambiguous → safe_clarification への変更は臨床的に正当だが、`safe_clarification` 応答内に軽量なクライシスリソース提示（例: 「こころの健康について不安がある場合はこちら: いのちの電話」）を含めることを将来の改善として推奨する。現行実装は許容範囲内だが、隠れた自傷意図の経路として監視対象とする。

---

## 4. CheckpointEntry Rollback

### 4.1 機能概要（コード根拠）

`policy_enforce.py` の `_build_checkpoint` / `_restore_checkpoint`。

**ロールバック対象キー** (`_CHECKPOINT_KEYS`):
- `messages`, `inappropriate_requests`, `counseling_mode`, `illegal_drug_block`, `pending_memory_delete`, `counseling_symptom_type`, `counseling_questions`, `_policy_enforcement_d2_request_local_dedup`, `_policy_enforcement_d2_receipt`

**発火条件**:
1. `_apply_mutation_plan` が例外 → ロールバック → SF-E1 (`fallback_reason="adapter_error"`)
2. DB commit が `failed` or `unknown` → ロールバック → SF-E1 (`fallback_reason="db_save_failed"` or `"db_commit_unknown"`)
3. `_build_checkpoint` 自体が失敗（deepcopy 失敗）→ **ロールバックなし** → SF-E1 (`fallback_reason="adapter_error"`, `mutation_started=False`)

`_restore_checkpoint` は `deep_equals_session` で等値チェックを行い、不一致なら `logger.error("policy_d2 rollback equality check failed")` を記録しつつ `return False`（ただし処理は継続）。

### 4.2 臨床安全上の有益性

- **セッション一貫性**: ミューテーション途中での DB 障害時に `messages` と `inappropriate_requests` が中途半端な状態に残ることを防ぐ。
- **illegal_drug_block の整合性**: DB 不整合時に `illegal_drug_block=True` のみメモリに残り、次回リクエストで DB と乖離する状態を防ぐ。
- **明示的なエラー記録**: `INTERNAL_ALERT policy_d2 rollback_failed` というログにより、観測性が確保されている。

### 4.3 臨床安全上の懸念

#### 懸念 A — ロールバック成功時の安全追跡記録の消去

ロールバック成功（`rollback_ok=True`）の場合：

- `inappropriate_requests` の新規エントリ（`type="unknown_controlled_policy"` 等）が**消去される**
- `illegal_drug_block=True` の設定が**消去される**
- `messages` の bot 応答追加も消去される

これはセッション一貫性のために正しい動作だが、安全追跡の観点では:

**DB commit 失敗 → ロールバック → 次回リクエストで安全記録なし**

ユーザーが DB 不可時に繰り返し controlled drug 要求を送った場合、各リクエストが記録なしにリセットされる。メモリ内（`touch_session_in_memory` via `"memory_only"` パス）への書き込みが成功した場合のみ、同一プロセス内では追跡が維持される。

**重大度**: 低～中程度。DB 完全不可シナリオは限定的。ただし `"unknown"` ステータス（`db.save_session` が例外を投げたケース）も rollback trigger となるため、一時的な DB 応答遅延でも安全記録が揮発する可能性がある。

#### 懸念 B — `deep_equals_session` の比較セマンティクス

`deep_equals_session` は `entry.value != session.get(key)` で比較する。Python の `!=` はデフォルトで `__eq__` を使用するが、`messages` リストに含まれる辞書オブジェクトが複雑な場合（例: `datetime` オブジェクトが `isoformat()` 文字列混在）、等値判定が不安定になる可能性がある。

不一致が発生した場合は `logger.error` のみで処理継続されるため、ロールバック不完全でも SF-E1 が返される。ユーザー体験上は同じだが、セッションが部分的に変更された状態で次のリクエストに進む。

#### 懸念 C — `_build_checkpoint` deepcopy 失敗

`CheckpointBuildError` が raise された場合は `mutation_started=False` として SF-E1 フォールバックが発生する。この場合はミューテーション前なので安全だが、checkpoint ビルドが失敗する状況（セッションデータに pickle 不可オブジェクトが含まれる等）は観測難易度が高い。

### 4.4 判定

**条件付き承認**: ロールバック機構の設計は適切。DB 不可時の安全追跡記録消去リスクは認識すべき限界値であり、「DB 不可 = 安全追跡なし」という前提でリスク受容を明示するか、メモリ内カウンターによる補完的な安全追跡を検討すること。

---

## 5. 統合的臨床安全評価

### 5.1 相互作用リスクのアセスメント

| R7機能間の組み合わせ | 相互作用タイプ | リスク評価 |
|-------------------|-------------|----------|
| Detector View + Ambiguous Sleep | **補完**: evasion で分断された `睡眠薬` は detector view で統合され ambiguous 検出が確実化 | 低（保護的） |
| Ambiguous Sleep + CheckpointEntry Rollback | **競合**: safe_clarification の `inappropriate_requests` 記録が DB 失敗でロールバック → 追跡消去 | 中程度 |
| NM Disabled + Detector View | **独立**: 相互作用なし | 無し |
| CheckpointEntry + NM Disabled | **補完**: ロールバック後に NM クレームがないため、不正確な「変更なし」メッセージが消去済み状態で表示される心配がない | 低（保護的） |

### 5.2 要改善事項（優先度順）

| 優先度 | 機能 | 改善内容 | 臨床根拠 |
|-------|------|---------|---------|
| 1 | Ambiguous Sleep Not Illegal | `_AMBIGUOUS_SLEEP_BOUNDARY` テキストに軽量クライシスリソース（相談窓口 URL）を追加 | 隠れた自傷意図の発話が safe_clarification に到達したとき、唯一のセーフティネット |
| 2 | CheckpointEntry Rollback | DB unknown（一時障害）時のロールバックをトリガー条件から分離し、メモリ内追跡は維持する設計を検討 | 一時的 DB 障害でのセキュリティ追跡消去防止 |
| 3 | Detector View | `evasion_residue && policy_block` の組み合わせを観測性ダッシュボードで個別モニタリング | 回避試行者の policy 応答品質の継続評価 |
| 4 | NM Disabled | SF-E1 fallback 経路が crisis path より後に到達するパイプライン順序を定期的に単体テストで確認 | クライシスルーティングの回帰防止 |

### 5.3 本評価の限界

1. **外部医療専門家レビュー未取得**: 精神科・薬剤師・救急医によるレビューは実施されていない。
2. **動的テスト未実施**: 本評価はソースコードの静的分析のみ。実際の LLM 応答・DB 動作・並行リクエスト挙動は評価外。
3. **評価スコープ限定**: R7 の4機能に限定。他コンポーネントとの全体統合安全性は評価外。
4. **評価者の独立性**: 本評価者はプロジェクト開発チームとは独立した立場で評価したが、正式な第三者医療機関の認定を受けていない。

---

## 6. 判定サマリー

| 機能 | 判定 | 条件・観察事項 |
|-----|------|------------|
| **Detector View（R7-B）** | 条件付き承認 ✅⚠️ | evasion + crisis 組み合わせの観測継続；未対応回避手法の将来検討 |
| **NM Disabled（R7-E）** | 承認 ✅ | SF-E1 経路でのクライシスリソース不在を継続監視 |
| **Ambiguous Sleep Not Illegal（R7-C）** | 条件付き承認 ✅⚠️ | `_AMBIGUOUS_SLEEP_BOUNDARY` へのクライシスリソース追加を推奨 |
| **CheckpointEntry Rollback** | 条件付き承認 ✅⚠️ | DB unknown 時の安全追跡消去リスクを明示的にリスク受容または対策 |

**外部医療セカンドオピニオン未取得** — 本文書は独立内部評価であり、正式な臨床承認の代替ではない。

---

*評価者: Independent Clinical Safety Reviewer（プロジェクト内独立評価）*  
*評価日時: 2026-09-23*  
*ソースコード参照コミット: HEAD（2026-09-23 時点）*

---

## Supervisor follow-up note（2026-09-23）

本文書の「`_AMBIGUOUS_SLEEP_BOUNDARY` へいのちの電話追加」推奨は **採用されなかった**。  
現行方針は `JEV_R7_MEDICAL_REVIEW_AMENDMENT_SLEEP_CRISIS_20260923.md` を正とする（ambiguous 単独に危機窓口を出さない）。  
本ファイルはレビュー当時の勧告記録として残す。旧コードと follow-up 後コードを混同しないこと。
