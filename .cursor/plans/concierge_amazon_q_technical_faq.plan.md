---
name: Concierge Amazon Q 型 技術 FAQ
overview: 医薬品相談ツールの本分（症状→市販薬案内）を維持しつつ、Concierge 経路で IT・アーキテクチャ・クロスクラウド・運用構成への質問に Amazon Q 相当の「根拠付き深掘り回答」を提供する。ナレッジ SSOT + RAG + 深掘り生成 + 境界ガードの 4 層で段階実装。
todos:
  - id: q0-decisions
    content: "Phase Q0 完了: mixed/全チャネル/OpenAI先行/開示=公開情報OK+深掘りは聞かれたとき+envメタ禁止"
    status: completed
  - id: q1-ssot-docs
    content: "Phase Q1: 技術ナレッジ SSOT 拡充（docs/concierge/technical/ + ops 同期）と CHANGELOG 連携ルール"
    status: in_progress
  - id: q1-local-rag
    content: "Phase Q1: ローカル tech reference（concierge_tech_reference.py）本番反映・architecture 深掘りモード"
    status: in_progress
  - id: q2-bedrock-kb
    content: "Phase Q2（Support 解消後）: Bedrock KB ingestion → sync 全量 → retrieve 検証（生成は OpenAI のまま）"
    status: pending
  - id: q2-hybrid-rag
    content: "Phase Q2（Support 解消後）: KB ベクトル検索をローカル参照に追加"
    status: pending
  - id: q3-runtime-tools
    content: "Phase Q3: ランタイム参照（/health/aws, git_commit — 秘匿除外）"
    status: pending
  - id: q3-eval-suite
    content: "Phase Q3: 技術 FAQ 評価 YAML 20–40 問"
    status: pending
  - id: q4-ui-deep-card
    content: "Phase Q4: 深掘り UI（LINE は詳しく聞かれたら medium・通常は概要）"
    status: pending
  - id: q4-guardrails
    content: "Phase Q4: プロンプト二重防御（Support 前）→ Bedrock Guardrails（Support 後）"
    status: pending
  - id: q5-optional-agents
    content: "Phase Q5（任意）: Bedrock Agents + Lambda ツール（KB 再検索・CHANGELOG 差分・デプロイ状態）"
    status: pending
isProject: false
---

# Concierge「Amazon Q 型」技術 FAQ 改善計画

**作成日**: 2026-07-23（Q0 回答反映: 2026-07-23）  
**関連**: [aws_cloudflare 一括改善](aws_cloudflare_一括改善_afd2b593.plan.md) / [AWS_FEATURES_ROLLOUT.md](../docs/ops/AWS_FEATURES_ROLLOUT.md)

---

## 0. Phase Q0 確定事項（ユーザー回答 2026-07-23）

| 項目 | 決定 |
|------|------|
| **読者** | **mixed** — 開発者・企業関係者・薬剤師・β 利用者すべて。チャネルで深さを調整 |
| **チャネル** | **全て** — GCP Web / AWS Web / LINE / admin_chat |
| **生成 LLM** | **C（段階的）** — **当面 OpenAI のみ**。Bedrock Converse は Support 解消・クォータ後に AWS 試験。**RAG 品質は OpenAI/Bedrock で同等**のため KB ingestion は Support 後 |
| **深さ** | **中** — ~1500 字・Sage カード 2–3 セクション（現 deep モード想定） |
| **Bedrock 方針** | Support 対応**前**に Bedrock 依存作業は行わない。Support 後に ingestion / ハイブリッド RAG / Guardrails / Converse 試験 |

### 推奨優先順位（Support 非依存 → 依存）

ユーザー質問「どうすべき？」への回答:

| 順位 | フェーズ | 理由 |
|------|----------|------|
| **1** | **Q1 SSOT + ローカル RAG の deploy** | Bedrock 不要。Amazon Q の「根拠付き回答」の 80% は **ドキュメント SSOT + プロンプト** で達成 |
| **2** | **Q1 SSOT 拡充（04–07 doc）** | 回答精度の上限はナレッジ品質。コードより doc 投資が効く |
| **3** | **Q3 評価セット 20 問** | 回 regressions 防止。手動 10 問 → YAML 自動化 |
| **4** | **Q3 ランタイム参照**（/health/aws, git_commit） | 「今のデプロイは？」系を facts で grounded |
| **5** | **Q4 UI**（多セクションカード・ソース表示） | mixed 読者向け可読性。medium 深さと整合 |
| **6** | **Q4 チャネル別深さ** | LINE=短め要約、admin=深め、Web=medium |
| **7** | **Q4 開示ポリシー** | 公開情報 OK / 深掘りは聞かれたとき / **env 読取に見えない出力**（§0.1） |

### 0.1 開示ポリシー（2026-07-23 確定）

| ルール | 内容 |
|--------|------|
| **言及可** | **公開されている情報はすべて**（URL、公開構成、/health の commit、ベンダー名、ops ドキュメントに載る ID 等） |
| **深さ** | **聞かれたときだけ深く** — 初回 architecture は概要。`wants_technical_deep_dive()` 時のみ medium |
| **見せ方** | **env を読んでいるように見せない** — 環境変数名・「設定を参照した」メタ禁止。事実は利用者向け文言（SSOT: [00-disclosure-policy.md](../docs/concierge/technical/00-disclosure-policy.md)） |
| **内部利用** | Phase Q3 の `/health/aws` 等はプロンプト補助のみ。ユーザー向けに API 名を出さない |
| **GitHub** | **公開リポジトリ** — URL・commit hash 言及 OK |
| **LINE 深さ** | 通常短め。**「詳しく」等があれば medium まで OK**（Web と同 deep トリガー） |
| **多言語** | **問い合わせ言語に合わせる** — `concierge_i18n.py`（GCP DeepL / AWS Translate） |
| **UI ソース** | 深掘り時のみセクション見出し + 「公開情報に基づく案内」ヒント（ドキュメント名は非表示） |
| **LINE 長文** | Flex 上限で切り詰め + Web 誘導 |
| **KB 未同期** | AWS ステージング architecture に **常に脚注**（全文同期準備中） |
| **目標日** | **なし** — Q1→Q3 を順次 |

---
| **—** | **Q5 Agents / コード索引** | 需要見てから |

---

## 1. ゴール定義

### Amazon Q から借りるもの（本プロダクト向けに再定義）

| Amazon Q の強み | 本アプリでの目標 |
|----------------|-----------------|
| 社内ドキュメントに grounded した回答 | `docs/concierge/technical/` + ops + CHANGELOG を **唯一の根拠** とする |
| フォローアップで深掘り | 「詳しく」「デプロイは？」→ **深掘りモード**（長文・多参照） |
| インフラ・運用の横断説明 | **クロスクラウド**（GCP 本番 / AWS ステージング / Cloudflare R2 / LINE）を正確に区別 |
| わからないときは推測しない | 「参照にない内容は不明と述べる」— hallucination 禁止をテストで担保 |

### 借りないもの（スコープ外または後回し）

- AWS コンソール操作の代行（IAM ポリシー編集等）
- リポジトリ全コードのセマンティック検索（Phase Q5 以降の検討）
- 医薬品推奨ロジックの LLM 化（**ルールベース維持**）

### 本分の維持（不変条件）

```
ユーザー入力
    │
    ├─ 症状・薬・用法 ──► PhysicalOrchestrator（ルールベース推奨）
    │
    └─ 挨拶 / IT / 更新 / 店舗 ──► ConciergeAgent（本計画の対象）
```

- Concierge は **案内役**。診断・処方・症状への具体助言はしない。
- 技術 FAQ に詳述しても、症状キーワードが主目的なら Physical 経路を優先（既存 IntentRouter）。

---

## 2. 現状（2026-07-23）

### 実装済み

| 項目 | 状態 |
|------|------|
| Concierge intent `architecture` / `doc_changelog` | 稼働 |
| `concierge_knowledge.ja.json` + about tech_bullets | GCP 向け抽象説明 |
| AWS ステージング参照ブロック（ECS/Translate/Polly 等） | `concierge_agent.py` |
| Bedrock KB retrieve + Redis キャッシュ | コード済み |
| **ローカル tech docs**（3 ファイル） | ローカル未 push あり |
| **concierge_tech_reference.py** + 深掘りモード | ローカル未 push あり |
| CodeBuild smoke（Translate/Polly/health） | `215a7eb` |

### ブロッカー

| 項目 | 影響 |
|------|------|
| **Bedrock Titan Embed 429** / Support 待ち | KB ingestion 0 件 → **ベクトル RAG が空** |
| 技術 doc が thin | Amazon Q 相当の「調べ上げ」には **SSOT 拡充が必須** |
| architecture 通常モードは 2–6 文 | 浅い質問には十分、IT 詳問には不足（深掘りで緩和） |

---

## 3. 目標アーキテクチャ

```mermaid
flowchart TB
  subgraph input [ユーザー]
    U[技術質問 / 更新履歴 / 症状]
  end

  subgraph route [IntentRouter]
    IR{分類}
  end

  subgraph concierge [ConciergeAgent]
    INT[intent: architecture / doc_changelog]
    REF[参照組み立て]
    GEN[LLM 生成 OpenAI または Bedrock]
    CARD[Sage カード]
  end

  subgraph knowledge [ナレッジ層]
    SSOT[docs/concierge/technical/]
    OPS[docs/ops/*.md]
    CL[CHANGELOG digest]
    KB[Bedrock KB retrieve]
    RT[/health/aws 等]
  end

  U --> IR
  IR -->|症状| PHY[PhysicalOrchestrator]
  IR -->|IT/更新| INT
  INT --> REF
  SSOT --> REF
  OPS --> REF
  CL --> REF
  KB --> REF
  RT --> REF
  REF --> GEN --> CARD
```

### 参照の優先順位（ハルシネーション抑制）

1. **ローカル SSOT**（`docs/concierge/technical/`）— 常に architecture で注入
2. **CHANGELOG digest** — 深掘り / doc_changelog
3. **Bedrock KB chunks** — ingestion 成功後、クエリ類似度 top-k
4. **ランタイムスナップショット** — git_commit・feature flags（秘匿除外）
5. **LLM 一般知識** — **使用禁止**（プロンプトで明示）

---

## 4. フェーズ計画

### Phase Q0 — 意思決定 ✅ 完了（残: 公開情報ホワイトリスト）

2026-07-23 回答済み（上記 §0）。**未回答**: 公開してよい情報の下限（アカウント ID・Support ケース ID 等）— 全チャネル公開のため **次回確認推奨**。

**出口条件**: 公開情報ホワイトリスト草案（1 ページ）

---

### Phase Q1 — ナレッジ SSOT + ローカル grounded 回答（**2–3 週間相当**）

**目的**: Bedrock 無しでも GCP/AWS 双方で正確な技術 FAQ。

| タスク | 詳細 |
|--------|------|
| Q1-a SSOT 拡充 | 追加 doc 案: `04-data-security.md`, `05-chat-pipeline-v2-flags.md`, `06-line-gcp-path.md`, `07-observability-ops.md` |
| Q1-b 同期 | [sync-concierge-kb-to-s3.sh](../scripts/sync-concierge-kb-to-s3.sh) — technical + ops + CHANGELOG（実装済み、運用化） |
| Q1-c コード反映 | [concierge_tech_reference.py](../src/content/concierge_tech_reference.py) + [concierge_agent.py](../src/agents/concierge_agent.py) 深掘り — **commit & deploy** |
| Q1-d intent 拡張 | AWS/GCP/Cloudflare キーワード（実装済み）+ 必要なら `doc_technical` 分離 |
| Q1-e 運用ルール | **インフラ変更時は SSOT 更新 → KB sync を同一 PR** に含める |

**出口条件**:

- 代表 10 問（下記）で手動 smoke PASS
- `tests/content/test_concierge_tech_reference.py` CI green

**代表 10 問（評価の種）**

1. GCP 本番と AWS ステージングの違いは？
2. CodePipeline のデプロイフローを教えて
3. 市販薬推奨は LLM？ ルールベース？
4. 画像 CDN はどこ？（R2）
5. Bedrock KB は何のため？ 今動いている？
6. LINE はどのクラウド？
7. セッションデータの保存先は？
8. 最近の AWS 関連更新は？（doc_changelog）
9. SSE とはこのアプリでは何に使う？
10. マルチエージェントの役割分担は？

---

### Phase Q2 — Bedrock KB RAG（**Support 解消後のみ**）

> **方針**: 生成は OpenAI のまま。Bedrock は **retrieve のみ** 追加。Support 前に本フェーズの作業は行わない。

**目的**: 質問に応じたチャンク取得（Amazon Q の検索層の強化）。

| タスク | 詳細 |
|--------|------|
| Q2-a クォータ | Support ケース 178479394100149 等フォロー |
| Q2-b ingestion | `sync-concierge-kb-to-s3.sh` → `sync-aws-bedrock-kb-ingestion.sh` |
| Q2-c ハイブリッド | ローカル全文（architecture 基礎）+ KB top-5（質問特化）をプロンプトに併記 |
| Q2-d 再ランク | 低スコア chunk は捨てる閾値（score < 0.4 等）— ノイズ抑制 |
| Q2-e キャッシュ | Redis TTL 600s（実装済み）— 同一 FAQ のコスト削減 |

**出口条件**:

- ingestion job SUCCESS ≥ 1
- 代表 10 問で KB provider=`bedrock_kb` ログ確認
- KB 空時は Q1 ローカル参照にフォールバック（既存）

---

### Phase Q3 — ランタイム参照 + 自動評価（**1–2 週間**）

**目的**: 「今デプロイされている版は？」「Translate は ON？」等の事実確認。

| タスク | 詳細 |
|--------|------|
| Q3-a Runtime snapshot | `/health` + `/health/aws` を Concierge 参照に注入（アカウント ID・シークレット名は **除外**） |
| Q3-b 評価 YAML | `tests/scenarios/concierge_technical_faq.yaml` — 20–40 問 |
| Q3-c 自動採点 | 必須フレーズ含有 + 禁止フレーズ（「おそらく Cloud Run と ECS の両方で…」等の曖昧推測） |
| Q3-d CI | AWS ステージング smoke 後に FAQ subset を curl/統合テスト |

**出口条件**: 評価セット 80% 以上 PASS（深掘り問）

---

### Phase Q4 — UX + ガードレール（**1–2 週間**）

**目的**: 長文技術回答の可読性と安全境界。

| タスク | 詳細 |
|--------|------|
| Q4-a 深掘り UI | Sage カード多セクション（「GCP 本番」「AWS ステージング」「デプロイ」見出し） |
| Q4-b ソース表示 | ユーザー向けに「参照: 更新履歴 / 技術ドキュメント」程度（ファイルパスは非表示） |
| Q4-c 境界 | 症状混入時は一行で相談導線へ |
| Q4-d Guardrails | Bedrock Guardrails — **Support 後**。Support 前はプロンプト + 出力サニタイズ |

### Phase Q4 追記 — チャネル別深さ（mixed 読者向け）

| チャネル | 深さ | 実装方針 |
|----------|------|----------|
| GCP/AWS Web | medium（deep モード） | 現行 architecture deep |
| LINE | 概要 → **詳しく聞かれたら medium** | deep トリガー共通、Flex 文字数に注意 |
| admin_chat | medium（deep モード） | Web と同様 |
| **多言語** | 問い合わせ言語 | 生成は日本語 SSOT 基準 → **GCP DeepL / AWS Translate** で応答言語に合わせる（既存経路） |

---

### Phase Q5 — 任意: Bedrock Agents / コード索引

| タスク | 詳細 |
|--------|------|
| Agent + Lambda | KB 再検索、CHANGELOG 差分、デプロイ revision 取得 |
| Code index | Kendra / 自前 embedding で `src/` 検索 — コスト・メンテ大のため **需要確認後** |

---

## 5. LLM 戦略（A/B 案 — Q0 で選択）

| 案 | 生成 | RAG | メリット | デメリット |
|----|------|-----|----------|------------|
| **A（現行）** | OpenAI `concierge` role | Bedrock KB retrieve | GCP 変更なし、実績あり | AWS で OpenAI 依存 |
| **B** | Bedrock Converse (Claude) | 同上 | AWS ネイティブ、Guardrails | クォータ・GCP 本番は別経路のまま |
| **C（ハイブリッド）** | env で切替 | 共通 | 段階移行 | 二重メンテ |

**推奨（暫定）**: Phase Q2 までは **A**。AWS ステージングで B をカナリア → 問題なければ AWS のみ B。

---

## 6. ドキュメント SSOT メンテナンス

| イベント | 更新対象 |
|----------|----------|
| インフラ変更 | `docs/concierge/technical/` + 該当 `docs/ops/` |
| 機能リリース | `CHANGELOG.md` → `write_changelog_digest.py` |
| AWS env 追加 | `AWS_FEATURES_ROLLOUT.md` + technical/01 |
| KB 反映 | merge 後 `sync-concierge-kb-to-s3.sh` + ingestion |

---

## 7. 成功指標（KPI）

| 指標 | 目標 |
|------|------|
| 代表 10 問 手動正答率 | ≥ 90%（深掘り ON） |
| hallucination 率（評価 YAML） | < 5%（参照外のサービス名創作なし） |
| 症状相談への誤ルーティング | 既存 IntentRouter テスト regression 0 |
| 深掘り応答 latency p95 | < 15s（OpenAI + 大プロンプト） |
| KB ingestion | job SUCCESS、chunk_count > 0 |

---

## 8. リスクと対策

| リスク | 対策 |
|--------|------|
| Titan 429 長期化 | Q1 ローカル RAG で機能継続 |
| プロンプト肥大 | deep のみ ops 全量、通常は technical/ のみ |
| 秘匿情報流出 | Q0 ホワイトリスト + Guardrails + 出力サニタイズ |
| 医療境界 blur | intent 分離 + 「症状は別途入力を」定型文 |
| doc 陳腐化 | PR チェックリストに SSOT 更新を必須化 |

---

## 9. 確認したいこと

### ✅ 回答済み（2026-07-23）

- 読者: **mixed**（チャネルで深さ調整）
- チャネル: **GCP Web / AWS Web / LINE / admin すべて**
- LLM: **OpenAI 先行 → Bedrock は Support 後**
- 深さ: **medium（~1500 字）**
- 優先: **Support 前は SSOT + ローカル RAG + 評価 + UI。Bedrock は Support 後**

### ✅ 開示ポリシー（2026-07-23 確定）

- **公開情報はすべて言及可**
- **深い情報は聞かれたときだけ**（深掘りモード）
- **env 読取に見えない出力** — 変数名・参照メタ禁止、利用者向け文言のみ

### ❓ 残り確認（任意）

計画実装の細部用。わかる範囲で結構です（下記 AskQuestion 参照）。

### ~~公開情報ホワイトリスト~~ → 上記で確定

~~次の表~~ — アーカイブ:

### 参考: 当初の質問票（アーカイブ）

1. **技術 FAQ の主な読者**は誰ですか？（複数可）
   - 開発者（自分・共同開発者）
   - 企業・行政の試験運用関係者
   - 薬剤師・登録販売者
   - β 版の一般利用者（技術に詳しくない人も含む）

2. **どのチャネルで深い IT 回答を許可しますか？**
   - Web `medicine.yutok.dev`（GCP 本番）
   - Web `aws.medicine.yutok.dev`（AWS ステージング）
   - LINE
   - 管理画面（admin_chat）

3. **公開してよい情報の下限** — 次のうち回答に **含めてよい** ものは？（含めてはいけないものも教えてください）
   - 公開 URL（medicine.yutok.dev, aws.medicine.yutok.dev, images.yutok.dev）
   - AWS アカウント ID（290780119994）
   - Bedrock KB ID / ECS サービス名
   - GitHub リポジトリ名・commit hash
   - コスト・クォータ・Support ケース ID
   - Neon / OpenAI 等のベンダー名

### B. 生成・検索基盤

4. **生成 LLM の方針** — 希望は？
   - A: OpenAI のまま（GCP/AWS 共通）
   - B: AWS ステージングのみ Bedrock Claude へ
   - C: まず A、クォータ後に B を試す（計画の暫定推奨）

5. **Amazon Q の「ツール参照」** — どこまで欲しいですか？
   - ドキュメント + CHANGELOG のみ（Phase Q1–Q2）
   - デプロイ revision / feature flags の live 参照（Phase Q3）
   - コード検索（`src/` を索引 — Phase Q5）

### C. UX・品質

6. **深掘り回答の長さ** — 許容する上限のイメージは？
   - 短め（~500 字・1 画面）
   - 中（~1500 字・カード 2–3 セクション）← 現 deep モード想定
   - 長い（Amazon Q 並み・~3000 字以上も可）

7. **多言語** — 技術 FAQ も英語 UI 時に英語で詳述しますか？（Translate 経由 vs 英語プロンプト）

8. **優先順位** — 次のどれを最優先しますか？（1 つ）
   - Support 解消 → KB RAG
   - SSOT ドキュメント充実
   - 評価自動化
   - UI（ソース表示・折りたたみ）

### D. スケジュール

9. **希望時期** — 試験運用デモ・社内説明など、いつまでに「Amazon Q 並み」と見せたい場面はありますか？

10. **Phase Q5（Bedrock Agents）** — 初期スコープに含めますか？ それとも KB + ローカル RAG で十分ですか？

---

## 10. 次のアクション

### 今すぐ（Support 不要）

1. Phase Q1 コード **commit & push**（`concierge_tech_reference.py` + 深掘り + technical docs）
2. SSOT **04–07** 草案（データ/セキュリティ、v2 フラグ、LINE 経路、監視）
3. 代表 **10 問** smoke → YAML **20 問**へ拡張
4. **チャネル別深さ**: LINE 短縮要約の実装設計

### Support 解消後のみ

5. `sync-concierge-kb-to-s3.sh` + ingestion
6. ハイブリッド RAG（KB chunk + ローカル）
7. Bedrock Guardrails / Converse カナリア（任意）

---

## 11. 関連ファイル

| ファイル | 役割 |
|----------|------|
| [concierge_tech_reference.py](../src/content/concierge_tech_reference.py) | ローカル tech 参照 |
| [concierge_agent.py](../src/agents/concierge_agent.py) | architecture / 深掘り |
| [bedrock_kb_retrieve.py](../src/services/bedrock_kb_retrieve.py) | KB RAG |
| [changelog_digest.py](../src/content/changelog_digest.py) | 更新履歴 |
| [sync-concierge-kb-to-s3.sh](../scripts/sync-concierge-kb-to-s3.sh) | KB ソース同期 |
