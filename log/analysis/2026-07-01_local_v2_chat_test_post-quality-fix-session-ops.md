# Chat Pipeline v2 ローカル統合テスト v2 (2026-07-01)

- ベース URL: `http://127.0.0.1:5000/`
- 参照: [CHAT_PIPELINE_V2.md](../docs/dev/CHAT_PIPELINE_V2.md)
- 実行時刻: 2026-06-30T17:01:58.378382+00:00
- 所要時間: 103.5s
- シナリオ/セッション: 12 / 総ターン: 12
- 自動合格: 7 / 要確認: 5
- GPT ユーザーシミュレータ: False
- GPT スケールモード: False

> **手動評価**: [http://127.0.0.1:5000/admin](http://127.0.0.1:5000/admin) で各 `session_id` の会話を確認してください。

## エグゼクティブサマリ

- **session_ops**: 7/12 自動合格 / 12 ターン

## カテゴリ別

| カテゴリ | セッション | ターン | 合格 | 要確認 |
|----------|------------|--------|------|--------|
| session_ops | 12 | 12 | 7 | 5 |

## 意図評価（intent evaluation）

- 追跡セッション: 12
- counseling_detail マッチ: 12
- route ログマッチ: 0

### セッション別意図サマリ

| session_id | scenario | turns | counseling | route_events | top_routes |
|------------|----------|-------|------------|--------------|------------|
| `1782838918402938265017` | session-ops-01 | 1 | 1/1 | 0 | — |
| `1782838926252656176844` | session-ops-02 | 1 | 1/1 | 0 | — |
| `1782838936513113566050` | session-ops-03 | 1 | 1/1 | 0 | — |
| `1782838944027384900340` | session-ops-04 | 1 | 1/1 | 0 | — |
| `1782838951551841610086` | session-ops-05 | 1 | 1/1 | 0 | — |
| `1782838959096063744644` | session-ops-06 | 1 | 1/1 | 0 | — |
| `1782838969314384823872` | session-ops-07 | 1 | 1/1 | 0 | — |
| `1782838976848981808517` | session-ops-08 | 1 | 1/1 | 0 | — |
| `1782838984324867439312` | session-ops-09 | 1 | 1/1 | 0 | — |
| `1782838994519435726347` | session-ops-10 | 1 | 1/1 | 0 | — |
| `1782839004759412575928` | session-ops-11 | 1 | 1/1 | 0 | — |
| `1782839015028810290187` | session-ops-12 | 1 | 1/1 | 0 | — |

## 自動メトリクス（gcp-log-analysis 系）

```json
{
  "since_unix": 1782838918.3783798,
  "pipeline_baseline": {
    "exit_code": 0,
    "data": {
      "counseling_detail_path": "D:\\Programing\\medicine-recommend\\log\\counseling_detail_log.jsonl",
      "counseling_detail_total": 6158,
      "with_response": 6158,
      "response_missing": 0,
      "response_missing_rate_pct": 0.0,
      "intent_router": {
        "shadow_total": 2880,
        "shadow_mismatch": 174,
        "shadow_mismatch_rate_pct": 6.04,
        "shadow_by_primary_route": {
          "Physical": 382,
          "SessionOps": 39,
          "Concierge": 2330,
          "Emergency": 44,
          "Store": 31,
          "Counseling": 54
        },
        "shadow_by_resolved_by": {
          "gate": 498,
          "llm": 23,
          "legacy": 210,
          "guard": 2149
        },
        "shadow_with_fever_context_flag": 89,
        "shadow_with_pending_cancelled_flag": 0,
        "dispatch_with_fever_context_flag": 33,
        "dispatch_with_pending_cancelled_flag": 0,
        "dispatch_total": 511,
        "dispatch_handled": 406,
        "dispatch_unhandled": 105,
        "dispatch_success_rate_pct": 79.45,
        "dispatch_by_handler": {
          "physical_agent": 197,
          "emergency_agent": 35,
          "session_ops": 37,
          "concierge_agent": 177,
          "counseling_processor": 52,
          "store_inquiry": 13
        },
        "mismatch_samples": [
          {
            "session_id": "1782717318767958735458",
            "user_input": "鼻水が止まらない",
            "primary_route": "Physical",
            "triage_category": "Other",
            "dialogue_flags": null
          },
          {
            "session_id": "1782717331790692413145",
            "user_input": "胃が痛い",
            "primary_route": "Physical",
            "triage_category": "Other",
            "dialogue_flags": null
          },
          {
            "session_id": "1782717345002559786616",
            "user_input": "下痢をしています",
            "primary_route": "Physical",
            "triage_category": "Other",
            "dialogue_flags": null
          },
          {
            "session_id": "1782717358082145444600",
            "user_input": "便秘です",
            "primary_route": "Physical",
            "triage_category": "Other",
            "dialogue_flags": null
          },
          {
            "session_id": "1782717371111493981907",
            "user_input": "目がかゆい",
            "primary_route": "Physical",
            "triage_category": "Other",
            "dialogue_flags": null
          },
          {
            "session_id": "1782717384636630906807",
            "user_input": "耳が痛い",
            "primary_route": "Physical",
            "triage_category": "Other",
            "dialogue_flags": null
          },
          {
            "session_id": "1782717397324593708841",
            "user_input": "肩こりがひどい",
            "primary_route": "Physical",
            "triage_category": "Other",
            "dialogue_flags": null
          },
          {
            "session_id": "1782717410097228277780",
            "user_input": "腰が痛い",
            "primary_route": "Physical",
            "triage_category": "Other",
            "dialogue_flags": null
          },
          {
            "session_id": "1782717422969711323681",
            "user_input": "めまいがする",
            "primary_route": "Physical",
            "triage_category": "Other",
            "dialogue_flags": null
          },
          {
            "session_id": "1782717436561396105511",
            "user_input": "吐き気がします",
            "primary_route": "Physical",
            "triage_category": "Other",
            "dialogue_flags": null
          },
          {
            "session_id": "1782717464619914328725",
            "user_input": "湿疹が出ました",
            "primary_route": "Physical",
            "triage_category": "Other",
            "dialogue_flags": null
          },
          {
            "session_id": "1782717478082699486770",
            "user_input": "口内炎が痛い",
            "primary_route": "Physical",
            "triage_category": "Other",
            "dialogue_flags": null
          },
          {
            "session_id": "1782717491022406289792",
            "user_input": "筋肉痛です",
            "primary_route": "Physical",
            "triage_category": "Other",
            "dialogue_flags": null
          },
          {
            "session_id": "1782717543896938653172",
            "user_input": "熱と頭痛があります",
            "primary_route": "Physical",
            "triage_category": "Other",
            "dialogue_flags": null
          },
          {
            "session_id": "1782717582631833194827",
            "user_input": "熱が下がりません",
            "primary_route": "Physical",
            "triage_category": "Other",
            "dialogue_flags": null
          },
          {
            "session_id": "1782718275694404951104",
            "user_input": "疲れが取れません",
            "primary_route": "Physical",
            "triage_category": "Other",
            "dialogue_flags": null
          },
          {
            "session_id": "1782718420081736662986",
            "user_input": "いや、頭痛です",
            "primary_route": "Physical",
            "triage_category": "Other",
            "dialogue_flags": null
          },
          {
            "session_id": "1782718459605389105878",
            "user_input": "違う、頭が痛い",
            "primary_route": "Physical",
            "triage_category": "Other",
            "dialogue_flags": null
          },
          {
            "session_id": "1782718507019374296805",
            "user_input": "訂正：のどの痛みが主です",
            "primary_route": "Physical",
            "triage_category": "Other",
            "dialogue_flags": null
          },
          {
            "session_id": "1782718530224157903605",
            "user_input": "いえ、ただの頭痛でした",
            "primary_route": "Physical",
            "triage_category": "Other",
            "dialogue_flags": null
          }
        ]
      },
      "gcp_analysis": {
        "source_md": "log\\analysis\\2026-06-28_downloaded-logs-20260626-20260627-20260627-162735.md",
        "counseling_detail_count_from_report": 0,
        "turns_response_missing_from_report": 36,
        "line_reply_fallback_push": 9,
        "slowest_post_seconds": 49.4
      },
      "notes": {
        "fast_path_ratio": "requires triage skip fields in structured logs (Wave 0 TODO)",
        "end_guard_redirect_rate": "requires pipeline_end_guard field in session/logs"
      }
    },
    "stderr": ""
  },
  "intent_router_shadow": {
    "exit_code": 0,
    "data": {
      "sources": {
        "shadow_jsonl": "D:\\Programing\\medicine-recommend\\log\\dialogue_route_shadow_log.jsonl",
        "dispatch_jsonl": "D:\\Programing\\medicine-recommend\\log\\dialogue_route_dispatch_log.jsonl",
        "gcp_log": null
      },
      "local": {
        "shadow_total": 2880,
        "shadow_mismatch": 174,
        "shadow_mismatch_rate_pct": 6.04,
        "shadow_by_primary_route": {
          "Physical": 382,
          "SessionOps": 39,
          "Concierge": 2330,
          "Emergency": 44,
          "Store": 31,
          "Counseling": 54
        },
        "shadow_by_resolved_by": {
          "gate": 498,
          "llm": 23,
          "legacy": 210,
          "guard": 2149
        },
        "shadow_with_fever_context_flag": 89,
        "shadow_with_pending_cancelled_flag": 0,
        "dispatch_with_fever_context_flag": 33,
        "dispatch_with_pending_cancelled_flag": 0,
        "dispatch_total": 511,
        "dispatch_handled": 406,
        "dispatch_unhandled": 105,
        "dispatch_success_rate_pct": 79.45,
        "dispatch_by_handler": {
          "physical_agent": 197,
          "emergency_agent": 35,
          "session_ops": 37,
          "concierge_agent": 177,
          "counseling_processor": 52,
          "store_inquiry": 13
        },
        "mismatch_samples": [
          {
            "session_id": "1782717318767958735458",
            "user_input": "鼻水が止まらない",
            "primary_route": "Physical",
            "triage_category": "Other",
            "dialogue_flags": null
          },
          {
            "session_id": "1782717331790692413145",
            "user_input": "胃が痛い",
            "primary_route": "Physical",
            "triage_category": "Other",
            "dialogue_flags": null
          },
          {
            "session_id": "1782717345002559786616",
            "user_input": "下痢をしています",
            "primary_route": "Physical",
            "triage_category": "Other",
            "dialogue_flags": null
          },
          {
            "session_id": "1782717358082145444600",
            "user_input": "便秘です",
            "primary_route": "Physical",
            "triage_category": "Other",
            "dialogue_flags": null
          },
          {
            "session_id": "1782717371111493981907",
            "user_input": "目がかゆい",
            "primary_route": "Physical",
            "triage_category": "Other",
            "dialogue_flags": null
          },
          {
            "session_id": "1782717384636630906807",
            "user_input": "耳が痛い",
            "primary_route": "Physical",
            "triage_category": "Other",
            "dialogue_flags": null
          },
          {
            "session_id": "1782717397324593708841",
            "user_input": "肩こりがひどい",
            "primary_route": "Physical",
            "triage_category": "Other",
            "dialogue_flags": null
          },
          {
            "session_id": "1782717410097228277780",
            "user_input": "腰が痛い",
            "primary_route": "Physical",
            "triage_category": "Other",
            "dialogue_flags": null
          },
          {
            "session_id": "1782717422969711323681",
            "user_input": "めまいがする",
            "primary_route": "Physical",
            "triage_category": "Other",
            "dialogue_flags": null
          },
          {
            "session_id": "1782717436561396105511",
            "user_input": "吐き気がします",
            "primary_route": "Physical",
            "triage_category": "Other",
            "dialogue_flags": null
          },
          {
            "session_id": "1782717464619914328725",
            "user_input": "湿疹が出ました",
            "primary_route": "Physical",
            "triage_category": "Other",
            "dialogue_flags": null
          },
          {
            "session_id": "1782717478082699486770",
            "user_input": "口内炎が痛い",
            "primary_route": "Physical",
            "triage_category": "Other",
            "dialogue_flags": null
          },
          {
            "session_id": "1782717491022406289792",
            "user_input": "筋肉痛です",
            "primary_route": "Physical",
            "triage_category": "Other",
            "dialogue_flags": null
          },
          {
            "session_id": "1782717543896938653172",
            "user_input": "熱と頭痛があります",
            "primary_route": "Physical",
            "triage_category": "Other",
            "dialogue_flags": null
          },
          {
            "session_id": "1782717582631833194827",
            "user_input": "熱が下がりません",
            "primary_route": "Physical",
            "triage_category": "Other",
            "dialogue_flags": null
          },
          {
            "session_id": "1782718275694404951104",
            "user_input": "疲れが取れません",
            "primary_route": "Physical",
            "triage_category": "Other",
            "dialogue_flags": null
          },
          {
            "session_id": "1782718420081736662986",
            "user_input": "いや、頭痛です",
            "primary_route": "Physical",
            "triage_category": "Other",
            "dialogue_flags": null
          },
          {
            "session_id": "1782718459605389105878",
            "user_input": "違う、頭が痛い",
            "primary_rou
```


## 要確認シナリオ

| id | category | session_id | failures | last_kind |
|----|----------|------------|----------|-----------|
| session-ops-02 | session_ops | `1782838926252656176844` | response_missing_or_too_short; route_mismatch expected=SessionOps got=unknown kind=None | None |
| session-ops-06 | session_ops | `1782838959096063744644` | response_missing_or_too_short; route_mismatch expected=SessionOps got=unknown kind=None | None |
| session-ops-09 | session_ops | `1782838984324867439312` | response_missing_or_too_short; route_mismatch expected=SessionOps got=unknown kind=None | None |
| session-ops-10 | session_ops | `1782838994519435726347` | response_missing_or_too_short; route_mismatch expected=SessionOps got=unknown kind=None | None |
| session-ops-11 | session_ops | `1782839004759412575928` | response_missing_or_too_short; route_mismatch expected=SessionOps got=unknown kind=None | None |

## 全セッション — 完全トランスクリプト

### session-ops-01 — session_ops (PASS)
- session_id: `1782838918402938265017`
- wave: 1a
#### Turn 1
- **User**: ステータスを教えて
- **Bot** (`session_integrated_status`, 5739ms):

チャット型医薬品相談ツール（β版）の利用状況です。個人を特定できる詳細は表示していません。

### session-ops-02 — session_ops (REVIEW)
- session_id: `1782838926252656176844`
- wave: 1a
#### Turn 1
- **User**: 何が記録されてる？
- **Bot** (`unknown`, 5489ms):

(empty)

### session-ops-03 — session_ops (PASS)
- session_id: `1782838936513113566050`
- wave: 1a
#### Turn 1
- **User**: 履歴を要約して
- **Bot** (`session_summary`, 5391ms):

要約できる相談履歴がまだありません。症状やお薬についてお話しいただくと、ここに要約が表示されます。

### session-ops-04 — session_ops (PASS)
- session_id: `1782838944027384900340`
- wave: 1a
#### Turn 1
- **User**: 履歴を教えて
- **Bot** (`session_summary`, 5409ms):

要約できる相談履歴がまだありません。症状やお薬についてお話しいただくと、ここに要約が表示されます。

### session-ops-05 — session_ops (PASS)
- session_id: `1782838951551841610086`
- wave: 1a
#### Turn 1
- **User**: 記憶を消して
- **Bot** (`memory_delete_confirm`, 5382ms):

このチャットの相談履歴と保存情報を削除します。よろしければ「削除する」、やめる場合は「キャンセル」とお送りください。

### session-ops-06 — session_ops (REVIEW)
- session_id: `1782838959096063744644`
- wave: 1a
#### Turn 1
- **User**: 履歴消して
- **Bot** (`unknown`, 5443ms):

(empty)

### session-ops-07 — session_ops (PASS)
- session_id: `1782838969314384823872`
- wave: 1a
#### Turn 1
- **User**: 会話を削除したい
- **Bot** (`memory_delete_confirm`, 5391ms):

このチャットの相談履歴と保存情報を削除します。よろしければ「削除する」、やめる場合は「キャンセル」とお送りください。

### session-ops-08 — session_ops (PASS)
- session_id: `1782838976848981808517`
- wave: 1a
#### Turn 1
- **User**: 今の状態を教えて
- **Bot** (`session_integrated_status`, 5357ms):

チャット型医薬品相談ツール（β版）の利用状況です。個人を特定できる詳細は表示していません。

### session-ops-09 — session_ops (REVIEW)
- session_id: `1782838984324867439312`
- wave: 1a
#### Turn 1
- **User**: セッションの状態は？
- **Bot** (`unknown`, 5438ms):

(empty)

### session-ops-10 — session_ops (REVIEW)
- session_id: `1782838994519435726347`
- wave: 1a
#### Turn 1
- **User**: これまでの会話をまとめて
- **Bot** (`unknown`, 5473ms):

(empty)

### session-ops-11 — session_ops (REVIEW)
- session_id: `1782839004759412575928`
- wave: 1a
#### Turn 1
- **User**: 保存されている情報は？
- **Bot** (`unknown`, 5479ms):

(empty)

### session-ops-12 — session_ops (PASS)
- session_id: `1782839015028810290187`
- wave: 1a
#### Turn 1
- **User**: 要約して
- **Bot** (`session_summary`, 5369ms):

要約できる相談履歴がまだありません。症状やお薬についてお話しいただくと、ここに要約が表示されます。

