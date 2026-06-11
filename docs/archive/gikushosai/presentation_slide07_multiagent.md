# スライド07 — マルチエージェント（正本ラベル）

`docs/dev/ARCHITECTURE_MULTI_AGENT.md` / `ChatOrchestrator` に準拠。画像内の日本語は誤字があり得るため、本番は PowerPoint で下表のラベルを優先すること。

## 処理の流れ

1. `POST /api/chat` → `chat_post_pipeline`
2. **TriageAgent** — キーワード前置 + LLM + キャッシュ（5分類）
3. **SafetyGate** — 診断名・不適切・緊急の決定的チェック
4. **ChatOrchestrator** — `resolve_handoff` 後の専門経路

## 5分類とハンドオフ

| category | ハンドオフ先 | 補足 |
|----------|-------------|------|
| Physical | PhysicalOrchestrator | NLUAgent / ExplanationAgent（SSE `cards`→`explanations`） |
| Emotional | CounselingManager | confidence ≥ 0.5 |
| Emergency | EmergencyRouter → dispatch | フォールスルー禁止・手動キュー |
| Ask | AskHandler | 再振り分けで Physical へ遷移可 |
| Other | ConciergeAgent → StoreInquiryAgent | 挨拶・店舗案内 |

## EmergencyRouter サブタイプ（slide07-D 向け）

| subtype | 方針 |
|---------|------|
| crisis_language | 推奨停止 |
| medical_self | OTCハードロック・119明示 |
| store_incident | ソフトバナー |

## スライド案の使い分け

| ファイル | 構成 |
|----------|------|
| `slide07-multiagent-A` | ハブ型（TriageAgent 中心） |
| `slide07-multiagent-B` | 分岐フロー（B.png レイアウト・クラス名正本） |
| `slide07-multiagent-C` | パイプライン（`LLM_AGENT_ENABLED` 注記） |
| `slide07-multiagent-D` | 緊急3分岐の拡大 |
| `slide07-multiagent-E` | 9エージェント協調（ChatOrchestrator ハブ） |
