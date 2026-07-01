# Chat Pipeline v2 ローカル統合テスト v2 (2026-07-01)

- ベース URL: `http://127.0.0.1:5010/`
- 参照: [CHAT_PIPELINE_V2.md](../docs/dev/CHAT_PIPELINE_V2.md)
- 実行時刻: 2026-06-30T17:08:33.457053+00:00
- 所要時間: 947.0s
- シナリオ/セッション: 30 / 総ターン: 30
- 自動合格: 25 / 要確認: 5
- GPT ユーザーシミュレータ: False
- GPT スケールモード: False

> **手動評価**: [http://127.0.0.1:5000/admin](http://127.0.0.1:5000/admin) で各 `session_id` の会話を確認してください。

## エグゼクティブサマリ

- **physical**: 13/18 自動合格 / 18 ターン
- **session_ops**: 12/12 自動合格 / 12 ターン

## カテゴリ別

| カテゴリ | セッション | ターン | 合格 | 要確認 |
|----------|------------|--------|------|--------|
| physical | 18 | 18 | 13 | 5 |
| session_ops | 12 | 12 | 12 | 0 |

## 意図評価（intent evaluation）

- 追跡セッション: 30
- counseling_detail マッチ: 30
- route ログマッチ: 36
- IntentRouter metrics: `{"shadow_total": 18, "shadow_mismatch": 0, "shadow_mismatch_rate_pct": 0.0, "shadow_by_primary_route": {"Physical": 18}, "shadow_by_resolved_by": {"gate": 17, "legacy": 1}, "shadow_with_fever_context_flag": 0, "shadow_with_pending_cancelled_flag": 0, "dispatch_with_fever_context_flag": 0, "dispatch_with_pending_cancelled_flag": 0, "dispatch_total": 18, "dispatch_handled": 18, "dispatch_unhandled": 0, "dispatch_success_rate_pct": 100.0, "dispatch_by_handler": {"physical_agent": 18}, "mismatch_sam`

### セッション別意図サマリ

| session_id | scenario | turns | counseling | route_events | top_routes |
|------------|----------|-------|------------|--------------|------------|
| `1782839313487447935082` | session-ops-01 | 1 | 1/1 | 0 | — |
| `1782839319545779318158` | session-ops-02 | 1 | 1/1 | 0 | — |
| `1782839325364107273150` | session-ops-03 | 1 | 1/1 | 0 | — |
| `1782839331192866257560` | session-ops-04 | 1 | 1/1 | 0 | — |
| `1782839337026767519976` | session-ops-05 | 1 | 1/1 | 0 | — |
| `1782839342841348527345` | session-ops-06 | 1 | 1/1 | 0 | — |
| `1782839348667078507845` | session-ops-07 | 1 | 1/1 | 0 | — |
| `1782839354485193965216` | session-ops-08 | 1 | 1/1 | 0 | — |
| `1782839360306972136041` | session-ops-09 | 1 | 1/1 | 0 | — |
| `1782839366119917115612` | session-ops-10 | 1 | 1/1 | 0 | — |
| `1782839371958363199551` | session-ops-11 | 1 | 1/1 | 0 | — |
| `1782839377796623680427` | session-ops-12 | 1 | 1/1 | 0 | — |
| `1782839383545755595365` | physical-symptom-01 | 1 | 1/1 | 2 | Physical:2 |
| `1782839432297743472014` | physical-symptom-02 | 1 | 1/1 | 2 | Physical:2 |
| `1782839480665563957649` | physical-symptom-03 | 1 | 1/1 | 2 | Physical:2 |
| `1782839533191211119713` | physical-symptom-04 | 1 | 1/1 | 2 | Physical:2 |
| `1782839585728756260295` | physical-symptom-05 | 1 | 1/1 | 2 | Physical:2 |
| `1782839635419823529265` | physical-symptom-06 | 1 | 1/1 | 2 | Physical:2 |
| `1782839681237094920983` | physical-symptom-07 | 1 | 1/1 | 2 | Physical:2 |
| `1782839734301424556194` | physical-symptom-08 | 1 | 1/1 | 2 | Physical:2 |
| `1782839782369087660892` | physical-symptom-09 | 1 | 1/1 | 2 | Physical:2 |
| `1782839827485671258799` | physical-symptom-10 | 1 | 1/1 | 2 | Physical:2 |
| `1782839876611470509365` | physical-symptom-11 | 1 | 1/1 | 2 | Physical:2 |
| `1782839926481346647744` | physical-symptom-12 | 1 | 1/1 | 2 | Physical:2 |
| `1782839973113192363777` | physical-symptom-13 | 1 | 1/1 | 2 | Physical:2 |
| `1782840007732029480616` | physical-symptom-14 | 1 | 1/1 | 2 | Physical:2 |
| `1782840061012287622287` | physical-symptom-15 | 1 | 1/1 | 2 | Physical:2 |
| `1782840111075744107115` | physical-symptom-16 | 1 | 1/1 | 2 | Physical:2 |
| `1782840162210863572224` | physical-symptom-17 | 1 | 1/1 | 2 | Physical:2 |
| `1782840206380577266515` | physical-symptom-18 | 1 | 1/1 | 2 | Physical:2 |

## 自動メトリクス（gcp-log-analysis 系）

```json
{
  "since_unix": 1782839313.4570496,
  "pipeline_baseline": {
    "exit_code": 0,
    "data": {
      "counseling_detail_path": "D:\\Programing\\medicine-recommend\\log\\counseling_detail_log.jsonl",
      "counseling_detail_total": 6205,
      "with_response": 6205,
      "response_missing": 0,
      "response_missing_rate_pct": 0.0,
      "intent_router": {
        "shadow_total": 2898,
        "shadow_mismatch": 174,
        "shadow_mismatch_rate_pct": 6.0,
        "shadow_by_primary_route": {
          "Physical": 400,
          "SessionOps": 39,
          "Concierge": 2330,
          "Emergency": 44,
          "Store": 31,
          "Counseling": 54
        },
        "shadow_by_resolved_by": {
          "gate": 515,
          "llm": 23,
          "legacy": 211,
          "guard": 2149
        },
        "shadow_with_fever_context_flag": 89,
        "shadow_with_pending_cancelled_flag": 0,
        "dispatch_with_fever_context_flag": 33,
        "dispatch_with_pending_cancelled_flag": 0,
        "dispatch_total": 529,
        "dispatch_handled": 424,
        "dispatch_unhandled": 105,
        "dispatch_success_rate_pct": 80.15,
        "dispatch_by_handler": {
          "physical_agent": 215,
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
        "shadow_total": 2898,
        "shadow_mismatch": 174,
        "shadow_mismatch_rate_pct": 6.0,
        "shadow_by_primary_route": {
          "Physical": 400,
          "SessionOps": 39,
          "Concierge": 2330,
          "Emergency": 44,
          "Store": 31,
          "Counseling": 54
        },
        "shadow_by_resolved_by": {
          "gate": 515,
          "llm": 23,
          "legacy": 211,
          "guard": 2149
        },
        "shadow_with_fever_context_flag": 89,
        "shadow_with_pending_cancelled_flag": 0,
        "dispatch_with_fever_context_flag": 33,
        "dispatch_with_pending_cancelled_flag": 0,
        "dispatch_total": 529,
        "dispatch_handled": 424,
        "dispatch_unhandled": 105,
        "dispatch_success_rate_pct": 80.15,
        "dispatch_by_handler": {
          "physical_agent": 215,
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
            "primary_route
```


## 要確認シナリオ

| id | category | session_id | failures | last_kind |
|----|----------|------------|----------|-----------|
| physical-symptom-08 | physical | `1782839734301424556194` | route_mismatch expected=Physical got=unknown kind=None | None |
| physical-symptom-12 | physical | `1782839926481346647744` | route_mismatch expected=Physical got=unknown kind=None | None |
| physical-symptom-14 | physical | `1782840007732029480616` | route_mismatch expected=Physical got=unknown kind=None | None |
| physical-symptom-15 | physical | `1782840061012287622287` | route_mismatch expected=Physical got=unknown kind=None | None |
| physical-symptom-17 | physical | `1782840162210863572224` | route_mismatch expected=Physical got=unknown kind=None | None |

## 全セッション — 完全トランスクリプト

### session-ops-01 — session_ops (PASS)
- session_id: `1782839313487447935082`
- wave: 1a
#### Turn 1
- **User**: ステータスを教えて
- **Bot** (`session_integrated_status`, 4280ms):

チャット型医薬品相談ツール（β版）の利用状況です。個人を特定できる詳細は表示していません。

### session-ops-02 — session_ops (PASS)
- session_id: `1782839319545779318158`
- wave: 1a
#### Turn 1
- **User**: 何が記録されてる？
- **Bot** (`session_integrated_status`, 4043ms):

チャット型医薬品相談ツール（β版）の利用状況です。個人を特定できる詳細は表示していません。

### session-ops-03 — session_ops (PASS)
- session_id: `1782839325364107273150`
- wave: 1a
#### Turn 1
- **User**: 履歴を要約して
- **Bot** (`session_summary`, 4053ms):

要約できる相談履歴がまだありません。症状やお薬についてお話しいただくと、ここに要約が表示されます。

### session-ops-04 — session_ops (PASS)
- session_id: `1782839331192866257560`
- wave: 1a
#### Turn 1
- **User**: 履歴を教えて
- **Bot** (`session_summary`, 4058ms):

要約できる相談履歴がまだありません。症状やお薬についてお話しいただくと、ここに要約が表示されます。

### session-ops-05 — session_ops (PASS)
- session_id: `1782839337026767519976`
- wave: 1a
#### Turn 1
- **User**: 記憶を消して
- **Bot** (`memory_delete_confirm`, 4042ms):

このチャットの相談履歴と保存情報を削除します。よろしければ「削除する」、やめる場合は「キャンセル」とお送りください。

### session-ops-06 — session_ops (PASS)
- session_id: `1782839342841348527345`
- wave: 1a
#### Turn 1
- **User**: 履歴消して
- **Bot** (`memory_delete_confirm`, 4050ms):

このチャットの相談履歴と保存情報を削除します。よろしければ「削除する」、やめる場合は「キャンセル」とお送りください。

### session-ops-07 — session_ops (PASS)
- session_id: `1782839348667078507845`
- wave: 1a
#### Turn 1
- **User**: 会話を削除したい
- **Bot** (`memory_delete_confirm`, 4044ms):

このチャットの相談履歴と保存情報を削除します。よろしければ「削除する」、やめる場合は「キャンセル」とお送りください。

### session-ops-08 — session_ops (PASS)
- session_id: `1782839354485193965216`
- wave: 1a
#### Turn 1
- **User**: 今の状態を教えて
- **Bot** (`session_integrated_status`, 4049ms):

チャット型医薬品相談ツール（β版）の利用状況です。個人を特定できる詳細は表示していません。

### session-ops-09 — session_ops (PASS)
- session_id: `1782839360306972136041`
- wave: 1a
#### Turn 1
- **User**: セッションの状態は？
- **Bot** (`session_integrated_status`, 4040ms):

チャット型医薬品相談ツール（β版）の利用状況です。個人を特定できる詳細は表示していません。

### session-ops-10 — session_ops (PASS)
- session_id: `1782839366119917115612`
- wave: 1a
#### Turn 1
- **User**: これまでの会話をまとめて
- **Bot** (`session_summary`, 4055ms):

要約できる相談履歴がまだありません。症状やお薬についてお話しいただくと、ここに要約が表示されます。

### session-ops-11 — session_ops (PASS)
- session_id: `1782839371958363199551`
- wave: 1a
#### Turn 1
- **User**: 保存されている情報は？
- **Bot** (`session_integrated_status`, 4055ms):

チャット型医薬品相談ツール（β版）の利用状況です。個人を特定できる詳細は表示していません。

### session-ops-12 — session_ops (PASS)
- session_id: `1782839377796623680427`
- wave: 1a
#### Turn 1
- **User**: 要約して
- **Bot** (`session_summary`, 3970ms):

要約できる相談履歴がまだありません。症状やお薬についてお話しいただくと、ここに要約が表示されます。

### physical-symptom-01 — physical (PASS)
- session_id: `1782839383545755595365`
- wave: 1b
#### Turn 1
- **User**: 頭痛い
- **Bot** (`no_recommendation`, 46977ms):

【以下の場合は医師にご相談ください】
・症状が3日以上続く場合
・症状が悪化する場合
・高熱（38.5度以上）が続く場合
・発疹、発赤、かゆみなどの副作用が現れた場合
・他の症状が現れた場合
・長期連用する場合

### physical-symptom-02 — physical (PASS)
- session_id: `1782839432297743472014`
- wave: 1b
#### Turn 1
- **User**: 頭が痛いです
- **Bot** (`no_recommendation`, 46588ms):

【以下の場合は医師にご相談ください】
・症状が3日以上続く場合
・症状が悪化する場合
・高熱（38.5度以上）が続く場合
・発疹、発赤、かゆみなどの副作用が現れた場合
・他の症状が現れた場合
・長期連用する場合

### physical-symptom-03 — physical (PASS)
- session_id: `1782839480665563957649`
- wave: 1b
#### Turn 1
- **User**: 咳が出ます
- **Bot** (`unknown`, 50722ms):

咳が出るんですね、つらいですね。のどの刺激で咳が出ている時は、ベンザブロックトローチや新エスベナントローチのような、のどをうるおして咳をやわらげる薬が向いています。水分をとり、加湿して安静にしてください。高熱や強いだるさがあれば、インフルエンザの可能性もあるので受診を。

### physical-symptom-04 — physical (PASS)
- session_id: `1782839533191211119713`
- wave: 1b
#### Turn 1
- **User**: のどが痛い
- **Bot** (`unknown`, 50733ms):

のどが痛いの、つらいですね。まずはスカイブブロンのどスプレーやトピックＧトローチで、のどを直接うるおしながら痛みを和らげるのが合っています。痛みや発熱が強いときはイブプロフェンも選択肢です。胃が弱い方、妊娠中の方は注意してください。高熱や関節痛があればインフルエンザも疑い、受診をおすすめします。

### physical-symptom-05 — physical (PASS)
- session_id: `1782839585728756260295`
- wave: 1b
#### Turn 1
- **User**: 鼻水が止まらない
- **Bot** (`unknown`, 47903ms):

鼻水が止まらないのですね、つらいですね。水っぽい鼻水なら、体質や症状に合いやすい小青龍湯が候補です。角野龍雲湯も鼻水の不調に用いられます。まずは水分補給と保温を心がけ、眠気や持病、妊娠中の方は服用前に確認してください。発熱や強いだるさがあればインフルエンザも疑い、早めに受診を。

### physical-symptom-06 — physical (PASS)
- session_id: `1782839635419823529265`
- wave: 1b
#### Turn 1
- **User**: 胃が痛い
- **Bot** (`unknown`, 44043ms):

胃が痛いのはつらいですね。新キャベジンコーワSは、胃酸や胃の荒れによる痛みに使いやすく、ザッツ錠も胃の不快感を和らげるお薬です。まずは食事を無理せず、刺激物やアルコールは控えてください。強い痛み、吐き気、黒い便、発熱がある、または長引く場合は早めに受診しましょう。

### physical-symptom-07 — physical (PASS)
- session_id: `1782839681237094920983`
- wave: 1b
#### Turn 1
- **User**: 下痢をしています
- **Bot** (`unknown`, 51281ms):

下痢をしていてつらいですね。まずは水分を少しずつとり、胃腸を休めてください。富士はら薬「赤玉」や高砂オウレン類は、下痢の症状に合わせて選びやすいです。血便、高熱、強い腹痛、脱水がある場合や長引く場合は受診を。インフルエンザで下痢が出ることもあるので、発熱やだるさがあれば注意してください。

### physical-symptom-08 — physical (REVIEW)
- session_id: `1782839734301424556194`
- wave: 1b
#### Turn 1
- **User**: 便秘です
- **Bot** (`unknown`, 46296ms):

便秘でつらいですね。まずは水分と食物繊維を意識し、軽い運動も試してみてください。つらいお腹の張りや早く出したいときは、浣腸が直接効きやすいです。腹痛、吐き気、血便がある、何日も出ない場合は無理せず受診してください。

### physical-symptom-09 — physical (PASS)
- session_id: `1782839782369087660892`
- wave: 1b
#### Turn 1
- **User**: 目がかゆい
- **Bot** (`unknown`, 43351ms):

目がかゆいのですね、つらいですね。まずはこすらず、手を洗ってから冷やすと少し楽になることがあります。今回の症状には、かゆみや炎症を抑えやすいリビメックスコーワシリーズが合っています。目の中には入れず、赤み・痛み・見えにくさがあれば受診してください。

### physical-symptom-10 — physical (PASS)
- session_id: `1782839827485671258799`
- wave: 1b
#### Turn 1
- **User**: 耳が痛い
- **Bot** (`unknown`, 47358ms):

耳が痛いのですね、つらいですね。耳鳴りもあるなら、まずは耳を触りすぎず清潔を保ち、痛みが強い時は無理せず受診も考えてください。キップパイロール-HIは耳まわりの炎症やかゆみ対策、オリブ油は乾燥時の保護に役立ちます。発熱や風邪症状があればインフルエンザにも注意してください。

### physical-symptom-11 — physical (PASS)
- session_id: `1782839876611470509365`
- wave: 1b
#### Turn 1
- **User**: 肩こりがひどい
- **Bot** (`unknown`, 48056ms):

肩こりがひどいんですね、つらいですね。まずは、つらい部分に貼るイブロックフィルムプラスターや冷感タイプのイブロック冷感Ｓが使いやすいです。デーチカも痛みと炎症をやわらげる選択肢です。かぶれやすい方、妊娠中、持病や服薬中なら使用前に確認を。発熱や強いだるさがあれば受診も検討してください。

### physical-symptom-12 — physical (REVIEW)
- session_id: `1782839926481346647744`
- wave: 1b
#### Turn 1
- **User**: 腰が痛い
- **Bot** (`unknown`, 44845ms):

腰が痛いんですね、つらいですね。まずは無理をせず、湿布で痛む部分をやさしくケアするのがよさそうです。サロンパス30やイブロックフィルムプラスター、イブロック冷感Sは、腰の痛みに使いやすい貼り薬です。かぶれや強い痛み、足のしびれがある時は受診してください。

### physical-symptom-13 — physical (PASS)
- session_id: `1782839973113192363777`
- wave: 1b
#### Turn 1
- **User**: めまいがする
- **Bot** (`no_recommendation`, 32810ms):

【以下の場合は医師にご相談ください】
・症状が3日以上続く場合
・症状が悪化する場合
・高熱（38.5度以上）が続く場合
・発疹、発赤、かゆみなどの副作用が現れた場合
・他の症状が現れた場合
・長期連用する場合

### physical-symptom-14 — physical (REVIEW)
- session_id: `1782840007732029480616`
- wave: 1b
#### Turn 1
- **User**: 吐き気がします
- **Bot** (`unknown`, 51476ms):

吐き気がつらいですね。女性の方で、つわりのような時にも使いやすい胃腸薬として「胃健錠」を案内します。胃の不快感やむかつきをやわらげる目的に合っています。まずは無理せず水分を少しずつ取り、食事は消化のよいものを。妊娠の可能性がある場合は、服用前に念のため確認してください。

### physical-symptom-15 — physical (REVIEW)
- session_id: `1782840061012287622287`
- wave: 1b
#### Turn 1
- **User**: かゆみがあります
- **Bot** (`unknown`, 48298ms):

かゆみがあるのですね、つらいですね。まずは掻かずに、清潔と保湿を心がけてください。リビメックスコーワやタクトプラス、ベトノバールＳは、皮膚の炎症とかゆみをしっかり抑える目的で使います。広範囲や顔、ジュクジュクする所は注意し、改善しなければ受診を。

### physical-symptom-16 — physical (PASS)
- session_id: `1782840111075744107115`
- wave: 1b
#### Turn 1
- **User**: 湿疹が出ました
- **Bot** (`unknown`, 49328ms):

湿疹が出てつらいですね。かゆみや赤みがある湿疹には、外用のメンソレータムメディクイッククリームS／プロクリームが使いやすいです。まずは薄く塗り、こすらず清潔・保湿を心がけてください。広がる、膿む、顔や目の周りに出る、数日でよくならない時は受診をおすすめします。

### physical-symptom-17 — physical (REVIEW)
- session_id: `1782840162210863572224`
- wave: 1b
#### Turn 1
- **User**: 口内炎が痛い
- **Bot** (`unknown`, 42325ms):

口内炎が痛いのはつらいですね。キップパイロール-Hiは患部を保護しつつ炎症を和らげ、オリブ油「タイセイ」Pは口内の乾燥や刺激をやさしく守ります。クールスロートはのどの痛みもある時に使いやすいです。食事はしみる物を避け、長引く・悪化する場合は受診してください。

### physical-symptom-18 — physical (PASS)
- session_id: `1782840206380577266515`
- wave: 1b
#### Turn 1
- **User**: 筋肉痛です
- **Bot** (`unknown`, 52603ms):

筋肉痛でつらいですね。サロンパス30は、痛む部分に直接貼れて、筋肉のこわばりや張りを和らげやすいので、今回のような筋肉痛に使いやすいです。かぶれや傷のある所は避け、強い痛み・腫れ・熱感がある、発熱やインフルエンザが疑われる場合は受診してください。

