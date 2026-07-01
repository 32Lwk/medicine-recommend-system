# Chat Pipeline v2 ローカル統合テスト v2 (2026-07-01)

- ベース URL: `http://127.0.0.1:5000/`
- 参照: [CHAT_PIPELINE_V2.md](../docs/dev/CHAT_PIPELINE_V2.md)
- 実行時刻: 2026-06-30T16:43:48.308351+00:00
- 所要時間: 906.3s
- シナリオ/セッション: 30 / 総ターン: 30
- 自動合格: 22 / 要確認: 8
- GPT ユーザーシミュレータ: False
- GPT スケールモード: False

> **手動評価**: [http://127.0.0.1:5000/admin](http://127.0.0.1:5000/admin) で各 `session_id` の会話を確認してください。

## エグゼクティブサマリ

- **physical**: 16/18 自動合格 / 18 ターン
- **session_ops**: 6/12 自動合格 / 12 ターン

## カテゴリ別

| カテゴリ | セッション | ターン | 合格 | 要確認 |
|----------|------------|--------|------|--------|
| physical | 18 | 18 | 16 | 2 |
| session_ops | 12 | 12 | 6 | 6 |

## 意図評価（intent evaluation）

- 追跡セッション: 30
- counseling_detail マッチ: 30
- route ログマッチ: 36
- IntentRouter metrics: `{"shadow_total": 18, "shadow_mismatch": 0, "shadow_mismatch_rate_pct": 0.0, "shadow_by_primary_route": {"Physical": 18}, "shadow_by_resolved_by": {"gate": 17, "legacy": 1}, "shadow_with_fever_context_flag": 0, "shadow_with_pending_cancelled_flag": 0, "dispatch_with_fever_context_flag": 0, "dispatch_with_pending_cancelled_flag": 0, "dispatch_total": 18, "dispatch_handled": 18, "dispatch_unhandled": 0, "dispatch_success_rate_pct": 100.0, "dispatch_by_handler": {"physical_agent": 18}, "mismatch_sam`

### セッション別意図サマリ

| session_id | scenario | turns | counseling | route_events | top_routes |
|------------|----------|-------|------------|--------------|------------|
| `1782837828333721263788` | session-ops-01 | 1 | 1/1 | 0 | — |
| `1782837836305379675639` | session-ops-02 | 1 | 1/1 | 0 | — |
| `1782837843749954787575` | session-ops-03 | 1 | 1/1 | 0 | — |
| `1782837851163040752630` | session-ops-04 | 1 | 1/1 | 0 | — |
| `1782837858507092306086` | session-ops-05 | 1 | 1/1 | 0 | — |
| `1782837865867333613297` | session-ops-06 | 1 | 1/1 | 0 | — |
| `1782837873241464924319` | session-ops-07 | 1 | 1/1 | 0 | — |
| `1782837880624425840201` | session-ops-08 | 1 | 1/1 | 0 | — |
| `1782837887986373940460` | session-ops-09 | 1 | 1/1 | 0 | — |
| `1782837895471228340279` | session-ops-10 | 1 | 1/1 | 0 | — |
| `1782837902869942760159` | session-ops-11 | 1 | 1/1 | 0 | — |
| `1782837910256060196556` | session-ops-12 | 1 | 1/1 | 0 | — |
| `1782837917635766305636` | physical-symptom-01 | 1 | 1/1 | 2 | Physical:2 |
| `1782837970348804898557` | physical-symptom-02 | 1 | 1/1 | 2 | Physical:2 |
| `1782838024661098953729` | physical-symptom-03 | 1 | 1/1 | 2 | Physical:2 |
| `1782838077758241755103` | physical-symptom-04 | 1 | 1/1 | 2 | Physical:2 |
| `1782838130599477476555` | physical-symptom-05 | 1 | 1/1 | 2 | Physical:2 |
| `1782838180502536429475` | physical-symptom-06 | 1 | 1/1 | 2 | Physical:2 |
| `1782838225016277438491` | physical-symptom-07 | 1 | 1/1 | 2 | Physical:2 |
| `1782838273506111777405` | physical-symptom-08 | 1 | 1/1 | 2 | Physical:2 |
| `1782838319350869774619` | physical-symptom-09 | 1 | 1/1 | 2 | Physical:2 |
| `1782838367361978108143` | physical-symptom-10 | 1 | 1/1 | 2 | Physical:2 |
| `1782838382876957556833` | physical-symptom-11 | 1 | 1/1 | 2 | Physical:2 |
| `1782838435298270380110` | physical-symptom-12 | 1 | 1/1 | 2 | Physical:2 |
| `1782838487130381417643` | physical-symptom-13 | 1 | 1/1 | 2 | Physical:2 |
| `1782838506382827304989` | physical-symptom-14 | 1 | 1/1 | 2 | Physical:2 |
| `1782838563109795160452` | physical-symptom-15 | 1 | 1/1 | 2 | Physical:2 |
| `1782838623228746775431` | physical-symptom-16 | 1 | 1/1 | 2 | Physical:2 |
| `1782838670978976598446` | physical-symptom-17 | 1 | 1/1 | 2 | Physical:2 |
| `1782838684887829712665` | physical-symptom-18 | 1 | 1/1 | 2 | Physical:2 |

## 自動メトリクス（gcp-log-analysis 系）

```json
{
  "since_unix": 1782837828.3083491,
  "pipeline_baseline": {
    "exit_code": 0,
    "data": {
      "counseling_detail_path": "D:\\Programing\\medicine-recommend\\log\\counseling_detail_log.jsonl",
      "counseling_detail_total": 6146,
      "with_response": 6146,
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
| session-ops-03 | session_ops | `1782837843749954787575` | response_missing_or_too_short; route_mismatch expected=SessionOps got=unknown kind=None | None |
| session-ops-04 | session_ops | `1782837851163040752630` | response_missing_or_too_short; route_mismatch expected=SessionOps got=unknown kind=None | None |
| session-ops-08 | session_ops | `1782837880624425840201` | response_missing_or_too_short; route_mismatch expected=SessionOps got=unknown kind=None | None |
| session-ops-09 | session_ops | `1782837887986373940460` | response_missing_or_too_short; route_mismatch expected=SessionOps got=unknown kind=None | None |
| session-ops-10 | session_ops | `1782837895471228340279` | response_missing_or_too_short; route_mismatch expected=SessionOps got=unknown kind=None | None |
| session-ops-11 | session_ops | `1782837902869942760159` | response_missing_or_too_short; route_mismatch expected=SessionOps got=unknown kind=None | None |
| physical-symptom-08 | physical | `1782838273506111777405` | route_mismatch expected=Physical got=unknown kind=None | None |
| physical-symptom-15 | physical | `1782838563109795160452` | route_mismatch expected=Physical got=unknown kind=None | None |

## 全セッション — 完全トランスクリプト

### session-ops-01 — session_ops (PASS)
- session_id: `1782837828333721263788`
- wave: 1a
#### Turn 1
- **User**: ステータスを教えて
- **Bot** (`session_integrated_status`, 5899ms):

チャット型医薬品相談ツール（β版）の利用状況です。個人を特定できる詳細は表示していません。

### session-ops-02 — session_ops (PASS)
- session_id: `1782837836305379675639`
- wave: 1a
#### Turn 1
- **User**: 何が記録されてる？
- **Bot** (`session_integrated_status`, 5380ms):

チャット型医薬品相談ツール（β版）の利用状況です。個人を特定できる詳細は表示していません。

### session-ops-03 — session_ops (REVIEW)
- session_id: `1782837843749954787575`
- wave: 1a
#### Turn 1
- **User**: 履歴を要約して
- **Bot** (`unknown`, 5347ms):

(empty)

### session-ops-04 — session_ops (REVIEW)
- session_id: `1782837851163040752630`
- wave: 1a
#### Turn 1
- **User**: 履歴を教えて
- **Bot** (`unknown`, 5249ms):

(empty)

### session-ops-05 — session_ops (PASS)
- session_id: `1782837858507092306086`
- wave: 1a
#### Turn 1
- **User**: 記憶を消して
- **Bot** (`memory_delete_confirm`, 5283ms):

このチャットの相談履歴と保存情報を削除します。よろしければ「削除する」、やめる場合は「キャンセル」とお送りください。

### session-ops-06 — session_ops (PASS)
- session_id: `1782837865867333613297`
- wave: 1a
#### Turn 1
- **User**: 履歴消して
- **Bot** (`memory_delete_confirm`, 5294ms):

このチャットの相談履歴と保存情報を削除します。よろしければ「削除する」、やめる場合は「キャンセル」とお送りください。

### session-ops-07 — session_ops (PASS)
- session_id: `1782837873241464924319`
- wave: 1a
#### Turn 1
- **User**: 会話を削除したい
- **Bot** (`memory_delete_confirm`, 5299ms):

このチャットの相談履歴と保存情報を削除します。よろしければ「削除する」、やめる場合は「キャンセル」とお送りください。

### session-ops-08 — session_ops (REVIEW)
- session_id: `1782837880624425840201`
- wave: 1a
#### Turn 1
- **User**: 今の状態を教えて
- **Bot** (`unknown`, 5268ms):

(empty)

### session-ops-09 — session_ops (REVIEW)
- session_id: `1782837887986373940460`
- wave: 1a
#### Turn 1
- **User**: セッションの状態は？
- **Bot** (`unknown`, 5409ms):

(empty)

### session-ops-10 — session_ops (REVIEW)
- session_id: `1782837895471228340279`
- wave: 1a
#### Turn 1
- **User**: これまでの会話をまとめて
- **Bot** (`unknown`, 5330ms):

(empty)

### session-ops-11 — session_ops (REVIEW)
- session_id: `1782837902869942760159`
- wave: 1a
#### Turn 1
- **User**: 保存されている情報は？
- **Bot** (`unknown`, 5321ms):

(empty)

### session-ops-12 — session_ops (PASS)
- session_id: `1782837910256060196556`
- wave: 1a
#### Turn 1
- **User**: 要約して
- **Bot** (`session_summary`, 5311ms):

要約できる相談履歴がまだありません。症状やお薬についてお話しいただくと、ここに要約が表示されます。

### physical-symptom-01 — physical (PASS)
- session_id: `1782837917635766305636`
- wave: 1b
#### Turn 1
- **User**: 頭痛い
- **Bot** (`unknown`, 50632ms):

頭痛いのはつらいですね。まずは休んで、水分をとり、空腹なら少し食べてから服用してください。カロナールA・タイレノールAは胃にやさしく、頭痛に使いやすいです。トキワイブプロエースAは痛みが強い時に向きますが、胃が弱い方は注意。発熱やのど痛みもあれば、インフルエンザの可能性もあるので無理せず受診を。

### physical-symptom-02 — physical (PASS)
- session_id: `1782837970348804898557`
- wave: 1b
#### Turn 1
- **User**: 頭が痛いです
- **Bot** (`unknown`, 52181ms):

頭が痛いんですね、しんどいですね。まずは安静と水分をとり、空腹なら少し食べてからの服用がおすすめです。頭痛には、解熱鎮痛成分のあるトキワイブプロエースＡ、カロナールＡ、タイレノールＡが使いやすいです。発熱や関節痛もある、インフルエンザっぽい場合は早めに受診してください。

### physical-symptom-03 — physical (PASS)
- session_id: `1782838024661098953729`
- wave: 1b
#### Turn 1
- **User**: 咳が出ます
- **Bot** (`unknown`, 50963ms):

咳が出るんですね、しんどいですね。のどの刺激で出る咳には、のどをうるおしてやわらげるトローチ類（ベンザブロックトローチ、新エスベナントローチ）がおすすめです。水分をこまめにとり、加湿も意識してください。発熱や強いだるさがあれば、インフルエンザの可能性もあるので早めに受診を。

### physical-symptom-04 — physical (PASS)
- session_id: `1782838077758241755103`
- wave: 1b
#### Turn 1
- **User**: のどが痛い
- **Bot** (`unknown`, 50709ms):

のどが痛いの、つらいですね。まずはのどを直接うるおす「スカイブブロンのどスプレー」や「トピックＧトローチ」が合っています。痛みが強ければ「イブプロフェンソフトカプセル」でつらさを和らげられます。高熱や関節痛があればインフルエンザも疑い、受診してください。

### physical-symptom-05 — physical (PASS)
- session_id: `1782838130599477476555`
- wave: 1b
#### Turn 1
- **User**: 鼻水が止まらない
- **Bot** (`unknown`, 47786ms):

鼻水が止まらないの、つらいですね。まずは鼻水を抑えやすいストナリニSや、小青龍湯が合いやすいです。くしゃみ・水っぽい鼻水に向いています。眠気が出ることがあるので運転は注意してください。発熱や強いだるさがあれば、インフルエンザの可能性もあるので受診をおすすめします。

### physical-symptom-06 — physical (PASS)
- session_id: `1782838180502536429475`
- wave: 1b
#### Turn 1
- **User**: 胃が痛い
- **Bot** (`unknown`, 42413ms):

胃が痛いのはつらいですね。まずは刺激物や空腹を避け、胃を休めてください。ご提案の第一三共胃腸薬コアブロック散剤や新キャベジンコーワSは、胃の痛み・もたれに使いやすい薬です。黒い便、吐血、強い痛みが続く場合は受診を。発熱や全身のだるさがあれば、インフルエンザも疑ってください。

### physical-symptom-07 — physical (PASS)
- session_id: `1782838225016277438491`
- wave: 1b
#### Turn 1
- **User**: 下痢をしています
- **Bot** (`unknown`, 46376ms):

下痢でつらいですね。まずは水分を少しずつ補い、脂っこい物や冷たい物は控えてください。ご提案の赤玉や高砂オウレンは、下痢をしやすい時の整腸・止瀉に向いています。発熱や強い腹痛、血便、インフルエンザのようなだるさがあれば受診を。

### physical-symptom-08 — physical (REVIEW)
- session_id: `1782838273506111777405`
- wave: 1b
#### Turn 1
- **User**: 便秘です
- **Bot** (`unknown`, 43723ms):

便秘でつらいですね。まずは水分と食物繊維を少しずつ増やし、軽い運動も試してみてください。お腹の張りや排便困難が強いなら、大柴胡湯や浣腸剤が役立つことがあります。浣腸は使いすぎに注意し、腹痛・吐き気・血便があれば受診してください。

### physical-symptom-09 — physical (PASS)
- session_id: `1782838319350869774619`
- wave: 1b
#### Turn 1
- **User**: 目がかゆい
- **Bot** (`unknown`, 45892ms):

目がかゆいのはつらいですね。目のまわりの皮膚のかゆみや赤みに使いやすい外用薬として、リビメックスコーワクリーム/ローション、タクトプラスローションを候補にしています。目の中には入れず、刺激が強ければ中止してください。妊娠中・授乳中やお子さまは使用前にご相談を。発熱や目やにが強いなら受診をおすすめします。

### physical-symptom-10 — physical (PASS)
- session_id: `1782838367361978108143`
- wave: 1b
#### Turn 1
- **User**: 耳が痛い
- **Bot** (`system_error`, 13423ms):

処理中に問題が発生しました。しばらく時間をおいてからもう一度お試しください。

### physical-symptom-11 — physical (PASS)
- session_id: `1782838382876957556833`
- wave: 1b
#### Turn 1
- **User**: 肩こりがひどい
- **Bot** (`unknown`, 50350ms):

肩こりがひどいんですね、つらいですね。まずはイブロックフィルムプラスターやイブロック冷感Ｓで、つらい部分を直接ケアすると楽になりやすいです。デーチカも血行を促して肩こりに合います。湿布かぶれ、妊娠中、持病や他の薬がある方は注意してください。発熱や強いだるさがあればインフルエンザの可能性もあるので受診をおすすめします。

### physical-symptom-12 — physical (PASS)
- session_id: `1782838435298270380110`
- wave: 1b
#### Turn 1
- **User**: 腰が痛い
- **Bot** (`unknown`, 49248ms):

腰が痛いんですね、つらいですね。まずは貼り薬のサロンパス30やイブロックフィルムプラスター、冷感タイプのイブロック冷感Sで、痛む場所を直接ケアするのがおすすめです。かぶれやすい方は短時間から試し、強い痛み・しびれ、発熱や転倒後の痛みがあれば受診してください。

### physical-symptom-13 — physical (PASS)
- session_id: `1782838487130381417643`
- wave: 1b
#### Turn 1
- **User**: めまいがする
- **Bot** (`system_error`, 16894ms):

処理中に問題が発生しました。しばらく時間をおいてからもう一度お試しください。

### physical-symptom-14 — physical (PASS)
- session_id: `1782838506382827304989`
- wave: 1b
#### Turn 1
- **User**: 吐き気がします
- **Bot** (`unknown`, 53569ms):

吐き気がつらいですね。女性の方で、つわりの可能性もあるため、胃酸をおさえて胃の不快感を和らげるガストール細粒・錠、胃健錠が合いやすいです。まずは少量ずつ飲食し、刺激物や脂っこい物は控えめに。発熱や強いだるさがあればインフルエンザも考え、早めに受診してください。

### physical-symptom-15 — physical (REVIEW)
- session_id: `1782838563109795160452`
- wave: 1b
#### Turn 1
- **User**: かゆみがあります
- **Bot** (`unknown`, 58007ms):

かゆみがあるんですね、つらいです。まずはかき壊しを避け、清潔と保湿を心がけてください。リビメックスコーワクリームやタクトプラスローション、ベトノバールＳクリームは、かゆみや炎症をしっかり抑えやすいお薬です。顔や陰部、じゅくじゅくした所は避け、数日でよくならない・広がる時は受診を。

### physical-symptom-16 — physical (PASS)
- session_id: `1782838623228746775431`
- wave: 1b
#### Turn 1
- **User**: 湿疹が出ました
- **Bot** (`unknown`, 45603ms):

湿疹が出てつらいですね。かゆみや赤みが主なら、まずはメンソレータムメディクイッククリームSがおすすめです。炎症をしっかり抑えたい場合はメディクイックプロも候補になります。掻くと悪化しやすいので、清潔にして保湿を心がけてください。広がる、ジュクジュクする、発熱がある時は受診を。

### physical-symptom-17 — physical (PASS)
- session_id: `1782838670978976598446`
- wave: 1b
#### Turn 1
- **User**: 口内炎が痛い
- **Bot** (`system_error`, 11810ms):

処理中に問題が発生しました。しばらく時間をおいてからもう一度お試しください。

### physical-symptom-18 — physical (PASS)
- session_id: `1782838684887829712665`
- wave: 1b
#### Turn 1
- **User**: 筋肉痛です
- **Bot** (`unknown`, 48241ms):

筋肉痛でしんどいですね。まずは安静と、痛みがつらい時はトキワイブプロエースAやカロナールAで内側からケア、局所の張りにはサロンパス30も使いやすいです。胃が弱い方は食後に、長引く・熱やだるさが強い時はインフルエンザも疑って受診を。

