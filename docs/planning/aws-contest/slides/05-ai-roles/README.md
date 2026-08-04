# AI の役割分担 — スライド5統合版 & 独立版（各5パターン）

**正本**: [`04-aws-tech-story.md`](../../04-aws-tech-story.md) §AIの使い方  
**デッキ**: [`02-presentation-deck.md`](../../02-presentation-deck.md) スライド5

## 正本メッセージ（両セット共通）

| 領域 | 技術 | 薬名決定 |
|------|------|----------|
| **薬選定** | ルールベース + CSV（PhysicalOrchestrator） | **ここで決定** |
| **会話** | LLM（NLU・振り分け・説明・Concierge） | 決定しない |
| **知識** | RAG（Bedrock KB / Local RAG）— FAQ・案内 | 決定しない（OTCランキング非使用） |

**原則**: LLM は薬名を自由創作しない。

---

## A. スライド5 統合版（`integrated/`）

ソリューション slide05 を **差し替え**。5分枠では **D または A** 推奨。

| ファイル | レイアウト |
|---------|-----------|
| `integrated-05-A-three-columns.png` | 3カラム + 機能 bullet |
| `integrated-05-B-pipeline.png` | 横パイプライン ①②③ |
| `integrated-05-C-table.png` | 表（薬名決定列付き） |
| `integrated-05-D-minimal.png` | 大見出し1行 + 3カード（**時間短**） |
| `integrated-05-E-split.png` | 左3層 + 右マルチエージェント |

---

## B. 独立版 5+（`standalone/`）

**05 と 06（AWS）の間**に挿入。予備・質疑用に **B または A** 推奨。

| ファイル | レイアウト |
|---------|-----------|
| `standalone-5plus-A-three-columns.png` | 3カラム詳細（**本番独立推奨**） |
| `standalone-5plus-B-wrong-vs-right.png` | 全部LLM ✗ vs 役割分担 ○ |
| `standalone-5plus-C-layers.png` | 3層レイヤー図 |
| `standalone-5plus-D-detailed-table.png` | 詳細表（質疑用） |
| `standalone-5plus-E-examples.png` | 例示3つ（喉の痛み/説明/FAQ） |

---

## PDF 構成案

### 5分・枚数厳守

| page | 内容 |
|------|------|
| 5 | **integrated/** から1枚（D 推奨） |
| 6 | AWS構成（独立版は**使わない**） |

### 質疑・技術深掘りあり

| page | 内容 |
|------|------|
| 5 | integrated A または C |
| **5+** | standalone A または B |
| 6 | AWS構成 |

---

## スピーカーノート

**統合版（20秒）**

> 薬の候補はルールベースだけが決めます。LLM は会話の理解と説明、RAG は FAQ 案内です。全部 AI に任せず、安全のために役割を分けています。

**独立版（25秒）**

> 独立スライドで補足します。OTC ランキングに RAG も LLM も使いません。Bedrock KB は Concierge の技術 Q&A 試験用です。ハルシネーションを抑える設計です。

---

## 本番前チェック

- [ ] 日本語誤字目視
- [ ] QR 実 URL 差し替え
- [ ] 「RAGで薬を選ぶ」と誤解されないか口頭で補足
- [ ] 統合+独立の**両方**を入れると +20〜25秒 — 5分 rehearsal で確認
