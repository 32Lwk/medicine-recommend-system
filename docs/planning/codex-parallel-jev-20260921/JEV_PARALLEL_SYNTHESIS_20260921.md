# Jev 並列調査 統合計画（Phase 0–2）

- 作成日: 2026-09-21
- 対象: Chat Pipeline v2 / IntentRouter × TypeSafe System One (Jev)
- 方針: 精度優先。コード実装・dev設定変更・本番接続は本書の対象外
- 採用 adapter: `jev:minimal` のみ

## 0. 統合結論

最終方針は次の1本とする。

1. **Phase 1 のローカル shadow 実装には進む。** 差し込み点は `src/dialogue/routing/router.py::resolve_route()` の legacy decision 確定後とし、Phase 1 は常に同じ legacy decision を返す。
2. **精度判定は primary と必須 sub-route の joint 判定にする。** primary confidence だけでは `013452` の medicine comparison 劣化を検出できない。
3. **Emergency / Security / medical_examination は Jev 単独確定を禁止する。** Jev は既存 SafetyGate / deterministic gate の陽性を解除できず、高リスク signal は OR で安全側へ寄せる。
4. **SessionOps は Jev primary 対象外。** 現行 fast-path を維持する。
5. **現時点で dev 展開・primary canary は No-Go。** 10シナリオは pilot としては合格だが、高リスク、境界、会話文脈、障害時挙動の母数が不足している。
6. **次の Jev 対象は Phase 1 完了後に `medicine_qa_focus_llm` から評価する。** eligibility と focus は責務が異なるため統合しない。triage stage1/2 の1-call統合は安全性未証明のため後段とする。

## 1. 根拠と数値

採用する最新の有効実測は `log/analysis/jev_intent_router_eval_10_20260921_013619.{json,md}` である。同じ10シナリオを各3回、cacheなしで比較している。

| Backend | Accuracy | Avg | P50 | P95 |
| --- | ---: | ---: | ---: | ---: |
| current | 30/30 (100%) | 1456.28 ms | 1112.62 ms | 3216.91 ms |
| `jev:minimal` | 30/30 (100%) | 536.78 ms | 532.54 ms | 594.15 ms |
| 短縮量 | 同率 | 919.50 ms | 580.08 ms | 2622.76 ms |

- latency 条件「avg 900ms以上、またはP95 2500ms以上短縮」は両方で達成した。
- 9/10シナリオで Jev が高速だった。SessionOps だけは current 490.13 ms、Jev 508.57 msで、Jevが18.44 ms遅い。
- `013452` では `jev:minimal` が10/10、`jev:with_baseline_triage` が9/10。後者は medicine comparison の sub-route を `medicine_qa` から `none` に落としたため棄却する。
- Jev usage は平均 input 1358.5 tokens、output 367.7 tokens。input $0.042/MTok 前提では約 $0.0000571/call（157円/USDの参考換算で約0.00896円/call）。
- `dialogue.intent_router_llm` の過去ログ上の平均は約0.0402円/call。OpenAI callを70%削減してもJev代控除後の純削減は約0.01918円/対象turn、現行OpenAI費比47.7%である。したがって「OpenAI cost 70%削減」と「総分類費70%削減」を混同しない。

今回の再測定は外部API接続拒否で完走していないため、`013619` の再現性は未確認である。接続失敗をaccuracy分母へ混ぜず、不完全な再測定結果も採用しない。

## 2. 仮説の最終裁定

| ID | 最終判定 | 主張 | 裁定理由 | 検証・合格条件 | 失敗時の次手 |
| --- | --- | --- | --- | --- | --- |
| H1 | **限定採用** | `jev:minimal` は IntentRouter の置換候補である | 30/30かつ速度条件達成。ただし10種類のみで一般化不可 | 拡張fixtureのjoint accuracy 100%、高リスクFN=0、既存正解の回帰0 | 回帰routeをprimary allowlistから除外しlegacy継続 |
| H2 | **棄却** | `with_baseline_triage` を改善して利用する | Ask hintが原文より強く作用し、primary 1.00のままsubを誤った。入力tokenも増える | 再検証しない。payloadに `baseline_triage_hint` がないことをcontract test化 | typed questionとしてlater phaseで別評価 |
| H3 | **採用** | 高リスクは Jev + 既存gateの二重確認が必要 | Jev陽性例はEmergency/Security各1件だけ。既存gateにも語彙・short-path上の穴がある | combined判定でEmergency/Security/medical_examination FN=0。Jev陰性で既存陽性を解除した件数0 | primary停止、既存gate優先、fixture/handlerを補強 |
| H4 | **採用** | SessionOpsは現行fast-pathを維持する | currentの方が18.44 ms高速。既存early returnがある | SessionOps matrix 100%、Jev call 0 | 曖昧caseのみ将来shadow、primaryにはしない |
| H5 | **保留** | 短い構造化metaがfollow-upを改善する | 合理性はあるがsetup付き実測がなく、stale anchoringリスクがある | none/correct/stale/conflicting stateでcold-start悪化0、follow-up改善 | 商品名最大3・鮮度条件を厳格化、それでも悪化なら履歴のみ |
| H6 | **暫定採用** | floor 0.70 / high 0.85を初期観測値にする | 境界例がなく校正不能だが、初期fallback設計には使える | primary/sub/Noul別coverage、誤り、ECE/Brierを拡張集合で評価 | route別閾値。未校正ならconfidence単独gateを禁止 |
| H7 | **採用** | primary/subを別々に判定する | primary 1.00でもsub誤りが実在。architecture subは0.69–0.71 | sub必須routeはprimaryとselected subの両方を検査。joint誤り0 | subが弱いrouteはlegacy fallback |
| H8 | **保留** | Noul override 0.75を一律利用できる | 高リスク陽性各1件では閾値を決められない | Emergency/Security別PR評価。FN=0制約、Emergency FPは参考上限2% | Noulは補助signalに限定、既存handlerで最終確定 |
| T1 | **保留** | triage stage1+2をJev 1 callへ統合する | latency余地はあるが選択肢干渉と単一障害点のリスクが大きい | combined/separated比較でsafety FN=0、category非劣性、Other macro-F1差-2pt以内 | stage2のみ分離導入 |
| T2 | **採用** | Medicine QA eligibilityとfocusを分離する | route可否とQA内部観点では誤りの影響が異なる | physical pivot FN=0、route exact必須集合100%、focus macro-F1非劣性 | focus単独を先行、eligibilityはshadow継続 |
| T3 | **保留・後回し** | Store専用分類をIntentRouter結果へ統合する | 重複削減余地はあるが到達頻度とPhysical競合精度が未計測 | Physical競合FN=0、non-store FP=0、store kind exact 100% | IntentRouterは候補のみ、既存store ruleを最終決定に残す |

### 矛盾の裁定原則

- 「10ケース100%なのでGo」と「primaryはNo-Go」は矛盾しない。前者は**pilotのaccuracy/latencyゲート**、後者は**運用安全性を含む総合ゲート**である。本書では精度優先により後者を採用する。
- Phase 1 shadowの実装前に必要なのは、API結果を増やすことではなく、mapping・禁止payload・failure contract・P0 fixtureを固定することである。ローカル実装とmock/unit整備は進めるが、dev有効化は拡張live評価後とする。
- background shadowは本線latency非干渉に有利だが、無制限threadやプロセス終了時のログ欠損を許容しない。bounded executorとテスト用同期入口を仕様に含める。
- `JEV_API_KEY` を唯一の正規名とする。`TYPESAFE_API_KEY` fallbackは設定の二重化と誤配備を生むためPhase 1仕様には採用しない。

## 3. Phase 1 実装仕様

### 3.1 実行シーケンスと不変条件

```text
try_agent_dispatch
  -> resolve_route(...)
       -> legacy = resolve_route_unified_or_legacy(...)
       -> flags OFF: legacyを返す
       -> allowlist済みsnapshotを構築
       -> bounded executorへJev shadowを1回だけ投入
       -> legacyと同一オブジェクトを返す

background worker
  -> Jev API (timeout 3.5s; 429/5xxのみ最大1 retry)
  -> schema/mapping検証
  -> legacy / Jev / executed / usage / latency / errorを専用eventへ記録
```

必須の不変条件:

1. Phase 1 は `JEV_INTENT_ROUTER_PRIMARY` の値にかかわらず Jev decisionを返さない。誤設定でprimary化できないコード構造にする。
2. Jev失敗、低confidence、不正schema、ログ失敗はchat本線へ伝播させない。
3. Jevは `_intent_router_shadow`、`_routing_decision`、`dialogue_state.routing`、`last_triage_result` を更新しない。
4. workerへsession proxyを渡さず、JSON-safeなimmutable snapshotだけを渡す。
5. 既存shadowが通常の `resolve_route()` を再入している箇所と二重起動・session競合を起こさない。
6. SessionOps fast/triage path、SafetyGate、回答生成、推薦ランキングは変更しない。
7. raw user input、履歴、Jev raw response、API keyをshadow logへ保存しない。

### 3.2 変更ファイル

| 種別 | ファイル | 変更内容 |
| --- | --- | --- |
| 新規 | `src/services/jev_client.py` | HTTP/auth、3.5s timeout、429/5xxのみ最大1 retry、usage/latency返却。route判断とsecret logは禁止 |
| 新規 | `src/services/jev_decisions.py` | Choice/Noulのschema検証、enum正規化、primary/sub/Noul confidenceを分離したshadow DTOへの変換 |
| 新規 | `src/services/jev_metrics.py` | `jev_intent_router_shadow` event、failure分類、cost/usage、execution join。書込失敗は非伝播 |
| 新規 | `src/dialogue/routing/jev_router.py` | typed questions、state allowlist builder、bounded scheduling。dispatch keyへの書込禁止 |
| 変更 | `src/dialogue/routing/router.py` | legacy確定後にshadowを一度だけscheduleし、常にlegacyを返す |
| 変更 | `config/llm_flags.py` | kill switchとshadow getter。全default OFF |
| 変更 | `config/routing_config.py` | model、timeout、confidence getter。不正値は安全な既定値 |
| 変更 | `src/dialogue/dispatcher.py` | 実行decisionをcorrelation id付きでmetricsへ通知。Jev decisionは読まない |
| 変更 | `src/handlers/chat/chat_post_pipeline.py` | 既存shadowとの二重起動を解消。Jev APIを直接呼ばない |
| 条件付変更 | `src/utils/structured_logger.py` | 専用event sinkが既存仕組みで不足する場合のみ追加 |
| 新規 | `tests/services/test_jev_client.py` | transport/retry/timeout/secret非出力 |
| 新規 | `tests/services/test_jev_decisions.py` | 全enum、sub必須、Noul、malformed response |
| 新規 | `tests/dialogue/routing/test_jev_router.py` | state allowlist、0/1/5/6 turn、schedule条件、session非変更 |
| 新規 | `tests/dialogue/routing/test_jev_shadow_integration.py` | ON/OFF/失敗時にexecuted routeとresponseが不変 |
| 新規 | `tests/fixtures/jev_intent_router_safety_expanded.yaml` | P0高リスク・競合・否定・会話文脈fixture |

### 3.3 Feature flags / 設定

| env | default | Phase 1での意味 |
| --- | ---: | --- |
| `JEV_ENABLED` | `false` | 全Jev callのkill switch |
| `JEV_INTENT_ROUTER_SHADOW` | `false` | IntentRouter shadow schedulingを許可 |
| `JEV_INTENT_ROUTER_PRIMARY` | `false` | 予約値。Phase 1ではtrueでも実行decisionに影響させない |
| `JEV_MODEL` | `jev-latest` | shadow評価用。primary前にversion pinを再判断 |
| `JEV_TIMEOUT_SEC` | `3.5` | runtime timeout |
| `JEV_CONFIDENCE_FLOOR` | `0.70` | 観測上の低信頼分類。primary判定には未使用 |
| `JEV_HIGH_CONFIDENCE` | `0.85` | Phase 2候補値。Phase 1では観測のみ |
| `JEV_API_KEY` | 未設定 | 正規の唯一のsecret名。値は保持・ログしない |

### 3.4 state契約

送信を許可するのは以下だけとする。

- `channel`: `web` / `line`。sidやuser idは送らない。
- sanitized `user_input`。
- 直近5 turnの `role` / `content`。
- `last_primary_route`, `last_sub_route`。
- `last_recommended_medicines`: 商品名のみ最大3。
- `active_symptoms`, `medicine_qa_focus`: 当該時点ですでに取得済みの場合のみ。Jevのために追加LLMを呼ばない。
- 固定の短い `app_context`。

送信禁止: `baseline_triage_hint`、生のtriage category、識別子、不要PII、user attributes、RAG全文、生成prompt全文、medicine説明全文、5 turnを超える履歴。

### 3.5 mapping / safety契約

- primary Choice: `Physical | SessionOps | Concierge | Emergency | Security | Store | Counseling | Unknown`。
- sub Choiceはfixtureで定義済みの有限enumに限定し、未知値・欠損・非数・範囲外confidenceはinvalidとする。
- shadow DTOは `primary_confidence`、`selected_sub_confidence`、各Noul値を別フィールドで保持する。primary confidenceでsubやNoulを代表させない。
- deterministic/SafetyGateが高リスク陽性なら、Jev陰性で降格させない。
- Phase 1のJev高リスクoverrideは比較用ラベルであり、実行decisionを変えない。
- Noul 0.75は評価用暫定値に留め、Phase 2契約へ固定しない。

### 3.6 観測契約

1 decisionにつき、成功・失敗のいずれでも集計可能なeventを残す。最低フィールドは次とする。

- `schema_version`, `timestamp`, `environment`, `release_id`, `correlation_id`, `trace_hash`
- `mode`, `adapter_mode=minimal`, `model` と解決version
- `legacy_decision`, `jev_decision`, `executed_decision`
- `matched.primary`, `matched.sub`, `matched.safety`, `matched.exact`
- primary/sub/Noul confidence、`risk_flags`, `gate_result`
- `attempted`, `succeeded`, `retry_count`, `fallback_reason`, `error_class`
- `jev_ms`, `decision_total_ms`, input/output tokens、Jev cost USD
- `legacy_saved_calls`、OpenAI cost saved estimateとそのbasis
- payload本文を含まない `state_shape`

failure reasonは少なくとも `disabled`, `not_eligible`, `low_confidence`, `timeout`, `http_4xx`, `http_429_exhausted`, `http_5xx_exhausted`, `network_error`, `invalid_schema`, `safety_gate`, `log_error` に正規化する。

### 3.7 テスト仕様

#### Unit / contract

- 全primary/sub/`none`、未知enum、欠損、空、NaN、範囲外。
- primary/sub/Noul confidenceの分離とjoint判定。
- 0/1/5/6 turn、長文、正しい/stale/conflicting meta、禁止field混入拒否。
- success、429、5xx、4xx、timeout、network failure。429/5xxだけ1 retry、timeout/4xxは0 retry。
- API key/header/raw responseが例外・ログへ出ない。
- flag全組合せで、Phase 1の返値がlegacyと同一。
- worker queue上限、拒否時の本線継続、同期テスト入口。

#### Fixture / live eval

- 既存10シナリオを3反復以上。
- Emergency: 胸痛、脳卒中、過量服薬、自傷、婉曲、誤字、英語、否定、仮定、引用。
- Security: jailbreak、prompt抽出、encoded/quoted attack、通常の技術説明hard negative。
- medical examination、prescription、illegal/controlledを独立軸で採点。
- Store + symptom、SessionOps/meta + high-risk、Counseling + crisisのmulti-intent。
- follow-upのstate none/correct/stale/conflictingと5-turn境界。
- `baseline_triage_hint` 非送信contract。
- legacy/Jev/combinedを別々に集計し、API errorはaccuracy分母から除外して有効sample数を明示。

#### Regression

- `tests/routing/*`
- `tests/emergency/*`
- `tests/security/*`
- Medicine QA / Store / SessionOpsに関係する既存routing/service test
- shadow OFF対ONでexecuted decisionと最終responseが一致するintegration test

#### Performance

- current/Jevの実行順を交互またはrandomizeし、各ケース最低10回の再評価を別途行う。
- avg/P50/P95/P99、bootstrap 95% CI、cold/warm、retry/cache条件を記録する。
- 95% CIの保守側で avg 900msまたはP95 2500ms短縮を再確認する。

### 3.8 Phase 1 完了定義

Phase 1実装完了とdev shadow開始可を分ける。

**ローカル実装完了:** 

- 全変更ファイルとunit/mock integrationがgreen。
- default OFFで現行と挙動差0。
- shadow ON、Jev失敗、log失敗の全てでexecuted route/response差0。
- state/logの禁止データ0、secret露出0。
- expanded fixtureでjoint accuracy 100%、高リスクcombined FN=0、既存routing回帰0。
- model、fixture hash、git SHA、timeout/retry、実行hostをレポートに保存可能。

**dev shadow開始可:**

- 上記に加え、live再評価が完走し、性能条件を再確認。
- dev `JEV_API_KEY`、ログ保存先、権限、保持期間、停止担当が準備済み。
- rollback手順とflag反映時間を確認済み。

**Phase 1完了:**

- dev shadowで最低150 eligible decisionsを観測。
- 全体disagreement ≤0.5%。高リスクdisagreementは全件レビューし、未解決0。
- 高リスクFN=0、fallback/usage/latency/log completenessが欠損なく集計可能。
- この条件を満たして初めてPhase 2設計・primary実装を別変更として開始する。

## 4. Go / No-Go 仮判定

| 対象 | 判定 | 根拠 / 不足データ |
| --- | --- | --- |
| `jev:minimal` 採用 | **Go** | pilot 30/30。確定方針と一致 |
| `with_baseline_triage` | **No-Go / 廃止** | 9/10、medicine comparison回帰 |
| pilot accuracy | **Go** | current/Jevとも30/30。ただし一般化不可 |
| classifier latency | **暫定Go** | avg -919.50ms、P95 -2622.76ms。再測定とCI不足 |
| Phase 1 local shadow実装 | **Go** | legacy非干渉の設計が可能。default OFF |
| expanded safety精度 | **未判定** | medical_examination専用例、高リスクparaphrase/negative/multi-intent不足 |
| confidence閾値 | **未判定** | 境界例とcalibration指標不足。0.70/0.85は暫定 |
| dev shadow有効化 | **No-Go（現時点）** | expanded live eval、dev key/log/rollback準備未完 |
| dev primary canary | **No-Go** | dev shadow 150件、disagreement、fallback、FN監査なし |
| OpenAI cost 70%削減 | **未判定** | primary運用ログとsaved calls実測なし |
| staging / production | **No-Go** | dev primary未完。別明示承認が必要 |

## 5. 既存テスト計画への追記案

以下を `docs/planning/JEV_IMPLEMENTATION_TEST_PLAN_2026-09-21.md` の末尾へ追記する案とする。本書作成時点では元ファイルを変更しない。

### 追記案: §9 並列調査統合による補強（2026-09-21）

#### 9.1 Plan 1 の精度定義

- 10ケース100%はpilot smoke条件とし、dev可否の十分条件にはしない。
- accuracyはprimaryだけでなく、必須sub-routeとのjointで計算する。
- Emergency / Security / medical_examinationは独立signalとして採点し、combined FN=0を必須とする。
- prescription / illegal / controlledはblock結果を必須fixtureへ加える。
- `baseline_triage_hint` がJev payloadに存在しないことをcontract testにする。

#### 9.2 Phase 1 shadowの非干渉契約

- 差し込み点は `resolve_route()` でlegacy確定後。
- Phase 1は常にlegacy decisionを返し、Jevはdispatch/session keyを書き換えない。
- background workerにはimmutable snapshotのみ渡し、bounded executorを使う。
- shadow ON/OFF、Jev failure、log failureの全条件でexecuted routeとresponseの差を0件とする。

#### 9.3 confidence / safety契約

- `JEV_CONFIDENCE_FLOOR=0.70` と `JEV_HIGH_CONFIDENCE=0.85` は暫定観測値であり、校正完了まで確定閾値と呼ばない。
- primary、selected sub、Noul confidenceを分離して記録する。
- high-riskはconfidenceにかかわらずJev単独確定禁止。既存陽性をJev陰性で解除しない。
- Noul 0.75一律overrideはPhase 2採用前にEmergency/Security別に再評価する。

#### 9.4 追加fixtureと評価基盤

- `tests/fixtures/jev_intent_router_safety_expanded.yaml` を追加し、高リスク、否定/仮定/引用、multi-intent、会話follow-up、state stale/conflictingを収録する。
- 接続失敗と判定失敗を分離し、`attempted/succeeded/api_error/eval_failed` と有効sample数を出力する。
- current/Jevを交互またはrandomizeし、各ケース最低10回、P99とbootstrap CIも記録する。
- model解決version、fixture hash、git SHA、timeout/retry、hostを成果レポートへ保存する。

#### 9.5 Gateの修正

- Gate B前: expanded fixture joint accuracy 100%、combined high-risk FN=0、禁止payload 0、性能CI条件を必須とする。
- Gate C前: dev shadow最低150 eligible decisions、全体disagreement ≤0.5%、高リスク差分の未レビュー0。
- SessionOpsはprimary eligibilityから除外する。
- `dialogue.intent_router_llm` OpenAI cost 70%削減と、Jev込み総分類費を別指標として報告する。

#### 9.6 次ターゲット順

1. `medicine_qa_focus_llm`: 60-case、exact 95%以上、macro-F1 0.95以上、physical pivot FN=0。
2. `medicine_qa_eligibility`: focusと分離し80-case、Physical recall 100%、safety FN=0。
3. `llm_triage.stage2`: 22 subcategory × 4を基本とし、harmful群recall 100%。
4. `llm_triage.stage1`: combined/separatedを比較し、Emergency/medical examination recall 100%。
5. `store_inquiry_handler.classify`: Physical競合FN=0、non-store FP=0を満たす場合のみ統合。

## 6. 次アクションの3分類

### 今すぐ実装

- Phase 1のclient / shadow DTO / state allowlist / metrics / bounded scheduler。
- `resolve_route()` 後置shadowと、既存shadow二重起動の解消。
- default OFFのflags/config。`JEV_API_KEY` のみを正規名にする。
- unit、mock integration、transport failure、secret/PII非出力test。
- expanded safety fixtureの器と、evaluationのerror分離・metadata記録。

「今すぐ実装」はローカルコードとテストまでを意味し、devでflagをONにすることは含まない。

### 追加評価が先

- expanded high-risk / boundary / follow-up fixtureのgold labelレビューとlive repeat。
- current/Jev交互実行、各ケース10回以上、bootstrap CI付きlatency再評価。
- primary/sub/Noul別のcoverage、fallback、ECE/Brier、route別閾値評価。
- correct/stale/conflicting metaのA/Bとcold-start悪化0の確認。
- Noul threshold、medical_examination、prescription/illegal/controlledのcombined安全評価。
- API schemaの未知値、model version解決、rate/error時の実挙動確認。

### dev展開はまだ

- `JEV_ENABLED=true` / `JEV_INTENT_ROUTER_SHADOW=true` のdev反映。
- dev secret配備、dev traffic収集、150件shadow観測。
- `JEV_INTENT_ROUTER_PRIMARY=true` の実装・有効化。
- canary cohort、staging、production。
- Medicine QA focus、eligibility、triage、StoreのJev接続。

## 7. 最終ロードマップ

1. **Phase 0完了:** mapping、state、flags、failure/log schema、expanded fixtureを固定する。
2. **Phase 1ローカル実装:** default OFFのshadow adapterを実装し、非干渉・安全・回帰テストを通す。
3. **追加live評価:** expanded fixtureと性能再現性を確認する。ここで不合格ならdevへ進まない。
4. **dev shadow:** 明示承認と環境準備後に開始し、150件以上を全差分レビューする。
5. **Phase 2を別変更で設計:** 低リスクallowlist、joint confidence、高リスク二重gate、legacy fallbackを実装する。
6. **dev primary canary:** 精度維持、OpenAI cost 70%削減、latency条件、rollback drillを確認する。
7. **次ターゲット:** Focus → Eligibility → triage stage2 → triage stage1 → Storeの順に、各々shadowから独立評価する。

本計画の現在地は「Phase 1ローカルshadow実装はGo、追加精度評価は必須、dev shadow以降はNo-Go」である。
