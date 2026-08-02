# マルチエージェント — PDF続きスタイル（5パターン）

**参考**: `症状に合った医薬品を チャットでやさしくご案内.pdf`（page7 AWS構成の**直後**に挿入）

**正本**: [`docs/dev/ARCHITECTURE_MULTI_AGENT.md`](../../../../dev/ARCHITECTURE_MULTI_AGENT.md)

## デザイン（PDF準拠）

| 要素 | 値 |
|------|-----|
| メイン背景 | オフホワイト・ベージュ `#f0ebe3` 付近 |
| 右サイドバー | タン/ベージュ縦帯 + **縦書きタイトル**（明朝系） |
| QR / URL | 右下 `aws.medicine.yutok.dev` |
| アクセント | フォレストグリーン（図・見出し） |
| 比率 | 16:9 |

※ 旧 `05-multiagent-A〜E.png`（セージグリーン和風）は [`../`](../) 直下。本フォルダは **PDF Canva 系**。

## 載せた内容（v2 詳細版）

1. **SafetyGate** — 入力安全チェック（pre/post）
2. **TriageAgent** — 5分類（Physical / Ask / Emotional / Emergency / Other）
3. **Chat Pipeline v2** — IntentRouter shadow → **AgentDispatcher**
4. **専門エージェント** — PhysicalOrchestrator / ConciergeAgent 等
5. **原則** — 薬選びはルールベース、LLM は NLU・説明のみ

## バリエーション

| ファイル | サイドバー縦書き | レイアウト | 向き |
|---------|----------------|-----------|------|
| `05-multiagent-pdf-A.png` | マルチエージェント | ハブ型（Triage 中心・5分岐） | 全体像 |
| `05-multiagent-pdf-B.png` | 会話の振り分け | 縦パイプライン（v2 含む） | 処理順・口頭説明 |
| `05-multiagent-pdf-C.png` | 役割分担 | Physical vs Concierge 2柱 | 審査・対比 |
| `05-multiagent-pdf-D.png` | 振り分けの例 | 具体例3つ | 聴衆イメージ |
| `05-multiagent-pdf-E.png` | 仕組み | 一覧表 + v2 ミニ図 | 質疑・整理 |

## PDF への挿入順（案）

| page | 内容 |
|------|------|
| 1–6 | 既存 PDF |
| 7 | AWS構成 |
| **8** | 本スライドいずれか 1 枚（推奨: **B** または **A**） |
| 9+ | まとめ・QR 等 |

## 本番前チェック

- [ ] 日本語誤字の目視確認（AI生成）
- [ ] QR を実 URL の QR に差し替え（Canva / Slides）
- [ ] `IntentRouter shadow` / `AgentDispatcher` の表記を正本ドキュメントと照合
- [ ] Emergency サブタイプ（crisis / medical / store）を載せる場合は別スライドで拡大

## スピーカーノート（約30秒・B 向け）

> ユーザー発話はまず SafetyGate で安全確認し、TriageAgent が5種類に分類します。v2 では IntentRouter が意図を shadow 記録し、AgentDispatcher が Physical ならルールベース選薬、Other なら Concierge が案内します。薬名を LLM が創作しない設計です。
