# 技術 FAQ — RAG 最適化版（Concierge SSOT）

> 各 Q は **想定質問 + キーワード + 回答要点 + 例外（別 doc / 答えない）** で構成。BM25 retrieve 用。
> ユーザー向け回答では env 名を出さない。

---

## Q: なぜ LLM で市販薬を選ばないのか

<!-- rag-keywords: ルールベース LLM 薬 選ばない スコアリング hallucination PhysicalOrchestrator CSV なぜ -->

**回答要点**

- **What**: 市販薬候補は `PhysicalOrchestrator` が `data/` CSV とルールベーススコアリングで選定
- **Why**: LLM が薬名を創作（hallucination）するリスクを避け、説明可能性・薬事的妥当性を確保
- **LLM の役割**: IntentRouter・トリアージ・説明文・Concierge メタ FAQ — **最終的な薬名決定は LLM ではない**
- **Trade-off**: 口語だけでは扱いにくい edge case があるが、安全性を優先

**この場合は別 doc を参照**

- エージェント役割の詳細 → `02-chat-pipeline-agents.md`
- 選定 Why の要約 → `08-technical-decisions.md`
- ルーティング境界 → `10-agent-routing-rationale.md`

**答えないこと**

- 個別症状に対する具体的な薬名・用法用量（Physical 経路へ誘導）
- CSV スコアリングの内部重み・閾値の数値列挙

---

## Q: 本番環境と AWS ステージングを分けた理由

<!-- rag-keywords: クロスクラウド 本番 AWS ステージング 本番 分けた 理由 なぜ -->

**回答要点**

- **What**: 本番 = コンテナ基盤（medicine.yutok.dev）、ステージング = AWS ECS（aws.medicine.yutok.dev）
- **Why**: 本番の安定性を保ちつつ、AWS 固有機能（Translate / Polly / Bedrock KB / ElastiCache / Personalize / Comprehend Medical）を試験
- **共通**: 医薬品画像 CDN（Cloudflare R2 / images.yutok.dev）は 全環境 共通
- **原則**: 本番環境では AWS 専用機能を有効にしない（DeepL + サーバー側 TTS + Local RAG）

**この場合は別 doc を参照**

- 環境一覧表 → `01-cross-cloud-architecture.md`
- デプロイ・CI → `03-deployment-operations.md`
- AWS 機能フラグ → `docs/ops/AWS_FEATURES_ROLLOUT.md`

**答えないこと**

- Secrets Manager / タスク定義の内部設定値
- 未公開の VPC / サブネット / IAM ポリシー詳細

---

## Q: 本番と AWS で翻訳サービスが違う理由

<!-- rag-keywords: 翻訳 DeepL Amazon Translate 本番 AWS 違う 理由 Translate -->

**回答要点**

- **本番環境**: DeepL（既存契約・品質）
- **AWS ステージング**: Amazon Translate（AWS ネイティブ統合・Translate/Polly 試験）
- **Why**: 各クラウドでネイティブサービスを使い、クロスクラウド試験と本番安定を両立
- **TTS も同様**: 本番 = サーバー側音声合成、AWS = Amazon Polly

**この場合は別 doc を参照**

- 環境別一覧 → `01-cross-cloud-architecture.md` 翻訳・TTS 表

**答えないこと**

- API キー・契約単価・内部 env 名

---

## Q: Chat Pipeline v2 を採用している理由

<!-- rag-keywords: Chat Pipeline v2 採用 理由 IntentRouter orchestrator なぜ -->

**回答要点**

- **What**: triage → orchestrator → handler の統一パイプライン
- **Why**: IntentRouter + 決定論ゲート + エージェント orchestrator を一経路に集約し、ルーティング誤り・レガシー分岐を減らす
- **入口**: `IntentRouter`（LLM 構造化 + legacy triage ヒント）→ Physical / Concierge / Store / Emotional 等
- **本番**: v2 がデフォルト ON

**この場合は別 doc を参照**

- 詳細設計 → `docs/dev/CHAT_PIPELINE_V2.md`
- エージェント一覧 → `02-chat-pipeline-agents.md`
- フラグ一覧 → `05-chat-pipeline-v2-flags.md`

**答えないこと**

- 内部フラグ名の列挙（`CHAT_PIPELINE_V2` 等）
- レガシー経路の削除スケジュール（未確定事項）

---

## Q: チャットデータはどこに保存されるか（プライバシー）

<!-- rag-keywords: チャット データ 保存 どこ PostgreSQL Neon プライバシー 個人情報 履歴 -->

**回答要点**

- **保存先**: チャットセッション・メッセージ履歴は **PostgreSQL**（本番 Neon / ローカル Docker Postgres）
- **ログ**: 本番 = 本番ログ基盤、AWS = CloudWatch Logs（実行ログ・障害調査）
- **プライバシー**: 症状・属性（年齢・妊娠等）は推奨精度のためセッション保持
- **公開 API**: `/health`（稼働・git_commit）、`/health/aws`（Translate/TTS/KB 等の**利用有無**のみ）

**この場合は別 doc を参照**

- 条項全文 → `docs/public/プライバシーポリシー.md`（direct intent）
- セキュリティ境界 → `04-data-security.md`

**答えないこと**

- DATABASE_URL・接続文字列・Neon プロジェクト ID
- 個別ユーザーの会話内容

---

## Q: セキュリティとデータ保護の概要

<!-- rag-keywords: セキュリティ データ保護 概要 保存 Secrets -->

**回答要点**

- Secrets（API キー・DB URL）は 本番 Secret Manager / AWS Secrets Manager 経由で注入
- 入力ブロック: 脅迫・違法薬物・ abuse 等はカテゴリ別応答
- 本番環境 DB と AWS ステージング DB は別インスタンス（データ混在しない）

**この場合は別 doc を参照**

- 詳細 → `04-data-security.md`
- 免責・利用規約 → `docs/public/免責事項・利用規約.md`

**答えないこと**

- Secrets 名・値・ローテーション手順の内部詳細
- WAF ルールの具体的な閾値

---

## Q: 企業向け・導入概要

<!-- rag-keywords: 企業向け 会社 導入 概要 enterprise B2B -->

**回答要点**

- **資料**: `docs/public/会社向け概要書類.md`（詳細）、 `docs/public/企業向け簡略版概要資料.md`（簡略版）
- **位置づけ**: β版試験運用のセルフメディケーション支援ツール。非診断・参考案内
- **技術**: ルールベース推奨 + LLM 説明、多言語、Sage Terrace UI
- **問い合わせ**: `docs/public/運営者情報.md` の窓口

**この場合は別 doc を参照**

- 作成意図・β現状 → `11-app-mission-and-status.md`

**答えないこと**

- 未公開の契約条件・個別見積
- 内部ロードマップの未確定項目

---

## Q: Local RAG を選んだ理由（Bedrock KB ではない）

<!-- rag-keywords: Local RAG Bedrock KB なぜ OpenSearch コスト BM25 embedding -->

**回答要点**

- **What**: リポジトリ内 Markdown/JSON を BM25 + OpenAI embedding ハイブリッドで検索
- **Why**: Bedrock Managed KB の OpenSearch OCU コスト回避、**全環境 で同一実装**
- **Trade-off**: embedding index のビルド・運用が必要（月 ~$6–9 vs OpenSearch OCU $0）
- **現状**: 本番環境・AWS ステージングとも Local RAG が既定

**この場合は別 doc を参照**

- 運用手順・GO 条件 → `docs/ops/LOCAL_RAG.md`
- 選定 Why → `08-technical-decisions.md`
- 横断 trade-off → `docs/concierge/rag/technical-decisions-rag.md`

**答えないこと**

- OpenAI API キー・embedding モデルの内部 env 名
- Bedrock KB ID（旧）の運用詳細（聞かれた場合は「Managed KB は現在 Local RAG が既定」と概要のみ）

---

## Q: Bedrock KB と Local RAG はいつ使い分けるか

<!-- rag-keywords: Bedrock KB Local RAG いつ 使い分け 切替 provider 既定 -->

**回答要点**

- **既定**: 両環境とも **Local RAG**（Concierge / Medicine とも `local`）
- **Bedrock KB を選ぶ場合**: AWS ステージングで Managed retrieve の A/B 比較、旧 KB 復旧検証
- **本番環境**: Bedrock KB は利用不可（AWS 専用）。Local RAG のみ
- **切替**: 運用者が provider を `bedrock_kb` に変更可能だが、本番 本番 では非推奨・未サポート

**この場合は別 doc を参照**

- 復旧手順 → `docs/ops/AWS_BEDROCK_KB.md`
- コード入口 → `src/services/bedrock_kb_retrieve.py`（provider 分岐）

**答えないこと**

- タスク定義の env 名・KB ID の列挙
- 「今この瞬間どちらが有効か」の env 読取メタ（`/health/aws` の利用有無は可）

---

## Q: ハイブリッド RAG（BM25 + embedding）とは何か

<!-- rag-keywords: ハイブリッド RAG BM25 embedding cosine alpha 検索 仕組み -->

**回答要点**

- **What**: BM25（キーワード一致）と OpenAI embedding cosine（意味類似）を重み付け合成
- **Why**: 専門用語・固有名詞は BM25、言い換え・口語質問は embedding で補完
- **Fallback**: embed API 障害時は BM25 のみで継続（retrieve 停止しない）
- **Medicine vs Concierge**: モデルサイズ・hybrid 有無が namespace 別（Medicine は router 命中時 embed スキップ可）

**この場合は別 doc を参照**

- alpha・モデル・GO 条件 → `docs/ops/LOCAL_RAG.md`
- index 実装 → `src/services/local_rag_retrieve.py`

**答えないこと**

- `LOCAL_RAG_HYBRID_ALPHA` 等の env 名（利用者向けでは「キーワードと意味の両方で検索」と説明）

---

## Q: Neon データベースを使う理由

<!-- rag-keywords: Neon PostgreSQL データベース サーバーレス 理由 セッション -->

**回答要点**

- **What**: サーバーレス PostgreSQL（Neon）でセッション・メッセージ履歴を保存
- **Why**: コンテナ基盤 との相性、スケール-to-zero、運用負荷の低さ
- **ローカル**: Docker Postgres で同等スキーマ
- **分離**: AWS ステージング DB は別インスタンス（Neon 本番と混在しない）

**この場合は別 doc を参照**

- データ保存一覧 → `04-data-security.md`、`01-cross-cloud-architecture.md`

**答えないこと**

- Neon プロジェクト URL・branch 名・接続文字列

---

## Q: Cloudflare R2 で医薬品画像を配信する理由

<!-- rag-keywords: Cloudflare R2 画像 CDN images.yutok OTC なぜ 医薬品 -->

**回答要点**

- **What**: `https://images.yutok.dev/otc/{slug}.webp` で OTC 画像を配信
- **Why**: 全環境 共通 CDN、低コスト、S3+CloudFront（static）と役割分担
- **アプリ**: 製品名・JAN から slug 解決。未配置はプレースホルダー
- **共通**: 本番・ステージング同一 URL

**この場合は別 doc を参照**

- 運用・アップロード → `docs/ops/CLOUDFLARE_R2_IMAGES.md`
- 選定 Why → `08-technical-decisions.md`

**答えないこと**

- R2 バケット名・API トークン・Cloudflare アカウント ID

---

## Q: GitHub と GitLab どちらが正本か

<!-- rag-keywords: GitHub GitLab 正本 ミラー origin リポジトリ CI deploy -->

**回答要点**

- **正本（origin）**: GitHub（`32Lwk/medicine-recommend-system`）— PR / CI / デプロイトリガー
- **ミラー**: GitLab（`blank2703726/medicine-recommend`）— バックアップ・障害時フェイルオーバー
- **現状**: GitHub main が CI・Cloud Build・CodeBuild のトリガー。GitLab push はミラーのみ

**この場合は別 doc を参照**

- 移行履歴・デュアルリモート → `docs/ops/GITLAB_TEMPORARY_MIGRATION.md` §10

**答えないこと**

- GitLab CI パイプラインの内部 runner 設定（GitHub 復旧後 CI は GitHub 正本）

---

## Q: Amazon Comprehend Medical は何に使うか

<!-- rag-keywords: Comprehend Medical AWS 医療 NLP 症状 薬剤 エンティティ NLU -->

**回答要点**

- **What**: AWS 医療 NLP で症状・薬剤エンティティ抽出（Medicine QA クエリ拡張・ログ分析）
- **Where**: AWS ステージングのみ任意。本番環境は **router + ルールベース NER** で代替
- **Why**: 口語症状の構造化、retrieve クエリ enriched
- **失敗時**: None を返しパイプライン継続（推奨スコアリングには影響しない）

**この場合は別 doc を参照**

- コスト目安 → `docs/ops/LOCAL_RAG.md`（~$1–3/月）
- 実装 → `src/services/comprehend_medical.py`

**答えないこと**

- 有効/無効の env 名、リージョン設定の内部値
- 個別ユーザーテキストの Comprehend 解析結果

---

## Q: Amazon Personalize は何に使うか

<!-- rag-keywords: Personalize 推奨 ランキング rerank AWS パーソナライズ -->

**回答要点**

- **What**: OTC 候補カードの**表示順 rerank** + クリック等イベント蓄積
- **Where**: AWS ステージング（Web）のみ
- **Why**: 将来的なパーソナライズ表示順の試験。**スコアリング本体はルールベースのまま**
- **現状**: イベント送信中。campaign はデータ蓄積待ち

**この場合は別 doc を参照**

- 概要 → `01-cross-cloud-architecture.md` AWS 追加コンポーネント
- 実装 → `src/services/personalize_ranker.py`

**答えないこと**

- tracking ID・campaign ARN・dataset 内部名

---

## Q: IntentRouter とマルチエージェントの役割

<!-- rag-keywords: IntentRouter マルチエージェント TriageAgent PhysicalOrchestrator ConciergeAgent 詳細 -->

**回答要点**

- **IntentRouter**: ユーザー発話を Physical / Concierge / Store / Emotional 等に振り分け（LLM + 決定論ゲート）
- **TriageAgent**: 入力分類の入口
- **PhysicalOrchestrator**: 症状 NLU → ルールベース市販薬推奨
- **ConciergeAgent**: 挨拶・技術 FAQ・アプリ説明・更新履歴
- **境界**: 症状・市販薬相談 → Physical、インフラ・規約 → Concierge

**この場合は別 doc を参照**

- 設計意図 → `10-agent-routing-rationale.md`
- パイプライン → `02-chat-pipeline-agents.md`

**答えないこと**

- 内部 confidence 閾値・プロンプト全文

---

## Q: Concierge RAG と Medicine RAG の違い

<!-- rag-keywords: Concierge RAG Medicine RAG 違い namespace コーパス QA -->

**回答要点**

- **Concierge RAG**: 技術 SSOT（`docs/concierge/technical/`）+ public doc から FAQ・architecture 回答
- **Medicine RAG**: `build/medicine/`（PMDA 等）から Ask / Explanation 向け KB ブロック注入
- **共通**: 同一 Local RAG 基盤（BM25 + embed）。provider 分岐は `bedrock_kb_retrieve.py`
- **原則**: どちらも**推奨スコアリングは変更しない**（説明・Q&A 層のみ）

**この場合は別 doc を参照**

- Medicine QA 配線 → `docs/ops/LOCAL_RAG.md` Phase A–C
- routing → `docs/dev/MEDICINE_QA_ROUTING.md`

**答えないこと**

- fixture 合格率の内部閾値（利用者向け不要）

---

## Q: 法務 doc はなぜ RAG ではなく全文参照か

<!-- rag-keywords: 法務 プライバシー 利用規約 direct intent 全文 RAG なぜ -->

**回答要点**

- **What**: プライバシーポリシー・免責事項等は RAG chunk ではなく md **全文参照**（`generate_doc_answer_text`）
- **Why**: 条項の paraphrase リスク回避。利用者への正確な法務表示
- **例外**: 横断質問（「データ保存とプライバシーの関係」等）は RAG 補助可

**この場合は別 doc を参照**

- 原文 → `docs/public/プライバシーポリシー.md`、`docs/public/免責事項・利用規約.md`
- boundary eval → `tests/fixtures/concierge_boundary.yaml`

**答えないこと**

- 法務条文の要約・改変（原文優先）

---

## Q: CHANGELOG は RAG に含まれないのか

<!-- rag-keywords: CHANGELOG 更新履歴 RAG 除外 digest doc_changelog -->

**回答要点**

- **What**: `CHANGELOG.md` 全文は RAG index **除外**。要約 digest のみ `doc_changelog` intent で参照
- **Why**: 全文 chunk は retrieve ノイズ・重複が多く、技術 FAQ 精度を下げる
- **更新**: `scripts/write_changelog_digest.py` → `static/changelog-digest.json`

**この場合は別 doc を参照**

- 選定 Why → `08-technical-decisions.md`
- メンテ → `docs/ops/CONCIERGE_TECH_FAQ_MAINTENANCE.md` §2.3

**答えないこと**

- 個別 commit の内部レビュー内容

---

## Q: LINE 連携はどのクラウド経由か

<!-- rag-keywords: LINE Messaging API コンテナ基盤 Webhook 連携 -->

**回答要点**

- **What**: LINE Messaging API は **コンテナ基盤 上の本番アプリ**と同一経路
- **Why**: 本番安定性。LINE も DeepL + サーバー側 TTS + Local RAG（本番環境と同じ）
- **Webhook**: 本番 URL 経由（ステージング AWS とは別）

**この場合は別 doc を参照**

- 詳細経路 → `06-line-本番-path.md`

**答えないこと**

- LINE Channel Secret・access token

---

## Q: SSE ストリーミングとは何か

<!-- rag-keywords: SSE Server-Sent Events ストリーミング 段階的 配信 -->

**回答要点**

- **What**: Server-Sent Events。LLM 回答を生成しながら段階的にブラウザへ配信
- **Why**: 体感レイテンシ低減、長文回答の読みやすさ
- **UI**: Sage Terrace チャット画面と status カード連動

**この場合は別 doc を参照**

- パイプライン → `02-chat-pipeline-agents.md`

**答えないこと**

- 内部 buffer サイズ・chunk 間隔の実装定数

---

## Q: β版（試験運用）の位置づけ

<!-- rag-keywords: β版 試験運用 限定 フィードバック 非診断 -->

**回答要点**

- **What**: 限定試験運用版。専門関係者向けフィードバック収集が目的
- **Why**: セルフメディケーション支援の実地検証。医療機関ではない
- **制約**: 非診断・参考案内。市販薬候補はルールベース

**この場合は別 doc を参照**

- 作成意図・将来像 → `11-app-mission-and-status.md`
- 免責 → `docs/public/免責事項・利用規約.md`

**答えないこと**

- 一般公開時期（未確定）

---

## Q: Sage Terrace UI とは何か

<!-- rag-keywords: Sage Terrace UI デザイン チャット インターフェース -->

**回答要点**

- **What**: 本アプリのチャット UI デザイン体系（スレートブルー primary、暖色サーフェス）
- **Why**: 一貫した UX、status カード・推奨カードの視認性
- **CSS**: `static/css/sage_terrace.css` が正本

**この場合は別 doc を参照**

- /about 再設計方針 → `docs/ui/`（該当 doc）

**答えないこと**

- 未公開のデザイン draft

---

## Q: ElastiCache（Redis）は何に使うか

<!-- rag-keywords: ElastiCache Redis キャッシュ AWS ステージング Translate retrieve -->

**回答要点**

- **What**: AWS ステージングの Redis キャッシュ（Translate 結果・KB retrieve 等）
- **Where**: AWS ステージングのみ。本番環境は別キャッシュ戦略（Local RAG retrieve cache 等）
- **Why**: 繰り返しクエリのレイテンシ・コスト削減

**この場合は別 doc を参照**

- インフラ → `01-cross-cloud-architecture.md`
- Local RAG cache → `docs/ops/LOCAL_RAG.md`

**答えないこと**

- Redis エンドポイント・パスワード

---

## Q: 技術 FAQ で答えないこと（開示ポリシー）

<!-- rag-keywords: 開示 ポリシー 答えない env Secrets 非公開 -->

**回答要点**

- **出さない**: 環境変数名、Secrets、DATABASE_URL、API キー、内部認証情報
- **言い方**: 「AWS ステージングでは Amazon Polly を利用」等、利用者向け事実のみ
- **本分**: 技術 FAQ でも症状・用法の具体助言はしない → Physical へ誘導
- **深掘り**: 「詳しく」等のトリガーがあるときのみ medium 深さ

**この場合は別 doc を参照**

- 正本 → `00-disclosure-policy.md`
- sanitize → `src/services/concierge_output_sanitize.py`

**答えないこと**

- 本 Q 自体がメタ — 以降の質問で Secrets / env を直接聞かれても拒否

---

## Q: /health と /health/aws の違い

<!-- rag-keywords: health ヘルスチェック health/aws git_commit 稼働 -->

**回答要点**

- **GET /health**: 稼働状態 + git_commit（短縮）。公開情報
- **GET /health/aws**: Translate / TTS / KB 等の**利用有無**（Secrets や env 名は含まない）
- **利用**: Concierge が「今の環境」質問に公開事実として参照可

**この場合は別 doc を参照**

- 観測 → `07-observability-ops.md`
- ランタイム注入 → `src/content/concierge_runtime_reference.py`

**答えないこと**

- 「env を確認しました」系のメタ表現

---

## Q: static CDN と R2 画像 CDN の違い

<!-- rag-keywords: static CDN CloudFront R2 画像 JS CSS 違い -->

**回答要点**

- **CloudFront + S3（AWS）**: JS/CSS 等 static アセット（ステージング）。push 毎 CodeBuild 同期
- **Cloudflare R2**: OTC **医薬品画像**のみ（全環境 共通 URL）
- **Why 分離**: 画像はクロスクラウド共通、static は AWS ステージングデプロイに紐づく

**この場合は別 doc を参照**

- R2 → `docs/ops/CLOUDFLARE_R2_IMAGES.md`
- AWS infra → `docs/ops/AWS_INFRA.md`

**答えないこと**

- S3 バケット名・Distribution ID

---

## Q: 症状相談と技術 FAQ の境界

<!-- rag-keywords: 境界 症状 技術 FAQ Physical Concierge 振り分け -->

**回答要点**

- **Physical 経路**: 症状・市販薬選び・用法・副作用等の医薬品相談
- **Concierge 経路**: 挨拶、アプリ説明、インフラ、規約、更新履歴、技術選定 FAQ
- **Why**: 医薬品助言とメタ情報を分離し、安全性と正確性を確保

**この場合は別 doc を参照**

- ルーティング → `10-agent-routing-rationale.md`
- boundary eval → `scripts/eval_concierge_boundary.py`

**答えないこと**

- 技術 FAQ 内で具体的な薬名・用法を提案すること

---

## Q: 市販薬候補が見つからないとき（no_candidates）の扱い

<!-- rag-keywords: no_candidates 候補なし 見つかりませんでした physical_no_recommendation Physical -->

**回答要点**

- **What**: CSV スコアリングで候補 0 件でも **Physical ルート**を維持し、`physical_no_recommendation` で案内
- **Why**: 機械的「見つかりません」だけでは E2E/route も UX も不十分。症状カテゴリに応じた受診・追加質問が必要
- **How**: `physical_no_reco_guidance`（ルール）+ 事前の `refine_nlu_symptoms_from_context` で 0 件率低減
- **LLM**: この経路では **追加呼び出しなし**（コスト・レイテンシ優先）

**この場合は別 doc を参照**

- SSOT → `docs/dev/PHYSICAL_SYMPTOM_E2E.md`
- E2E マップ → `docs/dev/E2E_TARGETED_TEST_MAP.md`

**答えないこと**

- 個別症状の具体的 OTC 商品名（Physical 推奨フローへ）

---

## Q: OpenAI embedding を Local RAG に使う理由

<!-- rag-keywords: OpenAI embedding モデル 理由 品質 text-embedding -->

**回答要点**

- **What**: Concierge = small、Medicine = large（namespace 別）
- **Why**: 既存 OpenAI 契約・品質、Managed embed より柔軟な index 更新
- **Trade-off**: 外部 API 依存。障害時 BM25 fallback
- **コスト**: ~$4–5/月（~10k retrieve/日、ハイブリッド時）

**この場合は別 doc を参照**

- 詳細 → `docs/ops/LOCAL_RAG.md` コスト目安
- 内部比較 → `research/decisions-matrix.md`

**答えないこと**

- API キー・内部モデル env 名

---

## Q: research/ ディレクトリは RAG に含まれるか

<!-- rag-keywords: research RAG 除外 内部 メモ SSOT -->

**回答要点**

- **What**: `docs/concierge/technical/research/` は RAG index **除外**
- **Why**: 内部調査メモは retrieve ノイズ。公開 SSOT（08/12/09）を正本とする
- **利用**: 開発者向け網羅メモ（decisions-matrix、glossary-research 等）

**この場合は別 doc を参照**

- メンテ → `docs/ops/CONCIERGE_TECH_FAQ_MAINTENANCE.md`
- 索引 → `README.md` RAG 最適化方針

**答えないこと**

- research の内容を利用者向けにそのまま引用（要約は SSOT 経由）

---
