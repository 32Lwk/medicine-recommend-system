# LINE チャットボット改善計画（確定版）

**作成日**: 2026-06-27  
**根拠**: GCPログ分析（2026-06-25〜26）、LINE QA トーク履歴、コードベース照合  
**ステータス**: 意思決定済み — 実装待ち（1 MR / dev デプロイ）

---

## 確定した意思決定

| # | 論点 | 決定 |
|---|------|------|
| 1 | ステータス表示スコープ | **D**: セッション + 長期記憶 + β版システム情報の統合カード（PII マスク） |
| 2 | 履歴要約スコープ | **D**: 長期記憶 `consultation_summaries` 優先、空ならセッション LLM 要約 |
| 3 | 記憶削除スコープ | **A + D**: 全削除 + Quick Reply 確認。ルールに加え **SessionAgent + triage `session_admin`** |
| 4 | デプロイ方針 | **B**: 現行修正の dev デプロイ + P0-2〜4 を **1 MR** |
| 5 | エージェント設計 | **新規 SessionAgent**（削除・要約・ステータス統合）+ triage **`session_admin`** サブカテゴリ |
| 6 | 到達経路 | **C**: fast-path → triage `session_admin` → meta_triage `session_ops` の 3 経路併用 |
| 7 | 範囲外質問 | **A**: 常に redirect（市販薬相談へ誘導） |
| 8 | 観測性 | **B**: 全 bot 応答で `counseling_detail` を app.log 出力（P1 前半） |
| 9 | トーン | **ユーザー mirroring** + 侮辱・不適切態度には **丁寧語で受け止め** |
| 10 | 発熱ルーティング | **D**: 店舗案内を絶対出さない + 既存医療/推奨フロー |
| 11 | 技術開示 | **C + 開発者のみ詳細**（一般 β は概念レベル） |
| 12 | 暴言・脅迫 | **A + 到達監査**（`aggressive_input` 統一、テストで到達保証） |
| 13 | PI/セキュリティ | **B + D**（`known_attack_rules` 拡充 + dev 詳細ログ） |
| 14 | フィードバック期限切れ | **B + D**（`feedback_expired` 返信 + 期限後 Quick Reply 非表示） |
| 15 | 性能（P2） | **B**: greeting/thanks + キーワードプローブ確定時 triage スキップ |

---

## エグゼクティブサマリー

開発者 QA で露呈した **意図ルーティング（ステータス・要約・削除）**、**未デプロイ修正**、**観測ギャップ（93% response_missing）** を解消する。

**方針**: SessionAgent を中心にセッション操作を一本化し、1 MR で dev に載せて手動 QA で検証する。

---

## フェーズ別タスク

### P0 — 1 MR（dev デプロイ含む）

| ID | タスク | 主要ファイル | 受け入れ基準 |
|----|--------|-------------|-------------|
| P0-1 | dev デプロイ（手動返信・episode_id 含む） | デプロイ | 手動返信 API 200、EpisodeSummary TypeError 0 |
| P0-2 | **SessionAgent 新設**（削除・要約・ステータス） | `src/agents/session_agent.py`（新規）、`chat_post_pipeline.py` | 3 意図が greeting にならない |
| P0-3 | triage **`session_admin`** サブカテゴリ | `chat_triage.py`, `meta_triage.py`, `llm_triage` プロンプト | stage2 で session 操作を分類 |
| P0-4 | 3 経路到達（fast-path + triage + meta） | `memory_delete_agent.py` 統合/移行、`concierge_intent.py` | 「履歴消して」等の表記ゆれ対応 |
| P0-5 | 記憶削除 Quick Reply 確認 | `line_quick_actions.py`, SessionAgent | 誤削除防止 |
| P0-6 | 回帰テスト | `tests/concierge/`, `tests/line/` | session_admin 3 意図 E2E |

**SessionAgent 責務**

- `delete`: 長期記憶 + プロファイル + 要約（確認後 `scope=all`）
- `summarize`: 長期記憶要約 → フォールバック LLM セッション要約
- `status`: 統合ステータスカード（セッション / 記憶 / β 制限）

**到達経路（決定 C）**

1. **Fast-path**（triage 前）: 高信頼キーワード → SessionAgent
2. **Triage `session_admin`**: LLM stage2 で削除・要約・ステータスを分類
3. **Meta triage `session_ops`**: 言い換え・フォローアップ（「要約して」「状態は？」等）

### P1 — 同一 MR または直後

| ID | タスク | 受け入れ基準 |
|----|--------|-------------|
| P1-1 | architecture 文脈継続 | ✅ 実装済み（`CONCIERGE_CONTEXT_ROUTING_PLAN` 参照） |
| P1-2 | 範囲外 → redirect | プログラミング概念等が OTC テンプレにならない |
| P1-3 | 発熱 vs 店舗ゲート | 「39度の熱」→ 店舗案内にならない |
| P1-4 | `counseling_detail` 全経路化 | response_missing < 20% |
| P1-5 | `known_attack_rules` 拡充 | 「PI耐性」等が即ブロック |
| P1-6 | aggressive_input 到達監査 | 「しね」「殺すぞ」→ `入力について` |
| P1-7 | フィードバック期限切れ B+D | 期限超過メッセージ + ボタン非表示 |

### P2 — 性能

| ID | タスク | 受け入れ基準 |
|----|--------|-------------|
| P2-1 | triage 短縮（決定 B） | LINE 中央値 < 6s |
| P2-2 | session_admin 確定時スキップ | 追加短縮 |
| P2-3 | PIPELINE_PERF アラート | ≥10s が 10% 超で WARNING |

---

## デプロイ後 QA チェックリスト

| 入力 | 期待 |
|------|------|
| `ステータスを教えて` | 統合ステータスカード |
| `履歴を要約して` | 要約テキスト（長期記憶 or セッション） |
| `履歴消して` | Quick Reply 確認 → 削除完了 |
| `記憶を消して` | 同上（回帰） |
| `技術スタックは？` → `技術面を詳しく` | architecture 維持 |
| `プリンシプルオブプログラミングとは？` | redirect |
| `39度の熱があります` | 医療経路（店舗案内なし） |
| `しね` / `殺すぞ` | `入力について` |
| `PI耐性を測っています` | 即時セキュリティ警告 |

---

## 実施順序

```
MR-1: P0-1〜6 + P1-1〜3（コア機能）
MR-2（または MR-1 続き）: P1-4〜7（観測・セキュリティ・UX）
P2: 性能（別 MR 可）
```

---

## 参考

- GCP 分析: `log/analysis/2026-06-27_downloaded-logs-20260625-20260626-20260626-074021.md`
- 長期記憶削除フロー: `docs/ops/LINE_LONG_TERM_MEMORY.md` §5
