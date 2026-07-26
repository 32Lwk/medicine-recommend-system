# Wave A — infra_errors 分析（AWS ECS staging）

## 対象メタデータ

| 項目 | 値 |
|------|-----|
| プラットフォーム | **AWS CloudWatch / ECS staging** |
| Log Group | `/ecs/medicine-recommend` |
| Region | `ap-northeast-1` |
| ECS Service | `medicine-recommend` |
| 期間 | 2026-07-25 02:42:59 UTC 〜 2026-07-26 05:54:29 UTC（約 27 時間） |
| ログ件数 | 22,460 |
| ログストリーム | 20 本（最大 `d37e134e…` 4,133 行） |
| 重大度カウント | ERROR 76 / WARNING 174 / INFO 18,488 / DEBUG 3,722 |
| HTTP 4xx/5xx（テキスト解析） | **27 件**（400: 14 / 403: 3 / 404: 10）— **5xx: 0** |
| `text_errors` | **0 件** |
| task definition / commit | `deploy_revision.json` 上は **未検出**（`revision_timeline: []`、`metadata.json` の `task_definitions` も空） |

**解析上の注意**: CloudWatch ログには GCP 型 `httpRequest` フィールドが無い。HTTP ステータスは botocore DEBUG 行や Gunicorn アクセスログの**テキスト**から抽出している。`errors_http.json` の `method: UNKNOWN` は outbound AWS API 呼び出しが混在するため、**ユーザー向け ALB アクセスログ（Gunicorn `"GET /path HTTP/1.1" 404` 形式）と区別**すること。

---

## エグゼクティブサマリ（最大 5 点）

- **ユーザー向け HTTP 5xx は 0 件。** Gunicorn アクセスログでも 500/502/503/504 は未検出。`/health` は常に 200。
- **🟡 2026-07-25 03:33〜03:40 UTC に Bedrock Medicine KB (`30BCEJCJHA`) への `Retrieve` が AccessDenied（403×3）。** ECS タスクロール `medicine-recommend-ecs-task-role` に `bedrock:Retrieve` 権限不足。RAG フォールバックでチャットは継続しうるが、医薬品 KB 参照は失敗。
- **🟡 同一時間帯に Comprehend Medical が `comprehendmedical.ap-northeast-1` へ DNS 解決不能（NameResolutionError×36）。** リージョン未対応エンドポイントへの設定ミス。NLU 補助は WARNING 後 `None` 返却でデグラデード。
- **🟢 ERROR 76 件のうち 50 件は Gunicorn Worker SIGTERM**（19 クラスタ）。32 回の `Starting gunicorn` と同期し、ECS ローリングデプロイ/タスク入替の正常ノイズ。特に **7/26 04:00〜05:27 UTC に 13 タスク起動**（Fargate リサイズ `scripts/downsize-aws-ecs.sh` 実行タイミングと整合）。
- **🟢 HTTP 404（10 件）は bot・ブラウザ自動取得・スキャン**（`apple-touch-icon`、`/robots.txt`、`/.env`、`/h`）。400×14 の大半は **Polly outbound `/v1/speech`**（SSML ValidationException → plain text フォールバック済み）。

---

## ECS デプロイ・タスク定義境界

`deploy_revision.json` / `metadata.json` から **ECS task definition revision 番号は抽出できなかった**（ログに `GIT_COMMIT` や revision 文字列が埋め込まれていない）。代わりに Gunicorn ライフサイクルでタスク境界を推定する。

| 種別 | 典型パターン | 本ログでの件数 |
|------|-------------|---------------|
| タスク起動 | `Starting gunicorn 21.2.0` + `Workers: 2` + `UvicornWorker` | **32 回**（32 本のユニーク log stream） |
| 計画停止 | `[ERROR] Worker (pid:N) was sent SIGTERM!` | **50 件**（19 クラスタ、各 2〜4 worker） |
| Worker ローテ | `Booting worker with pid`（max_requests 等） | 158 行（定期ローテと混在） |

### デプロイ・スケール推定タイムライン（UTC）

| フェーズ | 時刻帯 | 起動回数 | SIGTERM クラスタ | 解釈 |
|---------|--------|---------|-----------------|------|
| 初回ロールアウト | 07-25 02:58 〜 03:48 | 10 | 5（03:05〜03:55） | 連続デプロイまたは desired count 増加 |
| 安定稼働 | 07-25 04:28 〜 17:36 | 3 | 3（04:36〜17:44） | 散発的タスク入替 |
| 夜間 | 07-26 00:21 〜 01:10 | 5 | 5 | 軽微な入替 |
| **密集入替** | **07-26 04:00 〜 05:27** | **13** | **5（04:08〜05:19）** | **Fargate CPU/Memory 変更またはローリングデプロイ**（`scripts/downsize-aws-ecs.sh` 参照） |

**ユーザー影響の切り分け**:

| 種別 | ログ特徴 | ユーザー影響 |
|------|---------|-------------|
| **SIGTERM（良性）** | Gunicorn ERROR、worker pid 単位、起動ログ直前後 | なし（旧タスク停止。ALB は他タスクへ振分） |
| **ユーザー向け 503** | Gunicorn アクセスログ `" 503` または `text_errors` | **本ログ期間 0 件** |

コード根拠: `start.sh` / `config/gunicorn_config.py`（Workers 2、`graceful_timeout`）、`main.py` L756–764 `@app.get("/health")`。

---

## 所見詳細

### 1. Bedrock Medicine KB AccessDenied（403） — 🟡 warning

**概要:** 医薬品 Q&A RAG 用 KB `30BCEJCJHA` への `bedrock-agent-runtime` `Retrieve` が IAM 拒否。アプリは WARNING 後空結果を返しチャット継続。

| 時刻 (UTC) | ステータス | パス（outbound） | 備考 |
|------------|-----------|-----------------|------|
| 2026-07-25 03:33:00 | 403 | `/knowledgebases/30BCEJCJHA/retrieve` | AccessDeniedException |
| 2026-07-25 03:33:08 | 403 | 同上 | リトライ |
| 2026-07-25 03:39:52 | 403 | 同上 | 別セッション |

**エビデンス:**
- `sections/errors_http.json` → `by_path`: `UNKNOWN /knowledgebases/30BCEJCJHA/retrieve (403)` ×3
- 生ログ WARNING: `Bedrock KB retrieve failed (kb=30BCEJCJHA mode=managed): … AccessDeniedException … User: arn:aws:sts::290780119994:assumed-role/medicine-recommend-ecs-task-role/6253ce3e53bb4266a19196129f92ee74 is not authorized to perform: bedrock:Retrieve on resource: arn:aws:…`
- 同一秒（03:33:00）に `Redis unavailable, cache disabled: Timeout connecting to server` — インフラ瞬断または VPC 到達性の一時問題と時間的重複

**コード根拠:**
- `src/services/bedrock_kb_retrieve.py` L125–137 — 失敗時 WARNING + 空 dict
- `config/aws_features.py` L135–136 — `BEDROCK_MEDICINE_KB_ID`
- KB ID 参照: `scripts/reflect_medicine_kb.sh`（既定 `30BCEJCJHA`）

**推奨アクション:**
1. IAM ロール `medicine-recommend-ecs-task-role` に **`bedrock:Retrieve`** を KB リソース ARN へ付与（Terraform/CloudFormation または AWS コンソール）
2. `scripts/reflect_medicine_kb.sh` / `scripts/suspend-aws-bedrock-kb.sh` と ECS タスク定義の `BEDROCK_MEDICINE_KB_ID` 整合確認
3. `/health/aws`（`main.py` L767）で `use_medicine_bedrock_kb_rag` フラグと KB ID を smoke テストに含める

---

### 2. Comprehend Medical リージョン未対応 — 🟡 warning

**概要:** `COMPREHEND_MEDICAL_ENABLED` が有効な状態で `ap-northeast-1` エンドポイントへ接続試行。Comprehend Medical は **東京リージョン非対応** のため DNS 解決失敗。

| 時刻 (UTC) | エラー種別 | 件数（DEBUG スタック含む） |
|------------|-----------|---------------------------|
| 2026-07-25 03:32:43 〜 03:39:46 | `NameResolutionError` / `EndpointConnectionError` | 72 行（WARNING 4 件） |

**エビデンス:**
- `urllib3.exceptions.NameResolutionError: AWSHTTPSConnection(host='comprehendmedical.ap-northeast-1.amazonaws.com'…)`
- WARNING: `Comprehend Medical detect_entities_v2 failed: Could not connect to the endpoint URL`（03:32:54, 03:33:08, 03:39:35 等）
- Bedrock KB 403・Redis timeout と**同一 7 分ウィンドウ**（特定セッションの AWS 依存機能が集中失敗）

**コード根拠:**
- `src/services/comprehend_medical.py` L35 — `boto3.client("comprehendmedical", region_name=get_aws_region())`
- `config/aws_features.py` L88–89, L151–152 — `COMPREHEND_MEDICAL_ENABLED` + 既定 region `ap-northeast-1`

**推奨アクション:**
1. staging では **`COMPREHEND_MEDICAL_ENABLED=0`** にするか、対応リージョン（例: `us-east-1`）向けに **`COMPREHEND_MEDICAL_REGION`** 環境変数を追加（ECS タスク定義）
2. `get_aws_region()` と Comprehend 用 region を分離する改修を `config/aws_features.py` で検討
3. 機能無効時は `/health/aws` の `is_comprehend_medical_enabled` が false であることを CI smoke で確認

---

### 3. Polly TTS SSML ValidationException（400） — 🟢 info

**概要:** outbound Polly `SynthesizeSpeech` が SSML + neural engine 組合せで 400。アプリは plain text / standard engine へフォールバック。

| 時刻 (UTC) | ステータス | パス（outbound） | 備考 |
|------------|-----------|-----------------|------|
| 2026-07-25 03:05:21 | 400 | `/v1/speech` | SSML 失敗 → plain text リトライ |
| 2026-07-25 03:18:08 〜 05:18:08 | 400 | 同上 | 計 14 件（ペアリングで 7 イベント） |

**エビデンス:**
- DEBUG: `https://polly.ap-northeast-1.amazonaws.com:443 "POST /v1/speech HTTP/1.1" 400`
- WARNING: `Polly SSML synthesis failed, retrying plain text: … ValidationException … This voice does not support the selected engine`（7 件）
- `errors_http.json` の 400×14 は **ユーザー HTTP ではなく Polly API** 応答

**コード根拠:**
- `src/services/polly_tts.py` L71–101 — SSML 失敗時 plain text → neural 失敗時 standard engine
- `config/aws_features.py` L84–85 — `use_polly_tts()`

**推奨アクション:**
1. SSML 利用時は `src/services/polly_ssml.py` で Mizuki + neural の組合せを検証（または SSML 無効化 `POLLY_SSML_ENABLED=0`）
2. 監視では outbound Polly 400 を **ユーザー 4xx と分離**（アラート対象外または DEBUG 集計）

---

### 4. Gunicorn Worker SIGTERM（デプロイノイズ） — 🟢 info

**概要:** ERROR 76 件の **65%（50/76）** が SIGTERM。ECS が旧タスクを停止する際の Gunicorn 正常ログ。

**エビデンス（SIGTERM クラスタ例）:**

| SIGTERM 時刻 (UTC) | worker 数 | 直前のタスク起動 |
|-------------------|----------|----------------|
| 2026-07-25 03:05:45 | 4 | 02:58:14 / 02:58:37 起動タスク停止 |
| 2026-07-25 03:35:14 | 4 | 03:28:14 / 03:28:33 起動タスク停止 |
| 2026-07-26 04:29:41 | 2 | 04:00〜04:28 の密集デプロイフェーズ |
| 2026-07-26 05:19:44 | 2 | 05:12:27 起動タスク停止 |

- `misc_signals.json` → `gunicorn` セクションに起動/SIGTERM ペアが記録
- 各 SIGTERM 時刻に **ユーザー向け 503/502 は伴わない**

**推奨アクション:**
- 最終レポート統合時に SIGTERM を ERROR 件数から **dedupe**（skill 指示どおり）
- （任意）Gunicorn の SIGTERM ログレベル調整 — `config/gunicorn_config.py`、優先度低

---

### 5. Neon DB SSL 切断 WARNING — 🟢 info

**概要:** 接続プール検証で SSL 切断を検出し自動再接続。恒常障害ではなく idle 切断パターン。

| 指標 | 値 |
|------|-----|
| 件数 | 30（`⚠️ Connection validation failed: SSL connection has been closed`） |
| 期間 | 2026-07-25 05:58 UTC 〜 2026-07-26 05:51 UTC（散発） |
| プール枯渇 | **0 件**（前日ログ分析で観測された `connection pool exhausted` は本窗口なし） |

**エビデンス:** `sections/db_neon.json` top_patterns に urllib3 SSL スタック。WARNING 94 件の大半は `DATABASE_URL` の `channel_binding=require` 除去 INFO/WARNING（起動時 1 回/タスク）。

**コード根拠:** `src/services/database.py` L66–122（channel_binding 正規化）、L403（検証失敗時 reconnect）

**推奨アクション:**
1. Neon ダッシュボードで同時接続数を定期確認（Workers=2 × タスク数）
2. プール枯渇再発時は `DB_MAX_CONNECTIONS`（ECS タスク定義）を見直し

---

### 6. 静的アセット・スキャナ 404 — 🟢 info

**概要:** ユーザー機能外の自動リクエスト。アプリは 404 を返却（`main.py` L522–525 で URL を WARNING ログ）。

| パス | 件数（Gunicorn アクセスログ） | 時刻例 (UTC) |
|------|------------------------------|-------------|
| `/robots.txt` | 3 | 07-25 20:11, 21:41 / 07-26 00:10 |
| `/apple-touch-icon*.png` | 4 | 07-25 02:45 / 07-26 04:39 |
| `/h` | 2 | 07-26 05:12 |
| `/.env` | 1 | 07-26 03:28（脆弱性スキャン） |

**推奨アクション:**
- `static/apple-touch-icon.png` + `static/robots.txt` 追加、または `main.py` で favicon リダイレクト（GCP dev 分析と同様）
- `/.env` 404 は正常 — WAF/ALB でスキャナ IP ブロックを検討（任意）

---

### 7. Redis キャッシュ到達不可 — 🟢 info

**概要:** KB 403 と同ウィンドウで Redis タイムアウト 2 件。キャッシュ無効化でデグラデード動作。

| 時刻 (UTC) | メッセージ |
|------------|-----------|
| 2026-07-25 03:33:00 | `Redis unavailable, cache disabled: Timeout connecting to server` |
| 2026-07-25 03:39:52 | 同上 |

**コード根拠:** `config/aws_features.py` L92–93 — `REDIS_URL`

**推奨アクション:** ElastiCache / Redis エンドポイントの SG・VPC 到達性確認。KB IAM 修正と合わせて 03:33 UTC 前後のインフラ変更を突合。

---

## 優先アクション一覧

| 優先度 | アクション | 参照 |
|--------|-----------|------|
| P1 | ECS タスクロールへ `bedrock:Retrieve`（KB `30BCEJCJHA` ARN）を付与 | IAM / `src/services/bedrock_kb_retrieve.py` |
| P2 | Comprehend Medical を staging で無効化、または us-east-1 等へ region 分離 | ECS タスク定義、`config/aws_features.py` |
| P3 | 7/26 04:00 UTC 以降の密集タスク入替が意図的か確認（downsize スクリプト実行ログ） | `scripts/downsize-aws-ecs.sh`、ECS イベント |
| P4 | 監視: ユーザー 5xx / プール枯渇のみアラート。SIGTERM・Polly outbound 400・404 は除外 | CloudWatch アラーム |
| P5 | （任意）`static/robots.txt` + apple-touch-icon で 404 ノイズ削減 | `static/`、`main.py` |

---

## 結論

**AWS ECS staging 約 27 時間、ユーザー向け HTTP 5xx は 0 件。** インフラ上の実質的懸念は **Bedrock Medicine KB の IAM AccessDenied（3 回）** と **Comprehend Medical のリージョン設定ミス**（同一時間帯）。Gunicorn SIGTERM 50 件・32 タスク起動は **7/26 早朝の密集デプロイ/リサイズを含む正常ノイズ**。503 と SIGTERM の混同は不要。task definition revision はログから特定できず — ECS コンソール / CodePipeline と手動突合が必要。
