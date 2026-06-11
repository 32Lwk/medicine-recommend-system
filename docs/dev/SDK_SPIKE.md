# OpenAI SDK スパイク結果（P0-06）

## 環境

- `openai==1.54.0`（`requirements.txt`）
- Python 3.13 で検証

## 確認項目

| API | 利用可否 | 本プロジェクトでの採用 |
|-----|----------|----------------------|
| `client.chat.completions.create` | 可 | フォールバック経路（`llm_client` 内） |
| `client.responses.create` | 可 | `OPENAI_USE_RESPONSES_API=true` 時 |
| OpenAI Agents SDK (`openai-agents`) | 未導入 | **ハイブリッド**: コードオーケストレーション + `src/agents/*` ラッパ |

## 結論

- Responses API は SDK 1.54 で利用可能。`src/core/llm_client.py` で Completions 互換アダプタを実装済み。
- Agents SDK は本番依存にせず、`ChatPipeline` + `protocols` + deterministic tools で同等の handoff を実現（計画のハイブリッド方針）。
- SDK メジャー更新時は `tests/llm/test_llm_phase0.py`〜`phase3.py` を先に実行すること。
