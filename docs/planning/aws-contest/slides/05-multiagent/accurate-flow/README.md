# 会話の振り分け — 正本準拠スライド（5パターン）

**参考レイアウト**: ユーザー提供の `07 | 会話の振り分け（全体フロー）`  
**正本**: [`docs/dev/ARCHITECTURE_MULTI_AGENT.md`](../../../../dev/ARCHITECTURE_MULTI_AGENT.md)  
**v2 実装**: [`src/dialogue/dispatcher.py`](../../../../../src/dialogue/dispatcher.py)

## 好みスライドからの修正点（正本との差）

| 項目 | 参考画像 | 正本 |
|------|---------|------|
| Triage 5分類 | Concierge | **Other**（窓口は ConciergeAgent） |
| IntentRouter | 「本線に影響せず」のみ | shadow **記録** + dispatch ON 時は **AgentDispatcher が本線** |
| Ask | 独立 Q&A | Triage **Ask** → AskAgent。v2 では Physical/**medicine_qa** 等も |
| フォールバック | なし | dispatch 未処理 → **ChatOrchestrator** → legacy category route |
| SafetyGate | 1段 | **pre / post** の2段 |

## 5パターン

| ファイル | 用途 | 内容 |
|---------|------|------|
| `accurate-flow-E-reference-style.png` | **本番推奨** | 好みレイアウト + 正本ラベル（Other・fallback 記載） |
| `accurate-flow-A-overall.png` | 全体像 | 5ステップ + 5分類→担当エージェント対応表 |
| `accurate-flow-B-two-layer.png` | 技術詳細 | Triage 5分類 × IntentRouter 8 primary_route |
| `accurate-flow-C-physical.png` | Physical 深掘り | Orchestrator → NLU → rule_based → SSE |
| `accurate-flow-D-emergency.png` | Emergency 深掘り | 3 subtype + 手動キュー |

## 正本フロー（口頭30秒）

1. **SafetyGate pre** — 入力検証・診断名・不適切  
2. **SessionOps fast-path** — 削除/ステータス（該当時スキップ）  
3. **TriageAgent** — Physical / Ask / Emotional / Emergency / **Other**  
4. **SafetyGate post** — 緊急・不適切の再チェック  
5. **IntentRouter shadow** — Stage A gate → B LLM → C guards、shadow 記録  
6. **AgentDispatcher** — primary_route → 専門ハンドラ（v2 dispatch ON）  
7. **ChatOrchestrator / legacy** — 未処理時フォールバック  

## 5分類 → 担当（スライド下部カード）

| Triage | 担当 | 一言 |
|--------|------|------|
| Physical | PhysicalOrchestrator | ルールベース選薬・NLU |
| Ask | AskAgent | 推奨後の医薬品 Q&A |
| Emotional | CounselingManager | カウンセリング |
| Emergency | dispatch_emergency | 119・手動キュー（フォールスルー禁止） |
| Other | ConciergeAgent | 挨拶・案内（StoreInquiry 等） |

## IntentRouter primary_route（8種・B 参照）

Physical / SessionOps / Concierge / Emergency / Security / Store / Counseling / Unknown

## 本番前チェック

- [ ] 日本語誤字目視（AI生成）
- [ ] QR を実 URL に差し替え
- [ ] スライド番号（07/08）を PDF 全体と整合
- [ ] β版免責を必要なら追加

## スピーカーノート（E 向け）

> まず SafetyGate で安全確認し、TriageAgent が5種類に分類します。v2 では IntentRouter が意図を shadow 記録し、AgentDispatcher が Physical ならルールベース選薬、Other なら Concierge が案内します。Emergency は119案内でフォールスルーしません。薬選びはルールベース、LLM は NLU と説明だけです。
