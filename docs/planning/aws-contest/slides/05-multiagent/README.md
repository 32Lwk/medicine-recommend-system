# マルチエージェント構成・振り分け（5パターン）

正本: [`docs/dev/ARCHITECTURE_MULTI_AGENT.md`](../../../dev/ARCHITECTURE_MULTI_AGENT.md)

## スライドに載せる要点（5分発表向け・簡潔版）

1. **入口**: SafetyGate（安全）→ TriageAgent（5分類）
2. **振り分け**: 会話の種類ごとに専門エージェントへ
3. **中核**: 症状は PhysicalOrchestrator（**ルールベース選薬**）、案内は ConciergeAgent
4. **緊急**: Emergency はフォールスルー禁止（119・手動キュー）
5. **LLM の役割**: NLU・説明のみ（薬名の創作なし）

## 5分類

| category | 担当 | 一言 |
|----------|------|------|
| Physical | PhysicalOrchestrator | 症状 → OTC候補 |
| Ask | AskAgent | 推奨後の医薬品Q&A |
| Emotional | CounselingManager | カウンセリング |
| Emergency | EmergencyRouter | 119・受診案内 |
| Other | ConciergeAgent | 挨拶・構成説明 |

## バリエーション

| ファイル | レイアウト | 向いている場面 |
|---------|-----------|---------------|
| `05-multiagent-A.png` | ハブ型（Triage中心） | 全体像を一画面で |
| `05-multiagent-B.png` | 縦パイプライン | 処理順序を説明 |
| `05-multiagent-C.png` | 2柱比較（Physical vs Concierge） | 審査向け・役割の対比 |
| `05-multiagent-D.png` | 具体例3つ | 聴衆へのイメージ共有 |
| `05-multiagent-E.png` | 一覧表 + ミニ図 | 情報整理・質疑応答用 |

## デッキへの挿入案

- 現行 [`02-presentation-deck.md`](../../02-presentation-deck.md) スライド5（ソリューション）の直後、またはスライド5を分割
- 想定時間: **30〜40秒**（D または C が口頭と相性良い）

## 本番前チェック

- [ ] 日本語誤字の目視確認
- [ ] v2（IntentRouter / AgentDispatcher）まで載せるか要判断 — 本セットは **簡潔版**（v2 省略）
- [ ] 採用版を Slides に取り込み

## 未反映（詳細版に載せる場合）

- Chat Pipeline v2: IntentRouter shadow → AgentDispatcher
- Emergency サブタイプ: crisis_language / medical_self / store_incident
- SSE: cards → explanations の2段応答
