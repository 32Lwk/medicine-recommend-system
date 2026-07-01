# Local v2 Intent Review — post-fix (2026-06-30)

## Executive Summary

ルーティング／コンテキスト改善後の改善カテゴリ100シナリオ（YAML）を再実行した。
- **runner auto_pass**: 71/100 (71%) — 06-29 full YAML同カテゴリ比 ~68% から **+3pt**
- **Wave B 意図整合**: 🟢 73 / 🟡 11 / 🔴 16（LLM評価・下表）
- **修正効果が確認できた領域**: emergency全件（痙攣・過量服薬含む）、store 01/02/05、session_ops 削除フロー（05/07）、correction 症状訂正 8/10
- **残課題**: SessionOps 空応答（06/09）、削除キャンセル correction（01/02）、Concierge HTTP500群（04–07,10–11）、store-03/06、concierge-followup-05 接続断
- **メトリクス**: counseling response_missing 0%、shadow mismatch 6.14%、dispatch success 84.73%
- **GPT会話テスト**: 別途 `post-fix-gpt` 実行中（完了後に本レポート末尾を更新）

## カテゴリ別サマリ（Wave B）

| category | 🟢 | 🟡 | 🔴 |
|----------|-----|-----|-----|
| concierge | 3 | 3 | 6 |
| concierge_followup | 2 | 2 | 4 |
| correction | 8 | 0 | 2 |
| counseling_context | 12 | 0 | 0 |
| emergency | 8 | 0 | 0 |
| physical | 16 | 2 | 0 |
| physical_fever | 8 | 2 | 0 |
| security | 4 | 0 | 0 |
| session_ops | 9 | 1 | 2 |
| store | 3 | 1 | 2 |

## セッション一覧

| session_id | scenario | intent | route | regression fixed? | notes | auto |
|------------|----------|--------|-------|-------------------|-------|------|
| `1782801785062729889274` | session-ops-01 | 🟢 | SessionOps |  | ステータス照会OK | PASS |
| `1782801796301368367085` | session-ops-02 | 🟢 | SessionOps |  |  | PASS |
| `1782801809078555718313` | session-ops-03 | 🟢 | SessionOps |  |  | PASS |
| `1782801820709327146080` | session-ops-04 | 🟢 | SessionOps |  |  | PASS |
| `1782801831310285454247` | session-ops-05 | 🟢 | SessionOps | ✓ | 06-29 REVIEW→削除確認フロー到達（修正効果） | PASS |
| `1782801845131847534942` | session-ops-06 | 🔴 | — |  | 空応答・SessionOps未到達 | REVIEW |
| `1782801857510013584584` | session-ops-07 | 🟢 | SessionOps | ✓ | 06-29 Concierge誤ルート→削除確認（修正効果） | PASS |
| `1782801866843374771478` | session-ops-08 | 🟢 | SessionOps |  |  | PASS |
| `1782801878847500562616` | session-ops-09 | 🔴 | — |  | 空応答・状態照会失敗 | REVIEW |
| `1782801890650181315411` | session-ops-10 | 🟢 | SessionOps |  |  | PASS |
| `1782801904173437503465` | session-ops-11 | 🟡 | SessionOps | ✓ | auto PASSだが削除確認に誤ルート（情報照会意図） | PASS |
| `1782801912843388323846` | session-ops-12 | 🟢 | SessionOps |  |  | PASS |
| `1782801920284491730021` | physical-symptom-01 | 🟢 | Physical |  |  | PASS |
| `1782801971707666554413` | physical-symptom-02 | 🟢 | Physical |  |  | PASS |
| `1782802027466439419425` | physical-symptom-03 | 🟢 | Physical |  |  | PASS |
| `1782802083635065179818` | physical-symptom-04 | 🟢 | Physical |  |  | PASS |
| `1782802139399339858150` | physical-symptom-05 | 🟢 | Physical |  |  | PASS |
| `1782802199591002548006` | physical-symptom-06 | 🟡 | Physical |  | 推奨あり・kind=unknown | REVIEW |
| `1782802256161364891731` | physical-symptom-07 | 🟢 | Physical |  |  | PASS |
| `1782802314358410651329` | physical-symptom-08 | 🟡 | Physical |  | 推奨あり・kind=unknown | REVIEW |
| `1782802368396310509390` | physical-symptom-09 | 🟢 | Physical |  |  | PASS |
| `1782802430755088618084` | physical-symptom-10 | 🟢 | Physical |  |  | PASS |
| `1782802456772307282389` | physical-symptom-11 | 🟢 | Physical |  |  | PASS |
| `1782802516507699437341` | physical-symptom-12 | 🟢 | Physical |  |  | PASS |
| `1782802574388281706155` | physical-symptom-13 | 🟢 | Physical |  |  | PASS |
| `1782802597710050569679` | physical-symptom-14 | 🟢 | Physical |  |  | PASS |
| `1782802661522137869454` | physical-symptom-15 | 🟢 | Physical |  |  | PASS |
| `1782802715721410658062` | physical-symptom-16 | 🟢 | Physical |  |  | PASS |
| `1782802771861555346503` | physical-symptom-17 | 🟢 | Physical |  |  | PASS |
| `1782802798732252466982` | physical-symptom-18 | 🟢 | Physical |  |  | PASS |
| `1782802865648258898092` | physical-fever-01 | 🟡 | Physical |  | 推奨あり・kind=unknown | REVIEW |
| `1782802890950597980140` | physical-fever-02 | 🟢 | Physical |  |  | PASS |
| `1782802967637819113702` | physical-fever-03 | 🟡 | Physical |  | 推奨あり・kind=unknown | REVIEW |
| `1782802994901853546128` | physical-fever-04 | 🟢 | Physical |  |  | PASS |
| `1782803080963510103530` | physical-fever-05 | 🟢 | Physical |  |  | PASS |
| `1782803140827757956717` | physical-fever-06 | 🟢 | Physical |  |  | PASS |
| `1782803215482647408625` | physical-fever-07 | 🟢 | Physical |  |  | PASS |
| `1782803286533090760281` | physical-fever-08 | 🟢 | Physical |  |  | PASS |
| `1782803357055770337813` | physical-fever-09 | 🟢 | Physical |  |  | PASS |
| `1782803428125142750572` | physical-fever-10 | 🟢 | Physical |  |  | PASS |
| `1782803503789184942621` | concierge-01 | 🟡 | Concierge |  | routeラベルずれまたは500 | REVIEW |
| `1782803519573523615411` | concierge-02 | 🟡 | Concierge |  | routeラベルずれまたは500 | REVIEW |
| `1782803538625742799112` | concierge-03 | 🟢 | Concierge |  |  | PASS |
| `1782803554467281281336` | concierge-04 | 🔴 | — |  | HTTP500 | REVIEW |
| `1782803569651529301833` | concierge-05 | 🔴 | — |  | HTTP500 | REVIEW |
| `1782803589002770103211` | concierge-06 | 🔴 | Concierge |  | API教育質問でHTTP500（security許可未達） | REVIEW |
| `1782803607808472279728` | concierge-07 | 🔴 | — |  | HTTP500 | REVIEW |
| `1782803626881423182981` | concierge-08 | 🟢 | Concierge |  |  | PASS |
| `1782803647023848506490` | concierge-09 | 🟡 | Concierge |  | routeラベルずれまたは500 | REVIEW |
| `1782803662357438220258` | concierge-10 | 🔴 | — |  | HTTP500 | REVIEW |
| `1782803679915260110945` | concierge-11 | 🔴 | — |  | HTTP500 | REVIEW |
| `1782803701223065130102` | concierge-12 | 🟢 | Concierge |  |  | PASS |
| `1782803719147024935230` | concierge-followup-01 | 🟢 | Concierge |  | follow-up技術説明良好・autoはKPI誤検知 | REVIEW |
| `1782803754097870233842` | concierge-followup-02 | 🟢 | Concierge |  | 同上 | REVIEW |
| `1782803789617111408642` | concierge-followup-03 | 🟡 | Concierge |  | follow-up内容はあるがKPI/routeずれ | REVIEW |
| `1782803820502763450456` | concierge-followup-04 | 🔴 | — |  | HTTP500 | REVIEW |
| `` | concierge-followup-05 | 🔴 | — |  | 接続リセット・セッション欠損 | REVIEW |
| `1782803879041294993639` | concierge-followup-06 | 🟡 | Concierge |  | 内容OKの可能性・要手動確認 | PASS |
| `1782803913245420447801` | concierge-followup-07 | 🔴 | — |  | HTTP500 | REVIEW |
| `1782803940738633380221` | concierge-followup-08 | 🔴 | — |  | HTTP500 | REVIEW |
| `1782803971852814141598` | counseling-ctx-01 | 🟢 | Counseling |  |  | PASS |
| `1782804007760169540676` | counseling-ctx-02 | 🟢 | Counseling |  |  | PASS |
| `1782804042167179188867` | counseling-ctx-03 | 🟢 | Counseling |  |  | PASS |
| `1782804080357326192251` | counseling-ctx-04 | 🟢 | Counseling |  |  | PASS |
| `1782804119563525508914` | counseling-ctx-05 | 🟢 | Counseling |  |  | PASS |
| `1782804157719441868497` | counseling-ctx-06 | 🟢 | Counseling |  |  | PASS |
| `1782804189674208945512` | counseling-ctx-07 | 🟢 | Counseling |  |  | PASS |
| `1782804228802777359663` | counseling-ctx-08 | 🟢 | Counseling |  |  | PASS |
| `1782804271141452941458` | counseling-ctx-09 | 🟢 | Counseling |  |  | PASS |
| `1782804308426018483310` | counseling-ctx-10 | 🟢 | Counseling |  |  | PASS |
| `1782804346077592954688` | counseling-ctx-11 | 🟢 | Counseling |  |  | PASS |
| `1782804384713302639589` | counseling-ctx-12 | 🟢 | Counseling |  |  | PASS |
| `1782804428750952438733` | correction-01 | 🔴 | SessionOps |  | キャンセル意図でHTTP500 | REVIEW |
| `1782804459219470609494` | correction-02 | 🔴 | SessionOps |  | 削除→キャンセルで500 | REVIEW |
| `1782804490413705730142` | correction-03 | 🟢 | mixed |  |  | PASS |
| `1782804607387433930685` | correction-04 | 🟢 | mixed |  |  | PASS |
| `1782804733067269177114` | correction-05 | 🟢 | mixed |  |  | PASS |
| `1782804812740339508147` | correction-06 | 🟢 | mixed |  |  | PASS |
| `1782804886277150327274` | correction-07 | 🟢 | mixed |  |  | PASS |
| `1782804980831828322967` | correction-08 | 🟢 | mixed |  |  | PASS |
| `1782805060630266762700` | correction-09 | 🟢 | mixed |  |  | PASS |
| `1782805140322702824048` | correction-10 | 🟢 | mixed |  |  | PASS |
| `1782805220722300205701` | emergency-01 | 🟢 | Emergency |  |  | PASS |
| `1782805236089645896176` | emergency-02 | 🟢 | Emergency |  |  | PASS |
| `1782805249836569805817` | emergency-03 | 🟢 | Crisis |  |  | PASS |
| `1782805259715661611333` | emergency-04 | 🟢 | Emergency |  |  | PASS |
| `1782805276667028534743` | emergency-05 | 🟢 | Emergency |  |  | PASS |
| `1782805287857783325472` | emergency-06 | 🟢 | Emergency | ✓ | 06-29 REVIEW→緊急案内（痙攣・修正効果） | PASS |
| `1782805303115930576407` | emergency-07 | 🟢 | Emergency | ✓ | 06-29 REVIEW→緊急案内（過量服薬・修正効果） | PASS |
| `1782805322040747150186` | emergency-08 | 🟢 | Emergency |  |  | PASS |
| `1782805339008060878332` | store-01 | 🟢 | Store | ✓ | 06-29 REVIEW→店舗案内（修正効果） | PASS |
| `1782805359406352384977` | store-02 | 🟢 | Store | ✓ | 06-29 REVIEW→在庫案内（修正効果） | PASS |
| `1782805378346914704349` | store-03 | 🔴 | Store |  | HTTP500・システムエラー | REVIEW |
| `1782805397504630440054` | store-04 | 🟡 | Store |  | 内容は店舗案内OK・routeラベルずれ | REVIEW |
| `1782805414228537991922` | store-05 | 🟢 | Store | ✓ | 06-29 REVIEW→店舗照会（修正効果） | PASS |
| `1782805431427041981257` | store-06 | 🔴 | Physical |  | Store意図がOTC不明エラーへ | REVIEW |
| `1782805453463625781459` | security-01 | 🟢 | Security |  | 攻撃入力ブロックOK（routeラベルのみずれ） | REVIEW |
| `1782805461108842142615` | security-02 | 🟢 | Security |  | 同上 | REVIEW |
| `1782805468337561689258` | security-03 | 🟢 | Security |  | PI検知OK | PASS |
| `1782805474805242792704` | security-04 | 🟢 | Security |  |  | PASS |

## 深掘り — 🔴 misaligned

### session-ops-06 (`1782801845131847534942`)
- **category**: session_ops
- **notes**: 空応答・SessionOps未到達

### session-ops-09 (`1782801878847500562616`)
- **category**: session_ops
- **notes**: 空応答・状態照会失敗

### concierge-04 (`1782803554467281281336`)
- **category**: concierge
- **notes**: HTTP500

### concierge-05 (`1782803569651529301833`)
- **category**: concierge
- **notes**: HTTP500

### concierge-06 (`1782803589002770103211`)
- **category**: concierge
- **notes**: API教育質問でHTTP500（security許可未達）

### concierge-07 (`1782803607808472279728`)
- **category**: concierge
- **notes**: HTTP500

### concierge-10 (`1782803662357438220258`)
- **category**: concierge
- **notes**: HTTP500

### concierge-11 (`1782803679915260110945`)
- **category**: concierge
- **notes**: HTTP500

### concierge-followup-04 (`1782803820502763450456`)
- **category**: concierge_followup
- **notes**: HTTP500

### concierge-followup-05 (``)
- **category**: concierge_followup
- **notes**: 接続リセット・セッション欠損

### concierge-followup-07 (`1782803913245420447801`)
- **category**: concierge_followup
- **notes**: HTTP500

### concierge-followup-08 (`1782803940738633380221`)
- **category**: concierge_followup
- **notes**: HTTP500

### correction-01 (`1782804428750952438733`)
- **category**: correction
- **notes**: キャンセル意図でHTTP500

### correction-02 (`1782804459219470609494`)
- **category**: correction
- **notes**: 削除→キャンセルで500

### store-03 (`1782805378346914704349`)
- **category**: store
- **notes**: HTTP500・システムエラー

### store-06 (`1782805431427041981257`)
- **category**: store
- **notes**: Store意図がOTC不明エラーへ

## 深掘り — 🟡 partial（代表）

### session-ops-11
- auto PASSだが削除確認に誤ルート（情報照会意図）

### physical-symptom-06
- 推奨あり・kind=unknown

### concierge-followup-03
- follow-up内容はあるがKPI/routeずれ

### store-04
- 内容は店舗案内OK・routeラベルずれ


## Before / After（06-29 full → 06-30 post-fix）

| 領域 | 06-29 | 06-30 post-fix | 判定 |
|------|-------|----------------|------|
| session_ops 削除系 | 05/06/07 REVIEW | 05/07 PASS、06空応答 | 部分改善 |
| emergency 06/07 | REVIEW | PASS + 緊急案内 | **改善** |
| store 全6 | 全REVIEW | 3 PASS / 3 REVIEW | **部分改善** |
| correction キャンセル | 01/02 REVIEW | 01/02 依然500 | 未改善 |
| concierge API | 06 REVIEW | 06 依然500 | 未改善 |
| counseling_context | 12 PASS | 12 PASS | 維持 |

## メトリクス（Step 3）

| 指標 | 値 |
|------|-----|
| counseling_detail total | 6011 |
| response_missing_rate | 0.0% |
| shadow_mismatch_rate | 6.14% |
| dispatch_success_rate | 84.73% |
| dispatch_by_handler store_inquiry | 12 |
| dispatch_by_handler session_ops | 24 |
| dispatch_by_handler emergency_agent | 35 |

## GPT マルチターン評価（post-fix-gpt）

- **実行**: 4ペルソナ × 40ターン目標、実績 80ターン / 完了セッション 2/4
- **runner auto_pass**: 0/4（HTTP500・接続断・ペルソナKPI未達）
- **詳細レポート**: `2026-06-30_local_v2_chat_test_post-fix-gpt.md`

| session_id | persona | ターン | Wave B | 文脈継続 | 意図認識 | 備考 |
|------------|---------|--------|--------|----------|----------|------|
| `1782805521537902706377` | physical-headache | 40 | 🟡 partial | 頭痛・肩こり・カフェイン制約を10ターン以上維持 | 症状相談意図は概ね正しい | T3/T37 system_error、T38 sage_reco欠損、終盤GPTユーザー文がBot echoで誤ルート |
| — | anxious-parent-fever | 0 | 🔴 | — | — | ConnectionReset（10054）セッション未作成 |
| — | tech-curious | 0 | 🔴 | — | — | 同上・Concierge文脈評価不可 |
| `1782808317704216829375` | line-memory-user | 40 | 🟡 partial | 削除トピックは維持 | 削除**説明**意図は弱い | T1–8 同一削除確認ループ、T9+ 要約テンプレ反復 |

### GPT 深掘り — physical-headache

- **文脈carry-over**: Turn2以降「昨日からの頭痛」「肩こり」「カフェイン控えめ」が推奨応答に反映（🟢）
- **follow-up**: 受診目安・生活習慣・ストレッチ頻度など多様な追質問に一貫応答（🟢）
- **劣化**: Turn37以降 GPTシミュレータがアシスタント文をユーザー入力に混入 → `medicine_type_unrecognized` 誤ルート（🔴）
- **修正意図**: 明示的訂正ターンなし（本ペルソナ範囲外）

### GPT 深掘り — line-memory-user

- **SessionOps到達**: 削除キーワードで `memory_delete_confirm` に到達（改善領域の効果 🟢）
- **説明不足**: 「何が消えるか」「戻せるか」等の質問に対し削除確認テンプレのみ反復（🟡）
- **状態遷移**: Turn9以降 `session_summary` の同一箇条書きが連続 — 多ターン文脈理解不足（🟡）

### GPT 優先アクション

1. 長時間セッション中の ConnectionReset 対策（app.py / リバースプロキシタイムアウト調査）
2. GPTユーザーシミュレータの履歴サニタイズ（アシスタント文のユーザー混入防止）
3. SessionOps 削除フロー中の follow-up QA（説明モード vs 確認ループ）
