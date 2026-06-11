# エージェント経路 LLM 重複監査

| 経路 | 重複リスク | 対策 |
|------|------------|------|
| `chat_post_pipeline` | triage 1回/POST | Orchestrator 有効時は `route_triage_category` / `try_agent_pipeline` をスキップ |
| `chat_confidence_route` | 再 triage なし | 既存 `triage_result` の confidence のみ参照 |
| `chat_question_route` | llm_triage 直呼びなし | question フローは triage 結果を再利用 |

目標: 1 POST あたり `llm_triage` / `run_triage_agent` は原則 1 回。
