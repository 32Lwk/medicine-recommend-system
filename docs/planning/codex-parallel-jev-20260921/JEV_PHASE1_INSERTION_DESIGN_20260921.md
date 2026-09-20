# Jev Phase 1 shadow 差し込み設計

- 作成日: 2026-09-21
- 担当: Agent C（Phase 1 shadow 差し込み設計）
- 対象: Chat Pipeline v2 / IntentRouter
- 状態: 設計のみ。実装コード、本番設定、commit / push は変更しない

## 1. 結論

Phase 1 の最短かつ安全な差し込み点は `src/dialogue/routing/router.py::resolve_route()` である。ここで現行の `resolve_route_unified_or_legacy()` を**先に実行して legacy decision を確定**し、その後に Jev adapter を観測目的で呼ぶ。

`JEV_INTENT_ROUTER_PRIMARY=false` の間は、Jev の成功・失敗・confidence・不一致に関係なく、`resolve_route()` は先に確定した legacy decision を返す。Jev の結果は dispatch 用 session key（`_intent_router_shadow`, `_routing_decision`）へ書かず、専用ログにだけ残す。これにより dispatcher が Jev shadow を誤実行する余地をなくす。

Phase 1 では Jev call を同期で待つ必要はない。legacy decision と送信 state の immutable snapshot を作り、background worker で Jev を呼び、完了後に `legacy_decision / jev_decision / executed / matched / latency / usage` を記録する。ただしプロセス終了時の観測欠損を許容できない検証環境では、テスト用同期入口も用意する。

## 2. 現行フロー

コード上の実行順は次のとおり。

```text
run_chat_post_pipeline
  ├─ parse / session snapshot / LLM budget
  ├─ SafetyGate pre
  │    └─ run_safety_gate_pre()                 [chat_post_pipeline.py:259-273]
  ├─ SessionOps fast path
  │    └─ _try_session_ops_handler(phase="fast") [chat_post_pipeline.py:309-318]
  ├─ triage
  │    ├─ try_rule_based_symptom_triage()
  │    └─ run_triage()                          [chat_post_pipeline.py:334-360]
  ├─ routing context sync
  │    └─ sync_routing_context(ctx)              [chat_post_pipeline.py:381]
  ├─ 既存 IntentRouter shadow scheduling         [chat_post_pipeline.py:383-394]
  ├─ SessionOps triage path
  ├─ SafetyGate full                             [chat_post_pipeline.py:408-420]
  ├─ medicine QA / counseling 等の early route
  ├─ dispatcher
  │    └─ try_agent_dispatch(ctx, monitor)        [chat_post_pipeline.py:761-766]
  │         └─ _load_decision()
  │              └─ resolve_route()
  │                   └─ resolve_route_unified_or_legacy()
  │                        ├─ unified router
  │                        └─ legacy router       [unified_router.py:295-318]
  └─ 未処理なら ChatOrchestrator / legacy category route fallback
```

補足:

- `resolve_route()` は現状 `resolve_route_unified_or_legacy()` の薄い統合入口である（`src/dialogue/routing/router.py:14-29`）。
- unified router は決定を `_intent_router_shadow` と `_routing_decision` に保存する（`src/dialogue/routing/unified_router.py:210-218`）。
- dispatcher は最初に `_intent_router_shadow` を読み、なければ `resolve_route()` を呼ぶ（`src/dialogue/dispatcher.py:48-74`）。したがって Jev shadow を `_intent_router_shadow` に保存してはいけない。
- 現在の `schedule_shadow_observation()` は background thread 内で通常の `resolve_route()` を呼び、同じ session を更新し得る（`src/dialogue/routing/shadow.py:100-116`）。Jev 導入時にそのまま重ねると二重実行と session 書換競合が起きる。

## 3. Phase 1 のシーケンス

### 3.1 推奨シーケンス

```text
chat_post_pipeline
  │
  ├─ SafetyGate pre → SessionOps fast → triage → SafetyGate full / early routes
  │
  └─ try_agent_dispatch
       └─ resolve_route(user_text, session, sid, triage_result, client)
            ├─ legacy = resolve_route_unified_or_legacy(...)
            │    └─ 現行の deterministic / unified / legacy / post guard を完走
            ├─ if !JEV_ENABLED || !JEV_INTENT_ROUTER_SHADOW:
            │      return legacy
            ├─ state = build_jev_router_state(snapshot only)
            ├─ schedule_jev_shadow(state, legacy, correlation_id)
            ├─ if !JEV_INTENT_ROUTER_PRIMARY:
            │      return legacy                ← Phase 1 の不変条件
            └─ Phase 2 以降のみ select_primary(legacy, jev)

background worker
  ├─ jev_client.evaluate(timeout=3.5s, retry=429/5xx once)
  ├─ jev_decisions.to_route_decision(Choice/Noul)
  ├─ emergency/security deterministic override
  └─ jev_metrics.log_shadow(legacy, jev, executed=legacy, ...)
```

Jev shadow の scheduling は、現行 decision を得た直後の `resolve_route()` 内で一度だけ行う。`chat_post_pipeline.py:383-394` の既存 IntentRouter shadow scheduling は Jev scheduling と併存させない。移行時は、既存観測を維持するなら名称と責務を分け、Jev 側に同じ `resolve_route()` を再入させない。

### 3.2 本線を変えない保証

以下をコード上の invariant と unit test にする。

```python
def resolve_route(...):
    legacy = resolve_route_unified_or_legacy(...)

    if not jev_enabled() or not jev_intent_router_shadow_enabled():
        return legacy

    snapshot = build_jev_router_state(...)
    schedule_jev_shadow(snapshot=snapshot, legacy_decision=legacy)

    if not jev_intent_router_primary_enabled():
        return legacy  # object identity も維持する

    # Phase 1 では到達させない。Phase 2 の別変更で実装する。
    return legacy
```

保証条件:

1. `PRIMARY=false` では Jev decision を return しない。
2. Jev の timeout、例外、不正 payload、low confidence でも legacy の返値を変更しない。
3. Jev shadow は `_intent_router_shadow`, `_routing_decision`, `dialogue_state.routing`, `last_triage_result` を更新しない。
4. worker には session proxy 自体を渡さず、serializable な snapshot だけを渡す。
5. `SessionOps` は pipeline の fast path / triage pathをそのまま先行させ、最初の primary 対象にしない。
6. `executed` は「予定値」ではなく、dispatcher が採用した decision を correlation id で後から記録する。Phase 1 では通常 `legacy_decision` と一致する。

## 4. 変更ファイル一覧

### 4.1 新規ファイル

| ファイル | 責務 | 禁止事項 |
| --- | --- | --- |
| `src/services/jev_client.py` | HTTP client、auth、3.5s timeout、429/5xx のみ最大1 retry、usage/latency の生結果 | route 選択、session 参照、秘密値ログ |
| `src/services/jev_decisions.py` | System One の Choice/Noul response を検証し `RouteDecision` 相当へ変換 | HTTP、feature flag、dispatch |
| `src/services/jev_metrics.py` | shadow event の schema 化、JSONL/app log、集計用 field | route の変更、例外の本線伝播 |
| `src/dialogue/routing/jev_router.py` | IntentRouter questions、state builder、adapter orchestration、shadow scheduling | dispatcher key への書込、回答生成 |

### 4.2 既存ファイルの最小変更候補

| ファイル | 変更案 |
| --- | --- |
| `src/dialogue/routing/router.py` | legacy decision 確定後に `jev_router.schedule_shadow(...)` を一度だけ呼ぶ。Phase 1 は常に legacy を返す |
| `config/llm_flags.py` | boolean flags: enabled / shadow / primary。既存 `_flag()` と pytest 既定 OFF の考え方に合わせる |
| `config/routing_config.py` | model、timeout、confidence の typed getter。数値 parse error は安全な既定値へ戻す |
| `src/dialogue/dispatcher.py` | 実行決定を correlation id 付きで metrics に通知（観測のみ）。Jev decision の読込はしない |
| `src/handlers/chat/chat_post_pipeline.py` | `383-394` の既存 shadow との二重起動を解消。Jev の直接呼出しは追加しない |
| `src/utils/structured_logger.py` | 必要なら `jev_intent_router_shadow` event の sink を追加。既存 `dialogue_route_shadow` と schema を混同しない |

## 5. Feature flags と設定読込

boolean は `config/llm_flags.py`、数値・文字列設定は `config/routing_config.py` に置く。既存の `llm_flags._flag()`（`config/llm_flags.py:14-18`）と `routing_config._get_float/_get_int()`（`config/routing_config.py:9-26`）に合わせる。

| env | getter 配置 | Phase 1 default | 意味 |
| --- | --- | ---: | --- |
| `JEV_ENABLED` | `llm_flags.py::is_jev_enabled()` | `false` | 全体 kill switch |
| `JEV_INTENT_ROUTER_SHADOW` | `llm_flags.py::is_jev_intent_router_shadow_enabled()` | `false` | shadow call とログを有効化 |
| `JEV_INTENT_ROUTER_PRIMARY` | `llm_flags.py::is_jev_intent_router_primary_enabled()` | `false` | Phase 1 は false 固定。true の意味は Phase 2 で導入 |
| `JEV_MODEL` | `routing_config.py::jev_model()` | `jev-latest` | shadow 中の model |
| `JEV_TIMEOUT_SEC` | `routing_config.py::jev_timeout_sec()` | `3.5` | request timeout |
| `JEV_CONFIDENCE_FLOOR` | `routing_config.py::jev_confidence_floor()` | `0.70` | 観測上の usable 判定 |
| `JEV_HIGH_CONFIDENCE` | `routing_config.py::jev_high_confidence()` | `0.85` | Phase 2 primary 候補閾値 |

`JEV_API_KEY` は `jev_client.py` が呼出し時に `os.getenv()` で読む。キー値は保持・ログ出力しない。共通方針どおり、`TYPESAFE_API_KEY` fallback を互換目的で許容しても、ログは `key_configured: bool` のみにする。

boolean getter は `JEV_ENABLED` を親にする。ただし `PRIMARY=true` が誤設定されても Phase 1 コードは Jev を返さない。

```python
def is_jev_intent_router_shadow_enabled() -> bool:
    return is_jev_enabled() and _flag("JEV_INTENT_ROUTER_SHADOW", False)

def is_jev_intent_router_primary_enabled() -> bool:
    return is_jev_enabled() and _flag("JEV_INTENT_ROUTER_PRIMARY", False)
```

## 6. RouteDecision 変換

### 6.1 Choice / Noul mapping

Jev questions は評価 fixture と同じ有限集合に固定する。

- Choice `primary_route`: `Physical | SessionOps | Concierge | Emergency | Security | Store | Counseling | Unknown`
- Choice `physical_sub_route`: `rule_based_recommend | fever_flow | symptom_prompt_sports | medicine_qa | medicine_followup_qa | medicine_side_effect_qa | none`
- Choice `concierge_sub_route`: `greeting | chitchat | app_about | architecture | doc_changelog | redirect | none`
- Choice `session_sub_route`: `delete | summarize | status | none`
- Noul: `emergency_required`, `security_risk`, `store_inquiry`, `counseling_needed`

通常の sub route は primary に対応する Choice のみ採用し、`none` は `None` にする。Emergency / Security は既存契約に合わせた正規化済み sub route を adapter 内の定数表で付ける。`resolved_by` の現行 Literal は `jev` を含まないため、Phase 1 は Jev 用 DTO を別に持つか、実装前に `src/dialogue/routing/types.py::ResolvedBy` へ `"jev"` を追加する必要がある。shadow log だけなら前者が低リスクである。

### 6.2 emergency / security override 疑似コード

```python
def to_jev_route_decision(answers, deterministic_signals):
    primary = parse_primary_choice(answers["primary_route"])
    confidence = choice_confidence(answers["primary_route"])

    emergency = clamp01(noul(answers.get("emergency_required")))
    security = clamp01(noul(answers.get("security_risk")))

    # Jev 単独で安全系を解除しない。既存 gate signal は常に優先。
    if deterministic_signals.security_blocked_or_known_attack:
        return decision("Security", deterministic_signals.security_sub_route,
                        confidence=1.0, source="deterministic_security_override")

    if deterministic_signals.emergency_detected_or_medical_examination:
        return decision("Emergency", deterministic_signals.emergency_sub_route,
                        confidence=1.0, source="deterministic_emergency_override")

    # shadow 比較用の安全側 override。閾値は fixture で固定してから採用する。
    if security >= HIGH_RISK_NOUL_THRESHOLD:
        primary = "Security"
        confidence = max(confidence, security)
    elif emergency >= HIGH_RISK_NOUL_THRESHOLD:
        primary = "Emergency"
        confidence = max(confidence, emergency)

    sub = select_sub_choice_for(primary, answers)
    return decision(primary, sub, confidence, source="jev_systemone_shadow",
                    meta={"noul": safe_noul_values(answers)})
```

重要: `emergency_required` / `security_risk` が低いことを理由に、SafetyGate、medical examination、既存 deterministic gate の Emergency/Security を降格させない。高リスク FN=0 の判定は primary route だけでなく `medical_examination` fixture も別軸で集計する。

## 7. state builder（§8.3 準拠）

### 7.1 送信 state

```json
{
  "channel": "web|line",
  "user_input": "sanitized current input",
  "recent_turns": [{"role": "user|assistant", "content": "..."}],
  "meta": {
    "last_primary_route": "Physical",
    "last_sub_route": "medicine_qa",
    "last_recommended_medicines": ["商品名A", "商品名B"],
    "active_symptoms": ["頭痛"],
    "medicine_qa_focus": ["comparison"]
  },
  "app_context": "OTC medicine assistant; choose one supported route"
}
```

### 7.2 session field の出所と優先順位

| state field | 取得元 | 根拠ファイル | 注記 |
| --- | --- | --- | --- |
| `channel` | `sid` を `resolve_concierge_channel(sid)` で `line/web` 化 | `src/services/concierge_channel.py:11-24` | user id や sid 自体は送らない |
| `user_input` | `ctx.sanitized_message or ctx.user_message` | `src/dialogue/dispatcher.py:68-73` | raw PII を増やさない |
| `recent_turns` | `RoutingContext.history_messages` または `get_recent_messages(session, sid, limit=5)` | `src/services/routing_context.py:15-29, 57-88`; `src/services/triage_history.py:11-38` | `TRIAGE_HISTORY_MESSAGES=5` と一致。role/content のみ |
| `last_primary_route` / `last_sub_route` | `dialogue_state.routing` → `_routing_decision` → 現行確定済み decision | `src/dialogue/context.py:111-116`; `src/dialogue/routing/unified_router.py:210-218` | `_intent_router_shadow` は Jev 専用値として使わない |
| `last_recommended_medicines` | `resolve_session_recommended_medicines()` の返値から `product_name` または `name` のみ最大3 | `src/services/medicine_qa_routing.py:1315-1346` | 説明、成分全文、score は除外 |
| `active_symptoms` | 直近 bot message の `diagnosis.symptoms` が存在する場合のみ最大5 | `src/services/line_memory_context.py:36-37`; `src/handlers/chat/chat_recommendation_followup.py:79,129-130` | 専用 top-level session field は現状確認できない。再抽出しない |
| `medicine_qa_focus` | 当該 turn ですでに算出済みの focus が snapshot に渡された場合のみ | `src/handlers/chat/chat_post_pipeline.py:522-540`; `src/services/medicine_qa_routing.py:1159-1297` | state builder 内で focus LLM を新規実行しない |

`active_symptoms` と `medicine_qa_focus` は「session に既にある場合のみ」という §8.3 の制約を厳守する。現状は安定した専用 session key がないため、Phase 1 の初期実装では欠落を許容する。Jev のために NLU、focus LLM、DB full history を追加実行してはならない。

### 7.3 送らない情報

- `sid`, LINE userId、氏名、住所、電話番号などの識別子・不要 PII
- `last_triage_result.category` 等の `baseline_triage_hint`
- RAG 本文、生成 prompt、説明全文、medicine 詳細全文
- `user_attributes`（年齢、妊娠等を含む）。IntentRouter Phase 1 の対象外
- 5件を超える履歴。message の diagnosis / metadata / timestamp も除外

## 8. Shadow log schema

既存 `dialogue_route_shadow` は primary/sub を平坦に記録する（`src/utils/structured_logger.py:345-385`）。Jev は比較・latency・usage が必要なので、別 event `jev_intent_router_shadow` とする。

```json
{
  "log_type": "jev_intent_router_shadow",
  "schema_version": 1,
  "timestamp": "ISO-8601",
  "correlation_id": "random per route resolution",
  "session_hash": "optional one-way hash; raw sid forbidden",
  "mode": "shadow",
  "model": "jev-latest",
  "legacy_decision": {
    "primary_route": "Physical",
    "sub_route": "medicine_qa",
    "confidence": 0.93,
    "resolved_by": "llm",
    "source": "..."
  },
  "jev_decision": {
    "primary_route": "Physical",
    "sub_route": "medicine_qa",
    "confidence": 0.98,
    "source": "jev_systemone_shadow",
    "noul": {
      "emergency_required": 0.01,
      "security_risk": 0.01,
      "store_inquiry": 0.01,
      "counseling_needed": 0.02
    }
  },
  "executed": {
    "primary_route": "Physical",
    "sub_route": "medicine_qa",
    "source": "legacy"
  },
  "matched": {
    "primary": true,
    "sub": true,
    "exact": true
  },
  "latency": {
    "jev_ms": 532.54,
    "attempts": 1,
    "timed_out": false
  },
  "usage": {
    "input_tokens": 1358,
    "output_tokens": 368
  },
  "fallback_reason": null,
  "error_class": null,
  "high_risk": false,
  "state_shape": {
    "recent_turn_count": 5,
    "recommended_medicine_count": 2,
    "has_active_symptoms": false,
    "has_medicine_qa_focus": true
  }
}
```

ログ規則:

- 生の `user_input`, 会話履歴、API key、Jev raw response 全文は記録しない。
- `matched.primary` と `matched.sub` を分ける。sub の表記ゆれは明示した正規化関数を通す。
- Jev call が失敗した場合も `legacy_decision`, `executed`, `latency`, `fallback_reason`, `error_class` を記録し、`jev_decision=null` とする。
- background 完了前に dispatch が終わり得るため、`executed` は correlation id の小さな in-memory registry で結合するか、`shadow_result` と `route_execution` の2 eventに分けて集計時 join する。共有 session への後書きはしない。

## 9. 疑似コード

### 9.1 client

```python
async def evaluate_intent_router(state, questions, config):
    for attempt in (1, 2):
        try:
            return await post_system_one(
                api_key=read_key_at_call_time(),
                model=config.model,
                state=state,
                questions=questions,
                timeout=config.timeout_sec,  # 3.5
            )
        except HttpError as exc:
            if attempt == 1 and (exc.status == 429 or exc.status >= 500):
                await bounded_backoff_200_to_400_ms()
                continue
            raise
        except TimeoutError:
            raise  # timeout は retry しない
```

### 9.2 shadow orchestration

```python
def schedule_shadow(*, state, legacy_decision, deterministic_signals, correlation_id):
    immutable = deep_copy_json_safe(state)

    def worker():
        started = monotonic()
        try:
            raw = jev_client.evaluate_intent_router(immutable, QUESTIONS, config())
            jev = jev_decisions.to_route_decision(raw, deterministic_signals)
            metrics.record_result(
                correlation_id=correlation_id,
                legacy_decision=legacy_decision,
                jev_decision=jev,
                executed=execution_registry.get(correlation_id) or legacy_decision,
                latency_ms=elapsed_ms(started),
                usage=raw.usage,
            )
        except Exception as exc:
            metrics.record_failure(..., fallback_reason=classify(exc))

    submit_to_bounded_executor(worker)  # request ごとの無制限 thread 生成は避ける
```

## 10. 既存テストの回帰対象

Phase 1 PR では最低限、以下の既存 suite を回す。live integration は通常 CI と分離する。

### `tests/routing/*`

- `test_concierge_dispatch_execution_parity.py`
- `test_confidence_gate.py`
- `test_doc_changelog_intent.py`
- `test_llm_unavailability.py`
- `test_medicine_context_live_integration.py`（live 分離）
- `test_medicine_context_routing_matrix.py`
- `test_medicine_context_routing.py`
- `test_medicine_qa_comparison_broad.py`
- `test_medicine_qa_context_routing.py`
- `test_medicine_qa_multi_focus.py`
- `test_medicine_qa_route_pivot.py`
- `test_medicine_qa_routing.py`
- `test_medicine_qa_sections.py`
- `test_medicine_qa_session_context.py`
- `test_medicine_side_effect_handler.py`
- `test_medicine_side_effect_qa.py`
- `test_meta_safety_and_sync.py`
- `test_meta_topic_break_flexible.py`
- `test_meta_topic_everyday.py`
- `test_meta_triage.py`
- `test_routing_context.py`
- `test_routing_e2e_live_integration.py`（live 分離）
- `test_routing_golden.py`
- `test_routing_keyword_policy.py`
- `test_routing_v2_flags.py`
- `test_sports_medicine_routing.py`
- `test_triage_cache_matrix.py`
- `test_triage_cache_ttl.py`
- `test_triage_call_count.py`

### `tests/emergency/*`

- `test_emergency_dispatch.py`
- `test_emergency_flow_matrix.py`
- `test_emergency_notify.py`

### `tests/security/*`

- `test_aggressive_input.py`
- `test_aggressive_pipeline_reach.py`
- `test_input_block_responses.py`
- `test_jailbreak_patterns.py`
- `test_llm_security_check.py`

追加 unit / integration test（別担当に依頼）:

- flags 全組合せ。特に `SHADOW=true, PRIMARY=false` で legacy object identity が不変
- Jev success / timeout / 4xx / 429→success / 5xx→failure / malformed response
- Choice/Noul mapping と unknown choice の fail-closed
- Emergency / Security / medical_examination の deterministic override と FN=0
- state が5 message以内、識別子・PII・triage hint・RAG全文を含まないこと
- shadow worker が dispatcher session keys を変更しないこと
- `tests/fixtures/jev_intent_router_eval_10.yaml` の mock response 10件
- log schema、usage 欠落、sub route normalization、failure event

## 11. 仮説と合格条件

### 仮説 A: `resolve_route()` 後置 shadow が本線非干渉の最短経路

- 主張: legacy decision を先に確定してから Jev を schedule すれば、Phase 1 の dispatch 結果を変えずに同一入力の比較ができる。
- 根拠: `resolve_route()` が unified/legacy の単一入口であり、dispatcher もここへ収束する（`router.py:14-29`, `dispatcher.py:61-74`）。
- 検証方法: flags matrix と例外注入で返値 identity、session diff、dispatch handler を比較する。
- 合格条件: `PRIMARY=false` の全ケースで legacy の primary/sub/handler が完全一致し、Jev 障害が response/status/latency（background scheduling の微小 overhead を除く）を変えない。
- 失敗時の次手: pipeline から完全に切離したログ replay / queue consumer shadow に移す。

### 仮説 B: §8.3 の最小 state で評価精度を維持できる

- 主張: channel、現入力、直近5 message、既存の短いメタだけで IntentRouter に十分である。
- 根拠: 最新 repeat=3 は `jev:minimal` 30/30、avg 536.78ms、P95 594.15ms。baseline triage hint 付きは別 run で medicine comparison を1件失敗した。
- 検証方法: 10 fixture + routing golden + follow-up shadow disagreement を集計する。
- 合格条件: 10ケースと emergency/security fixture 100%、高リスク FN=0、全体 disagreement ≤0.5% を直近150件と累積で確認する。
- 失敗時の次手: follow-up 誤判定に限定して 5→8 turn、または直近 assistant 推奨 block 保持を A/B する。triage hint は追加しない。

### 仮説 C: 非同期 shadow で本線 latency を増やさない

- 主張: bounded executor と immutable snapshot により Jev の約0.5秒を user response path から外せる。
- 根拠: Phase 1 は Jev decision を実行に使わず、latest 評価の Jev P95 は約594ms。
- 検証方法: shadow OFF/ON の pipeline P50/P95、executor queue depth、drop rate を比較する。
- 合格条件: pipeline P95 の有意な悪化なし、worker saturation が可視化され、飽和時は shadow を drop して legacy を継続する。
- 失敗時の次手: sampling、out-of-process queue、ログ replay 方式へ移す。

## 12. リスク

| リスク | 影響 | 緩和策 |
| --- | --- | --- |
| `_intent_router_shadow` の名前衝突 | dispatcher が Jev を実行し本線変更 | Jev は専用ログのみ。既存 dispatch key に書かない |
| 既存 shadow と Jev shadow の二重 `resolve_route()` | LLM cost増、session race | scheduling を router 境界へ一本化し再入禁止 |
| request ごとの daemon thread | 高負荷時の resource 枯渇・ログ欠損 | bounded executor / queue、drop counter |
| background 中の mutable session | PII混入、turn 間競合 | JSON-safe immutable snapshot のみ渡す |
| Choice schema drift | Unknown route や誤 dispatch | strict validation、shadow failure、legacy継続 |
| Noul の閾値未確定 | safety FP/FN | shadow で分布収集。既存 gate を絶対優先し FN=0 を確認 |
| raw sid/user_input のログ | privacy / セキュリティ | raw値禁止、必要なら one-way session hash |
| `ResolvedBy` に `jev` がない | 型契約破壊 | Phase 1 は別 DTO。Phase 2 で型拡張を明示変更 |
| usage が欠落する API response | cost 集計不能 | nullable と `usage_missing=true` を記録 |
| process 終了で shadow 未完了 | 観測欠損 | dev は drain hook、CI は同期 adapter、欠損率を記録 |

## 13. 非目標

- Jev primary 化、canary、production rollout
- SessionOps の Jev primary 化
- triage stage1/stage2、Medicine QA focus、Store classifier の置換
- 回答生成、RAG、推薦 ranking、説明生成の変更
- SafetyGate / emergency / security deterministic rule の削除・弱体化
- Jev のための user attributes、RAG本文、不要PII送信
- model version pin の最終決定（shadow 中は `jev-latest`）
- token-cost ≥70% 削減の達成判定（primary 後に測定）

## 14. 他エージェントへの依頼メモ

### 実装担当

- `router.resolve_route()` で legacy を先に確定し、Phase 1 は必ず同じ legacy object を返すこと。
- Jev worker から session と `_intent_router_shadow` / `_routing_decision` を触らないこと。
- `chat_post_pipeline.py:383-394` の既存 shadow と二重起動しない移行を決めること。
- client は timeout 3.5s、429/5xx のみ最大1 retry、timeout/4xx retryなしを固定すること。

### テスト担当

- flags matrix、例外注入、session before/after diff、dispatcher handler parity を優先すること。
- Emergency/Security/medical_examination は primary route 一致だけでなく false negative を独立集計すること。
- 10-case fixture は `jev:minimal` のみを正式 adapter mode とし、`with_baseline_triage` は復活させないこと。

### 観測・分析担当

- `matched.primary/sub/exact`、failure reason、latency、usage、直近150件と累積 disagreement を集計すること。
- raw user text / session id を分析ログへ出さないこと。
- shadow drop / timeout / malformed response も母数から除外せず、coverage として別表示すること。

### API 契約担当

- 実装前に System One endpoint、認証 header、request/response schema、usage field、model名を dev で1件確認すること。
- `JEV_API_KEY` の有無のみ確認し、値を出力・fixture化しないこと。

