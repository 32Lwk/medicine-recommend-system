# LLM ロールバック手順

本番で LLM 変更（GPT-5 / Responses API / カナリア）に問題が出た場合の切り戻し手順です。

## 即時切り戻し（環境変数）

Cloud Run の環境変数を更新し、新リビジョンをデプロイします。

| 目的 | 変数 | 切り戻し値 |
|------|------|------------|
| モデル全体を従来に戻す | `LLM_MODEL_PROFILE` | `legacy` |
| Responses API を止める | `OPENAI_USE_RESPONSES_API` | `false` |
| カナリアを止める | `LLM_CANARY_PERCENT` | `0` |
| エージェント経路を止める | `LLM_AGENT_ENABLED` | `false` |
| GPT 推奨フォールバック（本番は通常 OFF） | `LLM_GPT_RECOMMEND_FALLBACK` | `false` |

推奨の最小セット:

```bash
LLM_MODEL_PROFILE=legacy
OPENAI_USE_RESPONSES_API=false
LLM_CANARY_PERCENT=0
LLM_AGENT_ENABLED=false
```

## 予算ブロック時

月額上限（`OPENAI_MONTHLY_BUDGET_JPY`）到達後は `budget_guard` が LLM 呼び出しを拒否します。
復旧には翌月のリセット、または管理画面／DB で `global_state` の月次コストを確認・調整してください。

## コード経路の確認

- すべての OpenAI 呼び出しは `src/core/llm_client.py` 経由であること
- 推奨ランキングの真実源は `rule_based_medicine_recommendation` のみ（`src/agents/tools/recommendation_tool.py`）
- AI 自動応答 OFF 時は `chat_manual_reply` がトリアージメタデータのみ保存

## 検証

```bash
py -3.13 -m pytest tests/test_llm_phase0.py tests/test_llm_phase1.py tests/test_llm_phase2.py -q
```

## 関連ファイル

- `config/llm_config.py` — モデルプロファイル
- `config/llm_flags.py` — 機能フラグ
- `config/llm_canary.py` — カナリア割合
- `src/services/budget_guard.py` — 月額ガード
